import logging
from fastapi import APIRouter, Request
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from app.schemas.documentos import DocumentoResponse
from app.services.nem_search import search_nem_chunks
from app.services.cost_estimator import estimate_tokens, estimate_embedding_cost
from app.db.supabase import supabase_client

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

@router.post("", response_model=SearchResponse, tags=["Búsqueda"])
def buscar_nem(payload: SearchRequest, request: Request):
    """
    Realiza una búsqueda semántica de contenidos de la Nueva Escuela Mexicana (NEM).
    Genera el embedding de la pregunta/frase enviada y consulta en Supabase usando
    similitud del coseno (pgvector). Soporta filtros por nivel, fase, grado y campo formativo.
    """
    # Construir diccionario de filtros para la consulta (metadata)
    filters = {}
    if payload.modelo:
        filters["modelo"] = payload.modelo
    if payload.nivel:
        filters["nivel"] = payload.nivel
    if payload.fase:
        filters["fase"] = payload.fase
    if payload.grado:
        filters["grado"] = payload.grado
    if payload.campo_formativo:
        filters["campo_formativo"] = payload.campo_formativo
    if payload.tipo_documento:
        filters["tipo_documento"] = payload.tipo_documento

    # Realizar búsqueda
    raw_results = search_nem_chunks(
        query_text=payload.query,
        limit=payload.limit,
        match_threshold=payload.match_threshold,
        filters=filters
    )

    # Si hay base de datos real, recuperar la metadata de los documentos padres
    docs_map = {}
    if supabase_client is not None and raw_results:
        # Extraer IDs de documentos únicos
        doc_ids = list(set([str(r["documento_id"]) for r in raw_results if "documento_id" in r]))
        if doc_ids:
            try:
                docs_res = supabase_client.table("documentos").select("*").in_("id", doc_ids).execute()
                for doc in docs_res.data:
                    docs_map[str(doc["id"])] = doc
            except Exception as e:
                logger.error(f"Error al obtener metadatos de documentos asociados: {e}")

    # Mapear a respuesta tipada
    resultados_mapeados = []
    for r in raw_results:
        doc_id_str = str(r["documento_id"])
        
        # Intentar obtener el documento del mapa de la DB o del mock/join (si viene pre-cargado)
        documento_resp = None
        if doc_id_str in docs_map:
            documento_resp = DocumentoResponse(**docs_map[doc_id_str])
        elif "documentos" in r and r["documentos"]:  # Estructura del mock
            documento_resp = DocumentoResponse(**r["documentos"])
        
        # Mapear similitud (soportando ambas llaves: similarity o similitud)
        similitud = r.get("similarity") or r.get("similitud") or 0.0

        resultados_mapeados.append(
            SearchResultItem(
                chunk_id=r["id"],
                documento_id=r["documento_id"],
                texto=r["texto"],
                pagina=r.get("pagina"),
                chunk_index=r.get("chunk_index", 0),
                metadata=r.get("metadata", {}),
                similitud=similitud,
                documento=documento_resp
            )
        )

    # Calcular costo de embedding de la búsqueda RAG
    tokens_in = estimate_tokens(payload.query)
    emb_cost = estimate_embedding_cost(tokens_in)
    
    # Guardar en request.state
    request.state.tokens_input = tokens_in
    request.state.tokens_output = 0
    request.state.estimated_cost = emb_cost
    request.state.is_search_request = True
    request.state.retrieval_success = len(resultados_mapeados) > 0

    return SearchResponse(
        query=payload.query,
        resultados=resultados_mapeados
    )
