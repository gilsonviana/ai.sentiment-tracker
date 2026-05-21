import aiosqlite
import json
import uuid
from datetime import datetime
from app.config import settings
from app.models.entry import JournalEntryDB
from app.models.analysis import AnalysisResponse
from pathlib import Path

DB_PATH = settings.db_path

async def get_db() -> aiosqlite.Connection:
    """Dependency — yields an open DB connection."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def save_entry(db: aiosqlite.Connection, content: str) -> str:
    """Persist raw entry, return generated ID."""
    entry_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO entries (id, content, created_at, status) VALUES (?, ?, ?, ?)",
        (entry_id, content, datetime.utcnow().isoformat(), "pending"),
    )
    await db.commit()
    return entry_id

async def update_status(db: aiosqlite.Connection, entry_id: str, status: str) -> None:
    await db.execute(
        "UPDATE entries SET status = ? WHERE id = ?",
        (status, entry_id),
    )
    await db.commit()

async def get_entry(db: aiosqlite.Connection, entry_id: str) -> JournalEntryDB | None:
    async with db.execute(
        "SELECT * FROM entries WHERE id = ?", (entry_id,)
    ) as cursor:
        row = await cursor.fetchone()
        if row is None:
            return None
        return JournalEntryDB(**dict(row))

async def get_analysis(db: aiosqlite.Connection, entry_id: str) -> AnalysisResponse | None:
    async with db.execute(
        "SELECT * FROM analysis WHERE entry_id = ?", (entry_id,)
    ) as cursor:
        row = await cursor.fetchone()
        if row is None:
            return None
        data = dict(row)
        data["entities"] = json.loads(data["entities"] or "[]")
        return AnalysisResponse(**data)
