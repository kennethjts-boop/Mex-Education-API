import os
import json
import logging
from typing import Dict, Any, Tuple, List
from datetime import datetime
from uuid import UUID
from app.db.supabase import supabase_client, is_supabase_configured

logger = logging.getLogger("uvicorn.error")

def calculate_heuristic_score(plan: Dict[str, Any], requested_duration: int = 5) -> Tuple[float, str]:
    """
    Calcula una calificación heurística de calidad de 0.0 a 10.0 para una planeación didáctica.
    Evalúa la presencia de campos críticos, estructura de momentos, materiales y PDAs.
    Retorna: (calificación, notas_de_auditoria)
    """
    if not plan:
        return 0.0, "Planeación vacía."
        
    score = 0.0
    notes = []
    
    # 1. Título (Máx 2.5 pts)
    titulo = plan.get("titulo")
    if titulo:
        score += 2.0
        if str(titulo).strip() and len(str(titulo).strip()) > 5:
            score += 0.5
        else:
            notes.append("Título muy corto o vacío.")
    else:
        notes.append("Falta campo 'titulo'.")
        
    # 2. Objetivo (Máx 2.0 pts)
    objetivo = plan.get("objetivo")
    if objetivo:
        score += 1.5
        if str(objetivo).strip() and len(str(objetivo).strip()) > 15:
            score += 0.5
        else:
            notes.append("Objetivo muy corto o vacío.")
    else:
        notes.append("Falta campo 'objetivo'.")
        
    # 3. Momentos y Duración (Máx 2.5 pts)
    momentos = plan.get("momentos")
    if momentos and isinstance(momentos, list):
        score += 1.5
        if len(momentos) > 0:
            if len(momentos) == requested_duration:
                score += 1.0
            else:
                score += 0.5
                notes.append(f"Cantidad de momentos ({len(momentos)}) difiere de duración solicitada ({requested_duration}).")
        else:
            notes.append("Lista de momentos está vacía.")
    else:
        notes.append("Falta la lista de 'momentos'.")
        
    # 4. Evaluación (Máx 1.5 pts)
    evaluacion = plan.get("evaluacion")
    if evaluacion:
        score += 1.0
        if str(evaluacion).strip() and len(str(evaluacion).strip()) > 10:
            score += 0.5
        else:
            notes.append("Evaluación vacía o muy simple.")
    else:
        notes.append("Falta campo 'evaluacion'.")
        
    # 5. Materiales (Máx 1.0 pts)
    materiales = plan.get("materiales")
    if materiales and isinstance(materiales, list):
        if len(materiales) >= 3:
            score += 1.0
        elif len(materiales) > 0:
            score += 0.5
            notes.append("La lista de materiales contiene menos de 3 elementos.")
        else:
            notes.append("Lista de materiales vacía.")
    else:
        notes.append("Falta la lista de 'materiales'.")
        
    # 6. PDA relacionados (Máx 0.5 pts)
    pdas = plan.get("pda_relacionados")
    if pdas and isinstance(pdas, list) and len(pdas) > 0:
        score += 0.5
    else:
        notes.append("Falta o está vacía la lista de 'pda_relacionados'.")
        
    notes_str = "; ".join(notes) if notes else "Estructura didáctica excelente."
    return round(score, 2), notes_str

def save_generation_evaluation(
    endpoint: str,
    query: str,
    retrieval_success: bool,
    structured_curriculum_success: bool,
    score: float,
    notes: str
) -> Dict[str, Any]:
    """
    Persiste una evaluación de planeación en Supabase.
    Si Supabase no está disponible, la escribe en un archivo JSON local acumulado.
    """
    record = {
        "endpoint": endpoint,
        "query": query,
        "retrieval_success": retrieval_success,
        "structured_curriculum_success": structured_curriculum_success,
        "score": float(score),
        "notes": notes,
        "created_at": datetime.utcnow().isoformat()
    }
    
    supabase_ready = is_supabase_configured and supabase_client is not None
    
    if supabase_ready:
        try:
            res = supabase_client.table("generation_evaluations").insert(record).execute()
            logger.info("Evaluación de generación guardada con éxito en Supabase.")
            return res.data[0] if res.data else record
        except Exception as e:
            logger.error(f"Error guardando evaluación en Supabase: {e}. Guardando en archivo local.")
            
    # Persistir localmente en data/generation_evaluations.json
    local_dir = "./data"
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, "generation_evaluations.json")
    
    evals = []
    if os.path.exists(local_path):
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                evals = json.load(f)
                if not isinstance(evals, list):
                    evals = []
        except Exception:
            evals = []
            
    record["id"] = f"simulated-eval-uuid-{len(evals)}"
    evals.append(record)
    
    try:
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(evals, f, ensure_ascii=False, indent=2)
        logger.info(f"Evaluación de generación guardada localmente en {local_path}.")
    except Exception as e:
        logger.error(f"No se pudo guardar la evaluación de generación localmente: {e}")
        
    return record
