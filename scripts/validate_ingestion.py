#!/usr/bin/env python3
import os
import sys
import argparse
import json
import logging
from typing import List, Dict, Any

# Añadir el directorio raíz al sys.path para poder importar el módulo 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pypdf import PdfReader
from app.services.chunking import split_text_by_tokens

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("validate_ingestion")

def clean_text(text: str) -> str:
    """Aplica la misma limpieza básica que ingest_nem.py"""
    if not text:
        return ""
    import re
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

def main():
    parser = argparse.ArgumentParser(description="Script de validación de calidad de ingestión de textos NEM.")
    parser.add_argument("--file", required=True, help="Ruta al archivo PDF local.")
    parser.add_argument("--titulo", required=True, help="Título del documento.")
    parser.add_argument("--modelo", required=True, help="Modelo educativo.")
    parser.add_argument("--nivel", required=True, help="Nivel educativo.")
    parser.add_argument("--fase", required=True, help="Fase escolar.")
    parser.add_argument("--grado", required=True, help="Grado escolar.")
    parser.add_argument("--campo_formativo", required=True, help="Campo formativo.")
    parser.add_argument("--tipo_documento", required=True, help="Tipo de documento.")

    args = parser.parse_args()

    pdf_path = args.file
    if not os.path.exists(pdf_path):
        logger.error(f"El archivo PDF no existe: {pdf_path}")
        sys.exit(1)

    logger.info(f"Validando calidad del PDF: {pdf_path}")

    # 1. Análisis de lectura y extracción de texto
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
    except Exception as e:
        logger.error(f"Error al abrir el PDF: {e}")
        sys.exit(1)

    total_characters = 0
    pages_without_text = []
    text_by_page = {}

    for page_idx, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text()
        cleaned = clean_text(raw_text)
        
        text_by_page[page_idx] = cleaned
        total_characters += len(cleaned)
        
        if not cleaned:
            pages_without_text.append(page_idx)

    # 2. Simulación de chunking y análisis de fragmentación
    all_chunks = []
    for page_idx, text in text_by_page.items():
        if not text:
            continue
        chunks = split_text_by_tokens(text, chunk_size=700, overlap=100)
        for c in chunks:
            all_chunks.append({
                "texto": c["texto"],
                "pagina": page_idx,
                "chunk_index": c["chunk_index"],
                "char_count": len(c["texto"]),
                "estimated_tokens": c.get("token_count", len(c["texto"]) // 4)
            })

    total_chunks = len(all_chunks)

    # 3. Cálculo de métricas
    avg_chunk_chars = 0
    empty_chunks = []
    small_chunks = []  # Chunks menores a 100 caracteres
    duplicate_chunks = []
    seen_texts = set()

    if total_chunks > 0:
        total_chars_in_chunks = sum(c["char_count"] for c in all_chunks)
        avg_chunk_chars = total_chars_in_chunks / total_chunks
        
        for idx, c in enumerate(all_chunks):
            if c["char_count"] == 0:
                empty_chunks.append(idx)
            elif c["char_count"] < 100:
                small_chunks.append({
                    "index": idx,
                    "pagina": c["pagina"],
                    "texto": c["texto"]
                })
            
            # Chequeo de duplicados
            normalized_text = c["texto"].lower().strip()
            if normalized_text in seen_texts:
                duplicate_chunks.append({
                    "index": idx,
                    "pagina": c["pagina"],
                    "texto_preview": c["texto"][:50] + "..."
                })
            else:
                seen_texts.add(normalized_text)

    # 4. Validar completitud de metadatos requeridos
    metadata_errors = []
    required_metadata = {
        "titulo": args.titulo,
        "modelo": args.modelo,
        "nivel": args.nivel,
        "fase": args.fase,
        "grado": args.grado,
        "campo_formativo": args.campo_formativo,
        "tipo_documento": args.tipo_documento
    }
    for k, v in required_metadata.items():
        if not v or v.strip() == "":
            metadata_errors.append(f"Falta el metadato: {k}")

    # 5. Armar reporte JSON
    report = {
        "archivo": pdf_path,
        "documento": {
            "titulo": args.titulo,
            "tipo_documento": args.tipo_documento
        },
        "metricas_generales": {
            "paginas_totales": total_pages,
            "caracteres_extraidos": total_characters,
            "chunks_generados": total_chunks,
            "promedio_caracteres_por_chunk": round(avg_chunk_chars, 2),
            "paginas_sin_texto_detectadas": len(pages_without_text)
        },
        "anomalias": {
            "chunks_vacios": len(empty_chunks),
            "chunks_pequenos": len(small_chunks),
            "chunks_duplicados": len(duplicate_chunks),
            "paginas_sin_texto": pages_without_text
        },
        "calidad_metadata": {
            "valida": len(metadata_errors) == 0,
            "errores": metadata_errors
        }
    }

    # Guardar reporte
    reports_dir = "./reports"
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, "ingestion_report.json")
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 6. Reporte por consola
    print("\n" + "="*50)
    print("📋 REPORT DE CALIDAD DE INGESTIÓN (Fase 3)")
    print("="*50)
    print(f"Documento:       {args.titulo}")
    print(f"Archivo:         {pdf_path}")
    print(f"Páginas Leídas:  {total_pages}")
    print(f"Total Chars:     {total_characters}")
    print(f"Total Chunks:    {total_chunks}")
    print(f"Tamaño Promedio: {round(avg_chunk_chars, 2)} caracteres por chunk")
    print("-"*50)
    print("⚠️ ALERTAS Y ANOMALÍAS:")
    print(f"- Páginas sin texto:    {len(pages_without_text)} {pages_without_text}")
    print(f"- Chunks vacíos:        {len(empty_chunks)}")
    print(f"- Chunks muy pequeños:  {len(small_chunks)}")
    print(f"- Chunks duplicados:    {len(duplicate_chunks)}")
    print(f"- Errores de Metadatos: {len(metadata_errors)}")
    print("-"*50)
    
    if len(pages_without_text) == 0 and len(empty_chunks) == 0 and len(small_chunks) == 0 and len(duplicate_chunks) == 0 and len(metadata_errors) == 0:
        print("✅ CALIDAD DE INGESTIÓN EXCELENTE (Cero anomalías detectadas).")
    else:
        print("💡 Se sugieren revisiones en el documento PDF original o metadatos.")
        
    print(f"\n💾 Reporte guardado en: {report_path}")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
