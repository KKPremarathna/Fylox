from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict


class PolicyStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"


# Admin Schema for Ingestion
class PolicyDocumentCreate(BaseModel):
    title: str
    version: str
    content: str
    effective_from: Optional[datetime] = None


class PolicyDocumentPatch(BaseModel):
    status: Optional[PolicyStatus] = None


# Public Schema (Narrowed, safe)
class PolicyDocumentSlimResponse(BaseModel):
    id: int
    title: str
    version: str
    effective_from: Optional[datetime] = None
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PolicyDocumentDetailResponse(PolicyDocumentSlimResponse):
    content: str


# Search Schemas
class PolicySearchResultItem(BaseModel):
    document_title: str
    version: str
    effective_date: Optional[datetime] = None
    section_heading: Optional[str] = None
    snippet_text: str
    relevance_score: float

    model_config = ConfigDict(from_attributes=True)


class PolicySearchResponse(BaseModel):
    query: str
    results: list[PolicySearchResultItem]
