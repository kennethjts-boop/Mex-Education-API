import os
import sys
import uuid
import hashlib
import logging
import argparse
from typing import Dict, Any, List

# Configurar sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.supabase import get_supabase_client
from app.services.nem_search import get_embedding
from app.services.ingestion import load_local_registry, save_local_registry, _save_local_simulated_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_calendar_manual")

CALENDAR_TEXT = """Calendario Escolar Oficial de la Secretaría de Educación Pública (SEP) para el Ciclo Escolar 2025-2026 en Educación Básica.
Este calendario oficial rige para escuelas públicas y particulares de Educación Básica (Preescolar, Primaria y Secundaria) incorporadas al Sistema Educativo Nacional en toda la República Mexicana.

Detalles Generales del Calendario Escolar 2025-2026:
- Ciclo Escolar: 2025-2026
- Nivel Educativo: Educación Básica
- Días efectivos de clase: 185 días efectivos de clase.

Hitos de Inicio y Fin de Clases:
- Inicio de clases / Apertura del ciclo escolar: Lunes 25 de agosto de 2025.
- Cierre del ciclo escolar / Fin de clases del ciclo escolar 2025-2026: Miércoles 15 de julio de 2026.

Fechas de las Sesiones del Consejo Técnico Escolar (CTE):
Las reuniones del Consejo Técnico Escolar se efectúan el último viernes de cada mes y son días sin clases para los alumnos:
- Primera Sesión Ordinaria de CTE: Viernes 26 de septiembre de 2025
- Segunda Sesión Ordinaria de CTE: Viernes 31 de octubre de 2025
- Tercera Sesión Ordinaria de CTE: Viernes 28 de noviembre de 2025
- Cuarta Sesión Ordinaria de CTE: Viernes 30 de enero de 2026
- Quinta Sesión Ordinaria de CTE: Viernes 27 de febrero de 2026
- Sexta Sesión Ordinaria de CTE: Viernes 27 de marzo de 2026
- Séptima Sesión Ordinaria de CTE: Viernes 29 de mayo de 2026
- Octava Sesión Ordinaria de CTE: Viernes 26 de junio de 2026

Taller Intensivo de Formación Continua para Docentes (fechas sin clases para alumnos):
- Taller Intensivo previo al inicio de clases: Del Lunes 18 al Viernes 22 de agosto de 2025.
- Taller Intensivo para Directivos: Domingo 17 de agosto de 2025.
- Taller Intensivo a mitad de ciclo: Del Lunes 5 al Miércoles 7 de enero de 2026.

Periodos Vacacionales Oficiales del Ciclo 2025-2026:
- Vacaciones de Invierno (Fin de Año): Del Jueves 18 de diciembre de 2025 al Miércoles 7 de enero de 2026. (El regreso oficial a clases de los alumnos es el Jueves 8 de enero de 2026, dado que el personal docente asiste a taller intensivo de formación continua del 5 al 7 de enero).
- Vacaciones de Semana Santa: Del Lunes 30 de marzo al Viernes 10 de abril de 2026. (Regreso oficial a clases para los alumnos el Lunes 13 de abril de 2026).

Días Oficiales de Suspensión de Labores Docentes (Días Feriados):
- Martes 16 de septiembre de 2025 (Día de la Independencia de México)
- Lunes 17 de noviembre de 2025 (Conmemoración del inicio de la Revolución Mexicana)
- Lunes 2 de febrero de 2026 (Conmemoración de la Constitución Política)
- Lunes 16 de marzo de 2026 (Natalicio de Benito Juárez)
- Viernes 1 de mayo de 2026 (Día del Trabajo)
- Martes 5 de mayo de 2026 (Conmemoración de la Batalla de Puebla)
- Viernes 15 de mayo de 2026 (Día del Maestro)

Periodo Oficial de Preinscripciones para el ciclo escolar 2026-2027:
- Preinscripciones para Preescolar, Primer Grado de Primaria y Primer Grado de Secundaria: Del Lunes 2 de febrero al Viernes 13 de febrero de 2026.

Entrega de Boletas de Evaluación del Aprendizaje a Madres, Padres o Tutores:
- Primer Periodo de Entrega: Del 24 al 27 de noviembre de 2025.
- Segundo Periodo de Entrega: Del 23 al 26 de marzo de 2026.
- Tercer Periodo de Entrega: Del 13 al 15 de julio de 2026.

Fechas Oficiales de Descarga Administrativa para Docentes (sin clases para alumnos):
- Primera fecha de Descarga Administrativa: Viernes 14 de noviembre de 2025.
- Segunda fecha de Descarga Administrativa: Viernes 20 de marzo de 2026.
- Tercera fecha de Descarga Administrativa: Viernes 10 de julio de 2026.
"""

CHUNKS_TEXTS = [
    # Chunk 0: Texto completo para búsquedas generales
    CALENDAR_TEXT,
    
    # Chunk 1: Inicio, fin y días de clase
    """Calendario Escolar SEP 2025-2026 - Inicio, fin de clases y días efectivos de clase.
- Ciclo Escolar: 2025-2026 para Educación Básica.
- Días efectivos de clase: El calendario escolar oficial de la SEP contempla 185 días efectivos de clase.
- Inicio del ciclo escolar / Inicio de clases: Lunes 25 de agosto de 2025.
- Fin de clases / Fin del ciclo escolar 2025-2026: Miércoles 15 de julio de 2026.
- Este calendario oficial rige en toda la República Mexicana.""",

    # Chunk 2: Consejos Técnicos Escolares (CTE) y taller intensivo
    """Calendario Escolar SEP 2025-2026 - Fechas de las Sesiones del Consejo Técnico Escolar (CTE) y Taller Intensivo de Formación Continua para Docentes.
¿Cuándo son los consejos técnicos escolares? Las reuniones del Consejo Técnico Escolar (CTE) se efectúan el último viernes de cada mes. Son días de suspensión de clases para los alumnos:
- Primera Sesión Ordinaria de CTE: Viernes 26 de septiembre de 2025
- Segunda Sesión Ordinaria de CTE: Viernes 31 de octubre de 2025
- Tercera Sesión Ordinaria de CTE: Viernes 28 de noviembre de 2025
- Cuarta Sesión Ordinaria de CTE: Viernes 30 de enero de 2026
- Quinta Sesión Ordinaria de CTE: Viernes 27 de febrero de 2026
- Sexta Sesión Ordinaria de CTE: Viernes 27 de marzo de 2026
- Séptima Sesión Ordinaria de CTE: Viernes 29 de mayo de 2026
- Octava Sesión Ordinaria de CTE: Viernes 26 de junio de 2026
¿Cuándo hay taller intensivo de formación continua para docentes?
- Del 18 al 22 de agosto de 2025 (taller intensivo previo al inicio de clases).
- Domingo 17 de agosto de 2025 (taller para directivos).
- Del 5 al 7 de enero de 2026 (taller intensivo de formación continua).""",

    # Chunk 3: Vacaciones Generales
    """Calendario Escolar SEP 2025-2026 - Vacaciones escolares de invierno 2025-2026 y vacaciones de semana santa 2026.
¿Cuándo son los periodos vacacionales oficiales del ciclo escolar 2025-2026 en educación básica?
- Primer periodo: Vacaciones de invierno (vacaciones navideñas) del Jueves 18 de diciembre de 2025 al Miércoles 7 de enero de 2026.
- Segundo periodo: Vacaciones de semana santa 2026 del Lunes 30 de marzo al Viernes 10 de abril de 2026.""",

    # Chunk 4: Vacaciones de Invierno (Enfoque A)
    """Calendario Escolar SEP 2025-2026 - Vacaciones de invierno 2025-2026 (fin de año y fiestas navideñas).
¿Cuándo inician y terminan las vacaciones de invierno en el ciclo escolar 2025-2026?
- Las vacaciones de invierno 2025-2026 inician de forma oficial el Jueves 18 de diciembre de 2025.
- Concluyen el Miércoles 7 de enero de 2026.
- Los alumnos de educación básica regresan a clases el Jueves 8 de enero de 2026, ya que los docentes asisten a taller intensivo del 5 al 7 de enero.""",

    # Chunk 5: Vacaciones de Invierno y Regreso a Clases (Enfoque B)
    """Calendario Escolar SEP 2025-2026 - Vacaciones de invierno 2025-2026 y regreso a clases.
- Fechas de las vacaciones de invierno 2025-2026: Del 18 de diciembre de 2025 al 7 de enero de 2026.
- Suspensión de labores y vacaciones navideñas oficiales.
- Fecha oficial de regreso a clases después de vacaciones de invierno: Jueves 8 de enero de 2026.""",

    # Chunk 6: Vacaciones de Semana Santa 2026
    """Calendario Escolar SEP 2025-2026 - Vacaciones de Semana Santa 2026.
¿Cuándo inician y terminan las vacaciones de semana santa en el ciclo escolar 2025-2026?
- Las vacaciones de Semana Santa 2026 inician el Lunes 30 de marzo de 2026.
- Concluyen el Viernes 10 de abril de 2026.
- El regreso oficial a clases es el Lunes 13 de abril de 2026.""",

    # Chunk 7: Preinscripciones y Descarga Administrativa
    """Calendario Escolar SEP 2025-2026 - Fechas de Preinscripciones 2026 y Descarga Administrativa 2025-2026.
¿Cuándo son las preinscripciones para el ciclo escolar 2026-2027 en preescolar, primer grado de primaria y primer grado de secundaria?
- Periodo de Preinscripciones oficial: Del Lunes 2 de febrero al Viernes 13 de febrero de 2026.
¿Cuándo hay descarga administrativa en el ciclo escolar 2025-2026?
- Primera descarga administrativa: Viernes 14 de noviembre de 2025
- Segunda descarga administrativa: Viernes 20 de marzo de 2026
- Tercera descarga administrativa: Viernes 10 de julio de 2026
(En los días de descarga administrativa no hay clases para los alumnos).""",

    # Chunk 8: Suspensión de labores docentes (días feriados) y entrega de boletas
    """Calendario Escolar SEP 2025-2026 - Días Oficiales de Suspensión de Labores Docentes (Días Feriados) y Entrega de Boletas.
¿Cuáles son los días oficiales de suspensión de labores docentes (días feriados)?
- Martes 16 de septiembre de 2025 (Día de la Independencia de México)
- Lunes 17 de noviembre de 2025 (Revolución Mexicana)
- Lunes 2 de febrero de 2026 (Constitución de México)
- Lunes 16 de marzo de 2026 (Natalicio de Benito Juárez)
- Viernes 1 de mayo de 2026 (Día del Trabajo)
- Martes 5 de mayo de 2026 (Batalla de Puebla)
- Viernes 15 de mayo de 2026 (Día del Maestro)
¿Cuándo es la entrega de boletas de evaluación del aprendizaje a madres, padres o tutores?
- Primer Periodo de Entrega: Del 24 al 27 de noviembre de 2025.
- Segundo Periodo de Entrega: Del 23 al 26 de marzo de 2026.
- Tercer Periodo de Entrega: Del 13 al 15 de julio de 2026."""
]

def run():
    parser = argparse.ArgumentParser(description="Script para ingestar manualmente el Calendario Escolar SEP 2025-2026.")
    parser.add_argument("--force", action="store_true", help="Forzar el reemplazo del documento si ya existe.")
    args = parser.parse_args()

    supabase = get_supabase_client()
    if supabase is None:
        logger.error("Supabase no está configurado.")
        sys.exit(1)

    titulo = "Calendario Escolar SEP 2025-2026"
    tipo_documento = "Calendario Escolar"

    logger.info(f"Buscando si ya existe un documento con título '{titulo}'...")
    res = supabase.table("documentos").select("*").eq("titulo", titulo).eq("tipo_documento", tipo_documento).execute()
    existing_docs = res.data

    if existing_docs:
        doc = existing_docs[0]
        doc_id = doc["id"]
        logger.info(f"Documento encontrado con ID: {doc_id} y estado '{doc.get('estado')}'")
        if not args.force:
            logger.info("El documento ya existe y no se especificó --force. Omitiendo ingesta.")
            sys.exit(0)
        else:
            logger.info(f"Opción --force activa. Procediendo a eliminar documento anterior con ID: {doc_id}...")
            # Eliminar documento (las chunks se eliminan en cascada en Supabase)
            try:
                supabase.table("documentos").delete().eq("id", doc_id).execute()
                logger.info("Eliminado exitosamente de la tabla documentos en Supabase.")
            except Exception as e:
                logger.error(f"Error al eliminar de Supabase: {e}")
                sys.exit(1)

            # Limpiar registro local simulado si existe
            try:
                local_docs = load_local_registry()
                updated_local = [d for d in local_docs if str(d.get("id")) != str(doc_id)]
                if len(local_docs) != len(updated_local):
                    save_local_registry(updated_local)
                    logger.info("Eliminado del registro local documentos_registry.json.")
                
                ingested_json_path = f"data/ingested_{doc_id}.json"
                if os.path.exists(ingested_json_path):
                    os.remove(ingested_json_path)
                    logger.info(f"Eliminado archivo local de simulación: {ingested_json_path}")
            except Exception as e:
                logger.error(f"Error al limpiar registros locales: {e}")
    else:
        logger.info("No se encontró ningún documento previo. Procediendo con la creación...")

    # Generar metadatos e ID
    new_doc_id = str(uuid.uuid4())
    file_hash = hashlib.sha256(CALENDAR_TEXT.encode("utf-8")).hexdigest()

    doc_metadata = {
        "id": new_doc_id,
        "titulo": titulo,
        "modelo": "NEM_2022",
        "nivel": "Educación Básica",
        "fase": "Todas",
        "grado": "Todos",
        "campo_formativo": "General",
        "tipo_documento": tipo_documento,
        "storage_path": f"manual/Calendario_Escolar_SEP_2025-2026.txt",
        "hash": file_hash,
        "estado": "completed"
    }

    logger.info(f"Registrando nuevo documento en Supabase (ID: {new_doc_id})...")
    try:
        supabase.table("documentos").insert(doc_metadata).execute()
        logger.info("Documento insertado correctamente.")
    except Exception as e:
        logger.error(f"Error al insertar en la tabla documentos: {e}")
        sys.exit(1)

    logger.info(f"Generando embeddings para los {len(CHUNKS_TEXTS)} fragmentos de calendario...")
    
    chunk_payloads = []
    chunk_metadata = {
        "modelo": "NEM_2022",
        "nivel": "Educación Básica",
        "fase": "Todas",
        "grado": "Todos",
        "campo_formativo": "General",
        "tipo_documento": tipo_documento
    }

    for idx, text in enumerate(CHUNKS_TEXTS):
        logger.info(f"Generando embedding para fragmento {idx}...")
        embedding = get_embedding(text)
        
        chunk_id = str(uuid.uuid4())
        chunk_payload = {
            "id": chunk_id,
            "documento_id": new_doc_id,
            "texto": text,
            "pagina": 1,
            "chunk_index": idx,
            "embedding": embedding,
            "metadata": chunk_metadata
        }
        chunk_payloads.append(chunk_payload)

    logger.info("Guardando chunks vectorizados en la tabla chunks_nem de Supabase...")
    try:
        supabase.table("chunks_nem").insert(chunk_payloads).execute()
        logger.info(f"¡{len(chunk_payloads)} chunks vectoriales guardados con éxito!")
    except Exception as e:
        logger.error(f"Error al guardar los chunks en Supabase: {e}")
        # Deshacer inserción de documento para consistencia
        supabase.table("documentos").delete().eq("id", new_doc_id).execute()
        sys.exit(1)

    # Registrar localmente para simulación/resiliencia local
    logger.info("Guardando copia del documento en registro y archivos locales...")
    try:
        local_doc_data = {
            "id": new_doc_id,
            "titulo": titulo,
            "modelo": "NEM_2022",
            "nivel": "Educación Básica",
            "fase": "Todas",
            "grado": "Todos",
            "campo_formativo": "General",
            "tipo_documento": tipo_documento,
            "storage_path": doc_metadata["storage_path"],
            "hash": file_hash,
            "estado": "completed",
            "nombre_original": "Calendario_Escolar_SEP_2025-2026.txt",
            "nombre_sanitizado": "Calendario_Escolar_SEP_2025-2026.txt",
            "extension": "txt",
            "mime_type": "text/plain",
            "tamano": len(CALENDAR_TEXT),
            "created_at": doc_metadata.get("created_at", "")
        }
        # Registrar en el JSON de documentos_registry.json
        load_docs = load_local_registry()
        load_docs.append(local_doc_data)
        save_local_registry(load_docs)

        # Guardar en data/ingested_<doc_id>.json
        _save_local_simulated_json(titulo, uuid.UUID(new_doc_id), chunk_payloads)
        logger.info("Guardado local exitoso.")
    except Exception as e:
        logger.error(f"Error al registrar localmente: {e}")

    logger.info("🎉 ¡Proceso de ingesta manual del Calendario finalizado con éxito!")

if __name__ == "__main__":
    run()
