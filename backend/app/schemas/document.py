"""
Pydantic schemas for document management.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class DocumentBase(BaseModel):
    title: str

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    file_type: str
    file_size_bytes: int
    word_count: int | None = None
    status: str
    created_at: datetime
    indexed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class DocumentDetailResponse(DocumentResponse):
    extracted_text: str | None = None
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)
