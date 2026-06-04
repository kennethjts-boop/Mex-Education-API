from fastapi import APIRouter, Query, status
from typing import List, Optional
from app.schemas.curriculo import (
    ContenidoResponse,
    PDAResponse,
    RelacionarRequest,
    RelacionarResponse
)
from app.services import curriculo_service

router = APIRouter()

@router.get("/contenidos", response_model=List[ContenidoResponse], status_code=status.HTTP_200_OK, tags=["Currículo Estructurado"])
def get_contenidos(
    modelo: Optional[str] = Query(None, example="NEM"),
    nivel: Optional[str] = Query(None, example="Secundaria"),
    fase: Optional[str] = Query(None, example="Fase 6"),
    grado: Optional[str] = Query(None, example="2"),
    campo_formativo: Optional[str] = Query(None, example="Saberes y Pensamiento Científico")
):
    """
    Retorna la lista de contenidos curriculares oficiales de la NEM.
    Permite filtrar por modelo, nivel, fase, grado y campo formativo.
    """
    filters = {
        "modelo": modelo,
        "nivel": nivel,
        "fase": fase,
        "grado": grado,
        "campo_formativo": campo_formativo
    }
    # Limpiar filtros None
    clean_filters = {k: v for k, v in filters.items() if v is not None}
    return curriculo_service.get_contenidos(clean_filters)

@router.get("/pda", response_model=List[PDAResponse], status_code=status.HTTP_200_OK, tags=["Currículo Estructurado"])
def get_pda(
    modelo: Optional[str] = Query(None, example="NEM"),
    nivel: Optional[str] = Query(None, example="Secundaria"),
    fase: Optional[str] = Query(None, example="Fase 6"),
    grado: Optional[str] = Query(None, example="2"),
    campo_formativo: Optional[str] = Query(None, example="Saberes y Pensamiento Científico"),
    contenido: Optional[str] = Query(None, description="Texto o id del contenido para filtrar sus PDA vinculados")
):
    """
    Retorna la lista de Procesos de Desarrollo de Aprendizaje (PDA) de la NEM.
    Permite filtrar por modelo, nivel, fase, grado, campo formativo y contenido.
    """
    filters = {
        "modelo": modelo,
        "nivel": nivel,
        "fase": fase,
        "grado": grado,
        "campo_formativo": campo_formativo,
        "contenido": contenido
    }
    clean_filters = {k: v for k, v in filters.items() if v is not None}
    return curriculo_service.get_pda(clean_filters)

@router.post("/relacionar", response_model=RelacionarResponse, status_code=status.HTTP_200_OK, tags=["Currículo Estructurado"])
def relacionar_curriculo(payload: RelacionarRequest):
    """
    Vincula un tema pedagógico de interés (ej. "energía solar") con los contenidos 
    y PDA correspondientes de la Nueva Escuela Mexicana, explicando el porqué de la relación.
    """
    return curriculo_service.relacionar_curriculo(
        tema=payload.tema,
        grado=payload.grado,
        nivel=payload.nivel,
        campo_formativo=payload.campo_formativo,
        modelo=payload.modelo
    )
