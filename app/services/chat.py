import asyncio

import aiosqlite

from app.db.sqlite import get_entries_by_ids
from app.services.embeddings import embed_text
from app.services.reflection import call_ollama
from app.services.vector_store import semantic_search


async def answer_question(db: aiosqlite.Connection, question: str) -> dict:
    """RAG Q&A: embed question → Chroma search → fetch entries → Ollama."""
    embedding = await embed_text(question)

    loop = asyncio.get_running_loop()
    try:
        ids = await loop.run_in_executor(
            None,
            lambda: semantic_search(embedding, n_results=5),
        )
    except Exception:
        ids = []

    entries = await get_entries_by_ids(db, ids)

    if not entries:
        return {
            "answer": "I don't have enough journal entries to answer that question yet. Keep writing!",
            "sources_used": 0,
        }

    context_lines = []
    for e in entries:
        context_lines.append(
            f"- {e['entry_date']} | mood: {e['composite_score']:+.2f} ({e['label']})\n"
            f"  \"{e['content']}\""
        )
    context = "\n".join(context_lines)

    prompt = f"""You are a helpful assistant answering questions about a user's personal journal.

Here are the most relevant journal entries:

{context}

User's question: {question}

Answer thoughtfully based on the journal entries above. Be specific and reference entries when relevant. Keep your answer concise (2–3 paragraphs max). Use second person ("you felt", "you wrote")."""

    answer = await call_ollama(prompt)
    return {"answer": answer, "sources_used": len(entries)}
