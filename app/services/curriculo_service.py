import os
import json
import logging
import re
from typing import List, Dict, Any, Optional
from uuid import UUID
from app.db.supabase import supabase_client
from app.services.nem_search import normalize_modelo, normalize_nivel, normalize_grado

logger = logging.getLogger("uvicorn.error")

def load_seed_data() -> Dict[str, Any]:
    """Carga el archivo seed JSON local."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    seed_path = os.path.join(base_dir, "data", "seed", "seed_nem_secundaria_fase6.json")
    
    if not os.path.exists(seed_path):
        logger.warning(f"No se encontró el archivo seed en {seed_path}. Retornando vacío.")
        return {"contenidos": []}
        
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error al cargar el seed JSON: {e}")
        return {"contenidos": []}

def get_contenidos(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Retorna la lista de contenidos que coinciden con los filtros especificados.
    Soporta modo Supabase y modo local simulado (offline).
    """
    # Normalizar modelo, nivel y grado si están presentes en los filtros
    if "modelo" in filters and filters["modelo"]:
        filters["modelo"] = normalize_modelo(filters["modelo"])
    if "nivel" in filters and filters["nivel"]:
        filters["nivel"] = normalize_nivel(filters["nivel"])
    if "grado" in filters and filters["grado"]:
        filters["grado"] = normalize_grado(filters["grado"])
        
    is_supabase_ready = (
        supabase_client is not None 
        and "placeholder" not in str(supabase_client.supabase_url)
    )

    if is_supabase_ready:
        try:
            query = supabase_client.table("contenidos_nem").select("*")
            for k, v in filters.items():
                if v is not None:
                    query = query.eq(k, v)
            res = query.execute()
            return res.data
        except Exception as e:
            logger.error(f"Error consultando contenidos en Supabase: {e}. Activando fallback local.")
            
    # Fallback local (Seed JSON)
    seed = load_seed_data()
    filtered = []
    for c in seed.get("contenidos", []):
        match = True
        for k, v in filters.items():
            if v is not None:
                if k == "modelo":
                    if normalize_modelo(v) != normalize_modelo(c.get("modelo")):
                        match = False
                        break
                elif k == "nivel":
                    if normalize_nivel(v) != normalize_nivel(c.get("nivel")):
                        match = False
                        break
                elif k == "grado":
                    if normalize_grado(v) != normalize_grado(c.get("grado")):
                        match = False
                        break
                elif str(c.get(k)) != str(v):
                    match = False
                    break
        if match:
            c_copy = c.copy()
            if "pda" in c_copy:
                del c_copy["pda"]
            filtered.append(c_copy)
    return filtered

def get_pda(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Retorna la lista de PDA que coinciden con los filtros especificados.
    Soporta modo Supabase y modo local simulado (offline).
    """
    if "modelo" in filters and filters["modelo"]:
        filters["modelo"] = normalize_modelo(filters["modelo"])
    if "nivel" in filters and filters["nivel"]:
        filters["nivel"] = normalize_nivel(filters["nivel"])
    if "grado" in filters and filters["grado"]:
        filters["grado"] = normalize_grado(filters["grado"])
        
    is_supabase_ready = (
        supabase_client is not None 
        and "placeholder" not in str(supabase_client.supabase_url)
    )

    if is_supabase_ready:
        try:
            query = supabase_client.table("pda_nem").select("*")
            for k, v in filters.items():
                if v is not None:
                    query = query.eq(k, v)
            res = query.execute()
            return res.data
        except Exception as e:
            logger.error(f"Error consultando PDA en Supabase: {e}. Activando fallback local.")

    # Fallback local (Seed JSON)
    seed = load_seed_data()
    filtered_pdas = []
    
    # Mapear todos los PDA aplanados
    for c in seed.get("contenidos", []):
        for p in c.get("pda", []):
            pda_record = {
                "id": p["id"],
                "contenido_id": c["id"],
                "modelo": c["modelo"],
                "nivel": c["nivel"],
                "fase": c["fase"],
                "grado": c["grado"],
                "campo_formativo": c["campo_formativo"],
                "contenido": c["contenido"],
                "pda": p["pda"],
                "fuente": p["fuente"]
            }
            
            # Aplicar filtros
            match = True
            for k, v in filters.items():
                if v is not None:
                    if k == "modelo":
                        if normalize_modelo(v) != normalize_modelo(pda_record.get("modelo")):
                            match = False
                            break
                    elif k == "nivel":
                        if normalize_nivel(v) != normalize_nivel(pda_record.get("nivel")):
                            match = False
                            break
                    elif k == "grado":
                        if normalize_grado(v) != normalize_grado(pda_record.get("grado")):
                            match = False
                            break
                    elif str(pda_record.get(k)) != str(v):
                        match = False
                        break
            if match:
                filtered_pdas.append(pda_record)
                
    return filtered_pdas

def relacionar_curriculo(
    tema: str,
    grado: str,
    nivel: str,
    campo_formativo: str,
    modelo: str
) -> Dict[str, Any]:
    """
    Busca contenidos y PDA estructurados relacionados con un tema específico en la NEM.
    Calcula la coincidencia por palabras clave e incluye la explicación pedagógica.
    """
    modelo_norm = normalize_modelo(modelo) or "NEM_2022"
    
    # 1. Cargar todos los contenidos con sus PDAs para el grado/nivel/campo
    filters = {
        "modelo": modelo_norm,
        "nivel": nivel,
        "grado": grado,
        "campo_formativo": campo_formativo
    }
    
    # Si estamos en Supabase, recuperamos la estructura
    is_supabase_ready = (
        supabase_client is not None 
        and "placeholder" not in str(supabase_client.supabase_url)
    )
    
    all_structures = []
    if is_supabase_ready:
        try:
            # Obtener contenidos
            contents = get_contenidos(filters)
            for c in contents:
                # Obtener PDAs correspondientes
                pdas = get_pda({"contenido_id": c["id"]})
                c_struct = c.copy()
                c_struct["pda"] = pdas
                all_structures.append(c_struct)
        except Exception as e:
            logger.error(f"Error consultando Supabase para relacionar curriculo: {e}")
            all_structures = []
            
    # Fallback/Lectura directa local
    if not all_structures:
        seed = load_seed_data()
        for c in seed.get("contenidos", []):
            # Filtrar
            if (
                normalize_modelo(c.get("modelo")) == modelo_norm
                and normalize_nivel(c.get("nivel")) == normalize_nivel(nivel)
                and normalize_grado(c.get("grado")) == normalize_grado(grado)
                and c.get("campo_formativo") == campo_formativo
            ):
                all_structures.append(c)

    # 2. Algoritmo de keyword matching
    query_words = [w.lower() for w in re.findall(r'\w+', tema) if len(w) > 2]
    
    contenidos_relacionados = []
    pda_relacionados = []
    relaciones = []
    
    for c in all_structures:
        # Texto total del contenido para buscar coincidencias
        pdas_texts = [p.get("pda", "") for p in c.get("pda", [])]
        search_target = " ".join([c["contenido"], c.get("descripcion", "")] + pdas_texts).lower()
        
        matches = 0
        for w in query_words:
            if w in search_target:
                matches += 1
                
        if len(query_words) > 0:
            score = round(matches / len(query_words), 2)
        else:
            score = 0.0
            
        # Si hay coincidencia, vincular
        if score > 0.0 or not query_words:
            # Formatear contenido para ContenidoResponse
            c_resp = c.copy()
            if "pda" in c_resp:
                del c_resp["pda"]
            contenidos_relacionados.append(c_resp)
            
            # Formatear PDAs y armar relaciones individuales
            for p in c.get("pda", []):
                # Validar que no falten campos en el PDA (por formato dual)
                pda_data = {
                    "id": p["id"],
                    "contenido_id": c["id"],
                    "modelo": c["modelo"],
                    "nivel": c["nivel"],
                    "fase": c["fase"],
                    "grado": c["grado"],
                    "campo_formativo": c["campo_formativo"],
                    "contenido": c["contenido"],
                    "pda": p.get("pda") or p.get("texto") or "",
                    "fuente": p.get("fuente", "seed_local_validacion")
                }
                pda_relacionados.append(pda_data)
                
                # Explicación pedagógica de la relación
                explicacion = (
                    f"El tema '{tema}' se relaciona directamente con el contenido curricular "
                    f"'{c['contenido']}' a través del PDA '{pda_data['pda']}' ya que ambos promueven "
                    f"el aprendizaje del campo formativo '{c['campo_formativo']}'."
                )
                
                relaciones.append({
                    "contenido": c["contenido"],
                    "pda": pda_data["pda"],
                    "explicacion": explicacion,
                    "score": float(score),
                    "fuente": c["fuente"]
                })
                
    return {
        "contenidos_relacionados": contenidos_relacionados,
        "pda_relacionados": pda_relacionados,
        "relaciones": relaciones
    }
