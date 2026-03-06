"""
Configuration module for Support Assistant.
Loads settings from environment variables using python-dotenv.
"""

import os
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Anthropic API settings
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    # Gmail IMAP settings
    GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
    IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
    IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))

    # Polling interval (default 5 minutes = 300 seconds)
    POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))

    # Support keywords for initial filtering
    SUPPORT_KEYWORDS = [
        kw.strip().lower()
        for kw in os.getenv(
            "SUPPORT_KEYWORDS",
            "help,issue,problem,error,not working,broken,how do I,can't,unable,support,question"
        ).split(",")
    ]

    # Optional Notion database ID for help articles
    NOTION_HELP_DATABASE_ID = os.getenv("NOTION_HELP_DATABASE_ID")

    # Logging level
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # File to track processed email IDs
    PROCESSED_EMAILS_FILE = "processed_emails.txt"

    @classmethod
    def validate(cls):
        """
        Validate that required configuration is present.
        Returns a list of missing/invalid configuration items.
        """
        errors = []

        if not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is not set")

        if not cls.GMAIL_ADDRESS:
            errors.append("GMAIL_ADDRESS is not set")
        elif "@" not in cls.GMAIL_ADDRESS:
            errors.append("GMAIL_ADDRESS does not appear to be a valid email")

        if not cls.GMAIL_APP_PASSWORD:
            errors.append("GMAIL_APP_PASSWORD is not set")

        if cls.POLL_INTERVAL_SECONDS < 60:
            errors.append("POLL_INTERVAL_SECONDS should be at least 60 to avoid rate limiting")

        return errors

    @classmethod
    def display(cls) -> str:
        """Return a display-safe view of configuration (masks sensitive values)."""
        return f"""
Configuration:
  Anthropic API Key: {'*' * 8 if cls.ANTHROPIC_API_KEY else '(not set)'}
  Gmail Address: {cls.GMAIL_ADDRESS}
  Gmail Password: {'*' * 8 if cls.GMAIL_APP_PASSWORD else '(not set)'}
  IMAP Server: {cls.IMAP_SERVER}:{cls.IMAP_PORT}
  Poll Interval: {cls.POLL_INTERVAL_SECONDS} seconds
  Log Level: {cls.LOG_LEVEL}
"""
