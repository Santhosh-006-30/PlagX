"""
Document router for file uploads and management.
"""
import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.document import Document
from app.schemas.document import DocumentResponse, DocumentDetailResponse
from app.services.extraction import ExtractionService
from app.config import settings

router = APIRouter()

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    print(f"DEBUG: Starting upload for {file.filename}...")
    # Validate file extension
    ext = file.filename.split(".")[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {settings.ALLOWED_EXTENSIONS}")
    
    # Read content
    content = await file.read()
    file_size = len(content)
    
    if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
    
    # Save file locally (Placeholder for S3/MinIO)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_key = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, file_key)
    
    import aiofiles
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    
    # Extract text with metadata
    try:
        extraction_res = await ExtractionService.extract_text_with_metadata(content, ext)
        extracted_text = extraction_res["full_text"]
        segments = extraction_res["segments"]
        word_count = len(extracted_text.split())
    except Exception as e:
        import traceback
        traceback.print_exc()
        extracted_text = None
        segments = []
        word_count = 0
        print(f"Extraction failed: {e}")

    # Create record
    doc = Document(
        owner_id=current_user.id,
        title=file.filename,
        file_key=file_key,
        file_type=ext,
        file_size_bytes=file_size,
        word_count=word_count,
        extracted_text=extracted_text,
        segments=segments,
        status="indexed" if extracted_text else "failed"
    )
    
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    print(f"DEBUG: Successfully uploaded and saved {file.filename} as ID {doc.id}")
    
    return doc
