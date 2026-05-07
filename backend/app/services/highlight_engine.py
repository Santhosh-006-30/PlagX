from typing import List, Dict, Any

class HighlightEngine:
    def __init__(self):
        # Color mapping as per requirements
        self.colors = {
            "exact_plagiarism": "red",
            "semantic_plagiarism": "orange",
            "citation_overlap": "yellow",
            "ai_generated": "purple"
        }

    def generate_highlights(self, 
                            exact_matches: List[Dict[str, Any]], 
                            semantic_matches: List[Dict[str, Any]],
                            ai_matches: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Create a flat list of non-overlapping highlights for the frontend.
        """
        highlights = []
        
        # 1. Add exact matches (highest priority)
        for m in exact_matches:
            highlights.append({
                "start": m["query_start"],
                "end": m["query_end"],
                "type": "exact_plagiarism",
                "color": self.colors["exact_plagiarism"],
                "confidence": m.get("score", 1.0),
                "source_id": m.get("source_id")
            })
            
        # 2. Add semantic matches (lower priority, skip if exact exists)
        for m in semantic_matches:
            if not self._overlaps_any(m["query_start"], m["query_end"], highlights):
                highlights.append({
                    "start": m["query_start"],
                    "end": m["query_end"],
                    "type": "semantic_plagiarism",
                    "color": self.colors["semantic_plagiarism"],
                    "confidence": m.get("score", 0.8),
                    "source_id": m.get("source_id")
                })
                
        # 3. Add AI matches (can overlap in some systems, but here we resolve or keep separate)
        if ai_matches:
            for m in ai_matches:
                # AI highlights might be sentence-level
                # We could support nested highlights, but for Phase 1 we simplify
                if not self._overlaps_any(m["start"], m["end"], highlights):
                    highlights.append({
                        "start": m["start"],
                        "end": m["end"],
                        "type": "ai_generated",
                        "color": self.colors["ai_generated"],
                        "confidence": m.get("score", 0.7)
                    })
                    
        # Sort by start position
        highlights.sort(key=lambda x: x["start"])
        return highlights

    def _overlaps_any(self, start: int, end: int, existing: List[Dict[str, Any]]) -> bool:
        """Helper to check for overlaps."""
        for h in existing:
            if start < h["end"] and end > h["start"]:
                return True
        return False
