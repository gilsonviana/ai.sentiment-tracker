import chromadb
from app.config import settings
from pathlib import Path

Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)

_client = chromadb.PersistentClient(path=settings.chroma_path)
_collection = _client.get_or_create_collection(
    name="journal_entries",
    metadata={"hnsw:space": "cosine"},
)


def upsert(
    entry_id: str,
    embedding: list[float],
    mood_score: float,
    entities: list[str],
    created_at: str,
) -> None:
    _collection.upsert(
        ids=[entry_id],
        embeddings=[embedding],
        metadatas=[{
            "mood_score": mood_score,
            "entities": ",".join(entities),
            "created_at": created_at,
        }],
    )


def semantic_search(
    query_embedding: list[float],
    n_results: int = 5,
    mood_filter: dict | None = None,
) -> list[dict]:
    """
    Returns top-n similar entries.
    mood_filter example: {"mood_score": {"$lt": -0.2}}
    """
    kwargs = dict(query_embeddings=[query_embedding], n_results=n_results)
    if mood_filter:
        kwargs["where"] = mood_filter
    results = _collection.query(**kwargs)
    return results["ids"][0] if results["ids"] else []


def get_similar_past_entries(
    query_embedding: list[float],
    before_iso: str,
    n_results: int = 3,
) -> list[dict]:
    """
    Finds entries older than `before_iso` that are semantically similar to
    `query_embedding`. Used to surface historical patterns for the reflection
    prompt. Returns empty list if no past entries exist or Chroma errors.
    """
    try:
        results = _collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={"created_at": {"$lt": before_iso}},
            include=["metadatas", "distances"],
        )
    except Exception:
        return []

    ids = results.get("ids", [[]])[0]
    if not ids:
        return []

    return [
        {
            "entry_id": entry_id,
            "mood_score": meta["mood_score"],
            "entities": [e for e in meta["entities"].split(",") if e],
            "created_at": meta["created_at"][:10],
        }
        for entry_id, meta in zip(ids, results["metadatas"][0])
    ]
