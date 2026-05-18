import numpy as np
from typing import List, Dict, Any

class CalibrationEngine:
    """
    Standardizes and normalizes scores across different detection engines.
    Prevents "raw match inflation" and ensures consistency.
    """
    
    @staticmethod
    def normalize_semantic_scores(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Applies a sigmoid normalization to semantic scores.
        Rerank scores are often clustered; this spreads them for better reporting.
        """
        for m in matches:
            raw = m.get("semantic_score", 0)
            # Sigmoid center at 0.85
            m["semantic_score"] = 1 / (1 + np.exp(-15 * (raw - 0.85)))
        return matches

    @staticmethod
    def calibrate_stylometry(metrics: Dict[str, Any]) -> float:
        """
        Converts raw stylometry metrics into a 0-100 "Inconsistency Score".
        Factors: Low sentence length variance + high readability + low lexical diversity = AI signature.
        """
        lexical = metrics.get("lexical_richness", 0.5)
        sent_var = metrics.get("sentence_length_variance", 10.0)
        
        # Lower lexical richness + lower variance = higher suspicion
        suspicion = (1.0 - lexical) * 0.7 + (1.0 - min(1.0, sent_var/20)) * 0.3
        return min(100.0, suspicion * 100)

    @staticmethod
    def apply_confidence_smoothing(score: float, match_count: int) -> float:
        """
        Dampens scores based on match count. 
        A single high-similarity sentence shouldn't flag a whole document as plagiarized.
        """
        if match_count < 3:
            return score * 0.5
        return score
