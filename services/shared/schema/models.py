from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ArticleStatus(str, Enum):
    RAW = "raw"
    CLEANED = "cleaned"
    NORMALIZED = "normalized"
    ENRICHED = "enriched"
    INDEXED = "indexed"


class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class RawArticle(BaseModel):
    """Raw article from RSS/API feeds"""
    id: str = Field(..., description="Unique article identifier")
    url: str = Field(..., description="Original article URL")
    title: str = Field(..., description="Article title")
    content: str = Field(..., description="Raw HTML content")
    author: Optional[str] = None
    source: str = Field(..., description="Source name/domain")
    published_at: datetime = Field(..., description="Publication timestamp")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CleanedArticle(BaseModel):
    """Article after HTML cleaning and deduplication"""
    id: str
    url: str
    title: str
    text: str = Field(..., description="Clean text content")
    author: Optional[str] = None
    source: str
    published_at: datetime
    scraped_at: datetime
    content_hash: str = Field(..., description="Content hash for deduplication")
    is_duplicate: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizedArticle(BaseModel):
    """Article after language detection and normalization"""
    id: str
    url: str
    title: str
    text: str
    author: Optional[str] = None
    source: str
    published_at: datetime
    scraped_at: datetime
    content_hash: str
    language: str = Field(..., description="Detected language code")
    translated_title: Optional[str] = None
    translated_text: Optional[str] = None
    word_count: int = Field(..., description="Number of words in text")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EnrichedArticle(BaseModel):
    """Article after LLM enrichment"""
    id: str
    url: str
    title: str
    text: str
    author: Optional[str] = None
    source: str
    published_at: datetime
    scraped_at: datetime
    content_hash: str
    language: str
    translated_title: Optional[str] = None
    translated_text: Optional[str] = None
    word_count: int
    
    # LLM-generated fields
    summary: str = Field(..., description="1-2 sentence summary")
    topics: List[str] = Field(default_factory=list, description="Extracted topics")
    entities: List[str] = Field(default_factory=list, description="Named entities")
    sentiment: SentimentType = Field(..., description="Sentiment analysis")
    sentiment_score: float = Field(..., description="Sentiment confidence score")
    embeddings: List[float] = Field(default_factory=list, description="Dense vector embeddings")
    
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    """Search request parameters"""
    query: str = Field(..., description="Search query")
    topics: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    sentiment: Optional[SentimentType] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class SearchResponse(BaseModel):
    """Search response"""
    articles: List[EnrichedArticle]
    total: int
    page: int
    size: int
    took: int = Field(..., description="Search time in milliseconds")


class HealthStatus(BaseModel):
    """Health check response"""
    service: str
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)


class KafkaMessage(BaseModel):
    """Base Kafka message wrapper"""
    message_id: str = Field(default_factory=lambda: str(datetime.utcnow().timestamp()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service: str
    payload: Dict[str, Any]