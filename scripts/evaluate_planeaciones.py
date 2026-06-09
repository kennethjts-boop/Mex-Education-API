#!/usr/bin/env python3
import os
import sys
import time
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime

# Añadir el directorio raíz al sys.path para poder importar módulos de la app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.evaluation_service import calculate_heuristic_score

# Configuración por defecto
DEFAULT_BASE_URL = "http://127.0.0.1:8001"

def percentile(values, p):
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)

def evaluate_run(base_url: str, payload: dict) -> dict:
    """
    Envía una petición de generación a la API, mide tiempos,
    recupera metadatos y calcula la evaluación de calidad.
    """
    url = f"{base_url}/planeaciones/generar"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    start_time = time.perf_counter()
    status_code = 0
    response_body = ""
    error_msg = ""
    
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            status_code = response.status
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        status_code = e.code
        response_body = e.read().decode("utf-8")
    except Exception as e:
        status_code = 500
        error_msg = str(e)
        
    latency_ms = (time.perf_counter() - start_time) * 1000.0
    
    # Valores por defecto para fallo
    eval_result = {
        "tema": payload["tema"],
        "grado": payload["grado"],
        "campo_formativo": payload["campo_formativo"],
        "duracion_dias": payload["duracion_dias"],
        "success": False,
        "status_code": status_code,
        "latency_ms": round(latency_ms, 2),
        "cache_hit": False,
        "chunks_count": 0,
        "context_chars": 0,
        "retrieval_success": False,
        "fallback_usage": False,
        "response_length_chars": 0,
        "score": 0.0,
        "notes": "Error de comunicación o error interno del servidor.",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if status_code == 200 and response_body:
        try:
            res_json = json.loads(response_body)
            planeacion = res_json.get("planeacion", {})
            retrieval_success = res_json.get("retrieval_success", False)
            structured_curriculum_success = res_json.get("structured_curriculum_success", False)
            fallback_usage = (not retrieval_success and structured_curriculum_success)
            
            metadata = res_json.get("metadata", {})
            server_latency_ms = metadata.get("latency_ms", latency_ms)
            cache_hit = metadata.get("cache_hit", False)
            chunks_count = metadata.get("chunks_count", 0)
            context_chars = metadata.get("context_chars", 0)
            
            # Calcular score heurístico local
            score, notes = calculate_heuristic_score(planeacion, payload["duracion_dias"])
            
            eval_result.update({
                "success": True,
                "retrieval_success": retrieval_success,
                "fallback_usage": fallback_usage,
                "response_length_chars": len(response_body),
                "score": score,
                "notes": notes,
                "latency_ms": round(server_latency_ms, 2),
                "cache_hit": cache_hit,
                "chunks_count": chunks_count,
                "context_chars": context_chars
            })
        except Exception as e:
            eval_result["notes"] = f"Error parseando respuesta JSON exitosa: {e}"
            
    elif status_code == 400 and response_body:
        try:
            res_json = json.loads(response_body)
            detail = res_json.get("detail", "Error 400.")
            eval_result["notes"] = f"Rechazado por política de seguridad: {detail}"
        except Exception:
            eval_result["notes"] = f"Rechazado por política de seguridad (No-Inventar)."
            
    elif error_msg:
        eval_result["notes"] = f"Error de conexión: {error_msg}"
        
    return eval_result

def main():
    parser = argparse.ArgumentParser(description="Script para evaluación automática de calidad de planeaciones en lote.")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help="URL base del servidor FastAPI.")
    args = parser.parse_args()
    
    base_url = args.url
    
    # 1. Definición de las 25 combinaciones de prueba abarcando los 10 temas requeridos
    test_runs = [
        # Tema: energía solar (Debe tener éxito por seed curricular grado 2)
        {"tema": "energía solar", "grado": "2", "nivel": "Secundaria", "campo_formativo": "Saberes y Pensamiento Científico", "duracion_dias": 5},
        {"tema": "energía solar y sustentabilidad", "grado": "2", "nivel": "Secundaria", "campo_formativo": "Saberes y Pensamiento Científico", "duracion_dias": 5},
        {"tema": "energía solar", "grado": "3", "nivel": "Secundaria", "campo_formativo": "Saberes y Pensamiento Científico", "duracion_dias": 8}, # Falla (grado 3)
        {"tema": "energía solar", "grado": "1", "nivel": "Secundaria", "campo_formativo": "Saberes y Pensamiento Científico", "duracion_dias": 3}, # Falla (grado 1)
        
        # Tema: reciclaje (Debe tener éxito usando 'sustentable' en grado 2)
        {"tema": "reciclaje sustentable", "grado": "2", "nivel": "Secundaria", "campo_formativo": "Ética, Naturaleza y Sociedades", "duracion_dias": 5},
        {"tema": "reciclaje y ecosistemas", "grado": "2", "nivel": "Secundaria", "campo_formativo": "Ética, Naturaleza y Sociedades", "duracion_dias": 4},
        {"tema": "reciclaje", "grado": "1", "nivel": "Secundaria", "campo_formativo": "Ética, Naturaleza y Sociedades", "duracion_dias": 3}, # Falla
        
        # Tema: biodiversidad (Debe tener éxito usando 'ecosistemas' en grado 2)
        {"tema": "biodiversidad y ecosistemas", "grado": "2", "nivel": "Secundaria", "campo_formativo": "Ética, Naturaleza y Sociedades", "duracion_dias": 5},
        {"tema": "preservación de la biodiversidad", "grado": "2", "nivel": "Secundaria", "campo_formativo": "Ética, Naturaleza y Sociedades", "duracion_dias": 5},
        {"tema": "biodiversidad", "grado": "3", "nivel": "Secundaria", "campo_formativo": "Saberes y Pensamiento Científico", "duracion_dias": 5}, # Falla
        
        # Tema: violencia (Debe fallar - No hay contexto)
        {"tema": "violencia escolar", "grado": "3", "nivel": "Secundaria", "campo_formativo": "Ética, Naturaleza y Sociedades", "duracion_dias": 4},
        {"tema": "violencia familiar", "grado": "2", "nivel": "Secundaria", "campo_formativo": "Ética, Naturaleza y Sociedades", "duracion_dias": 5},
        
        # Tema: salud (Debe fallar - No hay contexto)
        {"tema": "salud comunitaria", "grado": "2", "nivel": "Secundaria", "campo_formativo": "De lo Humano y lo Comunitario", "duracion_dias": 5},
        {"tema": "salud y nutrición", "grado": "3", "nivel": "Secundaria", "campo_formativo": "De lo Humano y lo Comunitario", "duracion_dias": 6},
        
        # Tema: migración (Debe fallar - No hay contexto)
        {"tema": "migración en México", "grado": "3", "nivel": "Secundaria", "campo_formativo": "Ética, Naturaleza y Sociedades", "duracion_dias": 5},
        {"tema": "migración y cultura", "grado": "1", "nivel": "Secundaria", "campo_formativo": "Ética, Naturaleza y Sociedades", "duracion_dias": 3},
        
        # Tema: alimentación (Debe fallar - No hay contexto)
        {"tema": "alimentación saludable", "grado": "2", "nivel": "Secundaria", "campo_formativo": "De lo Humano y lo Comunitario", "duracion_dias": 5},
        
        # Tema: matemáticas (Debe tener éxito usando 'proporcionalidad' o 'gráficas' en grado 2)
        {"tema": "proporcionalidad matemática", "grado": "2", "nivel": "Secundaria", "campo_formativo": "Saberes y Pensamiento Científico", "duracion_dias": 5},
        {"tema": "gráficas matemáticas", "grado": "2", "nivel": "Secundaria", "campo_formativo": "Saberes y Pensamiento Científico", "duracion_dias": 5},
        {"tema": "matemáticas puras", "grado": "1", "nivel": "Secundaria", "campo_formativo": "Saberes y Pensamiento Científico", "duracion_dias": 5}, # Falla
        
        # Tema: lectura (Debe tener éxito usando 'lenguas' o 'comunicación' en grado 2)
        {"tema": "lectura y lenguas de México", "grado": "2", "nivel": "Secundaria", "campo_formativo": "Lenguajes", "duracion_dias": 5},
        {"tema": "lectura en comunicación familiar", "grado": "2", "nivel": "Secundaria", "campo_formativo": "Lenguajes", "duracion_dias": 5},
        {"tema": "lectura libre", "grado": "1", "nivel": "Secundaria", "campo_formativo": "Lenguajes", "duracion_dias": 4}, # Falla
        
        # Tema: comunidad (Debe tener éxito en grado 2)
        {"tema": "comunidad escolar", "grado": "2", "nivel": "Secundaria", "campo_formativo": "De lo Humano y lo Comunitario", "duracion_dias": 5},
        {"tema": "comunidad y lenguas", "grado": "2", "nivel": "Secundaria", "campo_formativo": "Lenguajes", "duracion_dias": 5}
    ]
    
    print("\n" + "="*60)
    print("📋 INICIANDO EVALUACIÓN DE CALIDAD EN LOTE (Fase 6)")
    print("="*60)
    print(f"URL de API:      {base_url}")
    print(f"Total de corridas planificadas: {len(test_runs)}")
    print("="*60 + "\n")
    
    # Crear carpeta de reportes
    eval_dir = "./reports/evaluations"
    os.makedirs(eval_dir, exist_ok=True)
    
    results = []
    success_count = 0
    fallback_count = 0
    rag_only_count = 0
    total_score = 0.0
    total_latency = 0.0
    
    for idx, payload in enumerate(test_runs, start=1):
        payload["modelo"] = "NEM"
        print(f"[{idx}/{len(test_runs)}] Evaluando tema: '{payload['tema']}' ({payload['campo_formativo']} - Grado {payload['grado']})...")
        
        run_res = evaluate_run(base_url, payload)
        results.append(run_res)
        
        total_latency += run_res["latency_ms"]
        
        if run_res["success"]:
            success_count += 1
            total_score += run_res["score"]
            if run_res["fallback_usage"]:
                fallback_count += 1
                print(f"  └─ ✅ Generada vía FALLBACK CURRICULAR (Score: {run_res['score']})")
            else:
                rag_only_count += 1
                print(f"  └─ ✅ Generada vía RAG OFICIAL (Score: {run_res['score']})")
        else:
            print(f"  └─ ❌ FAILED (Status: {run_res['status_code']} | {run_res['notes'][:60]}...)")
            
        # Guardar reporte individual
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_tema = payload["tema"].replace(" ", "_").replace("/", "_")
        filename = f"planeacion_eval_{timestamp_str}_{clean_tema}_{idx}.json"
        
        try:
            with open(os.path.join(eval_dir, filename), "w", encoding="utf-8") as f:
                json.dump(run_res, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  ⚠️ No se pudo guardar el reporte individual: {e}")
            
    # Resumen acumulativo
    avg_latency = total_latency / len(test_runs) if test_runs else 0.0
    avg_score = total_score / success_count if success_count > 0 else 0.0
    failure_count = len(test_runs) - success_count
    
    latencies = [run_res["latency_ms"] for run_res in results]
    p50_latency = percentile(latencies, 50)
    p95_latency = percentile(latencies, 95)
    max_latency = max(latencies) if latencies else 0.0
    cache_hits = sum(1 for run_res in results if run_res.get("cache_hit", False))
    
    summary = {
        "evaluacion_total_corridas": len(test_runs),
        "generaciones_exitosas": success_count,
        "generaciones_fallidas": failure_count,
        "fallback_uso_curriculo": fallback_count,
        "rag_oficial_exitoso": rag_only_count,
        "calificacion_promedio_heuristica_exitosas": round(avg_score, 2),
        "latencia_promedio_ms": round(avg_latency, 2),
        "latencia_p50_ms": round(p50_latency, 2),
        "latencia_p95_ms": round(p95_latency, 2),
        "latencia_max_ms": round(max_latency, 2),
        "cache_hits": cache_hits,
        "corridas_detalle": results
    }
    
    summary_path = os.path.join(eval_dir, "summary_report.json")
    try:
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Resumen de evaluación guardado en: {summary_path}")
    except Exception as e:
        print(f"\n⚠️ Error al guardar el resumen final: {e}")
        
    print("\n" + "="*60)
    print("📊 RESUMEN FINAL DE CALIDAD PEDAGÓGICA (25 Corridas)")
    print("="*60)
    print(f"Total Corridas:             {len(test_runs)}")
    print(f"Generaciones Exitosas:      {success_count} ({success_count/len(test_runs)*100:.1f}%)")
    print(f"Rechazos (No-Inventar):     {failure_count} ({failure_count/len(test_runs)*100:.1f}%)")
    print(f"Uso de Fallback Curricular:  {fallback_count}")
    print(f"Uso de RAG Puro:            {rag_only_count}")
    print(f"Latencia Promedio:          {round(avg_latency, 2)} ms")
    print(f"Latencia p50:               {round(p50_latency, 2)} ms")
    print(f"Latencia p95:               {round(p95_latency, 2)} ms")
    print(f"Latencia Max:               {round(max_latency, 2)} ms")
    print(f"Cache Hits (Aciertos):      {cache_hits}")
    print(f"Score Promedio (Exitosas):  {round(avg_score, 2)} / 10.0")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
