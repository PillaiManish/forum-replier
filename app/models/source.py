"""Knowledge source model for documentation, GitHub repos, etc."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
import enum

from app.models.database import Base


class SourceType(enum.Enum):
    """Types of knowledge sources."""
    DOCUMENTATION = "documentation"
    GITHUB_OPERATOR = "github_operator"
    GITHUB_OPERAND = "github_operand"
    GITHUB_ISSUES = "github_issues"
    SLACK_HISTORY = "slack_history"


class SourceStatus(enum.Enum):
    """Status of knowledge source indexing."""
    PENDING = "pending"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"


class KnowledgeSource(Base):
    """A knowledge source for answering questions."""
    
    __tablename__ = "knowledge_sources"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    channel_id = Column(String(36), ForeignKey("monitored_channels.id"), nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    url = Column(Text, nullable=False)
    status = Column(Enum(SourceStatus), default=SourceStatus.PENDING)
    last_indexed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    channel = relationship("MonitoredChannel", back_populates="sources")
    
    def __repr__(self):
        return f"<KnowledgeSource {self.source_type.value}: {self.url[:50]}>"


