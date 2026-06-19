import aiosqlite
import json
import uuid
from datetime import datetime, date as Date
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

async def save_entry(db: aiosqlite.Connection, content: str, entry_date: Date | None = None) -> str:
    """Persist raw entry, return generated ID."""
    entry_id = str(uuid.uuid4())
    resolved_date = (entry_date or Date.today()).isoformat()
    await db.execute(
        "INSERT INTO entries (id, content, created_at, entry_date, status) VALUES (?, ?, ?, ?, ?)",
        (entry_id, content, datetime.utcnow().isoformat(), resolved_date, "pending"),
    )
    await db.commit()
    return entry_id

async def update_status(db: aiosqlite.Connection, entry_id: str, status: str) -> None:
    await db.execute(
        "UPDATE entries SET status = ? WHERE id = ?",
        (status, entry_id),
    )
    await db.commit()

async def update_entry(
    db: aiosqlite.Connection,
    entry_id: str,
    content: str | None,
    entry_date: Date | None,
) -> JournalEntryDB | None:
    sets: list[str] = []
    params: list = []

    if content is not None:
        sets += ["content = ?", "status = 'pending'"]
        params.append(content)

    if entry_date is not None:
        sets.append("entry_date = ?")
        params.append(entry_date.isoformat())

    params.append(entry_id)
    cursor = await db.execute(
        f"UPDATE entries SET {', '.join(sets)} WHERE id = ?",
        params,
    )
    await db.commit()

    if cursor.rowcount == 0:
        return None

    return await get_entry(db, entry_id)


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


async def save_reflection(
    db: aiosqlite.Connection,
    narrative: str,
    entry_count: int,
    avg_mood: float,
    window_start: str,
    window_end: str,
) -> str:
    ref_id = str(uuid.uuid4())
    await db.execute(
        """INSERT INTO reflections
           (id, narrative, entry_count, avg_mood, window_start, window_end, generated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (ref_id, narrative, entry_count, avg_mood, window_start, window_end,
         datetime.utcnow().isoformat()),
    )
    await db.commit()
    return ref_id


async def list_reflections(db: aiosqlite.Connection) -> list[dict]:
    async with db.execute(
        "SELECT * FROM reflections ORDER BY generated_at DESC"
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_entries_by_ids(db: aiosqlite.Connection, ids: list[str]) -> list[dict]:
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    async with db.execute(
        f"""SELECT e.id, e.content, e.entry_date, a.composite_score, a.label, a.entities
            FROM entries e
            JOIN analysis a ON a.entry_id = e.id
            WHERE e.id IN ({placeholders})""",
        ids,
    ) as cursor:
        rows = await cursor.fetchall()
    result = []
    for row in rows:
        data = dict(row)
        data["entities"] = json.loads(data["entities"] or "[]")
        result.append(data)
    return result


async def get_mood_data(db: aiosqlite.Connection, month: str) -> list[dict]:
    async with db.execute(
        """SELECT e.entry_date, a.composite_score, a.label
           FROM entries e
           JOIN analysis a ON a.entry_id = e.id
           WHERE e.entry_date LIKE ? AND e.status = 'processed'
           ORDER BY e.entry_date ASC""",
        (f"{month}-%",),
    ) as cursor:
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]
