import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.schemas.documentos import DocumentoCreate, IngestionResult, DocumentoResponse, ChunkNemBase
from app.services.chunking import split_text_by_tokens
from app.services.nem_search import get_embedding
from app.db.supabase import supabase_client

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

@router.post("", response_model=IngestionResult, status_code=201, tags=["Documentos"])
def create_documento(payload: DocumentoCreate):
    """
    Ingesta un nuevo documento educativo, realiza el chunking automático (~700 tokens con overlap de 100),
    genera los embeddings vectoriales (OpenAI) y guarda la información en Supabase (si está configurado).
    
    Si las variables de entorno de Supabase o OpenAI no están configuradas,
    el endpoint procesa la información y simula la respuesta exitosa para facilitar pruebas locales.
    """
    # 1. Realizar chunking de texto
    chunks_data = split_text_by_tokens(payload.texto_completo, chunk_size=700, overlap=100)
    total_chunks = len(chunks_data)
    
    documento_id = uuid.uuid4()
    now = datetime.utcnow()
    
    # Estructurar respuesta del documento
    doc_response = DocumentoResponse(
        id=documento_id,
        titulo=payload.titulo,
        modelo=payload.modelo,
        nivel=payload.nivel,
        fase=payload.fase,
        grado=payload.grado,
        campo_formativo=payload.campo_formativo,
        tipo_documento=payload.tipo_documento,
        storage_path=payload.storage_path,
        created_at=now
    )
    
    # 2. Generar embeddings y estructurar objetos de chunk
    processed_chunks = []
    db_chunks_to_insert = []
    
    for chunk in chunks_data:
        chunk_id = uuid.uuid4()
        embedding = get_embedding(chunk["texto"])
        
        chunk_metadata = {
            "modelo": payload.modelo,
            "nivel": payload.nivel,
            "fase": payload.fase,
            "grado": payload.grado
        }
        if payload.campo_formativo:
            chunk_metadata["campo_formativo"] = payload.campo_formativo
            
        # Modelo base de salida
        processed_chunks.append(
            ChunkNemBase(
                documento_id=documento_id,
                texto=chunk["texto"],
                pagina=1,  # Valor default para fase 1, puede extenderse a futuro
                chunk_index=chunk["chunk_index"],
                metadata=chunk_metadata
            )
        )
        
        # Modelo con embedding para inserción en DB
        db_chunks_to_insert.append({
            "id": str(chunk_id),
            "documento_id": str(documento_id),
            "texto": chunk["texto"],
            "pagina": 1,
            "chunk_index": chunk["chunk_index"],
            "embedding": embedding,
            "metadata": chunk_metadata
        })
        
    # 3. Intentar persistencia en Supabase
    if supabase_client is not None:
        try:
            # Insertar documento en DB
            doc_db_payload = {
                "id": str(documento_id),
                "titulo": payload.titulo,
                "modelo": payload.modelo,
                "nivel": payload.nivel,
                "fase": payload.fase,
                "grado": payload.grado,
                "campo_formativo": payload.campo_formativo,
                "tipo_documento": payload.tipo_documento,
                "storage_path": payload.storage_path
            }
            supabase_client.table("documentos").insert(doc_db_payload).execute()
            
            # Insertar chunks en batch
            if db_chunks_to_insert:
                supabase_client.table("chunks_nem").insert(db_chunks_to_insert).execute()
                
            return IngestionResult(
                mensaje="Documento e indexación vectorizada guardada correctamente en Supabase.",
                documento=doc_response,
                total_chunks=total_chunks,
                chunks=processed_chunks
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error al guardar datos en Supabase: {error_msg}")
            
            # Retornamos el resultado localmente indicando el error de red o de DB
            return IngestionResult(
                mensaje=f"Procesado localmente, pero falló persistencia en Supabase: {error_msg}",
                documento=doc_response,
                total_chunks=total_chunks,
                chunks=processed_chunks
            )
    else:
        # Si no hay Supabase
        return IngestionResult(
            mensaje="Procesamiento local exitoso. Modo SIMULACIÓN activo (Supabase no configurado).",
            documento=doc_response,
            total_chunks=total_chunks,
            chunks=processed_chunks
        )
