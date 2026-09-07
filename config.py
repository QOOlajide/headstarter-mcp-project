"""
Configuration Management
Validates and manages environment variables and configuration settings
"""
import os
import sys
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration with validation"""

    # Slack Configuration
    SLACK_BOT_TOKEN: Optional[str] = os.getenv("SLACK_BOT_TOKEN")
    SLACK_CHANNEL: Optional[str] = os.getenv("SLACK_CHANNEL")

    # Google Calendar Configuration
    GOOGLE_TOKEN_FILE: str = os.getenv("GOOGLE_TOKEN_FILE", "token.json")
    GOOGLE_CREDENTIALS_FILE: str = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

    # Notion Configuration (dual databases per requirements §3.2)
    NOTION_API_KEY: Optional[str] = os.getenv("NOTION_API_KEY")
    # Prefer dedicated meetings DB id; fall back to legacy NOTION_DATABASE_ID
    NOTION_MEETINGS_DATABASE_ID: Optional[str] = (
        os.getenv("NOTION_MEETINGS_DATABASE_ID") or os.getenv("NOTION_DATABASE_ID")
    )
    NOTION_DIRECTIVES_DATABASE_ID: Optional[str] = os.getenv(
        "NOTION_DIRECTIVES_DATABASE_ID"
    )
    # Legacy alias kept for older callers
    NOTION_DATABASE_ID: Optional[str] = NOTION_MEETINGS_DATABASE_ID

    # Gemini Configuration
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    # Webhook / local hub
    WEBHOOK_HOST: str = os.getenv("WEBHOOK_HOST", "127.0.0.1")
    WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8000"))

    @classmethod
    def validate(cls) -> dict[str, bool]:
        """
        Validate that all required configuration is present
        Returns a dictionary indicating which services are configured
        """
        validation = {
            "slack": bool(cls.SLACK_BOT_TOKEN),
            "google_calendar": bool(os.path.exists(cls.GOOGLE_CREDENTIALS_FILE)),
            "notion": bool(cls.NOTION_API_KEY and cls.NOTION_MEETINGS_DATABASE_ID),
            "notion_directives": bool(
                cls.NOTION_API_KEY and cls.NOTION_DIRECTIVES_DATABASE_ID
            ),
            "gemini": bool(cls.GEMINI_API_KEY),
        }
        return validation

    @classmethod
    def get_missing_config(cls) -> list[str]:
        """Get list of missing configuration items"""
        missing = []
        validation = cls.validate()

        if not validation["slack"]:
            missing.append("SLACK_BOT_TOKEN")

        if not validation["google_calendar"]:
            missing.append(f"Google credentials file ({cls.GOOGLE_CREDENTIALS_FILE})")

        if not cls.NOTION_API_KEY:
            missing.append("NOTION_API_KEY")
        if not cls.NOTION_MEETINGS_DATABASE_ID:
            missing.append("NOTION_MEETINGS_DATABASE_ID (or NOTION_DATABASE_ID)")
        if not cls.NOTION_DIRECTIVES_DATABASE_ID:
            missing.append("NOTION_DIRECTIVES_DATABASE_ID")

        if not validation["gemini"]:
            missing.append("GEMINI_API_KEY")

        return missing

    @classmethod
    def print_config_status(cls):
        """Print configuration status to stderr (stdout must stay MCP JSON-RPC)."""
        validation = cls.validate()
        missing = cls.get_missing_config()
        ok = "OK"
        missing_label = "Missing"

        print("=" * 50, file=sys.stderr)
        print("Configuration Status", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
        print(f"Slack: {ok if validation['slack'] else missing_label}", file=sys.stderr)
        print(
            f"Google Calendar: {ok if validation['google_calendar'] else missing_label}",
            file=sys.stderr,
        )
        print(f"Notion Meetings: {ok if validation['notion'] else missing_label}", file=sys.stderr)
        print(
            f"Notion Directives: {ok if validation['notion_directives'] else missing_label}",
            file=sys.stderr,
        )
        print(f"Gemini: {ok if validation['gemini'] else missing_label}", file=sys.stderr)

        if missing:
            print("Missing Configuration:", file=sys.stderr)
            for item in missing:
                print(f"  - {item}", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
