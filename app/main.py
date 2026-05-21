from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router, reflect_router, chat_router, mood_router
from app.db.migrations import run_migrations
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_migrations()
    print(f"[startup] {settings.app_name} ready")
    yield


app = FastAPI(
    title=settings.app_name,
    description="Sentiment-aware personal journal with local ML pipeline.",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(router)
app.include_router(reflect_router)
app.include_router(chat_router)
app.include_router(mood_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
