# Guía de Configuración: GitHub + Supabase Real (Fase 7)

Esta guía detalla el procedimiento paso a paso para publicar el proyecto `mex-education-api` en tu repositorio de GitHub, crear y configurar una base de datos real en Supabase, reingestar los documentos curriculares oficiales y verificar el funcionamiento general.

---

> [!WARNING]
> **ADVERTENCIA DE SEGURIDAD CRÍTICA:**
> - **NUNCA** subas el archivo `.env` al repositorio de GitHub. Contiene secretos altamente sensibles como tu clave privada `SUPABASE_SERVICE_ROLE_KEY` y tu `OPENAI_API_KEY`.
> - El archivo `.gitignore` ya está configurado para excluir automáticamente `.env`, entornos virtuales (`.venv/`) e informes de calidad locales (`reports/` y `data/*.json`). Asegúrate de que no se omitan estas exclusiones.

---

## Paso 1: Crear el Repositorio en GitHub

1. Entra a tu cuenta en [GitHub](https://github.com).
2. Haz clic en **New** (Nuevo Repositorio).
3. Nombra tu repositorio como `mex-education-api`.
4. Elígelo como **Public** o **Private** (Privado es recomendado para mayor seguridad con desarrollos propios).
5. **IMPORTANTE:** No selecciones "Add a README file", "Add .gitignore", ni "Choose a license" (el proyecto ya cuenta con estos archivos listos).
6. Haz clic en **Create repository**.
7. Copia la URL de tu repositorio remoto (ej. `https://github.com/tu-usuario/mex-education-api.git`).

---

## Paso 2: Inicializar y Subir el Proyecto a GitHub

Abre tu terminal en el directorio raíz de `mex-education-api` y ejecuta los siguientes comandos:

```bash
# 1. Inicializar el repositorio Git
git init

# 2. Comprobar el estado de los archivos y verificar que .env no esté listado para subirse
git status

# 3. Agregar todos los archivos al área de preparación
git add .

# 4. Crear el commit inicial indicando la versión estable
git commit -m "initial curriculum engine phase 1-6"

# 5. Renombrar la rama principal a 'main'
git branch -M main

# 6. Vincular el repositorio remoto (reemplaza URL_DEL_REPO con tu URL copiada)
git remote add origin URL_DEL_REPO

# 7. Subir el código a GitHub
git push -u origin main
```

---

## Paso 3: Crear y Configurar tu Proyecto en Supabase

1. Ve a la consola de [Supabase](https://supabase.com) e inicia sesión.
2. Haz clic en **New project** (Nuevo proyecto).
3. Selecciona tu organización, ingresa el nombre `mex-education-api`, define una contraseña segura para tu base de datos y elige la región geográfica más cercana.
4. Espera un par de minutos a que la base de datos y la infraestructura se terminen de aprovisionar.

---

## Paso 4: Ejecutar el Esquema de Base de Datos

1. Dentro de tu panel de Supabase, en el menú lateral izquierdo ve a **SQL Editor** (Editor de SQL).
2. Haz clic en **New query** (Nueva consulta).
3. Abre el archivo local [supabase_schema.sql](file:///Users/kennethjts/mex-education-api/supabase_schema.sql) en tu editor, copia todo su contenido y pégalo en el cuadro de texto del SQL Editor de Supabase.
4. Haz clic en el botón **Run** (Ejecutar) en la esquina superior derecha del editor.
5. Verifica en los logs inferiores que las 6 tablas (`documentos`, `chunks_nem`, `contenidos_nem`, `pda_nem`, `request_logs`, `generation_evaluations`), la función RPC `match_chunks_nem` y el índice HNSW se hayan creado correctamente.

---

## Paso 5: Obtener Credenciales y Configurar el Entorno

1. Ve a **Project Settings** (icono de engranaje abajo a la izquierda en Supabase) y luego a **API**.
2. Copia los siguientes valores:
   - **Project URL** (ej. `https://xxxxxx.supabase.co`)
   - **service_role key** (haz clic en *Reveal* para mostrar la clave de rol de servicio privada y cópiala).
3. Crea un archivo `.env` en la raíz de tu proyecto local (copiando la estructura de [.env.example](file:///Users/kennethjts/mex-education-api/.env.example)):
   ```env
   SUPABASE_URL=https://tu-proyecto-id.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=tu-service-role-key-secreta
   OPENAI_API_KEY=sk-tu-openai-api-key-real
   APP_ENV=development
   ```

---

## Paso 6: Ejecutar y Validar el Servidor Local

1. Reinicia tu servidor FastAPI en el puerto `8001` para que cargue la nueva configuración del `.env`:
   ```bash
   python3 -m uvicorn app.main:app --reload --port 8001
   ```
2. Realiza un curl de prueba al endpoint de salud para verificar la conexión activa a Supabase:
   ```bash
   curl http://127.0.0.1:8001/health
   ```
   **Resultado esperado (HTTP 200 OK):**
   ```json
   {"status":"operacional","supabase":"conectado"}
   ```

---

## Paso 7: Sembrar Currículo e Ingestar Documentos Reales

1. Siembra la base de datos con los Contenidos y PDA de la NEM de Secundaria:
   ```bash
   python3 scripts/seed_curriculo.py --file data/seed/seed_nem_secundaria_fase6.json
   ```
   *Ahora se insertarán los registros directamente en Supabase (mostrando el mensaje "SIEMBRA CURRICULAR EN SUPABASE EXITOSA").*

2. Coloca los dos PDFs oficiales reales bajo la carpeta `data/oficiales/`:
   - [plan-estudio-2022.pdf](file:///Users/kennethjts/mex-education-api/data/oficiales/plan-estudio-2022.pdf)
   - [Programa_Sintetico_Fase_6 (1).pdf](file:///Users/kennethjts/mex-education-api/data/oficiales/Programa_Sintetico_Fase_6%20%281%29.pdf)

3. Ejecuta la ingesta del **Plan de Estudio 2022**:
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

4. Ejecuta la ingesta del **Programa Sintético Fase 6**:
   ```bash
   python3 scripts/ingest_nem.py \
     --file "./data/oficiales/Programa_Sintetico_Fase_6 (1).pdf" \
     --titulo "Programa Sintético Fase 6" \
     --modelo "NEM_2022" \
     --nivel "Secundaria" \
     --fase "6" \
     --grado "Todos" \
     --campo_formativo "General" \
     --tipo_documento "Programa Sintético"
   ```

---

## Paso 8: Correr Pruebas de Calidad Finales

1. Ejecuta el validador semántico contra la base de datos real:
   ```bash
   python3 scripts/test_search_quality.py
   ```
2. Ejecuta la batería de 25 evaluaciones en lote para corroborar el flujo RAG, fallbacks y scoring en la base de datos real:
   ```bash
   python3 scripts/evaluate_planeaciones.py
   ```
3. Verifica las métricas actualizadas consumidas en la base de datos en:
   [http://127.0.0.1:8001/metrics/health](http://127.0.0.1:8001/metrics/health) y [http://127.0.0.1:8001/metrics/generations](http://127.0.0.1:8001/metrics/generations).
