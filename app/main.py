from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import health, modelos, campos, ejes, documentos, buscar, planeaciones, curriculo, metrics
from app.middleware.request_logger import RequestLoggerMiddleware
from app.core.config import settings

app = FastAPI(
    title="Nueva Escuela Mexicana API (NEM-API)",
    description="API base y motor de búsqueda semántica (RAG) para planes, programas y documentos de la Nueva Escuela Mexicana.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Registrar middleware de observabilidad (se ejecuta antes de CORS si se añade después, o viceversa)
app.add_middleware(RequestLoggerMiddleware)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modificar en producción para mayor seguridad
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de rutas de la aplicación
app.include_router(health.router, prefix="/health")
app.include_router(modelos.router, prefix="/modelos")
app.include_router(campos.router, prefix="/campos")
app.include_router(ejes.router, prefix="/ejes")
app.include_router(documentos.router, prefix="/documentos")
app.include_router(buscar.router, prefix="/buscar")
app.include_router(planeaciones.router, prefix="/planeaciones")
app.include_router(curriculo.router, prefix="/curriculo")
app.include_router(metrics.router, prefix="/metrics")


@app.get("/", tags=["General"])
def read_root():
    """
    Ruta raíz para bienvenida y estado básico.
    """
    return {
        "proyecto": "mex-education-api",
        "descripcion": "API base para la Nueva Escuela Mexicana",
        "fase": 1,
        "documentacion": "/docs",
        "estado": "activo",
        "ambiente": settings.APP_ENV
    }
