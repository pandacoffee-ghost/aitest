import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, Integer, Boolean, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class SourceType(str, Enum):
    WEBSITE = "website"
    API = "api"
    RSS = "rss"


class Protocol(str, Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class IntelligenceSourceModel(Base):
    __tablename__ = "intelligence_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    url = Column(String(2000), nullable=False)
    source_type = Column(String(50), nullable=False, default=SourceType.WEBSITE.value)
    采集周期 = Column(Integer, default=60)
    enabled = Column(Boolean, default=False)
    headers = Column(JSON, default=dict)
    cookies = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    intelligence_items = relationship("IntelligenceDetailModel", back_populates="source")


class ProxyModel(Base):
    __tablename__ = "proxies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ip = Column(String(50), nullable=False)
    port = Column(Integer, nullable=False)
    protocol = Column(String(20), default=Protocol.HTTP.value)
    username = Column(String(100), nullable=True)
    password = Column(String(100), nullable=True)
    quality_score = Column(Float, default=1.0)
    failure_count = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)
    last_tested_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserAgentModel(Base):
    __tablename__ = "user_agents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ua_string = Column(String(500), nullable=False)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CollectionTaskModel(Base):
    __tablename__ = "collection_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    source_ids = Column(JSON, default=list)
    proxy_enabled = Column(Boolean, default=True)
    ua_enabled = Column(Boolean, default=True)
    cron_expression = Column(String(100), nullable=True)
    timeout = Column(Integer, default=300)
    retry_count = Column(Integer, default=3)
    status = Column(String(50), default=TaskStatus.PENDING.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IntelligenceDetailModel(Base):
    __tablename__ = "intelligence_details"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(36), ForeignKey("intelligence_sources.id"), nullable=True)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    keywords = Column(JSON, default=list)
    entities = Column(JSON, default=list)
    raw_data = Column(JSON, default=dict)
    collected_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow)
    deduplication_key = Column(String(200), nullable=True, index=True)

    source = relationship("IntelligenceSourceModel", back_populates="intelligence_items")
