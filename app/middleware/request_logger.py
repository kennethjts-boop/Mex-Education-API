import os
import time
import json
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.db.supabase import supabase_client, is_supabase_configured
from app.middleware.metrics import system_metrics
from datetime import datetime

logger = logging.getLogger("uvicorn.error")

class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        
        # Inicializar variables por defecto en request.state
        request.state.tokens_input = 0
        request.state.tokens_output = 0
        request.state.estimated_cost = 0.0
        
        request.state.is_search_request = False
        request.state.is_generation_request = False
        request.state.retrieval_success = False
        request.state.fallback_used = False

        try:
            response = await call_next(request)
            success = response.status_code < 400
        except Exception as e:
            success = False
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            self._log_request(request, latency_ms, success)
            raise e

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        cost = getattr(request.state, "estimated_cost", 0.0)
        
        # 1. Registrar métricas agregadas en memoria para endpoints /metrics
        system_metrics.record_request(
            endpoint=request.url.path,
            latency_ms=latency_ms,
            success=success,
            cost=cost
        )
        
        if getattr(request.state, "is_search_request", False):
            system_metrics.record_search(
                retrieval_success=getattr(request.state, "retrieval_success", False)
            )
        elif getattr(request.state, "is_generation_request", False):
            system_metrics.record_generation(
                retrieval_success=getattr(request.state, "retrieval_success", False),
                fallback_used=getattr(request.state, "fallback_used", False),
                latency_ms=latency_ms
            )

        # 2. Guardar log detallado en Supabase o archivo local
        self._log_request(request, latency_ms, success)
        
        return response

    def _log_request(self, request: Request, latency_ms: float, success: bool):
        endpoint = request.url.path
        
        # Evitar loguear métricas internas y health checks recurrentes para evitar spam
        if endpoint in ["/metrics/health", "/metrics/generations", "/health", "/"]:
            return
            
        tokens_input = getattr(request.state, "tokens_input", 0)
        tokens_output = getattr(request.state, "tokens_output", 0)
        estimated_cost = getattr(request.state, "estimated_cost", 0.0)
        
        record = {
            "endpoint": endpoint,
            "execution_ms": round(latency_ms, 2),
            "success": success,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "estimated_cost": float(estimated_cost),
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase_ready = is_supabase_configured and supabase_client is not None
        if supabase_ready:
            try:
                supabase_client.table("request_logs").insert(record).execute()
                return
            except Exception as e:
                logger.error(f"Error escribiendo request_log en Supabase: {e}. Guardando localmente.")
                
        # Persistencia local fallback en data/request_logs.json
        local_dir = "./data"
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, "request_logs.json")
        
        logs = []
        if os.path.exists(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                    if not isinstance(logs, list):
                        logs = []
            except Exception:
                logs = []
                
        record["id"] = f"simulated-log-uuid-{len(logs)}"
        logs.append(record)
        
        # Limitar los logs locales en disco a los últimos 500 para control de tamaño
        if len(logs) > 500:
            logs = logs[-500:]
            
        try:
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"No se pudo escribir request_log en archivo local: {e}")
