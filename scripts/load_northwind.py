"""Download and load the Northwind sample database into PostgreSQL."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

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


async def _ensure_database(conn_url: str) -> None:
    """Create the target database if it does not exist."""
    parsed = urlparse(conn_url)
    db_name = parsed.path.lstrip("/")
    maintenance_url = urlunparse(parsed._replace(path="/postgres"))

    conn: asyncpg.Connection = await asyncpg.connect(maintenance_url)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            # CREATE DATABASE cannot run inside a transaction block
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Created database '{db_name}'.")
        else:
            print(f"Database '{db_name}' already exists.")
    finally:
        await conn.close()


async def load(db_url: str) -> None:
    # asyncpg requires postgresql://, not postgresql+asyncpg://
    conn_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    await _ensure_database(conn_url)
    sql = await _fetch_sql()
    conn: asyncpg.Connection = await asyncpg.connect(conn_url)
    try:
        await conn.execute(sql)
        print("Northwind data loaded successfully.")
    finally:
        await conn.close()


if __name__ == "__main__":
    url = os.getenv("DATABASE_URL", "postgresql://agent:agent_secret@localhost:5432/northwind")
    asyncio.run(load(url))
