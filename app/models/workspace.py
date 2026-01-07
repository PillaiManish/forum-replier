"""Workspace model for Slack workspaces."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship

from app.models.database import Base


class Workspace(Base):
    """Represents a Slack workspace where the bot is installed."""
    
    __tablename__ = "workspaces"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slack_team_id = Column(String(50), unique=True, nullable=False, index=True)
    slack_team_name = Column(String(255), nullable=True)
    installed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    channels = relationship("MonitoredChannel", back_populates="workspace", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Workspace {self.slack_team_name} ({self.slack_team_id})>"


