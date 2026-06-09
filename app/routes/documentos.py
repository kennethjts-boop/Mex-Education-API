import uuid
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.concurrency import run_in_threadpool
import asyncio
import os

from app.schemas.documentos import DocumentoCreate, IngestionResult, DocumentoResponse, ChunkNemBase
from app.services.chunking import split_text_by_tokens
from app.services.nem_search import get_embedding
from app.db.supabase import supabase_client
from app.services.ingestion import process_single_file_ingestion
from app.core.config import settings

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


@router.post("/upload", status_code=200, tags=["Documentos"])
async def upload_documento_file(
    file: UploadFile = File(...),
    modelo: str = Form(...),
    nivel: str = Form(...),
    fase: str = Form(...),
    grado: str = Form(...),
    grado_label: Optional[str] = Form(None),
    campo_formativo: Optional[str] = Form(None),
    tipo_documento: str = Form(...),
    estado: str = Form("completed")
):
    """
    Carga y procesa un único archivo (PDF, DOCX, TXT, CSV, XLSX, PNG, JPG, JPEG) con metadatos asociados.
    Valida tamaño, extensión, calcula hash de duplicados, extrae texto, fragmenta y genera embeddings.
    """
    # Validar que no sea un archivo vacío en FastAPI
    if file.size is not None and file.size == 0:
        raise HTTPException(status_code=400, detail="El archivo subido está vacío.")
        
    # Validar extensión
    filename = file.filename or "archivo"
    ext = os.path.splitext(filename)[1].replace(".", "").lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Extensión .{ext} no permitida. Formatos válidos: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
        
    # Validar tamaño máximo
    file_bytes = await file.read()
    if len(file_bytes) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400, 
            detail=f"El archivo excede el tamaño máximo permitido de {settings.MAX_FILE_SIZE_MB}MB."
        )
        
    # Procesar archivo en un hilo separado para evitar bloquear el loop de eventos asíncrono
    result = await run_in_threadpool(
        process_single_file_ingestion,
        file_bytes=file_bytes,
        original_filename=filename,
        mime_type=file.content_type or "application/octet-stream",
        modelo=modelo,
        nivel=nivel,
        fase=fase,
        grado=grado,
        campo_formativo=campo_formativo,
        tipo_documento=tipo_documento,
        extra_metadata={
            "grado_label": grado_label or f"{grado}° grado",
            "estado": estado
        }
    )
    
    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=result.get("error"))
        
    return result


@router.post("/upload-batch", status_code=200, tags=["Documentos"])
async def upload_documento_batch(
    files: List[UploadFile] = File(...),
    modelo: str = Form(...),
    nivel: str = Form(...),
    fase: str = Form(...),
    grado: str = Form(...),
    grado_label: Optional[str] = Form(None),
    campo_formativo: Optional[str] = Form(None),
    tipo_documento: str = Form(...),
    estado: str = Form("completed"),
    concurrency: int = Form(3)
):
    """
    Carga masiva de múltiples archivos en una sola llamada de API.
    Aplica concurrencia controlada en el servidor (usando semáforos) y devuelve el estado de cada archivo del lote.
    """
    if not files:
        raise HTTPException(status_code=400, detail="Debe seleccionar al menos un archivo para el lote.")
        
    if len(files) > settings.MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"El lote supera la cantidad máxima permitida de {settings.MAX_BATCH_SIZE} archivos."
        )
        
    # Limitar concurrencia en el servidor
    sem = asyncio.Semaphore(max(1, min(concurrency, 10)))
    
    async def process_file_task(file: UploadFile):
        async with sem:
            filename = file.filename or "archivo"
            ext = os.path.splitext(filename)[1].replace(".", "").lower()
            
            # Validar extensión
            if ext not in settings.ALLOWED_EXTENSIONS:
                return {
                    "fileName": filename,
                    "status": "failed",
                    "error": f"Extensión .{ext} no permitida."
                }
                
            file_bytes = await file.read()
            # Validar tamaño
            if len(file_bytes) == 0:
                return {
                    "fileName": filename,
                    "status": "failed",
                    "error": "El archivo está vacío."
                }
            if len(file_bytes) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
                return {
                    "fileName": filename,
                    "status": "failed",
                    "error": f"El archivo supera el límite de {settings.MAX_FILE_SIZE_MB}MB."
                }
                
            # Procesar el archivo en el thread pool de FastAPI
            return await run_in_threadpool(
                process_single_file_ingestion,
                file_bytes=file_bytes,
                original_filename=filename,
                mime_type=file.content_type or "application/octet-stream",
                modelo=modelo,
                nivel=nivel,
                fase=fase,
                grado=grado,
                campo_formativo=campo_formativo,
                tipo_documento=tipo_documento,
                extra_metadata={
                    "grado_label": grado_label or f"{grado}° grado",
                    "estado": estado
                }
            )
            
    # Ejecutar todas las tareas en paralelo
    tasks = [process_file_task(f) for f in files]
    results = await asyncio.gather(*tasks)
    
    # Compilar resultados
    total = len(files)
    uploaded = sum(1 for r in results if r.get("status") == "completed")
    failed = sum(1 for r in results if r.get("status") == "failed")
    duplicated = sum(1 for r in results if r.get("status") == "duplicated")
    
    return {
        "success": True,
        "total": total,
        "uploaded": uploaded,
        "failed": failed,
        "duplicated": duplicated,
        "results": results
    }


@router.get("/upload-ui", response_class=HTMLResponse, tags=["UI"])
def get_upload_ui():
    """
    Retorna el Dashboard interactivo de carga masiva de archivos.
    """
    ui_path = os.path.join("app", "static", "upload_ui.html")
    if not os.path.exists(ui_path):
        raise HTTPException(
            status_code=404, 
            detail="La interfaz gráfica de carga masiva no se encuentra en el servidor."
        )
        
    with open(ui_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    return html_content
