"""Pydantic models for the API."""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# API Key models
class APIKey(BaseModel):
    """API Key model."""
    id: str
    key: str
    tenant_id: str
    name: str
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True


class APIKeyCreate(BaseModel):
    """Create API key request."""
    name: str = Field(..., min_length=1, max_length=100)


class APIKeyResponse(BaseModel):
    """API key response (without exposing the full key after creation)."""
    id: str
    name: str
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True


# User models
class UserCreate(BaseModel):
    """Create user request."""
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    password: str = Field(..., min_length=8)
    name: Optional[str] = None


class UserResponse(BaseModel):
    """User response."""
    id: str
    email: str
    name: Optional[str] = None
    created_at: datetime


# Index models
class IndexSettings(BaseModel):
    """OpenSearch index settings."""
    number_of_shards: int = 1
    number_of_replicas: int = 0
    refresh_interval: str = "1s"


class IndexMappingProperty(BaseModel):
    """Field mapping property."""
    type: str = "text"
    analyzer: Optional[str] = None
    fields: Optional[dict[str, Any]] = None


class IndexMapping(BaseModel):
    """Index mapping definition."""
    properties: dict[str, IndexMappingProperty] = {}


class IndexCreate(BaseModel):
    """Create index request."""
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_-]*$")
    settings: Optional[IndexSettings] = None
    mapping: Optional[IndexMapping] = None


class IndexResponse(BaseModel):
    """Index response."""
    name: str
    settings: Optional[dict[str, Any]] = None
    mapping: Optional[dict[str, Any]] = None
    document_count: int = 0
    created_at: datetime
    status: str = "active"


class IndexListResponse(BaseModel):
    """List indexes response."""
    indexes: list[IndexResponse]
    total: int


# Document models (removed unused Document class)


class DocumentAdd(BaseModel):
    """Add document request."""
    id: Optional[str] = Field(None, alias="id")
    document: dict[str, Any]

    class Config:
        populate_by_name = True


class DocumentAddResponse(BaseModel):
    """Add document response."""
    _id: str
    status: str = "created"
    result: str = "created"


class BulkDocumentAdd(BaseModel):
    """Bulk add documents request."""
    documents: list[dict[str, Any]]


class BulkDocumentAddResponse(BaseModel):
    """Bulk add documents response."""
    items: list[dict[str, Any]]
    errors: bool = False
    took: int = 0


# Search models
class SearchRequest(BaseModel):
    """Search request body."""
    query: dict[str, Any]
    from_: Optional[int] = Field(None, alias="from", ge=0)
    size: int = Field(10, ge=0, le=10000)
    sort: Optional[list[dict[str, Any]]] = None
    aggs: Optional[dict[str, Any]] = None
    highlight: Optional[dict[str, Any]] = None


class SearchHit(BaseModel):
    """A single search hit."""
    _id: str
    _score: Optional[float] = None
    _source: dict[str, Any]


class SearchResponse(BaseModel):
    """Search response."""
    took: int
    timed_out: bool = False
    hits: dict[str, Any]


# Tenant models
class Tenant(BaseModel):
    """Tenant model."""
    id: str
    name: str
    email: str
    created_at: datetime
    is_active: bool = True


# Metrics models
class UsageMetrics(BaseModel):
    """Usage metrics for a tenant."""
    tenant_id: str
    document_count: int = 0
    search_queries: int = 0
    indexes_count: int = 0
    storage_bytes: int = 0
    period_start: datetime
    period_end: datetime


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    opensearch: str
    version: Optional[str] = None