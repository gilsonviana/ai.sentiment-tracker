import asyncio
import json
from datetime import datetime, timedelta
from functools import partial
from statistics import mean

import requests

import aiosqlite
from fastapi import HTTPException

from app.config import settings
from app.services.embeddings import embed_text
from app.services.vector_store import get_similar_past_entries


async def fetch_week_context(db: aiosqlite.Connection) -> list[dict]:
    """Returns entries + analysis joined for the past 7 days."""
    since = (datetime.utcnow() - timedelta(days=7)).isoformat()
    async with db.execute(
        """
        SELECT e.content, e.entry_date, a.composite_score, a.label, a.entities
        FROM entries e
        JOIN analysis a ON a.entry_id = e.id
        WHERE e.created_at >= ? AND e.status = 'processed'
        ORDER BY e.entry_date ASC, e.created_at ASC
        """,
        (since,),
    ) as cursor:
        rows = await cursor.fetchall()

    result = []
    for row in rows:
        data = dict(row)
        data["entities"] = json.loads(data["entities"] or "[]")
        result.append(data)
    return result


def build_prompt(entries: list[dict], similar_past: list[dict]) -> str:
    """Assembles the RAG prompt from the week's entries and optional historical context."""
    lines = []
    for e in entries:
        score = e["composite_score"]
        entities_str = ", ".join(e["entities"]) if e["entities"] else "none"
        lines.append(
            f"- {e['entry_date']} | mood: {score:+.2f} ({e['label']}) "
            f"| entities: {entities_str}\n  \"{e['content']}\""
        )
    context = "\n".join(lines)

    history_block = ""
    if similar_past:
        hist_lines = [
            f"  - {p['created_at']} | mood: {p['mood_score']:+.2f} "
            f"| entities: {', '.join(p['entities']) or 'none'}"
            for p in similar_past
        ]
        history_block = (
            "\n\nFor additional context, here are past entries that were "
            "emotionally similar to this week:\n" + "\n".join(hist_lines) +
            "\nReference these only if they add meaningful insight — "
            "do not force a comparison."
        )

    return f"""You are a warm, empathetic journaling coach writing a weekly reflection for your user.

Here are their journal entries from the past 7 days:

{context}{history_block}

Write a personal weekly reflection in 3–4 paragraphs. Use second person ("you felt", "your week").
Synthesise the entries — do not list them verbatim. Identify the emotional arc across the week.
Note any recurring themes or entities. End with one forward-looking observation or gentle encouragement.
Keep the tone warm, honest, and grounded."""


def _call_ollama_sync(prompt: str) -> str:
    """Synchronous Ollama call — must be run via run_in_executor."""
    try:
        response = requests.post(
            f"{settings.ollama_url}/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.75,
                    "num_predict": 400,
                },
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.ConnectionError:
        raise RuntimeError("ollama_offline")
    except requests.exceptions.Timeout:
        raise RuntimeError("ollama_offline")
    except Exception as e:
        raise RuntimeError(f"ollama_error: {e}")


async def call_ollama(prompt: str) -> str:
    """Calls Ollama in a thread pool to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(None, partial(_call_ollama_sync, prompt))
    except RuntimeError as e:
        if "ollama_offline" in str(e):
            raise HTTPException(
                status_code=503,
                detail="Ollama is not running. Start it with: ollama serve",
            )
        raise HTTPException(status_code=500, detail=str(e))


async def generate_weekly_reflection(db: aiosqlite.Connection) -> dict:
    """Orchestrates context retrieval, prompt assembly, and Ollama call."""
    entries = await fetch_week_context(db)

    if len(entries) < 3:
        return {
            "narrative": "Not enough entries this week to generate a reflection. Keep writing!",
            "entry_count": len(entries),
            "avg_mood": 0.0,
        }

    # Use the most emotionally significant entry as the Chroma query anchor
    anchor = max(entries, key=lambda e: abs(e["composite_score"]))
    since_iso = (datetime.utcnow() - timedelta(days=7)).isoformat()

    anchor_embedding = await embed_text(anchor["content"])
    loop = asyncio.get_event_loop()
    similar_past = await loop.run_in_executor(
        None,
        lambda: get_similar_past_entries(anchor_embedding, before_iso=since_iso),
    )

    prompt = build_prompt(entries, similar_past)
    narrative = await call_ollama(prompt)
    avg_mood = round(mean(e["composite_score"] for e in entries), 2)

    return {
        "narrative": narrative,
        "entry_count": len(entries),
        "avg_mood": avg_mood,
    }
