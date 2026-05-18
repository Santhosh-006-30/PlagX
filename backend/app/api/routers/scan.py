"""
Scan router for plagiarism analysis and reporting.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.scan import ScanJob
from app.schemas.scan import ScanJobResponse, ScanReportResponse, ScanJobCreate
from app.services.plagiarism import get_plagiarism_engine

router = APIRouter()

@router.post("/analyze", response_model=ScanJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_document(
    request: ScanJobCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch the target document
    result = await db.execute(select(Document).where(Document.id == request.document_id))
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to scan this document")
    
    if not doc.extracted_text:
        raise HTTPException(status_code=400, detail="Document has no extracted text to analyze")

    # 2. Create scan job in 'queued' status
    job = ScanJob(
        submitted_by_id=current_user.id,
        document_id=doc.id,
        status="queued",
        created_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    from app.tasks.scan_tasks import async_run_analysis
    background_tasks.add_task(async_run_analysis, job.id, doc.id)
    
    return job

@router.get("/report/{id}", response_model=ScanReportResponse)
async def get_report(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch job with document relationship
    result = await db.execute(
        select(ScanJob).where(ScanJob.id == id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    
    if job.submitted_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this report")
    
    # Fetch document explicitly to ensure we have the text and segments
    doc_result = await db.execute(select(Document).where(Document.id == job.document_id))
    doc = doc_result.scalar_one_or_none()
    
    return {
        "job": job,
        "document_title": doc.title if doc else "Unknown",
        "document_text": doc.extracted_text if doc else "",
        "document_segments": doc.segments if doc else [],
        "file_key": doc.file_key if doc else None,
        "file_type": doc.file_type if doc else None
    }
