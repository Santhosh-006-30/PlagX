import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func, UUID, JSON, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Fingerprint(Base):
    """Stores Winnowing fingerprints for exact match detection."""
    __tablename__ = "fingerprints"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    hash_value: Mapped[int] = mapped_column(BigInteger, index=True)
    offset: Mapped[int] = mapped_column(Integer) # Character offset in document

class HighlightRegion(Base):
    """Precise highlight spans for the Turnitin-style viewer."""
    __tablename__ = "highlight_regions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scan_jobs.id", ondelete="CASCADE"), index=True
    )
    start_char: Mapped[int] = mapped_column(Integer)
    end_char: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(50)) # exact | semantic | ai | citation
    confidence: Mapped[float] = mapped_column(Float)
    source_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

class StylometryMetric(Base):
    """Stores stylometric features for authorship/AI analysis."""
    __tablename__ = "stylometry_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    sentence_length_var: Mapped[float] = mapped_column(Float)
    lexical_richness: Mapped[float] = mapped_column(Float)
    punctuation_entropy: Mapped[float] = mapped_column(Float)
    readability_score: Mapped[float] = mapped_column(Float)
    passive_voice_ratio: Mapped[float] = mapped_column(Float)
