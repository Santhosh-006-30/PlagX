import asyncio
import uuid
from typing import Dict, Any
from celery import shared_task
from sqlalchemy import select, update, func
from app.core.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.document import Document
from app.models.scan import ScanJob
from app.models.analysis import Fingerprint, HighlightRegion, StylometryMetric
from app.services.extraction import extract_text_from_file
from app.services.fingerprinting import WinnowingEngine
from app.services.semantic import SemanticEngine
from app.services.ai_audit import get_ai_audit_service
from app.services.stylometry import StylometryEngine
from app.services.filters import AcademicFilter
from app.services.highlight_engine import HighlightEngine
from app.services.report_reconciliation import ReportReconciliationEngine
from app.services.final_scoring import FinalScoringEngine
from app.services.calibration import CalibrationEngine
from app.services.explainability import ExplainabilityEngine
from app.config import settings

@celery_app.task(name="app.tasks.run_analysis_task")
def run_analysis_task(job_id: str, document_id: str):
    """
    Main background task for document analysis.
    """
    # Use asyncio.run to bridge Celery (sync) and FastAPI/SQLAlchemy (async)
    return asyncio.run(async_run_analysis(uuid.UUID(job_id), uuid.UUID(document_id)))

async def async_run_analysis(job_id: uuid.UUID, document_id: uuid.UUID):
    async with AsyncSessionLocal() as db:
        # 1. Update Job Status
        await db.execute(
            update(ScanJob)
            .where(ScanJob.id == job_id)
            .values(status="processing", started_at=func.now())
        )
        await db.commit()

        try:
            # 2. Get Document
            result = await db.execute(select(Document).where(Document.id == document_id))
            doc = result.scalar_one()
            
            # 3. Extract & Filter
            text = doc.extracted_text or extract_text_from_file(doc.file_key, doc.file_type)
            filters = AcademicFilter()
            clean_text = filters.strip_bibliography(text)
            
            # 4. Exact Detection (Winnowing)
            winnowing = WinnowingEngine()
            current_fp = winnowing.get_fingerprints(clean_text)
            current_hashes = {f[0] for f in current_fp}
            
            # Fetch existing documents
            existing_docs_res = await db.execute(
                select(Document).where(Document.status == "completed")
            )
            all_existing_docs = existing_docs_res.scalars().all()
            
            existing_docs = []
            suppressed_self_matches = 0
            for d in all_existing_docs:
                if d.id == document_id:
                    suppressed_self_matches += 1
                else:
                    existing_docs.append(d)
            
            exact_matches = []
            matched_char_indices = set() # For overlap-aware scoring
            
            for other_doc in existing_docs:
                other_fp_res = await db.execute(
                    select(Fingerprint).where(Fingerprint.document_id == other_doc.id)
                )
                other_hashes = {f.hash_value for f in other_fp_res.scalars().all()}
                
                intersection = current_hashes.intersection(other_hashes)
                if intersection:
                    # Calculate unique character coverage for this source
                    similarity = len(intersection) / max(1, len(current_hashes))
                    if similarity > 0.05: 
                        matched_offsets = [offset for h, offset in current_fp if h in intersection]
                        if matched_offsets:
                            exact_matches.append({
                                "source_id": str(other_doc.id),
                                "title": other_doc.title,
                                "similarity": similarity,
                                "match_type": "exact",
                                "start_char": min(matched_offsets),
                                "end_char": max(matched_offsets) + 50
                            })

            # Save current fingerprints AFTER search to prevent self-collision
            for h, offset in current_fp:
                db.add(Fingerprint(document_id=document_id, hash_value=h, offset=offset))
            
            # 5. Semantic Detection
            semantic = SemanticEngine()
            # Load existing documents into FAISS
            if existing_docs:
                semantic.add_documents([
                    {"id": str(d.id), "text": d.extracted_text} for d in existing_docs if d.extracted_text
                ])
            
            # Search current chunks
            chunks = [clean_text[i:i+500] for i in range(0, len(clean_text), 400)]
            raw_semantic_matches = semantic.search(chunks)
            semantic_matches = []
            for m in raw_semantic_matches:
                start_char = clean_text.find(m["query_text"])
                if start_char != -1:
                    m["start_char"] = start_char
                    m["end_char"] = start_char + len(m["query_text"])
                    semantic_matches.append(m)
            
            # 6. AI & Stylometry
            ai_service = get_ai_audit_service()
            ai_results = await ai_service.analyze_text(clean_text)
            
            stylometry = StylometryEngine()
            sty_metrics = stylometry.analyze_document(clean_text)
            db.add(StylometryMetric(document_id=document_id, **sty_metrics))

            # 7. Calibration & Hardening
            calibration = CalibrationEngine()
            semantic_matches = calibration.normalize_semantic_scores(semantic_matches)
            stylo_suspicion = calibration.calibrate_stylometry(sty_metrics)
            
            # 8. Report Reconciliation (Overlap-Aware Highlights)
            ai_regions = []
            if ai_results.get("ai_score", 0) > 20:
                for i, chunk in enumerate(chunks):
                    ai_regions.append({
                        "start_char": i * 400,
                        "end_char": i * 400 + len(chunk),
                        "type": "ai",
                        "probability": ai_results["ai_score"] / 100,
                        "confidence": ai_results["ai_score"] / 100
                    })
                    
            reconciler = ReportReconciliationEngine(clean_text)
            reconciled_data = reconciler.reconcile(
                exact_matches, 
                semantic_matches, 
                ai_regions
            )
            
            # 9. Final Scoring (Hardened Ensemble)
            scoring_engine = FinalScoringEngine()
            final_overall_score = scoring_engine.calculate_ensemble_score(
                exact_score=reconciled_data["exact_coverage"],
                semantic_score=reconciled_data["semantic_coverage"],
                stylo_score=stylo_suspicion,
                ai_score=ai_results["ai_score"]
            )
            
            # 10. Explainability Layer
            explainer = ExplainabilityEngine()
            explainability_data = {
                "summary": explainer.generate_report_summary({
                    "exact": reconciled_data["exact_coverage"],
                    "semantic": reconciled_data["semantic_coverage"],
                    "ai": ai_results["ai_score"]
                }),
                "risk_level": scoring_engine.get_risk_level(final_overall_score)
            }

            # 11. Save Highlights with Explainability
            for h in reconciled_data["highlights"]:
                explanation = explainer.explain_match(
                    h["type"], 
                    h["confidence"], 
                    h.get("title", "External Source")
                )
                db.add(HighlightRegion(
                    scan_job_id=job_id,
                    start_char=h["start_char"],
                    end_char=h["end_char"],
                    type=h["type"],
                    confidence=h["confidence"],
                    source_id=str(h.get("source_id", "")),
                    explanation=explanation # Ensure model supports this
                ))
            
            # 12. Update Job Final (Hardened)
            results_payload = {
                "overall_similarity": final_overall_score,
                "ai_score": ai_results["ai_score"],
                "explainability": explainability_data,
                "metrics": {
                    "exact": reconciled_data["exact_coverage"],
                    "semantic": reconciled_data["semantic_coverage"],
                    "stylometry": round(stylo_suspicion, 2)
                },
                "matches": exact_matches + [{
                    "source": m["source_id"],
                    "similarity": m["semantic_score"] * 100,
                    "text": m["match_text"],
                    "match_type": "semantic"
                } for m in semantic_matches]
            }

            await db.execute(
                update(ScanJob)
                .where(ScanJob.id == job_id)
                .values(
                    status="completed",
                    overall_score=final_overall_score,
                    ai_probability=ai_results["ai_score"],
                    completed_at=func.now(),
                    results=results_payload
                )
            )
            await db.commit()
            
            import json
            import logging
            logger = logging.getLogger(__name__)

            debug_payload = {
                "raw_candidates": len(existing_docs),
                "validated_matches": len(exact_matches) + len(semantic_matches),
                "exact_matches": len(exact_matches),
                "semantic_matches": len(semantic_matches),
                "merged_spans": len(reconciled_data["highlights"]),
                "suppressed_self_matches": suppressed_self_matches,
                "rejected_low_confidence": len(current_fp) - len(exact_matches),
                "final_similarity": final_overall_score
            }
            logger.info(f"ANALYSIS DEBUG REPORT:\n{json.dumps(debug_payload, indent=2)}")
            
        except Exception as e:
            await db.execute(
                update(ScanJob)
                .where(ScanJob.id == job_id)
                .values(status="failed", error_message=str(e))
            )
            await db.commit()
            raise e
