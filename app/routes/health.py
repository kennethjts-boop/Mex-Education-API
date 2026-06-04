from fastapi import APIRouter
from app.db.supabase import supabase_client

router = APIRouter()

@router.get("", tags=["Salud"])
def get_health():
    """
    Verifica el estado de salud de la API y la conexión con Supabase.
    """
    db_status = "no_configurado"
    if supabase_client is not None:
        try:
            # Intentar hacer una consulta mínima para validar conectividad.
            # Nota: Si la tabla aún no existe en Supabase, esto podría lanzar excepción,
            # pero indica que sí hay conexión al servicio de base de datos.
            supabase_client.table("documentos").select("id").limit(1).execute()
            db_status = "conectado"
        except Exception as e:
            # Si el error es de tabla no encontrada, al menos el cliente se comunicó
            error_msg = str(e)
            if "does not exist" in error_msg or "relation" in error_msg:
                db_status = "conectado (tablas no creadas)"
            else:
                db_status = f"error: {error_msg}"
            
    return {
        "status": "operacional",
        "supabase": db_status
    }
