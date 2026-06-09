#!/usr/bin/env python3
import os
import sys
import requests
import logging

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.nem_search import search_nem_chunks
from app.db.supabase import get_supabase_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_calendar_search")

QUERIES = [
    "cuando inicia el ciclo escolar 2025-2026",
    "cuando termina el ciclo escolar 2025-2026",
    "cuantos días efectivos de clase tiene el calendario escolar 2025-2026",
    "cuando son los consejos técnicos escolares",
    "vacaciones de invierno 2025-2026",
    "vacaciones de semana santa 2026",
    "preinscripciones 2026",
    "descarga administrativa 2025-2026"
]

def search_http(query: str, port: int) -> list:
    url = f"http://127.0.0.1:{port}/buscar"
    payload = {
        "query": query,
        "limit": 5,
        "match_threshold": 0.2
    }
    try:
        r = requests.post(url, json=payload, timeout=5)
        if r.status_code == 200:
            return r.json().get("resultados", [])
    except Exception:
        pass
    return []

def search_direct(query: str) -> list:
    raw_results = search_nem_chunks(
        query_text=query,
        limit=5,
        match_threshold=0.2,
        filters={}
    )
    if not raw_results:
        return []
    
    supabase = get_supabase_client()
    docs_map = {}
    if supabase is not None:
        doc_ids = list(set([str(r["documento_id"]) for r in raw_results if "documento_id" in r]))
        if doc_ids:
            try:
                res = supabase.table("documentos").select("*").in_("id", doc_ids).execute()
                for doc in res.data:
                    docs_map[str(doc["id"])] = doc
            except Exception as e:
                logger.error(f"Error fetching documents: {e}")
                
    mapped = []
    for r in raw_results:
        doc_id_str = str(r["documento_id"])
        doc_data = None
        if doc_id_str in docs_map:
            doc_data = docs_map[doc_id_str]
        elif "documentos" in r and r["documentos"]:
            doc_data = r["documentos"]
        
        sim = r.get("similarity") or r.get("similitud") or 0.0
        mapped.append({
            "texto": r["texto"],
            "similitud": sim,
            "documento": doc_data
        })
    return mapped

def main():
    logger.info("Starting Calendar Search Tests...")
    
    # Try to detect running API server
    ports = [8000, 8001]
    active_port = None
    for p in ports:
        try:
            # Check with a simple GET to /buscar (should return 405 Method Not Allowed or 200 depending on endpoint)
            # or try a post to /buscar with empty query
            r = requests.get(f"http://127.0.0.1:{p}/", timeout=1)
            active_port = p
            logger.info(f"API server detected on port {p}")
            break
        except Exception:
            continue
            
    all_passed = True
    results_summary = []
    
    for q in QUERIES:
        print("\n" + "="*80)
        print(f"Testing Query: '{q}'")
        print("="*80)
        
        http_results = []
        if active_port:
            http_results = search_http(q, active_port)
            
        direct_results = search_direct(q)
        
        # Decide results to use for PASS/FAIL (default to HTTP, fallback to Direct)
        results = http_results if http_results else direct_results
        method = f"HTTP (Port {active_port})" if http_results else "Direct Service (offline)"
        
        # Print details for both
        if active_port:
            if http_results:
                h_doc = http_results[0].get("documento")
                h_title = h_doc.get("titulo") if h_doc else "None"
                h_sim = http_results[0].get("similitud") or http_results[0].get("similarity") or 0.0
                print(f"  [HTTP] Top: '{h_title}' (Sim: {h_sim:.4f})")
            else:
                print("  [HTTP] No results")
                
        if direct_results:
            d_doc = direct_results[0].get("documento")
            d_title = d_doc.get("titulo") if d_doc else "None"
            d_sim = direct_results[0].get("similitud") or direct_results[0].get("similarity") or 0.0
            print(f"  [Direct] Top: '{d_title}' (Sim: {d_sim:.4f})")
        else:
            print("  [Direct] No results")
            
        if not results:
            print("❌ No results found!")
            all_passed = False
            results_summary.append((q, "FAIL (No results)", 0.0, method))
            continue
            
        first_res = results[0]
        doc = first_res.get("documento")
        title = doc.get("titulo") if doc else "None"
        sim = first_res.get("similitud") or first_res.get("similarity") or 0.0
        
        print(f"First result: Document Title: '{title}' (Similarity: {sim:.4f})")
        print(f"Text snippet: {first_res.get('texto')[:200]}...")
        
        expected_title = "Calendario Escolar SEP 2025-2026"
        if title == expected_title:
            print(f"✅ PASS: First result is '{expected_title}' using {method}")
            results_summary.append((q, "PASS", sim, method))
        else:
            print(f"❌ FAIL: Expected first result '{expected_title}', but got '{title}' using {method}")
            all_passed = False
            results_summary.append((q, f"FAIL (Got: {title})", sim, method))
            
    print("\n" + "="*80)
    print("SUMMARY OF TEST RESULTS")
    print("="*80)
    for q, status, sim, method in results_summary:
        print(f"- Query: '{q}'\n  Result: {status} (Similarity: {sim:.4f}) via {method}\n")
        
    if all_passed:
        print("🎉 All calendar search tests passed successfully!")
        sys.exit(0)
    else:
        print("❌ Some calendar search tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
