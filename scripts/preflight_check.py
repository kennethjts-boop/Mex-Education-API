#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request
import urllib.error
from typing import Tuple, List

def check_file_exists(filepath: str) -> Tuple[bool, str]:
    if os.path.exists(filepath) and os.path.isfile(filepath):
        return True, "Archivo encontrado."
    return False, "Archivo ausente."

def check_dir_exists(dirpath: str) -> Tuple[bool, str]:
    if os.path.exists(dirpath) and os.path.isdir(dirpath):
        return True, "Directorio encontrado."
    return False, "Directorio ausente."

def check_env_placeholders() -> Tuple[bool, str]:
    env_path = ".env"
    if not os.path.exists(env_path):
        return False, ".env no existe."
    
    placeholders = [
        "your-project-id",
        "your-service-role-key",
        "sk-your-openai-api-key",
        "your-openai-api-key"
    ]
    
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return False, f"No se pudo leer .env: {e}"
        
    for p in placeholders:
        if p in content:
            return False, f"Contiene el placeholder de ejemplo: '{p}'."
            
    # Verificar que las llaves principales no estén vacías
    lines = content.splitlines()
    keys_checked = {"SUPABASE_URL": False, "SUPABASE_SERVICE_ROLE_KEY": False, "OPENAI_API_KEY": False}
    
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k in keys_checked:
                if v:
                    keys_checked[k] = True
                else:
                    return False, f"La variable {k} está vacía en .env."
                    
    missing = [k for k, present in keys_checked.items() if not present]
    if missing:
        return False, f"Faltan o están vacías las siguientes llaves requeridas en .env: {', '.join(missing)}"
        
    return True, ".env configurado correctamente con credenciales reales."

def check_git_ignore_env() -> Tuple[bool, str]:
    gitignore_path = ".gitignore"
    if not os.path.exists(gitignore_path):
        return False, ".gitignore no existe."
        
    # 1. Intentar validar usando el comando git directamente si git está inicializado
    if os.path.exists(".git"):
        try:
            res = subprocess.run(
                ["git", "check-ignore", "-q", ".env"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            if res.returncode == 0:
                return True, ".env está correctamente ignorado por Git (verificado vía git)."
        except Exception:
            pass
            
    # 2. Fallback: buscar manualmente en .gitignore
    try:
        with open(gitignore_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except Exception as e:
        return False, f"No se pudo leer .gitignore: {e}"
        
    for line in lines:
        line_clean = line.strip()
        if line_clean == ".env" or line_clean.startswith(".env ") or line_clean.endswith(".env"):
            return True, ".env está listado en .gitignore."
            
    return False, ".env NO está listado en .gitignore (riesgo de fuga de llaves)."

def check_local_server_health() -> Tuple[bool, str]:
    # Intentamos puertos comunes: 8001 (por defecto en esta fase) o 8000
    ports = [8001, 8000]
    for port in ports:
        url = f"http://127.0.0.1:{port}/health"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.status == 200:
                    body = json_loads_safe(r.read().decode("utf-8"))
                    supabase_status = body.get("supabase", "desconocido")
                    return True, f"Servidor activo en puerto {port}. Estado Supabase: {supabase_status}."
        except Exception:
            continue
    return False, "Servidor FastAPI apagado localmente (no responde en puerto 8000 ni 8001)."

def json_loads_safe(text: str) -> dict:
    try:
        import json
        return json.loads(text)
    except Exception:
        return {}

def main():
    print("\n" + "="*60)
    print("🔍 PREFLIGHT CHECK: PREPARACIÓN GITHUB & SUPABASE (Fase 7)")
    print("="*60)
    
    checks = [
        ("requirements.txt", check_file_exists("requirements.txt")),
        ("supabase_schema.sql", check_file_exists("supabase_schema.sql")),
        ("app/main.py", check_file_exists("app/main.py")),
        (".gitignore", check_file_exists(".gitignore")),
        (".env (existencia)", check_file_exists(".env")),
        ("data/oficiales/", check_dir_exists("data/oficiales")),
        ("data/seed/", check_dir_exists("data/seed")),
        ("Validez de .env (sin placeholders)", check_env_placeholders()),
        ("Exclusión de .env en Git", check_git_ignore_env()),
        ("Conexión de Servidor Local (Opcional)", check_local_server_health())
    ]
    
    failed_critical = False
    
    for name, (success, msg) in checks:
        icon = "✅" if success else "❌"
        # La salud del servidor es opcional para subir a github, pero útil
        if not success and name != "Conexión de Servidor Local (Opcional)":
            failed_critical = True
            
        print(f" {icon}  {name:<38} : {msg}")
        
    print("-"*60)
    if failed_critical:
        print("❌ ALERTA: Algunas validaciones críticas han fallado.")
        print("   Por favor corrige los errores antes de subir el proyecto a GitHub.")
        print("="*60 + "\n")
        sys.exit(1)
    else:
        print("✅ ÉXITO: El proyecto está listo para subirse a GitHub.")
        print("   No se detectaron fugas de secretos y la estructura está sana.")
        print("="*60 + "\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
