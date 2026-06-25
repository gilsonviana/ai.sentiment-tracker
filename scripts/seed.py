#!/usr/bin/env python3
"""Seed database with sample journal entries from JSON file."""

import asyncio
import json
import sys
import uuid
from datetime import datetime, date as Date, timezone
from pathlib import Path

import aiosqlite


async def seed_database(json_file: Path, db_path: Path) -> bool:
    """Load sample entries from JSON and insert into database."""

    # Validate JSON file exists
    if not json_file.exists():
        print(f"❌  Error: {json_file} not found")
        return False

    # Load entries from JSON
    print(f"📂 Loading entries from {json_file.name}...")
    try:
        with open(json_file) as f:
            data = json.load(f)
        entries = data.get("entries", [])
        if not entries:
            print("❌  No entries found in JSON file")
            return False
        print(f"✅  Loaded {len(entries)} entries")
    except json.JSONDecodeError as e:
        print(f"❌  Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌  Error reading file: {e}")
        return False

    # Ensure data directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Connect to database
    print(f"\n🔗 Connecting to database at {db_path}...")
    try:
        async with aiosqlite.connect(str(db_path)) as db:
            # Enable foreign key constraints
            await db.execute("PRAGMA foreign_keys = ON")

            # Run migrations to create tables
            print("📋 Running migrations...")
            await _run_migrations(db)

            # Insert entries
            print(f"\n🌱 Seeding database with {len(entries)} entries...")
            inserted_count = 0
            skipped_count = 0

            try:
                for idx, entry_data in enumerate(entries, 1):
                    try:
                        # Validate entry
                        content = entry_data.get("content", "").strip()
                        entry_date_str = entry_data.get("entry_date")

                        if not content:
                            print(f"   ⚠️  Entry {idx}: skipped (empty content)")
                            skipped_count += 1
                            continue

                        # Parse date
                        if entry_date_str:
                            try:
                                entry_date = Date.fromisoformat(entry_date_str)
                            except ValueError:
                                print(f"   ⚠️  Entry {idx}: invalid date {entry_date_str}, using today")
                                entry_date = Date.today()
                        else:
                            entry_date = Date.today()

                        # Generate ID and insert
                        entry_id = str(uuid.uuid4())
                        created_at = datetime.now(timezone.utc).isoformat()
                        status = "pending"

                        await db.execute(
                            """INSERT INTO entries
                               (id, content, created_at, entry_date, status)
                               VALUES (?, ?, ?, ?, ?)""",
                            (entry_id, content, created_at, entry_date.isoformat(), status),
                        )

                        # Enqueue for processing
                        queue_id = str(uuid.uuid4())
                        now = datetime.now(timezone.utc).isoformat()
                        await db.execute(
                            """INSERT INTO queue
                               (id, entry_id, status, enqueued_at, next_attempt_at)
                               VALUES (?, ?, ?, ?, ?)""",
                            (queue_id, entry_id, "pending", now, now),
                        )

                        inserted_count += 1
                        progress = f"[{idx}/{len(entries)}]"
                        print(f"   {progress} Entry ↳ enqueued")

                    except Exception as e:
                        print(f"   ❌  Entry {idx}: {e}")
                        skipped_count += 1
                        continue

                await db.commit()

            except Exception as e:
                await db.rollback()
                print(f"❌  Database error: {e}")
                return False

    except Exception as e:
        print(f"❌  Database connection error: {e}")
        return False

    # Print summary
    print("\n" + "=" * 50)
    print(f"✅  Seeding complete!")
    print(f"   📊 Inserted: {inserted_count} entries")
    if skipped_count > 0:
        print(f"   ⏭️  Skipped: {skipped_count} entries")
    print("   ⚙️  Status: enqueued for processing")
    print("=" * 50)
    return True


async def _run_migrations(db: aiosqlite.Connection) -> None:
    """Create database tables if they don't exist."""
    await db.execute(
        """CREATE TABLE IF NOT EXISTS entries (
            id          TEXT PRIMARY KEY,
            content     TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            entry_date  TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'pending'
        );"""
    )

    await db.execute(
        """CREATE TABLE IF NOT EXISTS analysis (
            entry_id        TEXT PRIMARY KEY REFERENCES entries(id),
            vader_score     REAL,
            roberta_score   REAL,
            composite_score REAL,
            label           TEXT,
            entities        TEXT,
            analysed_at     TEXT
        );"""
    )

    await db.execute(
        """CREATE TABLE IF NOT EXISTS reflections (
            id           TEXT PRIMARY KEY,
            narrative    TEXT NOT NULL,
            entry_count  INTEGER NOT NULL,
            avg_mood     REAL NOT NULL,
            window_start TEXT NOT NULL,
            window_end   TEXT NOT NULL,
            generated_at TEXT NOT NULL
        );"""
    )

    await db.execute(
        """CREATE TABLE IF NOT EXISTS queue (
            id              TEXT PRIMARY KEY,
            entry_id        TEXT NOT NULL REFERENCES entries(id),
            attempts        INTEGER NOT NULL DEFAULT 0,
            max_attempts    INTEGER NOT NULL DEFAULT 3,
            status          TEXT NOT NULL DEFAULT 'pending',
            error           TEXT,
            enqueued_at     TEXT NOT NULL,
            next_attempt_at TEXT NOT NULL
        );"""
    )

    await db.commit()


async def main():
    """Entry point."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    json_file = project_root / "data" / "sample_entries.json"
    db_path = project_root / "data" / "journal.db"

    # Parse arguments
    custom_json = next((arg for arg in sys.argv[1:] if arg.endswith(".json")), None)

    if custom_json:
        json_file = Path(custom_json)

    print("🌱 Sentiment Tracker - Database Seeder")
    print("=" * 50)

    if not await seed_database(json_file, db_path):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
