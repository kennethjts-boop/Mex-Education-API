from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter()

@router.get("", tags=["Catálogos"])
def get_ejes() -> List[Dict[str, Any]]:
    """
    Retorna los siete Ejes Articuladores de la Nueva Escuela Mexicana.
    Los ejes conectan los contenidos curriculares con la realidad social y el contexto del alumno.
    """
    return [
        {
            "id": "inclusion",
            "nombre": "Inclusión",
            "descripcion": "Garantiza el derecho de toda persona a una educación con equidad, valorando la diversidad y eliminando las barreras de aprendizaje."
        },
        {
            "id": "pensamiento_critico",
            "nombre": "Pensamiento Crítico",
            "descripcion": "Desarrolla la capacidad de interrogar la realidad, construir juicios propios y reflexionar sobre la sociedad de forma razonada."
        },
        {
            "id": "interculturalidad_critica",
            "nombre": "Interculturalidad Crítica",
            "descripcion": "Fomenta el diálogo de saberes entre diferentes culturas, reconociendo el valor intrínseco de cada una y cuestionando las asimetrías de poder."
        },
        {
            "id": "igualdad_genero",
            "nombre": "Igualdad de Género",
            "descripcion": "Promueve la igualdad de derechos, responsabilidades y oportunidades para todas y todos, erradicando estereotipos y violencias de género."
        },
        {
            "id": "vida_saludable",
            "nombre": "Vida Saludable",
            "descripcion": "Fomenta el bienestar físico, mental y social a través de hábitos alimentarios saludables, actividad física y cuidado personal y colectivo."
        },
        {
            "id": "apropiacion_culturas_lectura_escritura",
            "nombre": "Apropiación de las culturas a través de la lectura y la escritura",
            "descripcion": "Considera a la lectura y escritura como herramientas fundamentales para conocer, reinterpretar e interactuar con diversas culturas y mundos."
        },
        {
            "id": "artes_experiencias_esteticas",
            "nombre": "Artes y experiencias estéticas",
            "descripcion": "Valora la sensibilidad, creatividad y apreciación del arte y la belleza en la vida cotidiana como parte fundamental de la formación humana."
        }
    ]
