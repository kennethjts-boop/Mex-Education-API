import threading
from typing import Dict, Any

class SystemMetrics:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(SystemMetrics, cls).__new__(cls)
                    cls._instance._init_metrics()
        return cls._instance

    def _init_metrics(self):
        self.lock = threading.Lock()
        
        # Métricas generales de salud
        self.total_requests = 0
        self.successful_requests = 0
        self.total_latency_ms = 0.0
        self.total_cost = 0.0
        
        # Métricas de búsqueda y RAG
        self.total_search_requests = 0
        self.retrieval_successes = 0
        
        # Métricas de generación
        self.total_planeaciones = 0
        self.retrieval_failures = 0
        self.fallback_usages = 0
        self.total_planeacion_latency_ms = 0.0

    def record_request(self, endpoint: str, latency_ms: float, success: bool, cost: float = 0.0):
        with self.lock:
            self.total_requests += 1
            if success:
                self.successful_requests += 1
            self.total_latency_ms += latency_ms
            self.total_cost += cost

    def record_search(self, retrieval_success: bool):
        with self.lock:
            self.total_search_requests += 1
            if retrieval_success:
                self.retrieval_successes += 1

    def record_generation(self, retrieval_success: bool, fallback_used: bool, latency_ms: float):
        with self.lock:
            self.total_planeaciones += 1
            self.total_planeacion_latency_ms += latency_ms
            if not retrieval_success:
                self.retrieval_failures += 1
                if fallback_used:
                    self.fallback_usages += 1

    def get_health_metrics(self) -> Dict[str, Any]:
        with self.lock:
            avg_latency = (self.total_latency_ms / self.total_requests) if self.total_requests > 0 else 0.0
            success_rate = (self.successful_requests / self.total_requests) if self.total_requests > 0 else 0.0
            avg_cost = (self.total_cost / self.total_requests) if self.total_requests > 0 else 0.0
            
            # Tasa de éxito en recuperación (de todas las búsquedas RAG o generaciones)
            total_retrieval_attempts = self.total_search_requests + self.total_planeaciones
            successful_retrievals = self.retrieval_successes + (self.total_planeaciones - self.retrieval_failures)
            retrieval_rate = (successful_retrievals / total_retrieval_attempts) if total_retrieval_attempts > 0 else 0.0
            
            return {
                "avg_latency_ms": round(avg_latency, 2),
                "total_requests": self.total_requests,
                "success_rate": round(success_rate * 100, 2),
                "average_cost_usd": round(avg_cost, 6),
                "retrieval_success_rate": round(retrieval_rate * 100, 2)
            }

    def get_generation_metrics(self) -> Dict[str, Any]:
        with self.lock:
            avg_gen_latency = (self.total_planeacion_latency_ms / self.total_planeaciones) if self.total_planeaciones > 0 else 0.0
            return {
                "total_planeaciones": self.total_planeaciones,
                "retrieval_failures": self.retrieval_failures,
                "average_response_time_ms": round(avg_gen_latency, 2),
                "curriculum_fallback_usage": self.fallback_usages
            }

# Instancia global de métricas
system_metrics = SystemMetrics()
