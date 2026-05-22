import asyncio
from functools import partial
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from transformers import pipeline as hf_pipeline
from app.config import settings

# Initialise once at import time — expensive, do NOT do this per-request
_vader = SentimentIntensityAnalyzer()
_roberta = hf_pipeline(
    "text-classification",
    model=settings.roberta_model,
    top_k=1,
)

# Map RoBERTa label strings to a -1..1 float
_LABEL_MAP = {"negative": -1.0, "neutral": 0.0, "positive": 1.0}


def _vader_score(text: str) -> float:
    return _vader.polarity_scores(text)["compound"]


def _roberta_score(text: str) -> float:
    result = _roberta(text[:512])[0][0]  # [batch][top_k] — top_k=1 wraps in extra list
    label = result["label"]
    return _LABEL_MAP.get(label, 0.0)


async def score_sentiment(text: str) -> tuple[float, float, float, str]:
    """
    Returns (vader, roberta, composite, label).
    CPU-bound calls pushed to thread pool to avoid blocking the event loop.
    """
    loop = asyncio.get_event_loop()
    vader, roberta = await asyncio.gather(
        loop.run_in_executor(None, partial(_vader_score, text)),
        loop.run_in_executor(None, partial(_roberta_score, text)),
    )
    composite = (vader + roberta) / 2
    label = (
        "positive" if composite > 0.05
        else "negative" if composite < -0.05
        else "neutral"
    )
    return vader, roberta, composite, label
