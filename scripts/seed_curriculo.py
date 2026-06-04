#!/usr/bin/env python3
import os
import sys
import argparse
import json
import logging
from typing import List, Dict, Any

# Añadir el directorio raíz al sys.path para poder importar módulos de la app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.supabase import supabase_client, is_supabase_configured

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_curriculo")

def main():
    parser = argparse.ArgumentParser(description="Script para sembrar el currículo estructurado de la NEM en Supabase.")
    parser.add_argument(
        "--file", 
        default="data/seed/seed_nem_secundaria_fase6.json", 
        help="Ruta al archivo JSON con el currículo de semilla."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula la siembra de datos sin realizar cambios reales."
    )
    args = parser.parse_args()

    seed_path = args.file
    if not os.path.exists(seed_path):
        logger.error(f"El archivo semilla no existe en la ruta: {seed_path}")
        sys.exit(1)

    logger.info(f"Cargando semilla desde: {seed_path}")
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error al leer/parsear el archivo JSON: {e}")
        sys.exit(1)

    contenidos = data.get("contenidos", [])
    if not contenidos:
        logger.warning("No se encontraron contenidos para sembrar en el archivo JSON.")
        sys.exit(0)

    # Preparar registros para contenidos_nem y pda_nem
    contenidos_to_insert = []
    pdas_to_insert = []

    for c in contenidos:
        c_record = {
            "id": c["id"],
            "modelo": c["modelo"],
            "nivel": c["nivel"],
            "fase": c["fase"],
            "grado": str(c["grado"]),
            "campo_formativo": c["campo_formativo"],
            "contenido": c["contenido"],
            "descripcion": c.get("descripcion", ""),
            "fuente": c["fuente"]
        }
        contenidos_to_insert.append(c_record)

        for p in c.get("pda", []):
            p_record = {
                "id": p["id"],
                "contenido_id": c["id"],
                "modelo": c["modelo"],
                "nivel": c["nivel"],
                "fase": c["fase"],
                "grado": str(c["grado"]),
                "campo_formativo": c["campo_formativo"],
                "contenido": c["contenido"],
                "pda": p["pda"],
                "fuente": p["fuente"]
            }
            pdas_to_insert.append(p_record)

    logger.info(f"Se procesaron {len(contenidos_to_insert)} contenidos y {len(pdas_to_insert)} PDAs.")

    # Verificar si Supabase está activo
    supabase_ready = is_supabase_configured and supabase_client is not None

    if args.dry_run or not supabase_ready:
        if not supabase_ready:
            logger.warning("Supabase no está configurado o tiene valores por defecto. Se ejecutará en modo SIMULACIÓN.")
        else:
            logger.info("Modo --dry-run activado. Se ejecutará en modo SIMULACIÓN.")
        
        print("\n" + "="*50)
        print("🧪 SIMULACIÓN DE SIEMBRA CURRICULAR (Dry-Run / Offline)")
        print("="*50)
        print(f"Total Contenidos a insertar/upsert: {len(contenidos_to_insert)}")
        for idx, c in enumerate(contenidos_to_insert, start=1):
            print(f"  {idx}. [{c['campo_formativo']}] (Grado {c['grado']}): {c['contenido'][:60]}...")
            
        print(f"\nTotal PDAs a insertar/upsert: {len(pdas_to_insert)}")
        for idx, p in enumerate(pdas_to_insert, start=1):
            print(f"  {idx}. [Contenido Ref: {p['contenido_id'][:8]}...]: {p['pda'][:60]}...")
            
        print("-"*50)
        print("✅ SIMULACIÓN COMPLETADA CON ÉXITO.")
        print("="*50 + "\n")
        sys.exit(0)

    # Siembra real en base de datos
    logger.info("Iniciando inserción/upsert en la base de datos Supabase...")
    try:
        # 1. Sembrar contenidos_nem
        logger.info("Insertando en contenidos_nem...")
        res_c = supabase_client.table("contenidos_nem").upsert(contenidos_to_insert).execute()
        logger.info(f"Se insertaron/actualizaron {len(res_c.data)} contenidos.")

        # 2. Sembrar pda_nem
        logger.info("Insertando en pda_nem...")
        res_p = supabase_client.table("pda_nem").upsert(pdas_to_insert).execute()
        logger.info(f"Se insertaron/actualizaron {len(res_p.data)} PDAs.")

        print("\n" + "="*50)
        print("🚀 SIEMBRA CURRICULAR EN SUPABASE EXITOSA")
        print("="*50)
        print(f"Contenidos registrados: {len(res_c.data)}")
        print(f"PDAs registrados:        {len(res_p.data)}")
        print("="*50 + "\n")

    except Exception as e:
        logger.error(f"Error durante la siembra de base de datos: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
