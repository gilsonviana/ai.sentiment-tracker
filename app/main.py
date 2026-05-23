import asyncio
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api.routes import router, reflect_router, chat_router, mood_router
from app.config import settings
from app.core.worker import worker_loop
from app.db.migrations import run_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_migrations()
    if int(os.getenv("WEB_CONCURRENCY", "1")) > 1:
        raise RuntimeError(
            "Queue worker runs in-process. Start API with a single process "
            "(WEB_CONCURRENCY=1)."
        )
    worker_task = asyncio.create_task(worker_loop())
    print(f"[startup] {settings.app_name} ready")
    yield
    worker_task.cancel()
    with suppress(asyncio.CancelledError):
        await worker_task


app = FastAPI(
    title=settings.app_name,
    description="Sentiment-aware personal journal with local ML pipeline.",
    version="0.3.0",
    lifespan=lifespan,
)

app.include_router(router)
app.include_router(reflect_router)
app.include_router(chat_router)
app.include_router(mood_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
