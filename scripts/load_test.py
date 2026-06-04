#!/usr/bin/env python3
import os
import sys
import time
import json
import argparse
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple

# Configuración por defecto
DEFAULT_BASE_URL = "http://127.0.0.1:8001"

def send_request(url: str, payload: Dict[str, Any]) -> Tuple[bool, float]:
    """
    Envía una petición POST y mide la latencia.
    Retorna: (success, latency_ms)
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    start_time = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            _ = response.read()
            success = response.status == 200
    except urllib.error.HTTPError as e:
        # Algunos endpoints de planeación pueden retornar 400 controlados (política no-inventar)
        # en este contexto los consideramos errores del test si es 500, pero 400 puede ser éxito de lógica.
        # Sin embargo, para test de carga consideramos exitoso cualquier código < 400.
        success = e.code < 400
    except Exception:
        success = False
        
    latency_ms = (time.perf_counter() - start_time) * 1000.0
    return success, latency_ms

def run_concurrent_batch(base_url: str, count: int) -> Dict[str, Any]:
    """
    Ejecuta un lote de 'count' peticiones concurrentes divididas equitativamente
    entre /buscar y /planeaciones/generar.
    """
    buscar_url = f"{base_url}/buscar"
    generar_url = f"{base_url}/planeaciones/generar"
    
    # Payloads estándar
    buscar_payload = {
        "query": "campos formativos y ejes articuladores",
        "limit": 3,
        "match_threshold": 0.25,
        "modelo": "NEM"
    }
    generar_payload = {
        "tema": "energía solar",
        "grado": "2",
        "nivel": "Secundaria",
        "campo_formativo": "Saberes y Pensamiento Científico",
        "duracion_dias": 5,
        "modelo": "NEM"
    }
    
    tasks = []
    # Generar la lista de URLs y payloads a enviar
    for i in range(count):
        if i % 2 == 0:
            tasks.append((generar_url, generar_payload))
        else:
            tasks.append((buscar_url, buscar_payload))
            
    latencies = []
    success_count = 0
    
    # Ejecución concurrente
    with ThreadPoolExecutor(max_workers=count) as executor:
        futures = {executor.submit(send_request, url, payload): (url, i) for i, (url, payload) in enumerate(tasks)}
        
        for future in as_completed(futures):
            try:
                success, latency = future.result()
                latencies.append(latency)
                if success:
                    success_count += 1
            except Exception:
                latencies.append(0.0)
                
    # Calcular percentiles
    latencies_sorted = sorted(latencies)
    total = len(latencies_sorted)
    
    if total > 0:
        p50 = latencies_sorted[int(total * 0.50)]
        p95 = latencies_sorted[int(total * 0.95)]
        avg = sum(latencies_sorted) / total
    else:
        p50 = p95 = avg = 0.0
        
    error_rate = ((total - success_count) / total) * 100 if total > 0 else 0.0
    
    return {
        "total": total,
        "success_rate": (success_count / total) * 100 if total > 0 else 0.0,
        "error_rate": error_rate,
        "p50": round(p50, 2),
        "p95": round(p95, 2),
        "avg": round(avg, 2)
    }

def main():
    parser = argparse.ArgumentParser(description="Script de pruebas de carga concurrente para mex-education-api.")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help="URL base del servidor FastAPI.")
    args = parser.parse_args()
    
    base_url = args.url
    
    # Verificar si el servidor está en línea
    try:
        with urllib.request.urlopen(f"{base_url}/health", timeout=3) as r:
            if r.status != 200:
                print(f"❌ El servidor en {base_url} no está respondiendo correctamente (status: {r.status}).")
                sys.exit(1)
    except Exception as e:
        print(f"❌ No se pudo conectar al servidor en {base_url}: {e}")
        print("Asegúrate de que la API esté corriendo (ej. uvicorn app.main:app --port 8001).")
        sys.exit(1)
        
    print("\n" + "="*60)
    print("⚡ INICIANDO PRUEBAS DE CARGA CONCURRENTE")
    print("="*60)
    print(f"Objetivo:        {base_url}")
    print("Endpoints:       50% /buscar, 50% /planeaciones/generar")
    print("Lotes a probar:  50, 100 y 250 peticiones concurrentes")
    print("="*60 + "\n")
    
    concurrencies = [50, 100, 250]
    results = {}
    
    for c in concurrencies:
        print(f"🚀 Ejecutando lote de {c} peticiones concurrentes...")
        # Pequeña pausa antes de estresar el servidor
        time.sleep(1)
        res = run_concurrent_batch(base_url, c)
        results[c] = res
        print(f"  └─ Completado. Tasa de Éxito: {res['success_rate']:.1f}% | p50: {res['p50']}ms | p95: {res['p95']}ms\n")
        
    # Imprimir reporte tabulado final
    print("="*60)
    print("📊 RESULTADOS CONSOLIDADOS DE LA PRUEBA DE CARGA")
    print("="*60)
    print(f"{'Concurrencia':<15} | {'Éxito (%)':<10} | {'p50 (ms)':<10} | {'p95 (ms)':<10} | {'Avg (ms)':<10}")
    print("-"*60)
    for c in concurrencies:
        res = results[c]
        print(f"{c:<15} | {res['success_rate']:<10.1f} | {res['p50']:<10} | {res['p95']:<10} | {res['avg']:<10}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
