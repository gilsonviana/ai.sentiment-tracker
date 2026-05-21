from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router, reflect_router
from app.db.migrations import run_migrations
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: run DB migrations before accepting requests
    await run_migrations()
    print(f"[startup] {settings.app_name} ready")
    yield
    # Shutdown: add cleanup here if needed


app = FastAPI(
    title=settings.app_name,
    description="Sentiment-aware personal journal with local ML pipeline.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)
app.include_router(reflect_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
