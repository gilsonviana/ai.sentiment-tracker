import asyncio
from functools import partial
from sentence_transformers import SentenceTransformer
from app.config import settings

# Load once at startup
_model = SentenceTransformer(settings.embedding_model)


def _embed(text: str) -> list[float]:
    return _model.encode(text).tolist()


async def embed_text(text: str) -> list[float]:
    """Returns a 384-dim embedding vector. Non-blocking."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_embed, text))
