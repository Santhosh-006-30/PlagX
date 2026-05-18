"""
SQLAlchemy ORM model — documents and document_chunks tables.
"""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func, UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    file_key: Mapped[str] = mapped_column(Text, nullable=False)   # storage path
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf|docx|txt
    file_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | processing | indexed | failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    segments: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True) # Granular sentence mapping
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="documents")  # noqa: F821
    scan_jobs: Mapped[list["ScanJob"]] = relationship(  # noqa: F821
        "ScanJob", back_populates="document", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} title={self.title} status={self.status}>"
