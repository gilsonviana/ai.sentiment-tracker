import asyncio
import json
from datetime import datetime

import aiosqlite

from app.core.preprocessing import preprocess
from app.db.sqlite import update_status
from app.config import settings
from app.services import vector_store
from app.services.embeddings import embed_text
from app.services.sentiment import score_sentiment


async def run_analysis_pipeline(entry_id: str, raw_text: str) -> None:
    """
    Full async ML pipeline. Called by the queue worker — opens its own DB
    connection so the worker isn't holding a write lock across the ML work.
    """
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        try:
            text = preprocess(raw_text)

            (vader, roberta, composite, label), embedding = await asyncio.gather(
                score_sentiment(text),
                embed_text(text),
            )

            await db.execute(
                """INSERT OR REPLACE INTO analysis
                   (entry_id, vader_score, roberta_score, composite_score, label, entities, analysed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry_id, vader, roberta, composite, label,
                    json.dumps([]), datetime.utcnow().isoformat(),
                ),
            )
            await db.commit()

            vector_store.upsert(
                entry_id=entry_id,
                embedding=embedding,
                mood_score=composite,
                created_at=datetime.utcnow().isoformat(),
            )

            await update_status(db, entry_id, "processed")

        except Exception as exc:
            await update_status(db, entry_id, "failed")
            raise exc
