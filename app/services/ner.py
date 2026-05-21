import asyncio
from functools import partial
from transformers import pipeline as hf_pipeline

# bert-base-NER is small (~400MB), fast on CPU, no binary deps
_ner = hf_pipeline(
    "ner",
    model="dslim/bert-base-NER",
    aggregation_strategy="simple",  # merges B-/I- tokens into whole entities
)


def _extract(text: str) -> list[str]:
    results = _ner(text[:512])
    seen, entities = set(), []
    for r in results:
        word = r["word"].strip()
        key = word.lower()
        if key not in seen and len(key) > 2 and r["score"] > 0.85:
            seen.add(key)
            entities.append(word)
    return entities


async def extract_entities(text: str) -> list[str]:
    """Returns a deduplicated list of named entities. Non-blocking."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_extract, text))