import re

def preprocess(text: str) -> str:
    """
    Clean raw journal text before it hits the ML pipeline.
    Order matters: strip first, then normalise, then mask.
    """
    text = text.strip()
    text = re.sub(r"\s+", " ", text)            # collapse whitespace
    text = re.sub(r"http\S+", "[URL]", text)    # mask URLs
    text = re.sub(r"\S+@\S+\.\S+", "[EMAIL]", text)  # mask emails
    return text

def chunk_text(text: str, chunk_size: int = 512) -> list[str]:
    """
    Naive sentence-boundary chunking for long entries.
    Splits on '. ' boundaries, accumulates until chunk_size chars.
    Replace with spaCy sentencizer for production-quality splitting.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) > chunk_size and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current += " " + sentence
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text]
