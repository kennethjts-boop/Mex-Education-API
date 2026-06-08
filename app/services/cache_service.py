import hashlib
import json
import time
import threading
from typing import Any, Optional, Dict

class MemoryCache:
    """
    Caché en memoria thread-safe con soporte de expiración de TTL y hashing determinista.
    """
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key_data: Any) -> Optional[Any]:
        key = self._make_key(key_data)
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry["expires_at"] > time.time():
                    return entry["value"]
                else:
                    # Eliminar llave expirada
                    del self._cache[key]
        return None

    def set(self, key_data: Any, value: Any, ttl_seconds: int = 1800):
        key = self._make_key(key_data)
        with self._lock:
            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl_seconds
            }

    def clear(self):
        with self._lock:
            self._cache.clear()

    def _make_key(self, data: Any) -> str:
        """
        Genera una clave hash SHA-256 única y consistente basada en los datos de entrada.
        Ordena diccionarios y listas para garantizar consistencia.
        """
        if isinstance(data, str):
            serialized = data
        else:
            try:
                # Usar sort_keys=True para serializar diccionarios de forma determinista
                serialized = json.dumps(data, sort_keys=True)
            except Exception:
                serialized = str(data)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

# Instancias globales para caché de RAG y Planeaciones
rag_cache = MemoryCache()
plan_cache = MemoryCache()
