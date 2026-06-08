from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class PlaneacionRequest(BaseModel):
    tema: str = Field(..., example="energía solar")
    grado: str = Field(..., example="2")
    nivel: str = Field(..., example="Secundaria")
    campo_formativo: str = Field(..., example="Saberes y Pensamiento Científico")
    duracion_dias: int = Field(default=5, ge=1, le=15, example=5)
    modelo: str = Field(default="NEM", example="NEM")

class PlaneacionMomento(BaseModel):
    dia: int
    actividades: List[str]

class PlaneacionContenido(BaseModel):
    titulo: str
    objetivo: str
    pda_relacionados: List[str]
    momentos: List[PlaneacionMomento]
    evaluacion: str
    materiales: List[str]

class ChunkMinimalResponse(BaseModel):
    id: str
    documento_titulo: str
    pagina: Optional[int]
    texto: str
    similitud: float

class PlaneacionMetadata(BaseModel):
    latency_ms: float
    estimated_cost: float
    retrieval_success: bool
    structured_curriculum_success: bool
    chunks_count: int
    context_chars: int
    cache_hit: bool

class PlaneacionResponse(BaseModel):
    planeacion: PlaneacionContenido
    retrieval_success: bool
    structured_curriculum_success: bool
    chunks_utilizados: List[ChunkMinimalResponse]
    contenido_relacionado: List[str] = Field(default_factory=list)
    pda_relacionados: List[str] = Field(default_factory=list)
    curriculum_source: str = Field(default="RAG")
    source_warning: Optional[str] = None
    metadata: PlaneacionMetadata


class PlaneacionDebugResponse(BaseModel):
    query_generada: str
    chunks_utilizados: List[ChunkMinimalResponse]
    prompt_construido: str
    contenido_relacionado: List[str] = Field(default_factory=list)
    pda_relacionados: List[str] = Field(default_factory=list)
    curriculum_source: str = Field(default="RAG")
    source_warning: Optional[str] = None
    structured_curriculum_success: bool = False
