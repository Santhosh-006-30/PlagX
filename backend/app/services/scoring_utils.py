from typing import List, Dict, Any, Set

class OverlapAwareScorer:
    """
    Calculates unique character coverage to prevent score inflation from overlapping spans.
    """
    
    @staticmethod
    def calculate_unique_coverage(total_chars: int, spans: List[Dict[str, Any]]) -> float:
        """
        Calculates the percentage of the document covered by unique matched characters.
        """
        if total_chars == 0 or not spans:
            return 0.0
            
        # Use a bitset-like approach (set of indices) for precise character tracking
        # For very large documents, we would use a more memory-efficient interval tree
        covered_indices: Set[int] = set()
        
        for span in spans:
            start = max(0, span.get("start_char", 0))
            end = min(total_chars, span.get("end_char", 0))
            
            for i in range(start, end):
                covered_indices.add(i)
                
        return len(covered_indices) / total_chars

    @staticmethod
    def merge_overlapping_spans(spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merges adjacent or overlapping spans of the same type.
        """
        if not spans:
            return []
            
        # Sort by start position
        sorted_spans = sorted(spans, key=lambda x: x["start_char"])
        merged = []
        
        if not sorted_spans:
            return []
            
        current = sorted_spans[0].copy()
        
        for next_span in sorted_spans[1:]:
            # If overlap or gap is small (e.g. 2 chars), merge
            if next_span["start_char"] <= current["end_char"] + 2:
                current["end_char"] = max(current["end_char"], next_span["end_char"])
                # Maintain highest confidence
                current["confidence"] = max(current.get("confidence", 0), next_span.get("confidence", 0))
            else:
                merged.append(current)
                current = next_span.copy()
        
        merged.append(current)
        return merged
