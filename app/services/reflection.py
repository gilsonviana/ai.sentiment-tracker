import asyncio
from datetime import datetime, timedelta
from functools import partial
from statistics import mean

import aiosqlite
import requests
from fastapi import HTTPException

from app.config import settings
from app.db.sqlite import save_reflection
from app.services.embeddings import embed_text
from app.services.vector_store import get_similar_past_entries


async def fetch_window_context(
    db: aiosqlite.Connection,
    window_start: str,
    window_end: str,
) -> list[dict]:
    """Returns entries + analysis joined for the given date window."""
    async with db.execute(
        """
        SELECT e.content, e.entry_date, a.composite_score, a.label
        FROM entries e
        JOIN analysis a ON a.entry_id = e.id
        WHERE e.entry_date >= ? AND e.entry_date <= ? AND e.status = 'processed'
        ORDER BY e.entry_date ASC
""",
        (window_start, window_end),
    ) as cursor:
        rows = await cursor.fetchall()

    return [dict(row) for row in rows]


def build_prompt(
    entries: list[dict],
    similar_past: list[dict],
    window_start: str = "",
    window_end: str = "",
) -> str:
    lines = []
    for e in entries:
        score = e["composite_score"]
        lines.append(
            f"- {e['entry_date']} | mood: {score:+.2f} ({e['label']})\n"
            f"  \"{e['content']}\""
        )
    context = "\n".join(lines)

    history_block = ""
    if similar_past:
        hist_lines = [
            f"  - {p['created_at']} | mood: {p['mood_score']:+.2f}"
            for p in similar_past
        ]
        history_block = (
            "\n\nFor additional context, here are past entries that were "
            "emotionally similar to this period:\n" + "\n".join(hist_lines) +
            "\nReference these only if they add meaningful insight — "
            "do not force a comparison."
        )

    window_desc = (
        f"from {window_start} to {window_end}"
        if window_start and window_end
        else "from the past 7 days"
    )

    return f"""You are a warm, empathetic journaling coach writing a reflection for your user.

Here are their journal entries {window_desc}:

{context}{history_block}

Write a personal reflection in 3–4 paragraphs. Use second person ("you felt", "your week").
Synthesise the entries — do not list them verbatim. Identify the emotional arc across the period.
Identify recurring emotional patterns. End with one forward-looking observation or gentle encouragement.
Keep the tone warm, honest, and grounded."""


def _call_ollama_sync(prompt: str, model: str) -> str:
    """Synchronous Ollama call — must be run via run_in_executor."""
    try:
        response = requests.post(
            f"{settings.ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.75,
                    "num_predict": 300,
                },
            },
            timeout=180,
        )
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.ConnectionError:
        raise RuntimeError("ollama_offline")
    except requests.exceptions.Timeout:
        raise RuntimeError("ollama_offline")
    except Exception as e:
        raise RuntimeError(f"ollama_error: {e}")


async def call_ollama(prompt: str, model: str = settings.ollama_model) -> str:
    """Calls Ollama in a thread pool to avoid blocking the event loop."""
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, partial(_call_ollama_sync, prompt, model))
    except RuntimeError as e:
        if "ollama_offline" in str(e):
            raise HTTPException(
                status_code=503,
                detail="Ollama is not running. Start it with: ollama serve",
            )
        raise HTTPException(status_code=500, detail=str(e))


async def generate_weekly_reflection(
    db: aiosqlite.Connection,
    start: str | None = None,
    end: str | None = None,
    model: str = settings.ollama_model,
) -> dict:
    """Orchestrates context retrieval, prompt assembly, Ollama call, and persistence."""
    today = datetime.utcnow().date()
    window_end = end or today.isoformat()
    window_start = start or (today - timedelta(days=7)).isoformat()

    entries = await fetch_window_context(db, window_start, window_end)

    if len(entries) < 3:
        found = len(entries)
        missing = 3 - found
        entry_word = "entry" if found == 1 else "entries"
        more_word = "entry" if missing == 1 else "entries"
        narrative = (
            f"Only {found} processed {entry_word} found between {window_start} and "
            f"{window_end}. At least 3 are needed to generate a meaningful reflection — "
            f"add {missing} more {more_word} in this window and try again."
        )
        return {
            "narrative": narrative,
            "entry_count": len(entries),
            "avg_mood": 0.0,
            "window_start": window_start,
            "window_end": window_end,
        }

    anchor = max(entries, key=lambda e: abs(e["composite_score"]))

    anchor_embedding = await embed_text(anchor["content"])
    loop = asyncio.get_running_loop()
    similar_past = await loop.run_in_executor(
        None,
        lambda: get_similar_past_entries(anchor_embedding, before_iso=window_start),
    )

    prompt = build_prompt(entries, similar_past, window_start, window_end)
    narrative = await call_ollama(prompt, model=model)
    avg_mood = round(mean(e["composite_score"] for e in entries), 2)

    await save_reflection(db, narrative, len(entries), avg_mood, window_start, window_end)

    return {
        "narrative": narrative,
        "entry_count": len(entries),
        "avg_mood": avg_mood,
        "window_start": window_start,
        "window_end": window_end,
    }
