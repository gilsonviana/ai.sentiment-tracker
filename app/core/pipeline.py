import asyncio
import json
from datetime import datetime
import aiosqlite

from app.core.preprocessing import preprocess
from app.services.sentiment import score_sentiment
from app.services.embeddings import embed_text
from app.services.ner import extract_entities
from app.services import vector_store
from app.db.sqlite import update_status
from app.config import settings


async def run_analysis_pipeline(entry_id: str, raw_text: str, db: aiosqlite.Connection) -> None:
    """
    The full async ML fan-out. Called by BackgroundTasks after a 202 response.
    Failures update the entry status to 'failed' so the client can poll/retry.
    """
    try:
        text = preprocess(raw_text)

        # All four tasks run concurrently
        (vader, roberta, composite, label), embedding, entities = await asyncio.gather(
            score_sentiment(text),
            embed_text(text),
            extract_entities(text),
        )

        # Persist analysis to SQLite
        await db.execute(
            """INSERT OR REPLACE INTO analysis
               (entry_id, vader_score, roberta_score, composite_score, label, entities, analysed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (entry_id, vader, roberta, composite, label,
             json.dumps(entities), datetime.utcnow().isoformat()),
        )
        await db.commit()

        # Upsert into Chroma (sync call, fine here — runs after await chain)
        vector_store.upsert(
            entry_id=entry_id,
            embedding=embedding,
            mood_score=composite,
            entities=entities,
            created_at=datetime.utcnow().isoformat(),
        )

        await update_status(db, entry_id, "processed")

    except Exception as exc:
        await update_status(db, entry_id, "failed")
        # In production: push to a dead-letter queue or alerting system
        print(f"[pipeline error] entry={entry_id} error={exc}")
        raise
