from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

class DocumentoBase(BaseModel):
    titulo: str = Field(..., example="Plan de Estudio 2022")
    modelo: str = Field(..., example="NEM")
    nivel: str = Field(..., example="Primaria")
    fase: str = Field(..., example="Fase 3")
    grado: str = Field(..., example="1er Grado")
    campo_formativo: Optional[str] = Field(None, example="Lenguajes")
    tipo_documento: str = Field(..., example="Programa Sintético")
    storage_path: Optional[str] = Field(None, example="nem/planes/plan_2022.pdf")

class DocumentoCreate(DocumentoBase):
    texto_completo: str = Field(
        ..., 
        example="Este es el texto completo del documento educativo que se procesará en fragmentos (chunks) para indexar en el sistema..."
    )

class DocumentoResponse(DocumentoBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class ChunkNemBase(BaseModel):
    documento_id: UUID
    texto: str
    pagina: Optional[int] = Field(None, example=12)
    chunk_index: int = Field(..., example=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChunkNemCreate(ChunkNemBase):
    embedding: Optional[List[float]] = Field(None, description="Vector de embedding (1536 dimensiones para OpenAI)")

class ChunkNemResponse(ChunkNemBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class IngestionResult(BaseModel):
    mensaje: str
    documento: DocumentoResponse
    total_chunks: int
    chunks: List[ChunkNemBase]
