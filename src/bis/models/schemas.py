from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


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


class IntelligenceSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., max_length=2000)
    source_type: SourceType = SourceType.WEBSITE
    采集周期: int = Field(default=60, ge=1)
    headers: Dict[str, str] = Field(default_factory=dict)
    cookies: Dict[str, str] = Field(default_factory=dict)


class IntelligenceSourceCreate(IntelligenceSourceBase):
    pass


class IntelligenceSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    url: Optional[str] = Field(None, max_length=2000)
    source_type: Optional[SourceType] = None
    采集周期: Optional[int] = Field(None, ge=1)
    headers: Optional[Dict[str, str]] = None
    cookies: Optional[Dict[str, str]] = None


class IntelligenceSource(IntelligenceSourceBase):
    id: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProxyBase(BaseModel):
    ip: str = Field(..., max_length=50)
    port: int = Field(..., ge=1, le=65535)
    protocol: Protocol = Protocol.HTTP
    username: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, max_length=100)


class ProxyCreate(ProxyBase):
    pass


class Proxy(ProxyBase):
    id: str
    quality_score: float
    failure_count: int
    enabled: bool
    last_tested_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class UserAgentBase(BaseModel):
    ua_string: str = Field(..., max_length=500)
    browser: Optional[str] = Field(None, max_length=100)
    os: Optional[str] = Field(None, max_length=100)


class UserAgentCreate(UserAgentBase):
    pass


class UserAgent(UserAgentBase):
    id: str
    enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SelectorType(str, Enum):
    CSS = "css"
    XPATH = "xpath"
    REGEX = "regex"


class CollectionTaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    source_ids: List[str] = Field(default_factory=list)
    
    url: Optional[str] = Field(None, max_length=2000)
    charset: str = Field(default="utf-8")
    
    list_selector: Optional[str] = None
    list_selector_type: SelectorType = SelectorType.CSS
    
    title_selector: Optional[str] = None
    title_selector_type: SelectorType = SelectorType.CSS
    
    content_selector: Optional[str] = None
    content_selector_type: SelectorType = SelectorType.CSS
    
    link_selector: Optional[str] = None
    link_selector_type: SelectorType = SelectorType.CSS
    
    date_selector: Optional[str] = None
    date_selector_type: SelectorType = SelectorType.CSS
    
    keywords: List[str] = Field(default_factory=list)
    
    do_screenshot: bool = False
    
    proxy_enabled: bool = True
    ua_enabled: bool = True
    cron_expression: Optional[str] = Field(None, max_length=100)
    timeout: int = Field(default=30, ge=5, le=300)
    retry_count: int = Field(default=2, ge=0, le=5)


class CollectionTaskCreate(CollectionTaskBase):
    pass


class CollectionTaskUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    source_ids: Optional[List[str]] = None
    url: Optional[str] = None
    charset: Optional[str] = None
    list_selector: Optional[str] = None
    list_selector_type: Optional[SelectorType] = None
    title_selector: Optional[str] = None
    title_selector_type: Optional[SelectorType] = None
    content_selector: Optional[str] = None
    content_selector_type: Optional[SelectorType] = None
    link_selector: Optional[str] = None
    link_selector_type: Optional[SelectorType] = None
    date_selector: Optional[str] = None
    date_selector_type: Optional[SelectorType] = None
    keywords: Optional[List[str]] = None
    do_screenshot: Optional[bool] = None
    proxy_enabled: Optional[bool] = None
    ua_enabled: Optional[bool] = None
    cron_expression: Optional[str] = None
    timeout: Optional[int] = Field(None, ge=5, le=300)
    retry_count: Optional[int] = Field(None, ge=0, le=5)


class CollectionTask(CollectionTaskBase):
    id: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntelligenceDetailBase(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    summary: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    entities: List[Dict[str, Any]] = Field(default_factory=list)


class IntelligenceDetail(IntelligenceDetailBase):
    id: str
    source_id: Optional[str]
    raw_data: Dict[str, Any]
    collected_at: Optional[datetime]
    processed_at: datetime

    class Config:
        from_attributes = True


class IntelligenceSearchQuery(BaseModel):
    source_id: Optional[str] = None
    keyword: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class KeywordMatchType(str, Enum):
    CONTAINS = "contains"
    EXACT = "exact"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"


class CollectionRuleBase(BaseModel):
    source_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=200)
    
    list_selector: Optional[str] = None
    list_selector_type: SelectorType = SelectorType.CSS
    
    title_selector: Optional[str] = None
    title_selector_type: SelectorType = SelectorType.CSS
    
    content_selector: Optional[str] = None
    content_selector_type: SelectorType = SelectorType.CSS
    
    link_selector: Optional[str] = None
    link_selector_type: SelectorType = SelectorType.CSS
    
    date_selector: Optional[str] = None
    date_selector_type: SelectorType = SelectorType.CSS
    date_format: Optional[str] = None
    
    keyword_match: Optional[str] = None
    keyword_match_type: KeywordMatchType = KeywordMatchType.CONTAINS
    
    regex_pattern: Optional[str] = None
    
    follow_next_page: bool = False
    next_page_selector: Optional[str] = None
    max_pages: int = Field(default=1, ge=1)
    
    priority: int = Field(default=0)


class CollectionRuleCreate(CollectionRuleBase):
    pass


class CollectionRuleUpdate(BaseModel):
    name: Optional[str] = None
    list_selector: Optional[str] = None
    list_selector_type: Optional[SelectorType] = None
    title_selector: Optional[str] = None
    title_selector_type: Optional[SelectorType] = None
    content_selector: Optional[str] = None
    content_selector_type: Optional[SelectorType] = None
    link_selector: Optional[str] = None
    link_selector_type: Optional[SelectorType] = None
    date_selector: Optional[str] = None
    date_selector_type: Optional[SelectorType] = None
    date_format: Optional[str] = None
    keyword_match: Optional[str] = None
    keyword_match_type: Optional[KeywordMatchType] = None
    regex_pattern: Optional[str] = None
    follow_next_page: Optional[bool] = None
    next_page_selector: Optional[str] = None
    max_pages: Optional[int] = Field(None, ge=1)
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class CollectionRule(CollectionRuleBase):
    id: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
