#!/usr/bin/env python3
import hashlib
import mimetypes
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.supabase import get_supabase_client
from app.services.chunking import split_text_by_tokens
from app.services.document_parser import extract_text_from_file
from app.services.ingestion import sanitize_filename


GRADE_DIR = Path(
    "/Users/kennethjts/mex-education-api/data/oficiales/telesecundaria/grado_3"
)

OFFICIAL_FILENAMES = [
    "1_3_TS-Docente-F6-BAJA.pdf",
    "3_TS-ENS-BAJA.pdf",
    "3_TS-HC-BAJA.pdf",
    "3_TS-INGLES-BAJA.pdf",
    "3_TS-LENGUAJES-BAJA.pdf",
    "3_TS-ML-BAJA.pdf",
    "3_TS-NLP-T1-BAJA.pdf",
    "3_TS-NLP-T2-BAJA.pdf",
    "3_TS-NLP-T3-BAJA.pdf",
    "3_TS-SPC-BAJA.pdf",
    "DHC_G3_T123.pdf",
    "ENS_G3_T123.pdf",
    "L_G3_T123.pdf",
    "MULTI-TS-HIST-PUEBLO-MEX-BAJA.pdf",
    "POS_DHC_3.pdf",
    "POS_ENS_3.pdf",
    "POS_LEN_3.pdf",
    "POS_SyPC_3.pdf",
    "SPC_G3_T123.pdf",
]

FIELD_MAPPINGS = {
    "3_TS-ENS-BAJA.pdf": "Ética, Naturaleza y Sociedades",
    "3_TS-INGLES-BAJA.pdf": "Lenguajes",
    "3_TS-LENGUAJES-BAJA.pdf": "Lenguajes",
    "3_TS-SPC-BAJA.pdf": "Saberes y Pensamiento Científico",
    "DHC_G3_T123.pdf": "De lo Humano y lo Comunitario",
    "ENS_G3_T123.pdf": "Ética, Naturaleza y Sociedades",
    "L_G3_T123.pdf": "Lenguajes",
    "MULTI-TS-HIST-PUEBLO-MEX-BAJA.pdf": "Ética, Naturaleza y Sociedades",
    "POS_DHC_3.pdf": "De lo Humano y lo Comunitario",
    "POS_ENS_3.pdf": "Ética, Naturaleza y Sociedades",
    "POS_LEN_3.pdf": "Lenguajes",
    "POS_SyPC_3.pdf": "Saberes y Pensamiento Científico",
    "SPC_G3_T123.pdf": "Saberes y Pensamiento Científico",
}

MODEL = "NEM_2022"
LEVEL = "Telesecundaria"
PHASE = "Fase 6"
GRADE = "3"
GRADE_LABEL = "3° grado"
DOCUMENT_TYPE = "Libro de texto"
STORAGE_MODE = "local"
EMBEDDING_MODEL = "text-embedding-3-small"
CHUNK_BATCH_SIZE = 20
EMBEDDING_RETRIES = 3


def calculate_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_local_files() -> Dict[str, str]:
    actual = {path.name for path in GRADE_DIR.glob("*.pdf")}
    expected = set(OFFICIAL_FILENAMES)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        raise RuntimeError(
            f"Carpeta inválida. Faltantes={missing or 'ninguno'}; "
            f"inesperados={unexpected or 'ninguno'}"
        )

    hashes = {name: calculate_hash(GRADE_DIR / name) for name in OFFICIAL_FILENAMES}
    if len(set(hashes.values())) != len(hashes):
        raise RuntimeError("La carpeta grado_3 contiene PDFs duplicados por hash.")
    return hashes


def get_grade3_documents(supabase) -> List[Dict[str, Any]]:
    response = (
        supabase.table("documentos")
        .select("*")
        .eq("nivel", LEVEL)
        .eq("grado", GRADE)
        .execute()
    )
    return response.data


def count_vectorized_chunks(supabase, document_id: str) -> int:
    response = (
        supabase.table("chunks_nem")
        .select("id", count="exact")
        .eq("documento_id", document_id)
        .not_.is_("embedding", "null")
        .execute()
    )
    return response.count if response.count is not None else len(response.data)


def find_existing(
    documents: List[Dict[str, Any]],
    filename: str,
    file_hash: str,
) -> List[Dict[str, Any]]:
    return [
        doc
        for doc in documents
        if doc.get("titulo") == filename or doc.get("hash") == file_hash
    ]


def is_valid_document(supabase, document: Dict[str, Any], file_hash: str) -> bool:
    if document.get("estado") != "completed":
        return False
    if document.get("hash") != file_hash:
        return False
    if document.get("nivel") != LEVEL or str(document.get("grado")) != GRADE:
        return False
    return count_vectorized_chunks(supabase, str(document["id"])) > 0


def local_metadata() -> Dict[str, str]:
    return {
        "grado_label": GRADE_LABEL,
        "estado": "completed",
        "storage_mode": STORAGE_MODE,
    }


def document_payload(
    document_id: str,
    path: Path,
    file_hash: str,
    field: str,
    estado: str,
) -> Dict[str, Any]:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/pdf"
    return {
        "id": document_id,
        "titulo": path.name,
        "modelo": MODEL,
        "nivel": LEVEL,
        "fase": PHASE,
        "grado": GRADE,
        "campo_formativo": field,
        "tipo_documento": DOCUMENT_TYPE,
        "storage_path": str(path.resolve()),
        "nombre_original": path.name,
        "nombre_sanitizado": sanitize_filename(path.name),
        "extension": "pdf",
        "mime_type": mime_type,
        "tamano": path.stat().st_size,
        "hash": file_hash,
        "estado": estado,
        "error_message": None,
        "metadata_completa": local_metadata(),
    }


def update_valid_document_to_local(
    supabase,
    document: Dict[str, Any],
    path: Path,
) -> None:
    metadata = document.get("metadata_completa") or {}
    metadata.update(local_metadata())
    (
        supabase.table("documentos")
        .update(
            {
                "storage_path": str(path.resolve()),
                "metadata_completa": metadata,
                "error_message": None,
            }
        )
        .eq("id", document["id"])
        .eq("nivel", LEVEL)
        .eq("grado", GRADE)
        .execute()
    )


def generate_embedding(client: OpenAI, text: str) -> List[float]:
    last_error: Optional[Exception] = None
    for attempt in range(1, EMBEDDING_RETRIES + 1):
        try:
            response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
            return response.data[0].embedding
        except Exception as exc:
            last_error = exc
            if attempt < EMBEDDING_RETRIES:
                time.sleep(attempt * 2)
    raise RuntimeError(f"No se pudo generar embedding real: {last_error}")


def prepare_chunks(
    client: OpenAI,
    path: Path,
    document_id: str,
    field: str,
) -> List[Dict[str, Any]]:
    file_bytes = path.read_bytes()
    text = extract_text_from_file(file_bytes, "pdf", path.name)
    if not text.strip():
        raise ValueError("El PDF no contiene texto extraíble.")

    chunks = split_text_by_tokens(text, chunk_size=700, overlap=100)
    if not chunks:
        raise ValueError("No se generaron chunks.")

    metadata = {
        "modelo": MODEL,
        "nivel": LEVEL,
        "fase": PHASE,
        "grado": GRADE,
        "grado_label": GRADE_LABEL,
        "campo_formativo": field,
        "tipo_documento": DOCUMENT_TYPE,
        "estado": "completed",
        "storage_mode": STORAGE_MODE,
    }
    prepared = []
    for index, chunk in enumerate(chunks, start=1):
        print(
            f"    embedding {index}/{len(chunks)}",
            end="\r",
            flush=True,
        )
        prepared.append(
            {
                "id": str(uuid.uuid4()),
                "documento_id": document_id,
                "texto": chunk["texto"],
                "pagina": 1,
                "chunk_index": chunk["chunk_index"],
                "embedding": generate_embedding(client, chunk["texto"]),
                "metadata": metadata,
            }
        )
    print(" " * 50, end="\r", flush=True)
    return prepared


def persist_document(
    supabase,
    path: Path,
    file_hash: str,
    existing: Optional[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
    field: str,
) -> None:
    document_id = str(existing["id"]) if existing else chunks[0]["documento_id"]
    payload = document_payload(document_id, path, file_hash, field, "processing")

    if existing:
        (
            supabase.table("documentos")
            .update({key: value for key, value in payload.items() if key != "id"})
            .eq("id", document_id)
            .eq("nivel", LEVEL)
            .eq("grado", GRADE)
            .execute()
        )
    else:
        payload["created_at"] = datetime.now(timezone.utc).isoformat()
        supabase.table("documentos").insert(payload).execute()

    try:
        # Solo limpia chunks del mismo documento incompleto de 3°; nunca borra el documento.
        if existing:
            (
                supabase.table("chunks_nem")
                .delete()
                .eq("documento_id", document_id)
                .execute()
            )

        for start in range(0, len(chunks), CHUNK_BATCH_SIZE):
            batch = chunks[start : start + CHUNK_BATCH_SIZE]
            supabase.table("chunks_nem").insert(batch).execute()

        (
            supabase.table("documentos")
            .update({"estado": "completed", "error_message": None})
            .eq("id", document_id)
            .eq("nivel", LEVEL)
            .eq("grado", GRADE)
            .execute()
        )
    except Exception as exc:
        (
            supabase.table("documentos")
            .update({"estado": "failed", "error_message": str(exc)})
            .eq("id", document_id)
            .eq("nivel", LEVEL)
            .eq("grado", GRADE)
            .execute()
        )
        raise


def ingest_all(supabase, openai_client: OpenAI, hashes: Dict[str, str]) -> Dict[str, int]:
    stats = {"reingestados": 0, "duplicados": 0, "errores": 0}

    for index, filename in enumerate(OFFICIAL_FILENAMES, start=1):
        path = GRADE_DIR / filename
        file_hash = hashes[filename]
        field = FIELD_MAPPINGS.get(filename, "General")
        print(f"[{index}/19] {filename}", flush=True)

        try:
            documents = get_grade3_documents(supabase)
            matches = find_existing(documents, filename, file_hash)
            if len(matches) > 1:
                raise RuntimeError(
                    "Hay múltiples registros para el mismo PDF; "
                    "se requiere revisión manual."
                )

            valid = next(
                (doc for doc in matches if is_valid_document(supabase, doc, file_hash)),
                None,
            )
            if valid:
                update_valid_document_to_local(supabase, valid, path)
                stats["duplicados"] += 1
                print("    omitido: documento válido con chunks", flush=True)
                continue

            existing = matches[0] if matches else None
            document_id = str(existing["id"]) if existing else str(uuid.uuid4())
            chunks = prepare_chunks(openai_client, path, document_id, field)
            persist_document(
                supabase=supabase,
                path=path,
                file_hash=file_hash,
                existing=existing,
                chunks=chunks,
                field=field,
            )
            stats["reingestados"] += 1
            print(f"    completado: {len(chunks)} chunks", flush=True)
        except Exception as exc:
            stats["errores"] += 1
            print(f"    ERROR: {exc}", flush=True)

    return stats


def validate_corpus(supabase) -> Dict[str, int]:
    documents = get_grade3_documents(supabase)
    official = [doc for doc in documents if doc.get("titulo") in OFFICIAL_FILENAMES]
    by_title: Dict[str, List[Dict[str, Any]]] = {}
    for document in official:
        by_title.setdefault(document["titulo"], []).append(document)

    with_chunks = 0
    for filename in OFFICIAL_FILENAMES:
        matches = by_title.get(filename, [])
        if len(matches) != 1:
            continue
        document = matches[0]
        if (
            document.get("estado") == "completed"
            and document.get("hash")
            and count_vectorized_chunks(supabase, str(document["id"])) > 0
        ):
            with_chunks += 1

    return {
        "oficiales": len(by_title),
        "con_chunks": with_chunks,
        "sin_chunks": len(OFFICIAL_FILENAMES) - with_chunks,
    }


def rag_available(supabase, openai_client: OpenAI) -> bool:
    query_embedding = generate_embedding(
        openai_client,
        "contenidos oficiales de tercer grado de telesecundaria",
    )
    response = supabase.rpc(
        "match_chunks_nem",
        {
            "query_embedding": query_embedding,
            "match_threshold": 0.0,
            "match_count": 1,
            "filter_metadata": {
                "modelo": MODEL,
                "nivel": LEVEL,
                "fase": PHASE,
                "grado": GRADE,
                "tipo_documento": DOCUMENT_TYPE,
            },
        },
    ).execute()
    return bool(response.data)


def main() -> int:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY no está configurada.")

    hashes = validate_local_files()
    supabase = get_supabase_client()
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    stats = ingest_all(supabase, openai_client, hashes)
    validation = validate_corpus(supabase)

    try:
        rag = rag_available(supabase, openai_client)
    except Exception as exc:
        rag = False
        stats["errores"] += 1
        print(f"ERROR validando RAG: {exc}", flush=True)

    print()
    print("DOCUMENTOS OFICIALES 3°:", validation["oficiales"])
    print("CON CHUNKS VECTORIALES:", validation["con_chunks"])
    print("SIN CHUNKS:", validation["sin_chunks"])
    print("REINGESTADOS:", stats["reingestados"])
    print("DUPLICADOS:", stats["duplicados"])
    print("ERRORES:", stats["errores"])
    print("RAG PURO 3° DISPONIBLE:", "sí" if rag else "no")

    complete = (
        validation["oficiales"] == 19
        and validation["con_chunks"] == 19
        and validation["sin_chunks"] == 0
        and stats["errores"] == 0
        and rag
    )
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
