import torch
from typing import List, Dict, Any
from sentence_transformers import CrossEncoder

class RerankerService:
    def __init__(self, model_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        """
        Initialize the Cross-Encoder reranker.
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CrossEncoder(model_name, device=self.device)

    def rerank(self, query_text: str, candidates: List[Dict[str, Any]], top_k: int = 50) -> List[Dict[str, Any]]:
        """
        Rerank candidates using Cross-Encoder.
        Input: List of matches from initial retrieval.
        """
        if not candidates:
            return []

        # Prepare pairs for Cross-Encoder (query, source)
        pairs = []
        for cand in candidates:
            # We use the matched query segment and the matched source segment
            pairs.append([query_text, cand["source_text"]])

        # Batch reranking
        scores = self.model.predict(pairs, batch_size=32, show_progress_bar=False)

        # Update candidate scores and filter
        reranked = []
        for i, cand in enumerate(candidates):
            cand["rerank_score"] = float(scores[i])
            # Normalize score (CrossEncoder scores can vary)
            # Typically for MS MARCO, we might use sigmoid if we want 0-1
            cand["confidence"] = 1 / (1 + torch.exp(-torch.tensor(scores[i])).item())
            
            if cand["confidence"] > 0.5: # Threshold for high-quality semantic match
                reranked.append(cand)

        # Sort by confidence
        reranked.sort(key=lambda x: x["confidence"], reverse=True)
        return reranked[:top_k]
