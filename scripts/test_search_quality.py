#!/usr/bin/env python3
import os
import sys
import json
import logging
from typing import List, Dict, Any

# Añadir el directorio raíz al sys.path para poder realizar importaciones locales
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_search_quality")

# Preguntas / Conceptos clave obligatorios para validar
TEST_QUERIES = [
    "campos formativos",
    "ejes articuladores",
    "evaluación formativa",
    "comunidad como núcleo integrador",
    "perfil de egreso",
    "autonomía profesional docente",
    "programa analítico",
    "codiseño"
]

def search_via_http(query: str) -> List[Dict[str, Any]]:
    """Intenta consultar el endpoint HTTP local del API."""
    import requests
    url = "http://127.0.0.1:8000/buscar"
    payload = {
        "query": query,
        "limit": 3,
        "match_threshold": 0.25,
        "modelo": "NEM_2022"  # Se aplicará normalización si mandan variantes
    }
    try:
        response = requests.post(url, json=payload, timeout=3)
        if response.status_code == 200:
            data = response.json()
            # Mapear de respuesta de API a estructura uniforme
            return data.get("resultados", [])
    except Exception:
        # Silenciosamente falla para proceder con fallback directo offline
        pass
    return []

def search_via_service(query: str) -> List[Dict[str, Any]]:
    """Consulta directamente usando los servicios locales (Offline Fallback)."""
    from app.services.nem_search import search_nem_chunks
    
    filters = {"modelo": "NEM_2022"}
    try:
        raw_results = search_nem_chunks(
            query_text=query,
            limit=3,
            match_threshold=0.25,
            filters=filters
        )
        # Adaptar la salida a la estructura esperada
        resultados = []
        for r in raw_results:
            titulo = r.get("documentos", {}).get("titulo", "Desconocido") if "documentos" in r else "Plan de Estudio"
            similitud = r.get("similarity") or r.get("similitud") or 0.0
            resultados.append({
                "chunk_id": r.get("id"),
                "documento_id": r.get("documento_id"),
                "texto": r.get("texto"),
                "pagina": r.get("pagina"),
                "chunk_index": r.get("chunk_index", 0),
                "similitud": similitud,
                "documento": {
                    "titulo": titulo
                }
            })
        return resultados
    except Exception as e:
        logger.error(f"Error al buscar usando el servicio local directo: {e}")
    return []

def main():
    logger.info("Iniciando evaluación del motor de búsqueda semántica (Fase 3)...")
    
    report_items = []
    
    print("\n" + "="*80)
    print("🔍 EVALUACIÓN DE CALIDAD DE BÚSQUEDA SEMÁNTICA (RAG)")
    print("="*80)
    
    for query in TEST_QUERIES:
        # Intentar HTTP primero, si no está activo, usar la importación directa offline
        results = search_via_http(query)
        method_used = "HTTP (API Online)"
        
        if not results:
            results = search_via_service(query)
            method_used = "Service Direct (API Offline)"
            
        num_results = len(results)
        query_report = {
            "query": query,
            "metodo_busqueda": method_used,
            "total_coincidencias": num_results,
            "coincidencias": []
        }
        
        print(f"\n❓ QUERY: '{query}' ({method_used})")
        print(f"   Coincidencias encontradas: {num_results}")
        
        if num_results == 0:
            print("   ⚠️ ¡ALERTA! No se encontraron fragmentos para esta búsqueda.")
        else:
            for idx, r in enumerate(results, start=1):
                doc_title = r.get("documento", {}).get("titulo", "Plan de Estudio")
                page = r.get("pagina")
                sim = r.get("similitud") or r.get("similarity") or 0.0
                texto_preview = r.get("texto", "")[:130].replace("\n", " ").strip() + "..."
                
                print(f"   {idx}. [Score: {sim:.2f}] [Pag. {page}] Doc: '{doc_title}'")
                print(f"      Text: \"{texto_preview}\"")
                
                query_report["coincidencias"].append({
                    "documento_titulo": doc_title,
                    "pagina": page,
                    "similitud": sim,
                    "fragmento": texto_preview
                })
                
        report_items.append(query_report)
        print("-" * 80)

    # Calcular estadísticas generales del reporte
    total_queries = len(TEST_QUERIES)
    successful_queries = sum(1 for item in report_items if item["total_coincidencias"] > 0)
    success_rate = (successful_queries / total_queries) * 100

    final_report = {
        "resumen": {
            "total_consultas_evaluadas": total_queries,
            "consultas_exitosas": successful_queries,
            "tasa_recuperacion": f"{success_rate:.2f}%"
        },
        "reportes_detalle": report_items
    }

    # Guardar reporte JSON
    reports_dir = "./reports"
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, "search_quality_report.json")
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)
        
    print("\n" + "="*80)
    print("📊 RESUMEN FINAL DE CALIDAD")
    print("="*80)
    print(f"Consultas Totales: {total_queries}")
    print(f"Consultas Exitosas: {successful_queries} de {total_queries}")
    print(f"Tasa de Recuperación: {success_rate:.2f}%")
    print(f"Reporte JSON guardado en: {report_path}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
