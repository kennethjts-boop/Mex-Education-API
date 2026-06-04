import os
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from openai import OpenAI
from app.core.config import settings
from app.services.nem_search import search_nem_chunks, normalize_modelo
from app.services.curriculo_service import relacionar_curriculo

logger = logging.getLogger("uvicorn.error")

class RetrievalEmptyException(Exception):
    """Excepción lanzada cuando no se encuentra contexto en la base vectorial ni en el currículo."""
    pass

def load_prompt_template() -> str:
    """Carga el prompt de planeación desde el archivo de texto plano."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(base_dir, "prompts", "planeacion_prompt.txt")
    
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"No se encontró la plantilla de prompt en {prompt_path}")
        
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def generate_lesson_plan(
    tema: str,
    grado: str,
    nivel: str,
    campo_formativo: str,
    duracion_dias: int,
    modelo: str
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str, str, Dict[str, Any]]:
    """
    Ejecuta el flujo RAG Híbrido:
    1. Obtiene contenidos y PDA estructurados relacionados (Fase 5).
    2. Realiza búsqueda vectorial en chunks de PDF (Fase 3/4).
    3. Valida obligatoriedad curricular (No-Inventar). Si RAG falla pero hay currículo estructurado,
       permite la generación marcando alertas correspondientes.
    4. Compone el prompt de planeación pedagógica.
    5. Invoca a OpenAI o simula la respuesta.
    
    Retorna: (planeacion_dict, chunks_utilizados, prompt_construido, query_generada, metadatos_curriculo)
    """
    # 1. Normalizar modelo
    modelo_normalizado = normalize_modelo(modelo) or "NEM_2022"
    
    # 2. Consultar currículo estructurado
    rel_res = relacionar_curriculo(
        tema=tema,
        grado=grado,
        nivel=nivel,
        campo_formativo=campo_formativo,
        modelo=modelo_normalizado
    )
    
    contenidos_rel_objs = rel_res["contenidos_relacionados"]
    pda_rel_objs = rel_res["pda_relacionados"]
    
    contenido_relacionado_texts = list(set([c["contenido"] for c in contenidos_rel_objs]))
    pda_relacionado_texts = list(set([p["pda"] for p in pda_rel_objs]))
    
    # Determinar fuente curricular
    curriculum_source = "seed_local_validacion"
    if contenidos_rel_objs:
        curriculum_source = contenidos_rel_objs[0].get("fuente", "seed_local_validacion")
        
    # 3. Búsqueda RAG Vectorial
    query_generada = f"{tema} {campo_formativo}"
    filters = {
        "modelo": modelo_normalizado,
        "nivel": nivel
    }
    if campo_formativo:
        filters["campo_formativo"] = campo_formativo
        
    logger.info(f"RAG Híbrido: Buscando chunks para query: '{query_generada}' y filtros: {filters}")
    
    raw_chunks = search_nem_chunks(
        query_text=query_generada,
        limit=3,
        match_threshold=0.25,
        filters=filters
    )
    
    # Evaluar estados e interdependencias
    retrieval_success = len(raw_chunks) > 0
    structured_curriculum_success = len(contenido_relacionado_texts) > 0
    source_warning = None
    
    # Si RAG falla, validar si podemos levantar en modo currículo estructurado
    if not raw_chunks:
        if structured_curriculum_success:
            retrieval_success = False
            source_warning = "Generación basada en seed estructurado local, no en corpus oficial completo."
            logger.warning("RAG sin resultados. Generación aprobada bajo modo 'curriculo_estructurado'.")
        else:
            # Ambos fallaron
            logger.error(f"Fallo Absoluto: No se encontró contexto semántico ni estructurado para '{tema}'")
            raise RetrievalEmptyException(
                f"No se encontró contexto curricular oficial (RAG) ni estructurado (contenidos/PDA) "
                f"para el tema '{tema}' en el nivel '{nivel}' y campo formativo '{campo_formativo}'. "
                "La generación ha sido cancelada para evitar alucinaciones pedagógicas (política No-Inventar)."
            )
            
    # Formatear el contexto para el prompt
    context_parts = []
    chunks_utilizados = []
    
    if raw_chunks:
        for idx, r in enumerate(raw_chunks):
            sim = r.get("similarity") or r.get("similitud") or 0.0
            doc_titulo = r.get("documento", {}).get("titulo") or "Plan de Estudio"
            
            context_parts.append(
                f"--- Fragmento {idx+1} [Origen: {doc_title_clean(doc_titulo)} | Pág. {r.get('pagina')}] ---\n"
                f"{r['texto']}"
            )
            
            chunks_utilizados.append({
                "id": r.get("id") or r.get("chunk_id") or "simulated-id",
                "documento_titulo": doc_title_clean(doc_titulo),
                "pagina": r.get("pagina"),
                "texto": r["texto"],
                "similitud": sim
            })
    else:
        # Si no hay chunks, proveer el currículo estructurado como el contexto primordial
        context_parts.append("--- CONTENIDOS CURRICULARES ESTRUCTURADOS ---")
        for idx, c in enumerate(contenidos_rel_objs):
            context_parts.append(f"Contenido: {c['contenido']}\nDescripción: {c.get('descripcion', '')}")
        context_parts.append("--- PROCESOS DE DESARROLLO DE APRENDIZAJE (PDA) VINCULADOS ---")
        for idx, p in enumerate(pda_rel_objs):
            context_parts.append(f"- {p['pda']}")
            
    context_str = "\n\n".join(context_parts)
    
    # 4. Construir el prompt
    template = load_prompt_template()
    prompt_construido = template.format(
        context=context_str,
        tema=tema,
        grado=grado,
        nivel=nivel,
        campo_formativo=campo_formativo,
        duracion_dias=duracion_dias
    )
    
    # Consolidar metadatos curriculares
    metadatos_curriculo = {
        "contenido_relacionado": contenido_relacionado_texts,
        "pda_relacionados": pda_relacionado_texts,
        "curriculum_source": curriculum_source,
        "source_warning": source_warning,
        "retrieval_success": retrieval_success,
        "structured_curriculum_success": structured_curriculum_success
    }
    
    # 5. Generación con OpenAI o Simulación
    is_openai_ready = settings.OPENAI_API_KEY and "your-openai-api-key" not in settings.OPENAI_API_KEY
    
    if is_openai_ready:
        try:
            logger.info("Enviando prompt estructurado a OpenAI...")
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "Eres un asistente de planeación didáctica de la SEP y respondes estrictamente en formato JSON válido."},
                    {"role": "user", "content": prompt_construido}
                ],
                temperature=0.7
            )
            raw_response = response.choices[0].message.content
            planeacion_dict = json.loads(raw_response)
            return planeacion_dict, chunks_utilizados, prompt_construido, query_generada, metadatos_curriculo
        except Exception as e:
            logger.error(f"Error llamando a OpenAI: {e}. Activando simulación de contingencia.")
            planeacion_dict = _generate_mock_lesson_plan(tema, grado, nivel, campo_formativo, duracion_dias, pda_relacionado_texts)
            return planeacion_dict, chunks_utilizados, prompt_construido, query_generada, metadatos_curriculo
    else:
        logger.warning("OpenAI no configurado. Ejecutando simulación generativa local.")
        planeacion_dict = _generate_mock_lesson_plan(tema, grado, nivel, campo_formativo, duracion_dias, pda_relacionado_texts)
        return planeacion_dict, chunks_utilizados, prompt_construido, query_generada, metadatos_curriculo

def doc_title_clean(title: Any) -> str:
    if isinstance(title, dict):
        return title.get("titulo") or "Plan de Estudio"
    return str(title)

def _generate_mock_lesson_plan(
    tema: str,
    grado: str,
    nivel: str,
    campo_formativo: str,
    duracion_dias: int,
    pda_list: List[str]
) -> Dict[str, Any]:
    """Genera una planeación didáctica simulada utilizando los PDA reales del seed."""
    pda_rel = pda_list if pda_list else [f"Reconoce el impacto del tema '{tema}' en su comunidad."]
    
    momentos = []
    for dia in range(1, duracion_dias + 1):
        if dia == 1:
            actividades = [
                f"Inicio del proyecto sobre '{tema.capitalize()}'. Debate inicial en torno a la problemática local y saberes previos.",
                "Lectura de textos introductorios y registro de hipótesis en bitácora escolar."
            ]
        elif dia == duracion_dias:
            actividades = [
                "Presentación de proyectos finales y propuestas de sustentabilidad creadas en equipos.",
                "Sesión de retroalimentación constructiva, coevaluación y autoevaluación formativa NEM."
            ]
        else:
            actividades = [
                f"Sesión práctica {dia}: Investigación de campo y experimentación activa en el aula.",
                f"Elaboración de notas y discusión del PDA: '{pda_rel[0][:90]}...'"
            ]
        momentos.append({
            "dia": dia,
            "actividades": actividades
        })
        
    return {
        "titulo": f"Plan Didáctico NEM: {tema.capitalize()} y Sustentabilidad",
        "objetivo": f"Fomentar el desarrollo del pensamiento crítico y reflexivo de los alumnos de {nivel} ({grado}° grado) sobre el tema '{tema}'.",
        "pda_relacionados": pda_rel,
        "momentos": momentos,
        "evaluacion": "Rúbrica integradora, evaluación formativa procesual e instrumentos de autoevaluación.",
        "materiales": [
            "Bitácora de proyectos y material didáctico",
            "Recursos y material concreto para modelación física/sustentable",
            "Fichas de trabajo basadas en el currículo estructurado"
        ]
    }
