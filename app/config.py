"""
iGosa — Configuration module.
Loads settings from environment variables.
Tries python-dotenv for .env file support; falls back to os.getenv defaults.
"""
import os

# Load .env file (built-in, no dependencies needed)
def _load_env():
    for path in [os.path.join(os.path.dirname(__file__), '..', '.env'), '.env']:
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, val = line.split('=', 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key not in os.environ:
                            os.environ[key] = val
            return

_load_env()

# Also try python-dotenv if installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Settings:
    """Application settings loaded from environment variables."""

    # ── AI ────────────────────────────────
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

    @property
    def ai_provider(self) -> str:
        """Auto-detect which AI provider to use."""
        if self.openai_api_key:
            return "openai"
        if self.anthropic_api_key:
            return "anthropic"
        return "openai"

    # ── Evolution API ─────────────────────
    evolution_api_url: str = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
    evolution_api_key: str = os.getenv("EVOLUTION_API_KEY", "")
    evolution_instance_name: str = os.getenv("EVOLUTION_INSTANCE_NAME", "igosa")

    # ── Webhook ───────────────────────────
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "change-me")
    port: int = int(os.getenv("PORT", "8000"))

    # ── Database ──────────────────────────
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./igosa.db")

    # ── Redis ─────────────────────────────
    redis_url: str = os.getenv("REDIS_URL", "")

    # ── App ───────────────────────────────
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    default_country_code: str = os.getenv("DEFAULT_COUNTRY_CODE", "27")
    default_city: str = os.getenv("DEFAULT_CITY", "Johannesburg")


settings = Settings()
