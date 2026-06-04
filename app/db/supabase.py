import logging
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

supabase_client: Client = None

# Check if we have valid configurations or if we are using placeholders
is_supabase_configured = (
    settings.SUPABASE_URL 
    and "placeholder" not in settings.SUPABASE_URL 
    and "your-project-id" not in settings.SUPABASE_URL
    and settings.SUPABASE_SERVICE_ROLE_KEY 
    and "placeholder" not in settings.SUPABASE_SERVICE_ROLE_KEY
    and "your-service-role" not in settings.SUPABASE_SERVICE_ROLE_KEY
)

if is_supabase_configured:
    try:
        supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        logger.info("Supabase client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        supabase_client = None
else:
    logger.warning(
        "Supabase credentials are not fully configured or are placeholders. "
        "API will start, but database operations will be mock-simulated."
    )

def get_supabase_client() -> Client:
    """
    Returns the initialized Supabase client.
    Raises RuntimeError if client is not configured when requested.
    """
    if supabase_client is None:
        raise RuntimeError("Supabase client is not initialized. Check your environment variables.")
    return supabase_client
