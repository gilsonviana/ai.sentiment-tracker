from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
import aiosqlite

from app.models.entry import JournalEntryCreate, JournalEntryResponse
from app.db.sqlite import save_entry, get_entry
from app.core.pipeline import run_analysis_pipeline
from app.api.deps import get_db

router = APIRouter(prefix="/entries", tags=["entries"])

@router.get("", response_model=list[JournalEntryResponse], status_code=200)
async def list_entries(
    db: aiosqlite.Connection = Depends(get_db),
):
    async with db.execute(
        "SELECT * FROM entries ORDER BY created_at DESC"
    ) as cursor:
        rows = await cursor.fetchall()
        return [JournalEntryResponse(**dict(row)) for row in rows]



@router.post("", response_model=JournalEntryResponse, status_code=202)
async def create_entry(
    payload: JournalEntryCreate,
    background_tasks: BackgroundTasks,
    db: aiosqlite.Connection = Depends(get_db),
):
    entry_id = await save_entry(db, payload.content)
    background_tasks.add_task(run_analysis_pipeline, entry_id, payload.content, db)
    entry = await get_entry(db, entry_id)
    return entry


@router.get("/{entry_id}", response_model=JournalEntryResponse)
async def get_entry_status(
    entry_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    entry = await get_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry
