"""Environment-backed configuration for AnimeX."""
import os
from dotenv import load_dotenv

load_dotenv()


def _int_env(name, default, minimum=1, maximum=300):
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise RuntimeError(f"{name} must be an integer.")
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}.")
    return value


class Config:
    APP_NAME = os.getenv("APP_NAME", "AnimeX")
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = _int_env("PORT", 5000, 1, 65535)
    API_TIMEOUT = _int_env("API_TIMEOUT", 12, 2, 60)
    ANILIST_GRAPHQL_URL = os.getenv("ANILIST_GRAPHQL_URL", "https://graphql.anilist.co").rstrip("/")
    JIKAN_COMPATIBLE_BASE_URL = os.getenv("JIKAN_COMPATIBLE_BASE_URL", "").rstrip("/")
    SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
    # Kept only for backwards-compatible deployment environments. AnimeX does not
    # need a service-role key for user-owned library operations; never expose it.
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    DOWNLOADS_BUCKET = os.getenv("DOWNLOADS_BUCKET", "legal-anime-downloads")
    MAX_CONTENT_LENGTH = 64 * 1024
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "300 per hour")
    RATELIMIT_PUBLIC = os.getenv("RATELIMIT_PUBLIC", "90 per minute")
    RATELIMIT_SEARCH = os.getenv("RATELIMIT_SEARCH", "30 per minute")
    RATELIMIT_USER = os.getenv("RATELIMIT_USER", "120 per minute")
    PREFERRED_URL_SCHEME = "https"
