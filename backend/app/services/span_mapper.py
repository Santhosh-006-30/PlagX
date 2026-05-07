from typing import List, Dict, Any

class SpanMapper:
    def __init__(self):
        pass

    def merge_spans(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge overlapping and adjacent spans from the same source.
        """
        if not matches:
            return []

        # Sort matches by source and then start position
        sorted_matches = sorted(matches, key=lambda x: (x["source_id"], x["query_start"]))
        
        merged = []
        if not sorted_matches:
            return []
            
        current = sorted_matches[0].copy()
        
        for next_match in sorted_matches[1:]:
            # If same source and overlaps or is very close (e.g. 5 chars)
            if (next_match["source_id"] == current["source_id"] and 
                next_match["query_start"] <= current["query_end"] + 5):
                
                # Extend current span
                current["query_end"] = max(current["query_end"], next_match["query_end"])
                # Average or max score? Usually max for confidence
                current["score"] = max(current.get("score", 0), next_match.get("score", 0))
                
                # Handle source offsets if available
                if "source_end" in current and "source_end" in next_match:
                    current["source_end"] = max(current["source_end"], next_match["source_end"])
            else:
                merged.append(current)
                current = next_match.copy()
        
        merged.append(current)
        return merged

    def resolve_overlaps(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Resolve overlaps between DIFFERENT sources.
        Strategy: Keep the match with the highest score/confidence.
        """
        if not matches:
            return []
            
        # Sort by start char
        sorted_matches = sorted(matches, key=lambda x: x["query_start"])
        
        resolved = []
        for m in sorted_matches:
            # Check for overlaps with already resolved matches
            overlap_found = False
            for r in resolved:
                if m["query_start"] < r["query_end"] and m["query_end"] > r["query_start"]:
                    # Overlap! 
                    overlap_found = True
                    # If new match has higher score, we might want to split or replace
                    # For simplicity in this phase, we keep the one that started first or has higher score
                    if m["score"] > r["score"]:
                        # This is more complex (splitting spans). 
                        # For Phase 1, we just pick the best one per region.
                        pass
                    break
            
            if not overlap_found:
                resolved.append(m)
                
        return resolved
