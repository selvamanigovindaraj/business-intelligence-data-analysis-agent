from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    role: Role
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationRequest(BaseModel):
    session_id: str
    message: str
    stream: bool = False


class ConversationResponse(BaseModel):
    session_id: str
    message: Message
    sources: list[SourceDocument] = Field(default_factory=list)
    cost_usd: float | None = None


class SourceDocument(BaseModel):
    id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None


class FeedbackRequest(BaseModel):
    session_id: str
    message_id: UUID
    score: int = Field(..., ge=0, le=1)
    comment: str | None = None


class RouteDecision(StrEnum):
    RAG = "rag"
    WEB_SEARCH = "web_search"
    FINANCIAL = "financial"
    DIRECT = "direct"
