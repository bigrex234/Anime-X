import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    APP_NAME = os.getenv("APP_NAME", "AnimeX")
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-me")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", "15"))
    ANILIST_GRAPHQL_URL = os.getenv("ANILIST_GRAPHQL_URL", "https://graphql.anilist.co")
    JIKAN_COMPATIBLE_BASE_URL = os.getenv("JIKAN_COMPATIBLE_BASE_URL", "").rstrip("/")
    SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    AUTH_REQUIRED_FOR_LIBRARY = True
    DOWNLOADS_BUCKET = os.getenv("DOWNLOADS_BUCKET", "legal-anime-downloads")
