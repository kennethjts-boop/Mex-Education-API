#!/usr/bin/env python3
import time
import json
import random
import urllib.request
import urllib.error
import argparse

# Configuración por defecto
DEFAULT_BASE_URL = "http://127.0.0.1:8001"

def send_request(base_url: str, payload: dict) -> dict:
    """
    Envía una petición a /planeaciones/generar y retorna la respuesta JSON,
    la latencia del cliente, la latencia del servidor y si fue cache hit.
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
        with urllib.request.urlopen(req, timeout=30) as response:
            status_code = response.status
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        status_code = e.code
        response_body = e.read().decode("utf-8")
    except Exception as e:
        status_code = 500
        error_msg = str(e)
        
    client_latency_ms = (time.perf_counter() - start_time) * 1000.0
    
    if status_code == 200 and response_body:
        try:
            res_json = json.loads(response_body)
            meta = res_json.get("metadata", {})
            return {
                "success": True,
                "client_latency_ms": client_latency_ms,
                "server_latency_ms": meta.get("latency_ms", client_latency_ms),
                "cache_hit": meta.get("cache_hit", False),
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "client_latency_ms": client_latency_ms,
                "server_latency_ms": client_latency_ms,
                "cache_hit": False,
                "error": f"Error parseando JSON: {e}"
            }
    else:
        err = error_msg or f"HTTP status {status_code}"
        return {
            "success": False,
            "client_latency_ms": client_latency_ms,
            "server_latency_ms": client_latency_ms,
            "cache_hit": False,
            "error": err
        }

def main():
    parser = argparse.ArgumentParser(description="Benchmark de latencia y caché (Fase 8)")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help="URL base del servidor FastAPI.")
    args = parser.parse_args()
    
    base_url = args.url
    
    # Generar un sufijo aleatorio único para esta corrida de benchmark
    # de forma que garanticemos un "cold cache miss" en la primera ronda.
    run_id = random.randint(1000, 9999)
    
    # 5 temas correspondientes a currículos sembrados (grado 2)
    test_cases = [
        {
            "tema": f"energía solar y sustentabilidad (bench-{run_id}-1)",
            "grado": "2",
            "nivel": "Secundaria",
            "campo_formativo": "Saberes y Pensamiento Científico",
            "duracion_dias": 5,
            "modelo": "NEM"
        },
        {
            "tema": f"reciclaje y conservación del medio ambiente (bench-{run_id}-2)",
            "grado": "2",
            "nivel": "Secundaria",
            "campo_formativo": "Ética, Naturaleza y Sociedades",
            "duracion_dias": 5,
            "modelo": "NEM"
        },
        {
            "tema": f"biodiversidad y preservación de ecosistemas (bench-{run_id}-3)",
            "grado": "2",
            "nivel": "Secundaria",
            "campo_formativo": "Ética, Naturaleza y Sociedades",
            "duracion_dias": 5,
            "modelo": "NEM"
        },
        {
            "tema": f"proporcionalidad y gráficas matemáticas (bench-{run_id}-4)",
            "grado": "2",
            "nivel": "Secundaria",
            "campo_formativo": "Saberes y Pensamiento Científico",
            "duracion_dias": 5,
            "modelo": "NEM"
        },
        {
            "tema": f"lectura en lenguas nacionales y diversidad (bench-{run_id}-5)",
            "grado": "2",
            "nivel": "Secundaria",
            "campo_formativo": "Lenguajes",
            "duracion_dias": 5,
            "modelo": "NEM"
        }
    ]
    
    print("\n" + "="*70)
    print("🚀 INICIANDO BENCHMARK DE LATENCIA Y CACHÉ (Fase 8)")
    print("="*70)
    print(f"URL de API:      {base_url}")
    print(f"ID de corrida:   {run_id}")
    print(f"Total casos:     {len(test_cases)}")
    print("="*70 + "\n")
    
    cold_results = []
    hot_results = []
    
    # RAG Híbrido frío
    print("🥶 Ronda 1: Ejecutando peticiones FRÍAS (Cold Cache Misses)...")
    for idx, case in enumerate(test_cases, start=1):
        print(f"   [{idx}/{len(test_cases)}] Generando para tema: '{case['tema'][:40]}...'")
        res = send_request(base_url, case)
        cold_results.append(res)
        if res["success"]:
            print(f"      └─ OK (Server Latency: {res['server_latency_ms']:.2f} ms | Cache Hit: {res['cache_hit']})")
        else:
            print(f"      └─ ❌ ERROR: {res['error']}")
        # Pequeña pausa para no saturar
        time.sleep(0.5)
        
    print("\n🔥 Ronda 2: Ejecutando peticiones CALIENTES (Hot Cache Hits)...")
    for idx, case in enumerate(test_cases, start=1):
        print(f"   [{idx}/{len(test_cases)}] Generando para tema: '{case['tema'][:40]}...'")
        res = send_request(base_url, case)
        hot_results.append(res)
        if res["success"]:
            print(f"      └─ OK (Server Latency: {res['server_latency_ms']:.2f} ms | Cache Hit: {res['cache_hit']})")
        else:
            print(f"      └─ ❌ ERROR: {res['error']}")
        time.sleep(0.1)

    print("\n" + "="*85)
    print("📊 RESULTADOS DETALLADOS DEL BENCHMARK")
    print("="*85)
    print(f"{'Caso':<6} | {'Tema':<22} | {'Cold Latency':<14} | {'Hot Latency':<13} | {'Speedup':<10} | {'Cache Hit'}")
    print("-"*85)
    
    valid_cold_latencies = []
    valid_hot_latencies = []
    
    for i in range(len(test_cases)):
        case = test_cases[i]
        cold = cold_results[i]
        hot = hot_results[i]
        
        tema_short = case["tema"].split(" (bench-")[0][:22]
        
        if cold["success"] and hot["success"]:
            c_lat = cold["server_latency_ms"]
            h_lat = hot["server_latency_ms"]
            valid_cold_latencies.append(c_lat)
            valid_hot_latencies.append(h_lat)
            
            speedup = c_lat / h_lat if h_lat > 0 else 0.0
            hit_str = "SÍ" if hot["cache_hit"] else "NO"
            
            print(f"#{i+1:<5} | {tema_short:<22} | {c_lat:8.2f} ms   | {h_lat:7.2f} ms   | {speedup:6.2f}x    | {hit_str:<9}")
        else:
            err_str = f"Error: Cold={cold['success']}, Hot={hot['success']}"
            print(f"#{i+1:<5} | {tema_short:<22} | {'FAILED':<14} | {'FAILED':<13} | {'-':<10} | {'-'}")
            
    print("-"*85)
    
    if valid_cold_latencies and valid_hot_latencies:
        avg_cold = sum(valid_cold_latencies) / len(valid_cold_latencies)
        avg_hot = sum(valid_hot_latencies) / len(valid_hot_latencies)
        avg_speedup = avg_cold / avg_hot if avg_hot > 0 else 0.0
        
        print(f"{'PROMEDIO':<31} | {avg_cold:8.2f} ms   | {avg_hot:7.2f} ms   | {avg_speedup:6.2f}x    |")
        print("="*85)
        print(f"💡 El sistema de caché redujo la latencia promedio en un {((avg_cold - avg_hot)/avg_cold)*100:.1f}%.")
    else:
        print("❌ No se pudieron procesar datos suficientes para calcular promedios.")
        print("="*85)
    print()

if __name__ == "__main__":
    main()
