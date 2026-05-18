from typing import List, Dict, Any
from app.services.scoring_utils import OverlapAwareScorer

class ReportReconciliationEngine:
    """
    Hardens report data by reconciling raw matches into a consistent, overlap-free report.
    """
    
    def __init__(self, document_text: str):
        self.document_text = document_text
        self.total_chars = len(document_text)
        self.scorer = OverlapAwareScorer()

    def reconcile(self, 
                  exact_matches: List[Dict[str, Any]], 
                  semantic_matches: List[Dict[str, Any]], 
                  ai_regions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Consolidates all matches into a unified report structure.
        """
        # 1. Clean and filter raw matches
        filtered_exact = [m for m in exact_matches if m.get("similarity", 0) > 0.1]
        filtered_semantic = [m for m in semantic_matches if m.get("semantic_score", 0) > 0.85]
        
        # 2. Calculate unique coverage per type (Overlap-Aware)
        # Note: In a real report, we map fingerprint offsets to char offsets here
        exact_coverage = self.scorer.calculate_unique_coverage(self.total_chars, filtered_exact)
        semantic_coverage = self.scorer.calculate_unique_coverage(self.total_chars, filtered_semantic)
        
        # 3. Resolve overlaps across types (Priority: Exact > Semantic)
        all_highlights = self._generate_consolidated_highlights(filtered_exact, filtered_semantic, ai_regions)
        
        # 4. Final Aggregated Similarity (Unique chars / Total chars)
        overall_similarity = self.scorer.calculate_unique_coverage(self.total_chars, all_highlights)
        
        return {
            "overall_similarity": round(overall_similarity * 100, 2),
            "exact_coverage": round(exact_coverage * 100, 2),
            "semantic_coverage": round(semantic_coverage * 100, 2),
            "highlights": all_highlights,
            "metadata": {
                "total_characters": self.total_chars,
                "reconciled": True
            }
        }

    def _generate_consolidated_highlights(self, exact, semantic, ai) -> List[Dict[str, Any]]:
        """
        Creates a non-overlapping list of highlights for visual display.
        """
        consolidated = []
        
        # Merge semantic chunks that are close together from the same source
        # (This prevents "fragmented" highlighting)
        merged_semantic = self.scorer.merge_overlapping_spans(semantic)
        
        # Add Exact (Highest Priority)
        for m in exact:
            consolidated.append({
                **m,
                "type": "exact",
                "priority": 1
            })
            
        # Add Semantic (Only if not already covered by exact)
        for m in merged_semantic:
            if not self._is_significantly_covered(m, consolidated):
                consolidated.append({
                    **m,
                    "type": "semantic",
                    "priority": 2
                })
                
        # Add AI (Layered or separate)
        # AI highlights can overlap similarity highlights in the UI (heatmap)
        # but for scoring reconciliation we keep them separate
        for m in ai:
            consolidated.append({
                **m,
                "type": "ai",
                "priority": 3,
                "color": "purple"
            })
            
        return consolidated

    def _is_significantly_covered(self, span, existing) -> bool:
        for h in existing:
            overlap = max(0, min(span["end_char"], h["end_char"]) - max(span["start_char"], h["start_char"]))
            if overlap / (span["end_char"] - span["start_char"]) > 0.5:
                return True
        return False
