# Validación de corpus

## Cierre formal de 2° grado

**2° grado cerrado y aprobado. No volver a modificar salvo error real.**

La validación final confirmó 19/19 documentos oficiales con chunks vectoriales,
0 documentos sin chunks, 0 duplicados y 0 errores. Se reingestaron 18 documentos.

El RAG puro está disponible, no utilizó fallback curricular y recupera
correctamente Inglés de 2°. La evaluación pedagógica terminó con 23/25
generaciones exitosas (92%) y score promedio de 9.5/10.

No se deben modificar documentos, chunks, embeddings ni lógica de 2° grado salvo
que exista un error real reproducible.

Commit sugerido: `chore: close grade 2 corpus validation`

---

## Calendario Escolar SEP 2025-2026

Hemos agregado soporte completo y optimizado para el **Calendario Escolar SEP 2025-2026** (Educación Básica, NEM_2022) mediante una estrategia de ingesta manual y multi-chunking de alta fidelidad.

### Acciones Realizadas

1. **Ingesta Manual de Alta Fidelidad**:
   - Implementada en [ingest_calendar_manual.py](file:///Users/kennethjts/mex-education-api/scripts/ingest_calendar_manual.py).
   - Registra el documento en Supabase con metadatos específicos: `titulo="Calendario Escolar SEP 2025-2026"`, `nivel="Educación Básica"`, `fase="Todas"`, `grado="Todos"`, `campo_formativo="General"`, `tipo_documento="Calendario Escolar"`.
   - Divide la información detallada en **9 fragmentos conceptuales independientes** (en lugar de un solo chunk denso) optimizados para temas específicos como inicio/fin de clases, consejos técnicos escolares (CTE), vacaciones de invierno/semana santa, preinscripciones, entrega de boletas y descarga administrativa.
   - Genera embeddings reales con la API de OpenAI y los inserta en la tabla `chunks_nem` de Supabase.
   - Crea un registro del documento y simulación local en `data/uploads/documentos_registry.json` y `data/ingested_<doc_id>.json` para resiliencia offline.
   - Soporta la bandera `--force` para limpiar y reemplazar el documento y sus chunks correspondientes sin dejar datos huérfanos.

2. **Batería de Pruebas de Búsqueda Semántica**:
   - Desarrollada en [test_calendar_search.py](file:///Users/kennethjts/mex-education-api/scripts/test_calendar_search.py).
   - Valida 8 consultas semánticas críticas en lenguaje natural sobre el calendario escolar (como *"vacaciones de invierno 2025-2026"*, *"cuantos días efectivos de clase tiene..."*, *"cuando son los consejos técnicos escolares"*, etc.).
   - Compara y ejecuta la búsqueda tanto a través de peticiones HTTP en el endpoint `/buscar` del servidor activo como mediante consultas directas al servicio local RAG.
   - Confirma con éxito que en **el 100% de los casos (8/8 pasadas)** el primer resultado de búsqueda semántica devuelto es el documento **"Calendario Escolar SEP 2025-2026"**, con similitudes vectoriales altas (entre 0.52 y 0.75).

### Resultados de las Pruebas de Búsqueda

Todas las consultas clave del calendario recuperan el documento como primer resultado:

| Consulta de Prueba | Resultado Top | Similitud | Método | Estado |
|---------------------|---------------|-----------|--------|--------|
| *cuando inicia el ciclo escolar 2025-2026* | Calendario Escolar SEP 2025-2026 | 0.6846 | HTTP (Port 8001) | ✅ PASS |
| *cuando termina el ciclo escolar 2025-2026* | Calendario Escolar SEP 2025-2026 | 0.6583 | HTTP (Port 8001) | ✅ PASS |
| *cuantos días efectivos de clase tiene el calendario escolar 2025-2026* | Calendario Escolar SEP 2025-2026 | 0.7558 | HTTP (Port 8001) | ✅ PASS |
| *cuando son los consejos técnicos escolares* | Calendario Escolar SEP 2025-2026 | 0.6694 | HTTP (Port 8001) | ✅ PASS |
| *vacaciones de invierno 2025-2026* | Calendario Escolar SEP 2025-2026 | 0.6478 | HTTP (Port 8001) | ✅ PASS |
| *vacaciones de semana santa 2026* | Calendario Escolar SEP 2025-2026 | 0.6467 | HTTP (Port 8001) | ✅ PASS |
| *preinscripciones 2026* | Calendario Escolar SEP 2025-2026 | 0.5274 | HTTP (Port 8001) | ✅ PASS |
| *descarga administrativa 2025-2026* | Calendario Escolar SEP 2025-2026 | 0.5882 | HTTP (Port 8001) | ✅ PASS |
