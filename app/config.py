"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Application settings."""
    
    # Slack
    slack_bot_token: str = os.getenv("SLACK_BOT_TOKEN", "")
    slack_app_token: str = os.getenv("SLACK_APP_TOKEN", "")
    slack_signing_secret: str = os.getenv("SLACK_SIGNING_SECRET", "")
    
    # Google Cloud / Vertex AI
    google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    google_cloud_region: str = os.getenv("GOOGLE_CLOUD_REGION", "us-east5")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4@20250514")
    
    # GitHub
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///forum_replier.db")
    
    # ChromaDB
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")


settings = Settings()


