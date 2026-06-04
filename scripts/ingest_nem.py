#!/usr/bin/env python3
import os
import sys
import argparse
import uuid
import re
import logging
from typing import List, Dict, Any

# Añadir el directorio raíz al sys.path para poder importar el módulo 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pypdf import PdfReader
from app.core.config import settings
from app.db.supabase import supabase_client
from app.services.chunking import split_text_by_tokens
from app.services.nem_search import get_embedding

# Configurar logging básico para el script
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_nem")

def clean_text(text: str) -> str:
    """
    Aplica una limpieza básica al texto extraído:
    - Reemplaza múltiples espacios por uno solo.
    - Contrae saltos de línea múltiples a un máximo de dos.
    """
    if not text:
        return ""
    # Reemplazar múltiples espacios en la misma línea por uno solo
    text = re.sub(r'[ \t]+', ' ', text)
    # Reducir saltos de línea consecutivos
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

def main():
    parser = argparse.ArgumentParser(description="Pipeline de ingestión de PDFs educativos para la Nueva Escuela Mexicana.")
    parser.add_argument("--file", required=True, help="Ruta al archivo PDF local.")
    parser.add_argument("--titulo", required=True, help="Título del documento.")
    parser.add_argument("--modelo", required=True, help="Modelo educativo (ej. NEM_2022).")
    parser.add_argument("--nivel", required=True, help="Nivel educativo (ej. Primaria, Secundaria).")
    parser.add_argument("--fase", required=True, help="Fase del plan de estudios (ej. Fase 3).")
    parser.add_argument("--grado", required=True, help="Grado escolar (ej. 1er Grado, Todos).")
    parser.add_argument("--campo_formativo", required=True, help="Campo formativo principal (ej. Lenguajes).")
    parser.add_argument("--tipo_documento", required=True, help="Tipo de documento (ej. Plan de Estudio, Programa Sintético).")
    
    args = parser.parse_args()

    # 1. Validar existencia del archivo
    pdf_path = args.file
    if not os.path.exists(pdf_path):
        logger.error(f"El archivo PDF no existe en la ruta: {pdf_path}")
        sys.exit(1)

    logger.info(f"Iniciando procesamiento del archivo: {pdf_path}")

    # 2. Leer PDF
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        logger.info(f"PDF cargado con éxito. Total de páginas: {total_pages}")
    except Exception as e:
        logger.error(f"Error al leer el archivo PDF: {e}")
        sys.exit(1)

    # 3. Procesar y realizar chunking página por página
    documento_id = uuid.uuid4()
    all_chunks_payload = []
    
    global_chunk_idx = 0
    for page_idx, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text()
        cleaned_text = clean_text(raw_text)
        
        if not cleaned_text:
            logger.info(f"Página {page_idx} vacía o sin texto extraíble. Omitiendo.")
            continue
            
        # Dividir texto de la página en chunks usando el servicio
        # Tamaño objetivo ~700 tokens con overlap de 100
        chunks = split_text_by_tokens(cleaned_text, chunk_size=700, overlap=100)
        
        logger.info(f"Página {page_idx}/{total_pages}: generó {len(chunks)} chunks.")
        
        for c in chunks:
            # Generar embedding vectorial para el chunk
            embedding = get_embedding(c["texto"])
            
            chunk_metadata = {
                "modelo": args.modelo,
                "nivel": args.nivel,
                "fase": args.fase,
                "grado": args.grado,
                "campo_formativo": args.campo_formativo,
                "tipo_documento": args.tipo_documento
            }
            
            all_chunks_payload.append({
                "id": str(uuid.uuid4()),
                "documento_id": str(documento_id),
                "texto": c["texto"],
                "pagina": page_idx,
                "chunk_index": global_chunk_idx,
                "embedding": embedding,
                "metadata": chunk_metadata
            })
            global_chunk_idx += 1

    total_chunks_processed = len(all_chunks_payload)
    logger.info(f"Procesamiento de texto terminado. Total de chunks generados: {total_chunks_processed}")

    if total_chunks_processed == 0:
        logger.warning("No se generaron chunks de texto. Abortando inserción.")
        sys.exit(0)

    # 4. Registrar en Supabase
    is_supabase_ready = (
        supabase_client is not None 
        and "placeholder" not in settings.SUPABASE_URL
    )

    if is_supabase_ready:
        try:
            logger.info("Conexión con Supabase activa. Guardando registros en la base de datos...")
            
            # Registrar Documento
            doc_insert_data = {
                "id": str(documento_id),
                "titulo": args.titulo,
                "modelo": args.modelo,
                "nivel": args.nivel,
                "fase": args.fase,
                "grado": args.grado,
                "campo_formativo": args.campo_formativo,
                "tipo_documento": args.tipo_documento,
                "storage_path": pdf_path
            }
            supabase_client.table("documentos").insert(doc_insert_data).execute()
            logger.info("Registro de documento principal insertado correctamente.")

            # Inserción de Chunks en bloque (batch)
            # Para evitar sobrecargar peticiones grandes, podemos insertar en bloques de 100
            batch_size = 100
            for i in range(0, total_chunks_processed, batch_size):
                batch = all_chunks_payload[i:i + batch_size]
                supabase_client.table("chunks_nem").insert(batch).execute()
                logger.info(f"Insertados chunks {i + 1} a {min(i + batch_size, total_chunks_processed)}")

            logger.info("¡Ingestión finalizada con éxito en Supabase!")
            print(f"\n🚀 Éxito: Se ha indexado el documento '{args.titulo}' con ID: {documento_id} y {total_chunks_processed} chunks.")

        except Exception as e:
            logger.error(f"Error al guardar datos en Supabase: {e}")
            logger.info("Procediendo a volcar datos en archivo local de simulación por seguridad.")
            _save_local_simulated_json(args.titulo, documento_id, all_chunks_payload)
    else:
        logger.warning(
            "Supabase no está configurado o tiene valores placeholder. "
            "El script correrá en MODO SIMULACIÓN y guardará los resultados localmente."
        )
        _save_local_simulated_json(args.titulo, documento_id, all_chunks_payload)

def _save_local_simulated_json(titulo: str, documento_id: uuid.UUID, chunks: List[Dict[str, Any]]):
    """
    Guarda los datos ingeridos en un archivo JSON local cuando Supabase no está configurado.
    """
    import json
    data_dir = "./data"
    os.makedirs(data_dir, exist_ok=True)
    output_path = os.path.join(data_dir, f"ingested_{documento_id}.json")
    
    # Preparamos copia sin embeddings largos para que sea legible en JSON
    json_chunks = []
    for c in chunks:
        c_copy = c.copy()
        # Solo mostrar las primeras dimensiones del embedding en el log/archivo para legibilidad
        c_copy["embedding_length"] = len(c["embedding"])
        c_copy["embedding_sample"] = c["embedding"][:3] + ["..."] if c["embedding"] else []
        del c_copy["embedding"]
        json_chunks.append(c_copy)
        
    sim_data = {
        "documento": {
            "id": str(documento_id),
            "titulo": titulo,
            "creado_localmente": True
        },
        "total_chunks": len(chunks),
        "chunks": json_chunks
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sim_data, f, ensure_ascii=False, indent=2)
        
    logger.info(f"Datos de simulación guardados exitosamente en: {output_path}")
    print(f"\n📝 Modo Simulación: Documento procesado con éxito.")
    print(f"ID del Documento: {documento_id}")
    print(f"Total Chunks: {len(chunks)}")
    print(f"Archivo generado: {output_path}")

if __name__ == "__main__":
    main()
