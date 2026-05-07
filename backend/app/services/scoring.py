from typing import List, Dict, Any

class ScoringService:
    def __init__(self):
        # Weighted ensemble configuration
        self.weights = {
            "fingerprint": 0.40,
            "semantic": 0.35,
            "rerank": 0.15,
            "stylometry": 0.10
        }

    def calculate_final_score(self, 
                              fingerprint_score: float, 
                              semantic_score: float, 
                              rerank_score: float, 
                              stylometry_score: float) -> float:
        """
        Calculate the weighted ensemble score.
        All inputs should be normalized between 0.0 and 1.0.
        """
        final = (
            (self.weights["fingerprint"] * fingerprint_score) +
            (self.weights["semantic"] * semantic_score) +
            (self.weights["rerank"] * rerank_score) +
            (self.weights["stylometry"] * stylometry_score)
        )
        return round(final * 100, 2)

    def calibrate_confidence(self, match_type: str, raw_score: float) -> float:
        """
        Calibrate confidence based on match type and raw score.
        """
        if match_type == "exact":
            return 1.0 # Exact match is always 100% confident
        
        # For semantic matches, apply a sigmoid or similar scaling
        import math
        return 1 / (1 + math.exp(-10 * (raw_score - 0.5)))
