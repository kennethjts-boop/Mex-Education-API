-- 1. Habilitar la extensión pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Eliminar tablas existentes (si existen, para pruebas limpias)
-- DROP TABLE IF EXISTS chunks_nem CASCADE;
-- DROP TABLE IF EXISTS documentos CASCADE;

-- 3. Crear la tabla de documentos principales
CREATE TABLE documentos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo TEXT NOT NULL,
    modelo TEXT NOT NULL,
    nivel TEXT NOT NULL,
    fase TEXT NOT NULL,
    grado TEXT NOT NULL,
    campo_formativo TEXT,
    tipo_documento TEXT NOT NULL,
    storage_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);

-- 4. Crear la tabla de chunks indexados
CREATE TABLE chunks_nem (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    documento_id UUID REFERENCES documentos(id) ON DELETE CASCADE NOT NULL,
    texto TEXT NOT NULL,
    pagina INTEGER,
    chunk_index INTEGER NOT NULL,
    embedding VECTOR(1536), -- 1536 dimensiones para OpenAI Embeddings (text-embedding-3-small)
    metadata JSONB DEFAULT '{}'::JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);

-- 5. Crear índice vectorial HNSW para similitud del coseno
CREATE INDEX IF NOT EXISTS chunks_nem_embedding_hnsw_idx 
ON chunks_nem 
USING hnsw (embedding vector_cosine_ops);

-- 6. Crear la función de búsqueda semántica (RPC) match_chunks_nem
CREATE OR REPLACE FUNCTION match_chunks_nem (
  query_embedding VECTOR(1536),
  match_threshold FLOAT,
  match_count INT,
  filter_metadata JSONB DEFAULT '{}'::JSONB
) RETURNS TABLE (
  id UUID,
  documento_id UUID,
  texto TEXT,
  pagina INTEGER,
  chunk_index INTEGER,
  metadata JSONB,
  created_at TIMESTAMP WITH TIME ZONE,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    c.id,
    c.documento_id,
    c.texto,
    c.pagina,
    c.chunk_index,
    c.metadata,
    c.created_at,
    1 - (c.embedding <=> query_embedding) AS similarity
  FROM chunks_nem c
  WHERE 1 - (c.embedding <=> query_embedding) > match_threshold
    AND (
      filter_metadata = '{}'::JSONB 
      OR c.metadata @> filter_metadata
    )
  ORDER BY c.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- 7. Crear la tabla de contenidos curriculares NEM
CREATE TABLE contenidos_nem (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    modelo TEXT NOT NULL,
    nivel TEXT NOT NULL,
    fase TEXT NOT NULL,
    grado TEXT NOT NULL,
    campo_formativo TEXT NOT NULL,
    contenido TEXT NOT NULL,
    descripcion TEXT,
    fuente TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);

-- 8. Crear la tabla de PDA (Procesos de Desarrollo de Aprendizaje) NEM
CREATE TABLE pda_nem (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contenido_id UUID REFERENCES contenidos_nem(id) ON DELETE CASCADE NOT NULL,
    modelo TEXT NOT NULL,
    nivel TEXT NOT NULL,
    fase TEXT NOT NULL,
    grado TEXT NOT NULL,
    campo_formativo TEXT NOT NULL,
    contenido TEXT NOT NULL, -- Texto descriptivo del contenido padre
    pda TEXT NOT NULL,
    fuente TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);

-- 9. Crear la tabla de logs de peticiones
CREATE TABLE request_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint TEXT NOT NULL,
    execution_ms FLOAT NOT NULL,
    success BOOLEAN NOT NULL,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    estimated_cost NUMERIC(10, 6) DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);

-- 10. Crear la tabla de evaluaciones de generación
CREATE TABLE generation_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint TEXT NOT NULL,
    query TEXT NOT NULL,
    retrieval_success BOOLEAN NOT NULL,
    structured_curriculum_success BOOLEAN NOT NULL,
    score NUMERIC(5, 2) DEFAULT 0.0,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);


