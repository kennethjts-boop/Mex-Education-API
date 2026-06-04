#!/usr/bin/env python3
import os
import sys
import argparse
import json
import logging
from uuid import UUID
from collections import Counter
from typing import List, Dict, Any

# Añadir el directorio raíz al sys.path para poder importar módulos de la app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("validate_curriculo")

def is_valid_uuid(val: str) -> bool:
    try:
        UUID(str(val))
        return True
    except ValueError:
        return False

def main():
    parser = argparse.ArgumentParser(description="Script de validación del currículo estructurado de la NEM.")
    parser.add_argument(
        "--file", 
        default="data/seed/seed_nem_secundaria_fase6.json", 
        help="Ruta al archivo JSON con el currículo de semilla."
    )
    args = parser.parse_args()

    seed_path = args.file
    if not os.path.exists(seed_path):
        logger.error(f"El archivo semilla no existe en la ruta: {seed_path}")
        sys.exit(1)

    logger.info(f"Iniciando validación del archivo: {seed_path}")

    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error al leer/parsear el archivo JSON: {e}")
        sys.exit(1)

    if not isinstance(data, dict) or "contenidos" not in data:
        logger.error("El archivo JSON debe contener un objeto con la clave principal 'contenidos'.")
        sys.exit(1)

    contenidos = data["contenidos"]
    if not isinstance(contenidos, list):
        logger.error("La clave 'contenidos' debe ser una lista.")
        sys.exit(1)

    # 1. Variables de control y contadores
    total_contenidos = len(contenidos)
    total_pdas = 0
    
    seen_uuids = {}  # uuid -> path/description
    uuid_invalidos = []
    uuid_duplicados = []
    
    campos_faltantes_contenido = []
    campos_faltantes_pda = []
    
    # Listas para chequear duplicados semánticos
    contenido_textos = [] # (grado, campo, texto)
    pda_textos = []       # (contenido_id, texto)
    
    contenido_duplicados = []
    pda_duplicados = []
    
    # Estadísticas
    campo_stats = Counter()
    grado_stats = Counter()
    pda_por_contenido = []

    # 2. Análisis iterativo de contenidos y PDAs
    for c_idx, c in enumerate(contenidos):
        c_id = c.get("id")
        c_path = f"contenidos[{c_idx}]"
        
        # Validar campos requeridos en contenido
        required_c_fields = ["modelo", "nivel", "fase", "grado", "campo_formativo", "contenido", "fuente"]
        missing_c = [f for f in required_c_fields if not c.get(f)]
        if missing_c:
            campos_faltantes_contenido.append({
                "path": c_path,
                "missing": missing_c,
                "preview": c.get("contenido", "")[:30]
            })

        # Validar UUID del contenido
        if not c_id:
            uuid_invalidos.append({
                "path": c_path,
                "error": "UUID ausente o vacío"
            })
        elif not is_valid_uuid(c_id):
            uuid_invalidos.append({
                "path": c_path,
                "uuid": c_id,
                "error": "Formato de UUID inválido"
            })
        else:
            c_id_str = str(c_id).lower()
            if c_id_str in seen_uuids:
                uuid_duplicados.append({
                    "uuid": c_id_str,
                    "primer_uso": seen_uuids[c_id_str],
                    "segundo_uso": c_path
                })
            else:
                seen_uuids[c_id_str] = c_path

        # Recolectar metadatos para estadísticas y duplicados
        grado = c.get("grado", "Desconocido")
        campo = c.get("campo_formativo", "Desconocido")
        cont_texto = c.get("contenido", "").strip().lower()
        
        if cont_texto:
            cont_key = (grado, campo, cont_texto)
            if cont_key in contenido_textos:
                contenido_duplicados.append({
                    "grado": grado,
                    "campo_formativo": campo,
                    "contenido": c.get("contenido"),
                    "path": c_path
                })
            else:
                contenido_textos.append(cont_key)

        campo_stats[campo] += 1
        grado_stats[f"Grado {grado}"] += 1

        # Validar PDAs
        pda_list = c.get("pda", [])
        if not isinstance(pda_list, list):
            campos_faltantes_contenido.append({
                "path": c_path,
                "error": "El campo 'pda' debe ser una lista."
            })
            pda_list = []

        pda_por_contenido.append(len(pda_list))
        total_pdas += len(pda_list)

        for p_idx, p in enumerate(pda_list):
            p_id = p.get("id")
            p_path = f"contenidos[{c_idx}].pda[{p_idx}]"
            
            # Validar campos requeridos en PDA
            required_p_fields = ["pda", "fuente"]
            missing_p = [f for f in required_p_fields if not p.get(f)]
            if missing_p:
                campos_faltantes_pda.append({
                    "path": p_path,
                    "missing": missing_p,
                    "preview": p.get("pda", "")[:30]
                })

            # Validar UUID del PDA
            if not p_id:
                uuid_invalidos.append({
                    "path": p_path,
                    "error": "UUID ausente o vacío en el PDA"
                })
            elif not is_valid_uuid(p_id):
                uuid_invalidos.append({
                    "path": p_path,
                    "uuid": p_id,
                    "error": "Formato de UUID inválido en el PDA"
                })
            else:
                p_id_str = str(p_id).lower()
                if p_id_str in seen_uuids:
                    uuid_duplicados.append({
                        "uuid": p_id_str,
                        "primer_uso": seen_uuids[p_id_str],
                        "segundo_uso": p_path
                    })
                else:
                    seen_uuids[p_id_str] = p_path

            # Chequear duplicado semántico de PDA en el mismo contenido
            pda_texto = p.get("pda", "").strip().lower()
            if pda_texto:
                pda_key = (c_id, pda_texto)
                if pda_key in pda_textos:
                    pda_duplicados.append({
                        "contenido_id": str(c_id),
                        "pda": p.get("pda"),
                        "path": p_path
                    })
                else:
                    pda_textos.append(pda_key)

    # 3. Validar si el JSON es completamente válido
    is_valid = (
        len(uuid_invalidos) == 0 and 
        len(uuid_duplicados) == 0 and 
        len(campos_faltantes_contenido) == 0 and 
        len(campos_faltantes_pda) == 0
    )

    # 4. Construir reporte final
    avg_pda_per_contenido = round(total_pdas / total_contenidos, 2) if total_contenidos > 0 else 0

    report = {
        "archivo": seed_path,
        "valido": is_valid,
        "metricas_generales": {
            "total_contenidos": total_contenidos,
            "total_pda": total_pdas,
            "promedio_pdas_por_contenido": avg_pda_per_contenido,
            "campo_formativo_stats": dict(campo_stats),
            "grado_stats": dict(grado_stats)
        },
        "anomalias": {
            "campos_faltantes_contenido": campos_faltantes_contenido,
            "campos_faltantes_pda": campos_faltantes_pda,
            "uuid_invalidos": uuid_invalidos,
            "uuid_duplicados": uuid_duplicados,
            "contenido_duplicados": contenido_duplicados,
            "pda_duplicados": pda_duplicados
        }
    }

    # Guardar reporte
    reports_dir = "./reports"
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, "curriculo_validation_report.json")
    
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"Reporte de validación guardado en: {report_path}")
    except Exception as e:
        logger.error(f"No se pudo guardar el reporte de validación: {e}")

    # 5. Imprimir resumen en consola
    print("\n" + "="*50)
    print("📋 REPORTE DE VALIDACIÓN CURRICULAR (Fase 5)")
    print("="*50)
    print(f"Archivo analizado:         {seed_path}")
    print(f"Total Contenidos:          {total_contenidos}")
    print(f"Total PDA (Procesos):      {total_pdas}")
    print(f"Promedio PDA/Contenido:    {avg_pda_per_contenido}")
    print("-"*50)
    print("📊 DISTRIBUCIÓN POR CAMPO FORMATIVO:")
    for campo, count in campo_stats.items():
        print(f" - {campo[:30]:<30}: {count} contenidos")
    print("-"*50)
    print("📊 DISTRIBUCIÓN POR GRADO:")
    for grado, count in grado_stats.items():
        print(f" - {grado:<15}: {count} contenidos")
    print("-"*50)
    print("⚠️ ALERTAS Y ANOMALÍAS DE INTEGRIDAD:")
    print(f" - Campos faltantes contenido: {len(campos_faltantes_contenido)}")
    print(f" - Campos faltantes PDA:       {len(campos_faltantes_pda)}")
    print(f" - UUIDs inválidos:            {len(uuid_invalidos)}")
    print(f" - UUIDs duplicados:           {len(uuid_duplicados)}")
    print(f" - Contenidos duplicados:      {len(contenido_duplicados)}")
    print(f" - PDAs duplicados:            {len(pda_duplicados)}")
    print("-"*50)

    if is_valid:
        print("✅ VALIDACIÓN EXITOSA: El currículo estructurado cumple con todas las reglas de integridad.")
        sys.exit(0)
    else:
        print("❌ VALIDACIÓN FALLIDA: Se detectaron fallas de integridad en la semilla curricular.")
        print("Revisa el archivo de reporte JSON para más detalles sobre las fallas.")
        sys.exit(1)

if __name__ == "__main__":
    main()
