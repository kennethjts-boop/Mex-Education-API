import logging
import time
import json
from fastapi import APIRouter, HTTPException, status, Request
from app.schemas.planeacion import (
    PlaneacionRequest, 
    PlaneacionResponse, 
    PlaneacionDebugResponse,
    PlaneacionContenido,
    ChunkMinimalResponse,
    PlaneacionMetadata
)
from app.services.plan_generator import generate_lesson_plan, RetrievalEmptyException
from app.services.cost_estimator import estimate_chat_cost, estimate_embedding_cost, estimate_tokens
from app.services.evaluation_service import calculate_heuristic_score, save_generation_evaluation

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

@router.post("/generar", response_model=PlaneacionResponse, status_code=status.HTTP_200_OK, tags=["Planeaciones"])
def generar_planeacion(payload: PlaneacionRequest, request: Request):
    """
    Genera una planeación curricular didáctica utilizando RAG Híbrido.
    Busca de forma obligatoria coincidencias en el currículo estructurado (contenidos y PDA) 
    y en el corpus de texto (chunks PDF).
    
    Si RAG falla pero se ubican contenidos y PDA estructurados, aprueba la generación didáctica 
    marcando 'retrieval_success: false' y arrojando una advertencia (source_warning).
    """
    start_time = time.perf_counter()
    try:
        planeacion_data, chunks_utilizados, prompt_construido, query_generada, meta = generate_lesson_plan(
            tema=payload.tema,
            grado=payload.grado,
            nivel=payload.nivel,
            campo_formativo=payload.campo_formativo,
            duracion_dias=payload.duracion_dias,
            modelo=payload.modelo
        )
        
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        
        # 1. Estimar tokens y costos
        in_tokens, out_tokens, chat_cost = estimate_chat_cost(prompt_construido, json.dumps(planeacion_data))
        emb_cost = estimate_embedding_cost(query_generada)
        total_cost = chat_cost + emb_cost
        total_in_tokens = in_tokens + estimate_tokens(query_generada)
        
        # 2. Registrar en request.state para el middleware request_logger
        request.state.tokens_input = total_in_tokens
        request.state.tokens_output = out_tokens
        request.state.estimated_cost = total_cost
        request.state.is_generation_request = True
        request.state.retrieval_success = meta["retrieval_success"]
        request.state.fallback_used = (not meta["retrieval_success"] and meta["structured_curriculum_success"])
        
        # 3. Evaluar la planeación generada
        score, notes = calculate_heuristic_score(planeacion_data, payload.duracion_dias)
        save_generation_evaluation(
            endpoint="/planeaciones/generar",
            query=payload.tema,
            retrieval_success=meta["retrieval_success"],
            structured_curriculum_success=meta["structured_curriculum_success"],
            score=score,
            notes=notes
        )
        
        # Mapear estructura de respuesta
        planeacion_contenido = PlaneacionContenido(**planeacion_data)
        chunks_mapeados = [ChunkMinimalResponse(**c) for c in chunks_utilizados]
        
        metadata_obj = PlaneacionMetadata(
            latency_ms=round(latency_ms, 2),
            estimated_cost=round(total_cost, 6),
            retrieval_success=meta["retrieval_success"],
            structured_curriculum_success=meta["structured_curriculum_success"]
        )
        
        return PlaneacionResponse(
            planeacion=planeacion_contenido,
            retrieval_success=meta["retrieval_success"],
            structured_curriculum_success=meta["structured_curriculum_success"],
            chunks_utilizados=chunks_mapeados,
            contenido_relacionado=meta["contenido_relacionado"],
            pda_relacionados=meta["pda_relacionados"],
            curriculum_source=meta["curriculum_source"],
            source_warning=meta["source_warning"],
            metadata=metadata_obj
        )

        
    except RetrievalEmptyException as e:
        logger.warning(f"Error de generación (RAG Híbrido): {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al generar planeación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno en el motor de generación: {e}"
        )

@router.post("/debug", response_model=PlaneacionDebugResponse, status_code=status.HTTP_200_OK, tags=["Planeaciones"])
def debug_planeacion(payload: PlaneacionRequest):
    """
    Ruta técnica de auditoría para el flujo RAG Híbrido.
    Realiza la búsqueda y devuelve el prompt final construido, los chunks y metadatos curriculares localizados.
    """
    try:
        _, chunks_utilizados, prompt_construido, query_generada, meta = generate_lesson_plan(
            tema=payload.tema,
            grado=payload.grado,
            nivel=payload.nivel,
            campo_formativo=payload.campo_formativo,
            duracion_dias=payload.duracion_dias,
            modelo=payload.modelo
        )
        
        chunks_mapeados = [ChunkMinimalResponse(**c) for c in chunks_utilizados]
        
        return PlaneacionDebugResponse(
            query_generada=query_generada,
            chunks_utilizados=chunks_mapeados,
            prompt_construido=prompt_construido,
            contenido_relacionado=meta["contenido_relacionado"],
            pda_relacionados=meta["pda_relacionados"],
            curriculum_source=meta["curriculum_source"],
            source_warning=meta["source_warning"],
            structured_curriculum_success=meta["structured_curriculum_success"]
        )
        
    except RetrievalEmptyException as e:
        logger.warning(f"Error de depuración (RAG Híbrido): {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado al depurar planeación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno de depuración: {e}"
        )
