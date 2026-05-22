import uuid
from datetime import datetime, timedelta

import aiosqlite


async def enqueue(db: aiosqlite.Connection, entry_id: str) -> str:
    job_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    await db.execute(
        """INSERT INTO queue (id, entry_id, enqueued_at, next_attempt_at)
           VALUES (?, ?, ?, ?)""",
        (job_id, entry_id, now, now),
    )
    await db.commit()
    return job_id


async def claim_next_job(db: aiosqlite.Connection) -> dict | None:
    """
    Atomically claim the next pending job whose next_attempt_at has passed.
    Returns the job dict with attempts already incremented, or None if the
    queue is empty.
    """
    now = datetime.utcnow().isoformat()
    async with db.execute(
        """SELECT id, entry_id, attempts, max_attempts
           FROM queue
           WHERE status = 'pending' AND next_attempt_at <= ?
           ORDER BY enqueued_at ASC
           LIMIT 1""",
        (now,),
    ) as cursor:
        row = await cursor.fetchone()

    if row is None:
        return None

    job = dict(row)
    await db.execute(
        "UPDATE queue SET status = 'processing', attempts = attempts + 1 WHERE id = ?",
        (job["id"],),
    )
    await db.commit()
    job["attempts"] += 1
    return job


async def complete_job(db: aiosqlite.Connection, job_id: str) -> None:
    await db.execute("DELETE FROM queue WHERE id = ?", (job_id,))
    await db.commit()


async def fail_job(
    db: aiosqlite.Connection,
    job_id: str,
    error: str,
    backoff_seconds: int,
) -> None:
    """
    On failure: if attempts < max_attempts, reschedule with backoff.
    Otherwise mark as permanently failed and store the error.
    """
    async with db.execute(
        "SELECT attempts, max_attempts FROM queue WHERE id = ?", (job_id,)
    ) as cursor:
        row = await cursor.fetchone()

    if row is None:
        return

    attempts, max_attempts = row[0], row[1]
    if attempts < max_attempts:
        next_attempt = (
            datetime.utcnow() + timedelta(seconds=backoff_seconds)
        ).isoformat()
        await db.execute(
            """UPDATE queue SET status = 'pending', error = ?, next_attempt_at = ?
               WHERE id = ?""",
            (error, next_attempt, job_id),
        )
    else:
        await db.execute(
            "UPDATE queue SET status = 'failed', error = ? WHERE id = ?",
            (error, job_id),
        )
    await db.commit()


async def reset_stale_jobs(db: aiosqlite.Connection) -> int:
    """
    On startup: any job left in 'processing' means the worker crashed mid-run.
    Reset those back to 'pending' so they are retried.
    """
    cursor = await db.execute(
        "UPDATE queue SET status = 'pending' WHERE status = 'processing'"
    )
    await db.commit()
    return cursor.rowcount
