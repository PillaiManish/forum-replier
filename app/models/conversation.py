"""Conversation log model for tracking Q&A interactions."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON

from app.models.database import Base


class ConversationLog(Base):
    """Log of questions and answers for learning and feedback."""
    
    __tablename__ = "conversation_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    channel_id = Column(String(36), ForeignKey("monitored_channels.id"), nullable=False, index=True)
    thread_ts = Column(String(50), nullable=True, index=True)
    user_id = Column(String(50), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    sources_used = Column(JSON, nullable=True)  # List of source URLs/files used
    confidence = Column(String(20), nullable=True)  # high, medium, low
    feedback = Column(String(20), nullable=True)  # thumbsup, thumbsdown
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships  
    from sqlalchemy.orm import relationship
    channel = relationship("MonitoredChannel", back_populates="conversations")
    
    def __repr__(self):
        return f"<ConversationLog {self.id[:8]} in {self.channel_id[:8]}>"


