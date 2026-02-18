"""
Configuration Management
Validates and manages environment variables and configuration settings
"""
import os
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
    
    # Notion Configuration
    NOTION_API_KEY: Optional[str] = os.getenv("NOTION_API_KEY")
    NOTION_DATABASE_ID: Optional[str] = os.getenv("NOTION_DATABASE_ID")
    
    @classmethod
    def validate(cls) -> dict[str, bool]:
        """
        Validate that all required configuration is present
        Returns a dictionary indicating which services are configured
        """
        validation = {
            "slack": bool(cls.SLACK_BOT_TOKEN and cls.SLACK_CHANNEL),
            "google_calendar": bool(os.path.exists(cls.GOOGLE_CREDENTIALS_FILE)),
            "notion": bool(cls.NOTION_API_KEY and cls.NOTION_DATABASE_ID)
        }
        return validation
    
    @classmethod
    def get_missing_config(cls) -> list[str]:
        """Get list of missing configuration items"""
        missing = []
        validation = cls.validate()
        
        if not validation["slack"]:
            if not cls.SLACK_BOT_TOKEN:
                missing.append("SLACK_BOT_TOKEN")
            if not cls.SLACK_CHANNEL:
                missing.append("SLACK_CHANNEL")
        
        if not validation["google_calendar"]:
            missing.append(f"Google credentials file ({cls.GOOGLE_CREDENTIALS_FILE})")
        
        if not validation["notion"]:
            if not cls.NOTION_API_KEY:
                missing.append("NOTION_API_KEY")
            if not cls.NOTION_DATABASE_ID:
                missing.append("NOTION_DATABASE_ID")
        
        return missing
    
    @classmethod
    def print_config_status(cls):
        """Print configuration status to console"""
        validation = cls.validate()
        missing = cls.get_missing_config()
        
        print("\n" + "="*50)
        print("Configuration Status")
        print("="*50)
        print(f"Slack: {'✓ Configured' if validation['slack'] else '✗ Missing'}")
        print(f"Google Calendar: {'✓ Configured' if validation['google_calendar'] else '✗ Missing'}")
        print(f"Notion: {'✓ Configured' if validation['notion'] else '✗ Missing'}")
        
        if missing:
            print("\nMissing Configuration:")
            for item in missing:
                print(f"  - {item}")
        print("="*50 + "\n")

