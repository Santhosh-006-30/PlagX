"""
Pydantic schemas for scanning and reports.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ScanJobCreate(BaseModel):
    document_id: uuid.UUID

class ScanJobResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    submitted_by_id: uuid.UUID
    status: str
    progress_detail: str | None = None
    overall_score: float | None = None
    ai_probability: float | None = None
    results: dict | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class ScanReportResponse(BaseModel):
    job: ScanJobResponse
    document_title: str
    document_text: str | None = None
    document_segments: list[dict] | None = None
    file_key: str | None = None
    file_type: str | None = None

    model_config = ConfigDict(from_attributes=True)
