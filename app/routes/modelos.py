from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter()

@router.get("", tags=["Catálogos"])
def get_modelos() -> List[Dict[str, Any]]:
    """
    Retorna la lista de Modelos Educativos vigentes o de transición en México.
    """
    return [
        {
            "id": "nem_2022",
            "nombre": "Nueva Escuela Mexicana (NEM)",
            "año": 2022,
            "descripcion": "Modelo educativo enfocado en la comunidad-territorio, aprendizaje activo, humanismo y el codiseño curricular.",
            "activo": True
        },
        {
            "id": "aprendizajes_clave_2017",
            "nombre": "Modelo Educativo para la Educación Obligatoria (Aprendizajes Clave)",
            "año": 2017,
            "descripcion": "Modelo basado en competencias clave, campos de formación académica, áreas de desarrollo personal y social y autonomía curricular.",
            "activo": False
        },
        {
            "id": "rseb_2011",
            "nombre": "Reforma Integral de la Educación Básica (RIEB)",
            "año": 2011,
            "descripcion": "Modelo orientado al desarrollo de competencias para la vida y estándares curriculares.",
            "activo": False
        }
    ]
