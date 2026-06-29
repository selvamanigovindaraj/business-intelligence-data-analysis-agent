from __future__ import annotations

from uuid import UUID

from app.models import FeedbackRequest


async def record_feedback(feedback: FeedbackRequest) -> None:
    """Persist user feedback and send annotation to Arize Phoenix."""
    raise NotImplementedError


async def get_feedback_stats(session_id: str) -> dict[str, float]:
    """Return thumbs-up rate and average score for a session."""
    raise NotImplementedError
