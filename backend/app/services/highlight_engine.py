from typing import List, Dict, Any, Tuple
import uuid

class HighlightEngine:
    """
    Coordinates highlights from all detection modules and resolves overlaps.
    """
    def __init__(self):
        # Color mapping for different match types
        self.colors = {
            "exact": "red",
            "semantic": "orange",
            "citation": "yellow",
            "ai": "purple"
        }

    def resolve_highlights(self, 
                           exact_matches: List[Dict[str, Any]], 
                           semantic_matches: List[Dict[str, Any]], 
                           ai_regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merges matches and resolves overlaps by priority.
        Priority: Exact > AI > Semantic
        """
        all_highlights = []
        
        # 1. Add Exact Matches
        for m in exact_matches:
            all_highlights.append({
                "start_char": m["start_char"],
                "end_char": m["end_char"],
                "type": "exact",
                "confidence": m.get("confidence", 1.0),
                "source_id": m.get("source_id"),
                "color": self.colors["exact"]
            })
            
        # 2. Add AI Heatmap regions
        for m in ai_regions:
            # Only add if probability is high
            if m["probability"] > 0.7:
                all_highlights.append({
                    "start_char": m["start_char"],
                    "end_char": m["end_char"],
                    "type": "ai",
                    "confidence": m["probability"],
                    "color": self.colors["ai"]
                })
                
        # 3. Add Semantic matches (if not already covered by exact)
        for m in semantic_matches:
            if not self._is_covered(m["start_char"], m["end_char"], all_highlights):
                all_highlights.append({
                    "start_char": m["start_char"],
                    "end_char": m["end_char"],
                    "type": "semantic",
                    "confidence": m["score"],
                    "source_id": m["source_id"],
                    "color": self.colors["semantic"]
                })
                
        # Final Sort
        return sorted(all_highlights, key=lambda x: x["start_char"])

    def _is_covered(self, start: int, end: int, existing: List[Dict[str, Any]]) -> bool:
        """Checks if a span is significantly overlapped by an existing higher-priority highlight."""
        for h in existing:
            # Overlap calculation
            overlap_start = max(start, h["start_char"])
            overlap_end = min(end, h["end_char"])
            
            if overlap_end > overlap_start:
                overlap_len = overlap_end - overlap_start
                span_len = end - start
                # If more than 50% covered, skip
                if overlap_len / span_len > 0.5:
                    return True
        return False
