from typing import Dict, Any

class FinalScoringEngine:
    """
    Calibrated ensemble scoring for enterprise reports.
    Weights: Exact(40%), Semantic(35%), Stylometry(15%), AI(10%)
    """
    
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or {
            "exact": 0.40,
            "semantic": 0.35,
            "stylometry": 0.15,
            "ai": 0.10
        }

    def calculate_ensemble_score(self, 
                                 exact_score: float, 
                                 semantic_score: float, 
                                 stylo_score: float, 
                                 ai_score: float) -> float:
        """
        Calculates a normalized, weighted score.
        All inputs expected as 0.0 - 100.0
        """
        # Apply sigmoid-like smoothing to AI score to prevent low-level noise
        calibrated_ai = self._calibrate_ai_score(ai_score)
        
        # Apply penalty for stylometry inconsistency
        # (If stylo_score is high, it indicates inconsistent writing)
        
        raw_score = (
            exact_score * self.weights["exact"] +
            semantic_score * self.weights["semantic"] +
            stylo_score * self.weights["stylometry"] +
            calibrated_ai * self.weights["ai"]
        )
        
        return round(min(100.0, raw_score), 2)

    def _calibrate_ai_score(self, score: float) -> float:
        """
        Suppresses AI noise below 20% and caps at 99% unless extremely certain.
        """
        if score < 25:
            return 0.0
        if score > 90:
            return 99.0
        return score

    def get_risk_level(self, score: float) -> str:
        if score < 15: return "Low"
        if score < 40: return "Medium"
        if score < 75: return "High"
        return "Critical"
