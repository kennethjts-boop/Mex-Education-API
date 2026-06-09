import logging
import random
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.core.config import settings
from app.db.supabase import supabase_client

logger = logging.getLogger("uvicorn.error")

_openai_client = None

def get_embedding(text: str) -> List[float]:
    """
    Generates a 1536-dimensional vector embedding for the input text using OpenAI.
    If the OpenAI API key is missing or invalid, generates a mock embedding vector.
    """
    global _openai_client
    is_openai_configured = settings.OPENAI_API_KEY and "your-openai-api-key" not in settings.OPENAI_API_KEY
    
    if not is_openai_configured:
        logger.warning("OpenAI API key not configured or is placeholder. Generating mock embedding (1536 dims).")
        # Generates a normalized mock vector of 1536 dims
        raw_vec = [random.uniform(-0.1, 0.1) for _ in range(1536)]
        magnitude = sum(x**2 for x in raw_vec) ** 0.5
        return [x / magnitude for x in raw_vec]
    
    try:
        if _openai_client is None:
            _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = _openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating OpenAI embedding: {e}. Falling back to mock embedding.")
        raw_vec = [random.uniform(-0.1, 0.1) for _ in range(1536)]
        magnitude = sum(x**2 for x in raw_vec) ** 0.5
        return [x / magnitude for x in raw_vec]


def normalize_modelo(modelo: Optional[str]) -> Optional[str]:
    """
    Normaliza el modelo educativo a la cadena estándar 'NEM_2022'.
    Permite mapear sinónimos como 'NEM', 'nueva escuela mexicana', etc.
    """
    if not modelo:
        return None
    val = modelo.lower().strip()
    if val in ["nem", "nem_2022", "nueva escuela mexicana", "nueva escuela mexicana 2022"]:
        return "NEM_2022"
    return modelo

def normalize_nivel(nivel: Optional[str]) -> Optional[str]:
    """
    Normaliza el nivel educativo a la cadena estándar 'Telesecundaria'.
    Acepta variaciones como 'Secundaria', 'secundaria', 'Telesecundaria',
    'tele secundaria', 'TELESECUNDARIA', 'Nivel secundaria', 'Educación secundaria'.
    """
    if not nivel:
        return None
    val = nivel.lower().strip()
    if "secundaria" in val:
        return "Telesecundaria"
    return nivel

def normalize_grado(grado: Optional[str]) -> Optional[str]:
    """
    Normaliza el grado escolar a un dígito estándar ('1', '2' o '3').
    Mapea variaciones como '2', '2°', '2do', '2do Grado', 'Segundo', 'Segundo grado' a '2'.
    Mapea '1', '1°', '1er', '1er Grado', 'Primer', 'Primer grado' a '1'.
    Mapea '3', '3°', '3er', '3er Grado', 'Tercer', 'Tercer grado' a '3'.
    """
    if not grado:
        return None
    val = grado.lower().strip()
    if any(x in val for x in ["segundo", "2"]):
        return "2"
    if any(x in val for x in ["primer", "1"]):
        return "1"
    if any(x in val for x in ["tercer", "3"]):
        return "3"
    return grado

def search_nem_chunks(
    query_text: str,
    limit: int = 5,
    match_threshold: float = 0.3,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Performs a semantic vector search in the chunks_nem table via Supabase RPC.
    If Supabase is not configured or queries fail, returns mock demonstration results.
    """
    # 1. Intentar obtener de la caché
    cache_key = {
        "query_text": query_text,
        "limit": limit,
        "match_threshold": match_threshold,
        "filters": filters
    }
    
    from app.services.cache_service import rag_cache
    cached_val = rag_cache.get(cache_key)
    if cached_val is not None:
        logger.info(f"Caché RAG Hit para consulta: '{query_text}'")
        return cached_val

    # Normalizar el modelo, nivel y grado si se especifican en los filtros
    if filters:
        if "modelo" in filters and filters["modelo"]:
            filters["modelo"] = normalize_modelo(filters["modelo"])
        if "nivel" in filters and filters["nivel"]:
            filters["nivel"] = normalize_nivel(filters["nivel"])
        if "grado" in filters and filters["grado"]:
            filters["grado"] = normalize_grado(filters["grado"])
        
    embedding = get_embedding(query_text)
    
    if supabase_client is None:
        logger.warning("Supabase client not initialized. Returning mock search results for demo.")
        results = _get_mock_search_results(query_text, filters)
        rag_cache.set(cache_key, results)
        return results
        
    try:
        # Prepare parameters for the RPC call
        rpc_params = {
            "query_embedding": embedding,
            "match_threshold": match_threshold,
            "match_count": limit,
            "filter_metadata": filters or {}
        }
        
        # Execute RPC function match_chunks_nem
        response = supabase_client.rpc("match_chunks_nem", rpc_params).execute()
        results = response.data
        rag_cache.set(cache_key, results)
        return results
    except Exception as e:
        logger.error(f"Error executing match_chunks RPC on Supabase: {e}. Falling back to mock search results.")
        results = _get_mock_search_results(query_text, filters)
        rag_cache.set(cache_key, results)
        return results

def _get_mock_search_results(query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Generates mock search results for local testing and demonstration.
    Loads and searches across locally ingested JSON files under ./data/ingested_*.json if available.
    """
    import uuid
    import glob
    import json
    import re
    from datetime import datetime
    
    # 1. Intentar cargar chunks desde archivos ingestados localmente
    local_chunks = []
    ingested_files = glob.glob("./data/ingested_*.json")
    
    for filepath in ingested_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                doc_data = json.load(f)
                doc_id = doc_data["documento"]["id"]
                titulo = doc_data["documento"]["titulo"]
                for c in doc_data["chunks"]:
                    local_chunks.append({
                        "id": c["id"],
                        "documento_id": doc_id,
                        "texto": c["texto"],
                        "pagina": c["pagina"],
                        "chunk_index": c["chunk_index"],
                        "metadata": c["metadata"],
                        "titulo": titulo,
                        "storage_path": filepath
                    })
        except Exception as e:
            logger.error(f"Error cargando archivo ingestado {filepath}: {e}")

    # 2. Si hay archivos locales, realizar búsqueda por coincidencia de palabras clave
    if local_chunks:
        # Limpiar y extraer palabras clave de la query (mínimo 3 letras)
        query_words = [w.lower() for w in re.findall(r'\w+', query) if len(w) > 2]
        
        scored_results = []
        for chunk in local_chunks:
            # Validar filtros
            match = True
            if filters:
                for k, v in filters.items():
                    if v is not None and chunk["metadata"].get(k) != v:
                        match = False
                        break
            if not match:
                continue
            
            # Puntuación por coincidencia de palabras
            text_lower = chunk["texto"].lower()
            matches = 0
            for w in query_words:
                if w in text_lower:
                    matches += 1
            
            # Calcular pseudo-similitud
            if query_words:
                similarity = 0.3 + 0.65 * (matches / len(query_words))
            else:
                similarity = 0.5
                
            # Si no hay ninguna coincidencia (y había palabras de búsqueda), omitimos para calidad de búsqueda
            if query_words and matches == 0:
                continue
                
            scored_results.append({
                "id": chunk["id"],
                "documento_id": chunk["documento_id"],
                "texto": chunk["texto"],
                "pagina": chunk["pagina"],
                "chunk_index": chunk["chunk_index"],
                "metadata": chunk["metadata"],
                "created_at": datetime.utcnow().isoformat(),
                "similarity": round(similarity, 2),
                "documentos": {
                    "id": chunk["documento_id"],
                    "titulo": chunk["titulo"],
                    "modelo": chunk["metadata"]["modelo"],
                    "nivel": chunk["metadata"]["nivel"],
                    "fase": chunk["metadata"]["fase"],
                    "grado": chunk["metadata"]["grado"],
                    "campo_formativo": chunk["metadata"].get("campo_formativo"),
                    "tipo_documento": chunk["metadata"].get("tipo_documento", "Simulado"),
                    "storage_path": chunk["storage_path"],
                    "created_at": datetime.utcnow().isoformat()
                }
            })
            
        # Ordenar por similitud y limitar
        scored_results.sort(key=lambda x: x["similarity"], reverse=True)
        return scored_results[:5]

    # 3. FALLBACK: Si no hay archivos locales, usar base de datos estática
    mock_db = [
        {
            "texto": "El Campo Formativo 'Lenguajes' vincula procesos de aprendizaje de español, lenguas indígenas, lenguas extranjeras y artes. Permite el desarrollo cognitivo y social a través del diálogo y la expresión cultural.",
            "metadata": {"modelo": "NEM_2022", "nivel": "Primaria", "fase": "Fase 3", "grado": "1er Grado", "campo_formativo": "Lenguajes", "tipo_documento": "Programa Sintético"},
            "titulo": "Programa Sintético - Fase 3"
        },
        {
            "texto": "El Pensamiento Crítico es un Eje Articulador que promueve un desarrollo cognitivo reflexivo, permitiendo a los estudiantes interrogar al mundo y cuestionar de manera fundamentada la realidad que les rodea.",
            "metadata": {"modelo": "NEM_2022", "nivel": "Secundaria", "fase": "Fase 6", "grado": "1er Grado", "campo_formativo": "Multidisciplinario", "tipo_documento": "Plan de Estudio"},
            "titulo": "Ejes Articuladores en el Aula"
        },
        {
            "texto": "El Campo Formativo 'Saberes y Pensamiento Científico' tiene como objeto de aprendizaje la comprensión y explicación de los fenómenos naturales y procesos matemáticos en relación con lo social.",
            "metadata": {"modelo": "NEM_2022", "nivel": "Primaria", "fase": "Fase 3", "grado": "2do Grado", "campo_formativo": "Saberes y Pensamiento Científico", "tipo_documento": "Programa Sintético"},
            "titulo": "Programa Sintético - Fase 3"
        }
    ]
    
    results = []
    # Filter matching
    for i, item in enumerate(mock_db):
        match = True
        if filters:
            for k, v in filters.items():
                if v is not None and item["metadata"].get(k) != v:
                    match = False
                    break
        if match:
            doc_id = str(uuid.uuid4())
            results.append({
                "id": str(uuid.uuid4()),
                "documento_id": doc_id,
                "texto": item["texto"],
                "pagina": 42 + i,
                "chunk_index": i,
                "metadata": item["metadata"],
                "created_at": datetime.utcnow().isoformat(),
                "similarity": 0.85 - (i * 0.05),
                "documentos": {
                    "id": doc_id,
                    "titulo": item["titulo"],
                    "modelo": item["metadata"]["modelo"],
                    "nivel": item["metadata"]["nivel"],
                    "fase": item["metadata"]["fase"],
                    "grado": item["metadata"]["grado"],
                    "campo_formativo": item["metadata"]["campo_formativo"],
                    "tipo_documento": item["metadata"]["tipo_documento"],
                    "storage_path": f"simulated/docs/doc_{i}.pdf",
                    "created_at": datetime.utcnow().isoformat()
                }
            })
            
    return results[:5]
