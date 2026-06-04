from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter()

@router.get("", tags=["Catálogos"])
def get_campos() -> List[Dict[str, Any]]:
    """
    Retorna los cuatro Campos Formativos del Plan de Estudios 2022 de la Nueva Escuela Mexicana.
    """
    return [
        {
            "id": "lenguajes",
            "nombre": "Lenguajes",
            "descripcion": "Busca el aprendizaje y desarrollo de la expresión, comunicación y comprensión oral, escrita y artística (Español, Lenguas Indígenas, Lengua de Señas, Inglés y Artes)."
        },
        {
            "id": "saberes_pensamiento_cientifico",
            "nombre": "Saberes y Pensamiento Científico",
            "descripcion": "Favorece la indagación, razonamiento, sistematización y resolución de problemas utilizando las matemáticas y las ciencias experimentales en contextos reales."
        },
        {
            "id": "etica_naturaleza_sociedades",
            "nombre": "Ética, Naturaleza y Sociedades",
            "descripcion": "Aborda la relación del ser humano con la sociedad y la naturaleza, promoviendo el cuidado ambiental, civismo, geografía, historia y derechos humanos."
        },
        {
            "id": "humano_comunitario",
            "nombre": "De lo Humano y lo Comunitario",
            "descripcion": "Centrado en el autoconocimiento, la vida saludable, la educación física, la tecnología y el sentido de comunidad e identidad."
        }
    ]
