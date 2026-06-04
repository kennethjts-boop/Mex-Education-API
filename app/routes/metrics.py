from fastapi import APIRouter, status
from app.middleware.metrics import system_metrics

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK, tags=["Métricas & Observabilidad"])
def get_health_metrics():
    """
    Devuelve las métricas globales de salud y uso general de la API:
    - avg latency (en ms)
    - total requests
    - success rate (%)
    - average cost (en USD)
    - retrieval success rate (%)
    """
    return system_metrics.get_health_metrics()

@router.get("/generations", status_code=status.HTTP_200_OK, tags=["Métricas & Observabilidad"])
def get_generation_metrics():
    """
    Devuelve métricas específicas del motor generativo RAG Híbrido:
    - total planeaciones
    - retrieval failures
    - average response time (en ms)
    - curriculum fallback usage
    """
    return system_metrics.get_generation_metrics()
