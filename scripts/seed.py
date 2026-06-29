from __future__ import annotations

"""Seed script — load sample documents into Pinecone."""

import asyncio
from pathlib import Path

from app.components.retriever import PineconeRetriever


def load_raw_docs(data_dir: Path = Path("data/raw")) -> list[str]:
    """Read all .txt files from *data_dir*."""
    raise NotImplementedError


async def seed() -> None:
    retriever = PineconeRetriever()
    # TODO: load, chunk, and upsert documents
    raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(seed())
