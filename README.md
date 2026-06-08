# mex-education-api (Fase 6)

API base y motor de búsqueda semántica (RAG) para la Nueva Escuela Mexicana (NEM). Diseñada con Python 3.11+, FastAPI, Supabase (PostgreSQL + pgvector) y lista para desplegarse localmente o en Railway.

---

## 🛠️ Tecnologías del Stack

- **Lenguaje:** Python 3.11+
- **Framework Web:** FastAPI (documentación automática interactiva en `/docs`)
- **Servidor ASGI:** Uvicorn
- **Base de Datos & Vector Store:** Supabase (PostgreSQL con extensión `pgvector`)
- **Validación de Datos:** Pydantic v2
- **Gestión de Entorno:** Python-dotenv & Pydantic-settings
- **Embeddings:** OpenAI API (`text-embedding-3-small` / `text-embedding-ada-002`)
- **Procesamiento de Texto:** Tiktoken (tokenizado exacto con codificación `cl100k_base`)

---

## 📂 Estructura del Proyecto

El proyecto está organizado bajo las mejores prácticas de arquitectura limpia:

```text
mex-education-api/
├── app/
│   ├── main.py              # Punto de entrada y configuración de la app FastAPI
│   ├── core/
│   │   └── config.py        # Carga tipada de variables de entorno con Pydantic
│   ├── db/
│   │   └── supabase.py      # Inicialización resiliente del cliente Supabase
│   ├── routes/              # Controladores y Endpoints de la API
│   │   ├── health.py
│   │   ├── modelos.py
│   │   ├── campos.py
│   │   ├── ejes.py
│   │   ├── documentos.py
│   │   └── buscar.py
│   ├── schemas/             # Definición de modelos de validación Pydantic
│   │   ├── documentos.py
│   │   └── search.py
│   └── services/            # Servicios de lógica de negocio
│       ├── chunking.py      # Separación de textos por tokens (tiktoken)
│       └── nem_search.py    # Generación de embeddings e invocación de búsqueda vectorial
├── requirements.txt         # Dependencias del proyecto
├── .env.example             # Plantilla de variables de entorno
├── README.md                # Esta guía
└── railway.json             # Configuración de despliegue para Railway
```

## 💾 Base de Datos (Supabase SQL Setup)

Para el funcionamiento completo del sistema, ejecuta el script consolidado [supabase_schema.sql](file:///Users/kennethjts/mex-education-api/supabase_schema.sql) en el SQL Editor de tu proyecto de Supabase. Este script:
1. Activa la extensión `pgvector`.
2. Crea las tablas `documentos` y `chunks_nem`.
3. Crea un índice HNSW en la columna vectorial.
4. Crea la función RPC **`match_chunks_nem`** para búsquedas de similitud vectorial de coseno con soporte de metadatos.

---

## 🚀 Pipeline y Control de Calidad (Fase 3)

### 1. Colocación de PDFs Reales
Los documentos oficiales reales de la Nueva Escuela Mexicana deben ubicarse dentro del directorio `data/oficiales/`. Ejemplo:
- [plan-estudio-2022.pdf](file:///Users/kennethjts/mex-education-api/data/oficiales/plan-estudio-2022.pdf)

### 2. Validación Pre-Ingesta (`scripts/validate_ingestion.py`)
Antes de indexar, ejecuta el script de control de calidad para analizar la fragmentación, detectar páginas vacías, chunks pequeños o duplicaciones:
```bash
python3 scripts/validate_ingestion.py \
  --file "./data/oficiales/plan-estudio-2022.pdf" \
  --titulo "Plan de Estudio 2022" \
  --modelo "NEM_2022" \
  --nivel "Educación Básica" \
  --fase "Todas" \
  --grado "Todos" \
  --campo_formativo "General" \
  --tipo_documento "Plan de Estudio"
```
*Genera un reporte analítico en:* `reports/ingestion_report.json`

### 3. Ejecutar Ingestión Indexada (`scripts/ingest_nem.py`)
Indexa el archivo extrayendo páginas y calculando embeddings OpenAI en Supabase o en simulación local:
```bash
python3 scripts/ingest_nem.py \
  --file "./data/oficiales/plan-estudio-2022.pdf" \
  --titulo "Plan de Estudio 2022" \
  --modelo "NEM_2022" \
  --nivel "Educación Básica" \
  --fase "Todas" \
  --grado "Todos" \
  --campo_formativo "General" \
  --tipo_documento "Plan de Estudio"
```
*Genera un archivo JSON de simulación bajo:* `data/ingested_<doc_id>.json`

### 4. Evaluación de Calidad de Búsqueda Semántica (`scripts/test_search_quality.py`)
Ejecuta la batería de 8 consultas clave sobre conceptos NEM (e.g. campos formativos, autonomía profesional docente, codiseño, evaluación formativa):
```bash
python3 scripts/test_search_quality.py
```
*Este script evalúa la tasa de recuperación, mostrando similitudes y fragmentos y guardando un informe en:* `reports/search_quality_report.json`

### 🔍 Interpretación de Reportes
- **`ingestion_report.json`**: Revisa la sección `anomalias`. Si detecta chunks duplicados o pequeños, evalúa limpiar el PDF.
- **`search_quality_report.json`**: Comprueba la `tasa_recuperacion`. Un valor del `100.00%` indica que todos los conceptos clave de la NEM fueron localizados satisfactoriamente en los textos indexados.

---

## ⚙️ Configuración e Instalación

### 1. Clonar o acceder al proyecto
Asegúrate de estar en el directorio de la aplicación:
```bash
cd mex-education-api
```

### 2. Crear y configurar variables de entorno
Copia el archivo de plantilla `.env.example` a `.env`:
```bash
cp .env.example .env
```
Edita el archivo `.env` configurando los valores correspondientes:
```env
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=tu-service-role-key-secreta
OPENAI_API_KEY=sk-tu-openai-api-key
APP_ENV=development
PORT=8000
```
> **Nota:** La API iniciará y funcionará en **modo Simulación/Mock** si dejas las llaves vacías o con los placeholders por defecto.

### 3. Instalar dependencias
Se recomienda usar un entorno virtual (venv):
```bash
python -m venv .venv
source .venv/bin/activate  # En macOS/Linux
# .venv\Scripts\activate   # En Windows

pip install -r requirements.txt
```

### 4. Iniciar el Servidor de Desarrollo Local
```bash
uvicorn app.main:app --reload
```
Una vez iniciado, abre las siguientes URL en tu navegador:
- **Bienvenida:** [http://localhost:8000](http://localhost:8000)
- **Documentación Interactiva (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Documentación ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📡 Endpoints del API

### Rutas Informativas y Catálogos
- `GET /` - Bienvenida, estado del ambiente y versión.
- `GET /health` - Monitoreo de salud del API y conexión activa de Supabase.
- `GET /modelos` - Listado estático de los modelos educativos de México (NEM, RIEB, etc.).
- `GET /campos` - Listado de los Campos Formativos vigentes del plan de estudio 2022.
- `GET /ejes` - Listado de los 7 Ejes Articuladores que estructuran la didáctica de la NEM.

### Rutas de Operación e Ingestión
- `POST /documentos` - Recibe metadatos y texto completo de un documento. Realiza el chunking en fragmentos de aproximadamente **700 tokens con 100 tokens de overlap** usando tiktoken, genera los embeddings con OpenAI y los inserta en Supabase en lotes (batch).
- `POST /buscar` - Realiza una consulta semántica en lenguaje natural. Genera el embedding de la pregunta, invoca la función RPC `match_chunks_nem` en Supabase aplicando filtros por metadatos (modelo, nivel, fase, etc.) y devuelve los fragmentos más relevantes ordenados por similitud.

#### Ejemplo de JSON de Búsqueda (`POST /buscar`):
```json
{
  "query": "¿Cuáles son los campos formativos en educación básica?",
  "limit": 3,
  "match_threshold": 0.35,
  "modelo": "NEM_2022",
  "nivel": "Educación Básica"
}
```

### Rutas de Planeación Curricular (Generativo RAG)
- `POST /planeaciones/generar` - Genera una planeación didáctica oficial estructurada. Aplica RAG de forma obligatoria; si la búsqueda en el corpus no arroja ningún contexto curricular relevante, cancela la generación arrojando un error controlado para evitar alucinaciones pedagógicas.
- `POST /planeaciones/debug` - Devuelve la consulta expandida que se generó, la lista de chunks recuperados por búsqueda vectorial con sus respectivos scores de similitud, y el prompt final construido que es enviado al modelo generativo LLM.

#### Ejemplo de JSON de Entrada para Planeación:
```json
{
  "tema": "campos formativos",
  "grado": "2",
  "nivel": "Educación Básica",
  "campo_formativo": "General",
  "duracion_dias": 5,
  "modelo": "NEM"
}
```

#### Ejemplo de JSON de Respuesta de Planeación:
```json
{
  "planeacion": {
    "titulo": "Proyecto Comunitario: El Poder de los Campos Formativos en Educación Básica",
    "objetivo": "Indagar los principios fundamentales...",
    "pda_relacionados": [
      "Describe el origen y la importancia..."
    ],
    "momentos": [
      {
        "dia": 1,
        "actividades": [
          "Inicio del proyecto..."
        ]
      }
    ],
    "evaluacion": "Rúbrica de autoevaluación formativa...",
    "materiales": [
      "Cuaderno de apuntes..."
    ]
  },
  "retrieval_success": true,
  "chunks_utilizados": [
    {
      "id": "171a00e0-7665-4319-abda-4b6da56ca915",
      "documento_titulo": "Plan de Estudio",
      "pagina": 2,
      "texto": "Campos Formativos y Ejes Articuladores...",
      "similitud": 0.73
    }
  ]
}
```


---

## 📚 Módulo Curricular Estructurado (Fase 5)

La Fase 5 añade un motor curricular estructurado que permite relacionar los temas pedagógicos de interés de manera directa con los **Contenidos** y **PDA (Procesos de Desarrollo de Aprendizaje)** oficiales de la Nueva Escuela Mexicana, además de habilitar la generación híbrida (RAG con fallback de currículo estructurado local en caso de ausencia de fragmentos vectoriales en el PDF).

### 1. Archivo de Semilla Curricular
La semilla se ubica en:
- [seed_nem_secundaria_fase6.json](file:///Users/kennethjts/mex-education-api/data/seed/seed_nem_secundaria_fase6.json) (contiene la estructura curricular de 2do Grado de Secundaria, Fase 6 para todos los Campos Formativos).

### 2. Validación de Currículo Estructurado (`scripts/validate_curriculo.py`)
Valida la integridad del archivo JSON curricular (UUIDs válidos, consistencia de modelo/fase/grado/campo formativo, detección de duplicados semánticos) y genera estadísticas generales:
```bash
python3 scripts/validate_curriculo.py --file data/seed/seed_nem_secundaria_fase6.json
```
*Genera un reporte analítico en:* `reports/curriculo_validation_report.json`

### 3. Siembra Curricular en Supabase (`scripts/seed_curriculo.py`)
Carga y siembra los registros del JSON en las tablas relacionales `contenidos_nem` y `pda_nem` de Supabase mediante un proceso seguro de upsert:
```bash
python3 scripts/seed_curriculo.py --file data/seed/seed_nem_secundaria_fase6.json
```
*Si Supabase no está configurado, el script ejecutará una simulación (Dry-run / Offline) mostrando los registros procesados.*

### 🛠️ Nuevos Endpoints de Currículo (`/curriculo`)

- `GET /curriculo/contenidos` - Recupera la lista de contenidos oficiales de la NEM. Permite filtrar por modelo, nivel, fase, grado y campo formativo.
- `GET /curriculo/pda` - Recupera los Procesos de Desarrollo de Aprendizaje (PDA). Permite filtrar por grado, campo formativo, contenido padre, etc.
- `POST /curriculo/relacionar` - Evalúa un tema didáctico (e.g. "energía solar") contra los contenidos/PDA utilizando un algoritmo de coincidencia de palabras clave, arrojando una justificación pedagógica estructurada y un score de relevancia.

#### Ejemplo de Relación Curricular (`POST /curriculo/relacionar`):
```json
{
  "tema": "energía solar",
  "grado": "2",
  "nivel": "Secundaria",
  "campo_formativo": "Saberes y Pensamiento Científico",
  "modelo": "NEM"
}
```

### 🧠 Generación Híbrida en Planeación (`POST /planeaciones/generar`)

El motor de planeación didáctica ahora opera de forma híbrida:
1. Intenta la búsqueda semántica vectorial (RAG) en los fragmentos de PDF.
2. Simultáneamente busca relaciones en el currículo estructurado (Contenidos/PDA).
3. Si la búsqueda semántica (RAG) no retorna fragmentos porque el tema no está explícito en el PDF (por ejemplo, "energía solar"), la API **no cancela la generación** si existe un contenido y PDA estructurado relacionado. En su lugar, utiliza el currículo de la semilla como contexto y retorna:
   - `retrieval_success`: `false`
   - `structured_curriculum_success`: `true`
   - `source_warning`: `"Generación basada en seed estructurado local, no en corpus oficial completo."`

---

## ⚡ Pruebas de Carga y Evaluación de Calidad (Fase 6)

La Fase 6 integra observabilidad y control de calidad cuantitativo mediante scripts de simulación de carga y lote:

### 1. Ejecutar Pruebas de Carga (`scripts/load_test.py`)
Mide la capacidad de concurrencia y latencias (percentiles p50, p95) bajo cargas de **50, 100 y 250 requests concurrentes**:
```bash
python3 scripts/load_test.py --url http://127.0.0.1:8001
```
*Imprime un reporte consolidado en consola con latencias promedio y tasas de éxito.*

### 2. Ejecutar Evaluación de Planeaciones (`scripts/evaluate_planeaciones.py`)
Genera y evalúa en lote **25 planeaciones didácticas** abarcando combinaciones de los 10 temas críticos (violencia, salud, lectura, etc.):
```bash
python3 scripts/evaluate_planeaciones.py --url http://127.0.0.1:8001
```
*Este script:*
1. Emite las peticiones a la API.
2. Califica heurísticamente de 0 a 10 cada plan según su estructura didáctica.
3. Guarda los reportes individuales y el consolidado bajo `reports/evaluations/`.

### 📊 Interpretación de Métricas en Producción

Puedes consultar las métricas del sistema directamente desde los endpoints expuestos:
- **`GET /metrics/health`**: Proporciona el estado general del API (latencia promedio, éxito general, costos y tasa de acierto RAG).
- **`GET /metrics/generations`**: Proporciona estadísticas del motor generativo (uso de fallbacks curriculares, fallas de RAG y velocidad).

*Valores clave a observar:*
- **Rechazos por Política (No-Inventar)**: Si el tema no tiene contexto (e.g. "salud", "violencia" en el seed parcial), se retornará un HTTP 400 controlado. Esto se refleja como rechazo intencional en la tasa de éxito de métricas de salud (con una tasa esperada en la suite de pruebas del ~48% exitoso y ~52% rechazado por seguridad).
- **Latencia p95**: Un valor menor a 1500 ms bajo 100 peticiones concurrentes es óptimo para la API en despliegues productivos.

---

## 🔒 Preparación para GitHub + Supabase Real (Fase 7)

La Fase 7 prepara el proyecto para ser publicado de forma segura en GitHub y enlazarse con una base de datos real de Supabase sin comprometer credenciales confidenciales.

### 1. Archivo de Exclusiones `.gitignore`
El proyecto incluye un `.gitignore` optimizado que previene subir secretos locales y datos simulados:
- Excluye: `.env`, `reports/`, `data/*.json` (logs y simulaciones locales), entornos virtuales y cachés.
- Permite subir: `data/oficiales/`, `data/seed/` y esquemas SQL.

### 2. Script de Diagnóstico Pre-Vuelo (`scripts/preflight_check.py`)
Antes de subir tu proyecto a producción o GitHub, ejecuta el script de diagnóstico para verificar que no haya archivos de secretos en tracking de Git, que el `.env` no contenga placeholders de prueba y que la estructura de carpetas oficiales esté completa:
```bash
python3 scripts/preflight_check.py
```
*Si alguna validación crítica falla (como la existencia de placeholders de Supabase o OpenAI en el `.env`), el script terminará con error, alertando al desarrollador.*

### 3. Guía Detallada Paso a Paso
Para configurar el repositorio de GitHub y la base de datos real de Supabase, sigue las instrucciones del manual detallado:
- [SETUP_GITHUB_SUPABASE.md](file:///Users/kennethjts/mex-education-api/SETUP_GITHUB_SUPABASE.md)

---

## ⚡ Optimización de Latencia y Calidad RAG (Fase 8)

La Fase 8 implementa técnicas avanzadas para reducir drásticamente la latencia promedio del motor RAG por debajo de los **5 segundos** (con respuestas por debajo de **50 ms** para peticiones en caché) y mejorar la precisión del contexto didáctico.

### 1. Sistema de Caché en Memoria
Se implementó un sistema de caché en memoria (`MemoryCache`) thread-safe con expiración TTL de 30 minutos y hashing SHA-256 determinista:
- **Caché RAG:** Almacena resultados de búsqueda vectorial en Supabase basados en consulta y filtros.
- **Caché de Generación:** Almacena la planeación didáctica generada en base a la configuración completa del payload de entrada.

### 2. Optimización y Compresión de Prompt (RAG)
Para mitigar la latencia asociada a tokens excesivos en el prompt al LLM:
- **Reducción de Top-K:** Límite máximo de **3 chunks** para solicitudes estándar de `/generar` y **5 chunks** para `/debug`.
- **Umbral de Similitud:** Filtro estricto que descarta cualquier fragmento con similitud menor a **0.35**.
- **Compresión de Chunks:** Cada fragmento de texto recuperado se comprime a un tamaño máximo de **900 caracteres**, conservando el título del documento original, la página y la información didáctica clave.
- **Expansión de Query RAG:** Normalización y enriquecimiento automático del término de búsqueda utilizando palabras clave de la NEM.

### 3. Ejecutar Benchmark de Latencia (`scripts/benchmark_generation.py`)
Mide la latencia de 5 peticiones secuenciales frías (cold) contra 5 calientes (hot/cached) para demostrar cuantitativamente el rendimiento y el speedup del sistema de caché:
```bash
python3 scripts/benchmark_generation.py
```
*Genera una tabla comparativa en la consola mostrando la reducción de tiempos de respuesta y el porcentaje de optimización logrado (típicamente >95% en aciertos de caché).*

### 4. Evaluación Completa con Percentiles (`scripts/evaluate_planeaciones.py`)
El script de evaluación por lotes calcula e informa automáticamente los percentiles p50, p95 y latencia máxima de la corrida de 25 planeaciones, además del número de aciertos de caché.

---

## ☁️ Despliegue en Railway

Esta aplicación está completamente configurada para desplegarse en **Railway** usando el archivo de configuración `railway.json`.

1. Conecta tu repositorio de GitHub a Railway.
2. Railway detectará la configuración de Nixpacks por defecto y el comando configurado en `railway.json`.
3. Configura las variables de entorno en la sección **Variables** del panel de control de tu servicio en Railway (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`, `APP_ENV=production`).
4. ¡Listo! Tu servicio estará en línea.
