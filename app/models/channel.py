"""Channel model for monitored Slack channels."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.models.database import Base


class MonitoredChannel(Base):
    """A Slack channel being monitored by the bot."""
    
    __tablename__ = "monitored_channels"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    slack_channel_id = Column(String(50), nullable=False, index=True)
    slack_channel_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workspace = relationship("Workspace", back_populates="channels")
    sources = relationship("KnowledgeSource", back_populates="channel", cascade="all, delete-orphan")
    conversations = relationship("ConversationLog", back_populates="channel", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<MonitoredChannel #{self.slack_channel_name} ({self.slack_channel_id})>"


