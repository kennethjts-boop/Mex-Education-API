import logging
import tiktoken
from typing import List, Dict, Any

logger = logging.getLogger("uvicorn.error")

def get_encoder(encoding_name: str = "cl100k_base"):
    """
    Attempts to get the tiktoken encoder. Fallbacks to None if it fails.
    """
    try:
        return tiktoken.get_encoding(encoding_name)
    except Exception as e:
        logger.warning(f"Could not load tiktoken encoding '{encoding_name}': {e}. Falling back to word splitting.")
        return None

def split_text_by_tokens(text: str, chunk_size: int = 700, overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Splits text into chunks of target token size with specified overlap.
    Returns a list of dictionaries with:
    - 'texto': str
    - 'chunk_index': int
    - 'token_count': int/float (approximate or exact)
    """
    if not text or not text.strip():
        return []
    
    encoder = get_encoder("cl100k_base")
    
    # Safe checks for chunk size logic to prevent infinite loop
    if chunk_size <= overlap:
        logger.warning(f"chunk_size ({chunk_size}) must be greater than overlap ({overlap}). Setting defaults.")
        chunk_size = 700
        overlap = 100
        
    if encoder is None:
        # FALLBACK: Word-based splitting.
        # Estimating 1 word ~ 1.3 tokens for typical Spanish/English text.
        words = text.split()
        word_chunk_size = max(1, int(chunk_size / 1.3))
        word_overlap = max(0, int(overlap / 1.3))
        step = max(1, word_chunk_size - word_overlap)
        
        chunks = []
        start = 0
        chunk_idx = 0
        while start < len(words):
            end = min(start + word_chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)
            chunks.append({
                "texto": chunk_text,
                "chunk_index": chunk_idx,
                "token_count": int(len(chunk_words) * 1.3)
            })
            if end == len(words):
                break
            start += step
            chunk_idx += 1
        return chunks

    # TIKTOKEN EXACT TOKENIZATION
    try:
        tokens = encoder.encode(text)
        num_tokens = len(tokens)
        step = chunk_size - overlap
        
        chunks = []
        start = 0
        chunk_idx = 0
        
        while start < num_tokens:
            end = min(start + chunk_size, num_tokens)
            chunk_tokens = tokens[start:end]
            chunk_text = encoder.decode(chunk_tokens)
            
            chunks.append({
                "texto": chunk_text.strip(),
                "chunk_index": chunk_idx,
                "token_count": len(chunk_tokens)
            })
            
            if end == num_tokens:
                break
                
            start += step
            chunk_idx += 1
            
        return chunks
    except Exception as e:
        logger.error(f"Error during tiktoken encoding: {e}. Falling back to basic string split.")
        # Super fallback
        return [{"texto": text, "chunk_index": 0, "token_count": len(text) // 4}]
