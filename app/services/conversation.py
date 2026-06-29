from __future__ import annotations

from app.models import Message


async def get_history(session_id: str, limit: int = 20) -> list[Message]:
    """Load recent messages for *session_id* from Postgres."""
    raise NotImplementedError


async def save_message(session_id: str, message: Message) -> None:
    """Persist a single message to Postgres."""
    raise NotImplementedError


async def clear_session(session_id: str) -> None:
    """Delete all messages for *session_id*."""
    raise NotImplementedError
