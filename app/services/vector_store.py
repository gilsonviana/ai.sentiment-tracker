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
