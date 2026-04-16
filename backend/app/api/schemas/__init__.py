"""API Schemas (DTO)"""
from app.api.schemas.entry import (
    EntryCreate,
    EntryUpdate,
    EntryResponse,
    EntryListResponse,
    SearchResult,
    RelatedEntry,
    RelatedEntriesResponse,
    EntrySummaryResponse,
    EntryLinkCreate,
    EntryLinkResponse,
    EntryLinkItem,
    EntryLinkListResponse,
    LinkTargetEntry,
)
from app.api.schemas.common import (
    SuccessResponse,
    ProjectProgressResponse,
)

__all__ = [
    "EntryCreate",
    "EntryUpdate",
    "EntryResponse",
    "EntryListResponse",
    "SearchResult",
    "SuccessResponse",
    "ProjectProgressResponse",
    "RelatedEntry",
    "RelatedEntriesResponse",
    "EntrySummaryResponse",
    "EntryLinkCreate",
    "EntryLinkResponse",
    "EntryLinkItem",
    "EntryLinkListResponse",
    "LinkTargetEntry",
]
