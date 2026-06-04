import logging
import tiktoken
from typing import Tuple, Any

logger = logging.getLogger("uvicorn.error")

# Precios oficiales de OpenAI por millón de tokens (en USD)
# gpt-4o-mini
GPT_4O_MINI_INPUT_PRICE_PER_M = 0.150
GPT_4O_MINI_OUTPUT_PRICE_PER_M = 0.600

# text-embedding-3-small
EMBEDDING_PRICE_PER_M = 0.020

def get_encoder(encoding_name: str = "cl100k_base"):
    """Intenta cargar el codificador tiktoken de forma segura."""
    try:
        return tiktoken.get_encoding(encoding_name)
    except Exception as e:
        logger.warning(f"No se pudo cargar tiktoken '{encoding_name}': {e}. Se utilizará aproximación de caracteres.")
        return None

def estimate_tokens(text: str) -> int:
    """
    Calcula o aproxima la cantidad de tokens para un texto dado.
    Si tiktoken no está disponible, estima 1 token por cada 4 caracteres.
    """
    if not text:
        return 0
    
    encoder = get_encoder("cl100k_base")
    if encoder is None:
        # Fallback aproximado (1 token ≈ 4 caracteres en promedio)
        return max(1, len(text) // 4)
    
    try:
        return len(encoder.encode(text))
    except Exception as e:
        logger.error(f"Error codificando con tiktoken: {e}. Usando fallback.")
        return max(1, len(text) // 4)

def estimate_embedding_cost(text_or_tokens: Any) -> float:
    """
    Calcula el costo estimado de generación de embeddings usando text-embedding-3-small.
    Acepta tanto texto (str) como cantidad de tokens (int).
    """
    if isinstance(text_or_tokens, str):
        tokens = estimate_tokens(text_or_tokens)
    else:
        tokens = int(text_or_tokens)
        
    cost = (tokens / 1_000_000) * EMBEDDING_PRICE_PER_M
    return round(cost, 8)

def estimate_chat_cost(prompt: str, completion: str) -> Tuple[int, int, float]:
    """
    Calcula los tokens de prompt y respuesta, y estima el costo total en USD
    usando las tarifas de gpt-4o-mini.
    
    Retorna: (input_tokens, output_tokens, total_cost_usd)
    """
    input_tokens = estimate_tokens(prompt)
    output_tokens = estimate_tokens(completion)
    
    input_cost = (input_tokens / 1_000_000) * GPT_4O_MINI_INPUT_PRICE_PER_M
    output_cost = (output_tokens / 1_000_000) * GPT_4O_MINI_OUTPUT_PRICE_PER_M
    
    total_cost = input_cost + output_cost
    return input_tokens, output_tokens, round(total_cost, 8)
