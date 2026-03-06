"""Configuration loaded from environment variables."""

import os
import sys

from dotenv import load_dotenv

# Load .env from the cloud-bot root (one level up from app/)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(_env_path, override=True)


class Config:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    FATHOM_API_KEY = os.getenv("FATHOM_API_KEY", "")
    NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
    NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")
    GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
    POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "900"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        """Check all required config. Exits on failure."""
        errors = []
        if not cls.ANTHROPIC_API_KEY or cls.ANTHROPIC_API_KEY == "your-api-key-here":
            errors.append("ANTHROPIC_API_KEY is not set")
        if not cls.FATHOM_API_KEY:
            errors.append("FATHOM_API_KEY is not set")
        if not cls.NOTION_API_KEY:
            errors.append("NOTION_API_KEY is not set")
        if not cls.NOTION_DATABASE_ID:
            errors.append("NOTION_DATABASE_ID is not set")
        if not cls.GMAIL_ADDRESS:
            errors.append("GMAIL_ADDRESS is not set")
        if not cls.GMAIL_APP_PASSWORD:
            errors.append("GMAIL_APP_PASSWORD is not set")
        if cls.POLL_INTERVAL_SECONDS < 60:
            errors.append("POLL_INTERVAL_SECONDS must be >= 60")
        if errors:
            print("Configuration errors:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
