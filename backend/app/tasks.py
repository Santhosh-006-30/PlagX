import uuid
import asyncio
from datetime import datetime
from sqlalchemy import select
from app.celery_worker import celery_app
from app.database import AsyncSessionLocal
from app.models.scan import ScanJob, ScanMatch, HighlightRegion, StylometryMetrics
from app.models.document import Document
from app.services.plagiarism import get_plagiarism_engine
from app.services.ai_audit import get_ai_audit_service
from app.services.reranker import RerankerService
from app.services.span_mapper import SpanMapper
from app.services.highlight_engine import HighlightEngine
from app.services.scoring import ScoringService

@celery_app.task(name="run_analysis_task")
def run_analysis_task(job_id_str: str, doc_id_str: str):
    """
    Celery task to perform the full enterprise analysis pipeline.
    """
    job_id = uuid.UUID(job_id_str)
    doc_id = uuid.UUID(doc_id_str)
    
    # Celery tasks are usually synchronous in their definition, 
    # but we use asyncio to run our async DB operations.
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_async_analysis_pipeline(job_id, doc_id))

async def _async_analysis_pipeline(job_id: uuid.UUID, doc_id: uuid.UUID):
    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch Job and Document
            job_result = await db.execute(select(ScanJob).where(ScanJob.id == job_id))
            job = job_result.scalar_one()
            
            doc_result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = doc_result.scalar_one()
            
            job.status = "processing"
            job.progress_detail = "Starting enterprise audit..."
            job.started_at = datetime.utcnow()
            await db.commit()

            text = doc.extracted_text or ""
            if not text:
                raise ValueError("No text extracted from document")

            # 2. Initialize Services
            engine = get_plagiarism_engine()
            ai_service = get_ai_audit_service()
            reranker = RerankerService()
            span_mapper = SpanMapper()
            highlight_engine = HighlightEngine()
            scoring_service = ScoringService()

            # 3. Reference Indexing (In production, this would be a pre-built global index)
            job.progress_detail = "Indexing reference corpus..."
            await db.commit()
            
            engine.clear_index()
            others_result = await db.execute(select(Document).where(Document.id != doc.id))
            for other in others_result.scalars().all():
                if other.extracted_text:
                    engine.add_document(str(other.id), other.extracted_text)

            # 4. AI Audit
            job.progress_detail = "Performing AI content analysis..."
            await db.commit()
            ai_results = await ai_service.analyze_text(text)

            # 5. Hybrid Plagiarism Retrieval
            job.progress_detail = "Scanning for lexical and semantic matches..."
            await db.commit()
            raw_results = engine.analyze_text(text, exclude_doc_id=doc.id)
            
            exact_matches = raw_results["exact_matches"]
            semantic_candidates = raw_results["semantic_matches"]

            # 6. Reranking
            job.progress_detail = "Reranking semantic candidates for precision..."
            await db.commit()
            reranked_semantic = reranker.rerank(text, semantic_candidates)

            # 7. Span Mapping & Merging
            job.progress_detail = "Reconstructing match spans..."
            await db.commit()
            merged_exact = span_mapper.merge_spans(exact_matches)
            merged_semantic = span_mapper.merge_spans(reranked_semantic)
            
            # Final resolved matches (Exact takes priority)
            resolved_matches = span_mapper.resolve_overlaps(merged_exact + merged_semantic)

            # 8. Scoring
            job.progress_detail = "Calculating final originality scores..."
            await db.commit()
            
            # Simple heuristic for scores based on match lengths
            total_len = len(text)
            exact_len = sum([m["query_end"] - m["query_start"] for m in merged_exact])
            semantic_len = sum([m["query_end"] - m["query_start"] for m in merged_semantic])
            
            fingerprint_score = min(1.0, exact_len / total_len)
            semantic_score = min(1.0, semantic_len / total_len)
            rerank_score = max([m.get("confidence", 0) for m in reranked_semantic]) if reranked_semantic else 0
            
            # Placeholder for stylometry (Phase 1 simplicity)
            stylometry_score = 0.1 if ai_results.get("ai_score", 0) > 50 else 0.0

            overall_score = scoring_service.calculate_final_score(
                fingerprint_score, semantic_score, rerank_score, stylometry_score
            )

            # 9. Store Matches & Highlights
            for m in resolved_matches:
                match_obj = ScanMatch(
                    scan_job_id=job.id,
                    query_start=m["query_start"],
                    query_end=m["query_end"],
                    source_id=str(m["source_id"]),
                    source_start=m.get("source_start"),
                    source_end=m.get("source_end"),
                    match_type=m["match_type"],
                    confidence=m.get("confidence", 1.0),
                    score=m.get("score", 1.0)
                )
                db.add(match_obj)

            highlights = highlight_engine.generate_highlights(merged_exact, merged_semantic)
            for h in highlights:
                hl_obj = HighlightRegion(
                    scan_job_id=job.id,
                    start=h["start"],
                    end=h["end"],
                    type=h["type"],
                    color=h["color"],
                    confidence=h["confidence"],
                    source_id=str(h.get("source_id"))
                )
                db.add(hl_obj)

            # 10. Finalize Job
            job.status = "completed"
            job.overall_score = overall_score
            job.ai_probability = ai_results.get("ai_score", 0)
            job.completed_at = datetime.utcnow()
            job.progress_detail = "Audit complete."
            
            # Legacy support for frontend segments (Phase 1)
            doc.segments = highlights 

            await db.commit()

        except Exception as e:
            import traceback
            traceback.print_exc()
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            await db.commit()
