import asyncio
import logging

import aiosqlite

from app.config import settings
from app.core.pipeline import run_analysis_pipeline
from app.db.queue import claim_next_job, complete_job, fail_job, reset_stale_jobs
from app.db.sqlite import get_entry

logger = logging.getLogger(__name__)

POLL_INTERVAL = 2  # seconds between queue checks when idle


async def worker_loop() -> None:
    logger.info("[worker] started")
    stale_reset_done = False

    while True:
        try:
            async with aiosqlite.connect(settings.db_path) as db:
                db.row_factory = aiosqlite.Row
                if not stale_reset_done:
                    count = await reset_stale_jobs(db)
                    if count:
                        logger.info("[worker] reset %d stale job(s) to pending", count)
                    stale_reset_done = True
                job = await claim_next_job(db)

            if job is None:
                await asyncio.sleep(POLL_INTERVAL)
                continue

            logger.info(
                "[worker] processing job=%s entry=%s attempt=%d",
                job["id"], job["entry_id"], job["attempts"],
            )

            async with aiosqlite.connect(settings.db_path) as db:
                db.row_factory = aiosqlite.Row
                entry = await get_entry(db, job["entry_id"])

            if entry is None:
                logger.warning("[worker] entry %s not found — discarding job", job["entry_id"])
                async with aiosqlite.connect(settings.db_path) as db:
                    db.row_factory = aiosqlite.Row
                    await complete_job(db, job["id"])
                continue

            try:
                await run_analysis_pipeline(job["entry_id"], entry.content)
                async with aiosqlite.connect(settings.db_path) as db:
                    db.row_factory = aiosqlite.Row
                    await complete_job(db, job["id"])
                logger.info("[worker] completed job=%s", job["id"])
            except Exception as exc:
                backoff = 2 ** (job["attempts"] - 1) * 5
                logger.warning(
                    "[worker] job=%s failed (attempt %d/%d): %s — retry in %ds",
                    job["id"], job["attempts"], job["max_attempts"], exc, backoff,
                )
                async with aiosqlite.connect(settings.db_path) as db:
                    db.row_factory = aiosqlite.Row
                    await fail_job(db, job["id"], str(exc), backoff)

        except asyncio.CancelledError:
            logger.info("[worker] shutting down")
            raise
        except Exception as exc:
            logger.error("[worker] unexpected error: %s", exc)
            await asyncio.sleep(POLL_INTERVAL)
