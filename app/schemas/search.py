from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from app.schemas.documentos import DocumentoResponse

class SearchRequest(BaseModel):
    query: str = Field(..., example="¿Cuáles son los campos formativos en la Fase 3?")
    limit: Optional[int] = Field(default=5, ge=1, le=50)
    match_threshold: Optional[float] = Field(default=0.3, ge=0.0, le=1.0)
    # Filtros opcionales
    modelo: Optional[str] = Field(None, example="NEM")
    nivel: Optional[str] = Field(None, example="Primaria")
    fase: Optional[str] = Field(None, example="Fase 3")
    grado: Optional[str] = Field(None, example="1er Grado")
    campo_formativo: Optional[str] = Field(None, example="Lenguajes")
    tipo_documento: Optional[str] = Field(None, example="Plan de Estudio")

class SearchResultItem(BaseModel):
    chunk_id: UUID
    documento_id: UUID
    texto: str
    pagina: Optional[int] = None
    chunk_index: int
    metadata: Dict[str, Any]
    similitud: float
    documento: Optional[DocumentoResponse] = None

class SearchResponse(BaseModel):
    query: str
    resultados: List[SearchResultItem]
