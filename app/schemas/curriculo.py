from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID

class ContenidoBase(BaseModel):
    modelo: str = Field(..., example="NEM_2022")
    nivel: str = Field(..., example="Secundaria")
    fase: str = Field(..., example="Fase 6")
    grado: str = Field(..., example="2")
    campo_formativo: str = Field(..., example="Saberes y Pensamiento Científico")
    contenido: str = Field(..., example="Saberes y prácticas para el aprovechamiento de energías y la sustentabilidad")
    descripcion: Optional[str] = Field(None, example="Estudio de las fuentes de energía...")
    fuente: str = Field(..., example="seed_local_validacion")

class ContenidoResponse(ContenidoBase):
    id: UUID

    class Config:
        from_attributes = True

class PDABase(BaseModel):
    contenido_id: UUID
    modelo: str = Field(..., example="NEM_2022")
    nivel: str = Field(..., example="Secundaria")
    fase: str = Field(..., example="Fase 6")
    grado: str = Field(..., example="2")
    campo_formativo: str = Field(..., example="Saberes y Pensamiento Científico")
    contenido: str = Field(..., example="Saberes y prácticas para el aprovechamiento de energías y la sustentabilidad")
    pda: str = Field(..., example="Analiza las características de la energía solar...")
    fuente: str = Field(..., example="seed_local_validacion")

class PDAResponse(PDABase):
    id: UUID

    class Config:
        from_attributes = True

class RelacionarRequest(BaseModel):
    tema: str = Field(..., example="energía solar")
    grado: str = Field(..., example="2")
    nivel: str = Field(..., example="Secundaria")
    campo_formativo: str = Field(..., example="Saberes y Pensamiento Científico")
    modelo: str = Field(default="NEM", example="NEM")

class RelacionarResult(BaseModel):
    contenido: str
    pda: str
    explicacion: str
    score: float
    fuente: str

class RelacionarResponse(BaseModel):
    contenidos_relacionados: List[ContenidoResponse]
    pda_relacionados: List[PDAResponse]
    relaciones: List[RelacionarResult]
