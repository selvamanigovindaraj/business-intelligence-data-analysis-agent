from __future__ import annotations

"""Download and load the Northwind sample database into PostgreSQL."""

import asyncio
import os
from pathlib import Path

import asyncpg
import httpx

NORTHWIND_URL = "https://raw.githubusercontent.com/pthom/northwind_psql/master/northwind.sql"
_CACHE = Path("db/init/northwind.sql")


async def _fetch_sql() -> str:
    if _CACHE.exists():
        return _CACHE.read_text()
    print(f"Downloading Northwind SQL from {NORTHWIND_URL} …")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(NORTHWIND_URL)
        response.raise_for_status()
    _CACHE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE.write_text(response.text)
    print(f"Cached → {_CACHE}")
    return response.text


async def load(db_url: str) -> None:
    sql = await _fetch_sql()
    # asyncpg requires postgresql://, not postgresql+asyncpg://
    conn_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn: asyncpg.Connection = await asyncpg.connect(conn_url)
    try:
        await conn.execute(sql)
        print("Northwind data loaded successfully.")
    finally:
        await conn.close()


if __name__ == "__main__":
    url = os.getenv("DATABASE_URL", "postgresql://agent:agent_secret@localhost:5432/northwind")
    asyncio.run(load(url))
