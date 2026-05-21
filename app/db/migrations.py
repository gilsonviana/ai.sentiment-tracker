import aiosqlite
from app.config import settings
from pathlib import Path

CREATE_ENTRIES = """
CREATE TABLE IF NOT EXISTS entries (
    id          TEXT PRIMARY KEY,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending'
);
"""

CREATE_ANALYSIS = """
CREATE TABLE IF NOT EXISTS analysis (
    entry_id        TEXT PRIMARY KEY REFERENCES entries(id),
    vader_score     REAL,
    roberta_score   REAL,
    composite_score REAL,
    label           TEXT,
    entities        TEXT,   -- JSON array stored as string
    analysed_at     TEXT
);
"""

async def run_migrations() -> None:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(CREATE_ENTRIES)
        await db.execute(CREATE_ANALYSIS)
        await db.commit()
    print("Migrations complete.")
