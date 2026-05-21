from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from typing import Optional
import aiosqlite

from app.models.entry import JournalEntryCreate, JournalEntryResponse
from app.models.analysis import AnalysisResponse
from app.models.reflection import ReflectionResponse
from app.db.sqlite import save_entry, get_entry, get_analysis
from app.core.pipeline import run_analysis_pipeline
from app.services.reflection import generate_weekly_reflection
from app.api.deps import get_db

router = APIRouter(prefix="/entries", tags=["entries"])
reflect_router = APIRouter(prefix="/reflect", tags=["reflection"])

@router.get("", response_model=list[JournalEntryResponse], status_code=200)
async def list_entries(
    month: Optional[str] = Query(None, description="Filter by month, format YYYY-MM"),
    db: aiosqlite.Connection = Depends(get_db),
):
    if month:
        async with db.execute(
            "SELECT * FROM entries WHERE entry_date LIKE ? ORDER BY entry_date DESC, created_at DESC",
            (f"{month}-%",),
        ) as cursor:
            rows = await cursor.fetchall()
    else:
        async with db.execute(
            "SELECT * FROM entries ORDER BY entry_date DESC, created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
    return [JournalEntryResponse(**dict(row)) for row in rows]



@router.post("", response_model=JournalEntryResponse, status_code=202)
async def create_entry(
    payload: JournalEntryCreate,
    background_tasks: BackgroundTasks,
    db: aiosqlite.Connection = Depends(get_db),
):
    entry_id = await save_entry(db, payload.content, payload.entry_date)
    background_tasks.add_task(run_analysis_pipeline, entry_id, payload.content, db)
    entry = await get_entry(db, entry_id)
    return entry


@router.get("/{entry_id}/analysis", response_model=AnalysisResponse, status_code=200)
async def get_entry_analysis(
    entry_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    entry = await get_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    analysis = await get_analysis(db, entry_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not available yet")
    return analysis


@router.get("/{entry_id}", response_model=JournalEntryResponse)
async def get_entry_status(
    entry_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    entry = await get_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@reflect_router.post("", response_model=ReflectionResponse, status_code=200)
async def reflect(
    db: aiosqlite.Connection = Depends(get_db),
):
    result = await generate_weekly_reflection(db)
    return result
