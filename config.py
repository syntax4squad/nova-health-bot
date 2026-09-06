import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or (
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'nova.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@nova.local")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    # --- Fact-checker (claim_checker.py) settings ---
    # SEARCH_PROVIDER: "auto" (default), "serper", "serpapi", "google_cse",
    # "duckduckgo", or "none" to disable live search entirely.
    SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "auto")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
    SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")
    GOOGLE_CSE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY", "")
    GOOGLE_CSE_CX = os.getenv("GOOGLE_CSE_CX", "")
    FACT_CHECK_MAX_CLAIM_LENGTH = int(os.getenv("FACT_CHECK_MAX_CLAIM_LENGTH", "2000"))
    FACT_CHECK_MAX_SEARCH_RESULTS = int(os.getenv("FACT_CHECK_MAX_SEARCH_RESULTS", "8"))
    FACT_CHECK_CACHE_TTL = int(os.getenv("FACT_CHECK_CACHE_TTL", "21600"))  # 6 hours
    FACT_CHECK_MIN_TRUSTED_SOURCES = int(os.getenv("FACT_CHECK_MIN_TRUSTED_SOURCES", "2"))
    FACT_CHECK_ENABLE_LIVE_SEARCH = os.getenv("FACT_CHECK_ENABLE_LIVE_SEARCH", "1") == "1"
    FACT_CHECK_RATE_LIMIT_PER_MIN = int(os.getenv("FACT_CHECK_RATE_LIMIT_PER_MIN", "6"))
