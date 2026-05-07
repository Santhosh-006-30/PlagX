import torch
import numpy as np
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from typing import List, Dict, Any, Tuple

class AIAnalysisService:
    def __init__(self, model_name: str = "gpt2"):
        """
        Initialize the AI analysis service using a language model for perplexity.
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = GPT2Tokenizer.from_pretrained(model_name)
        self.model = GPT2LMHeadModel.from_pretrained(model_name).to(self.device)
        self.model.eval()

    def analyze_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyzes each segment for perplexity, burstiness, and token entropy.
        """
        results = []
        metrics = []

        for seg in segments:
            text = seg["text"].strip()
            if len(text) < 15: # Ignore very short segments
                results.append({**seg, "ai_score": 0.0, "perplexity": 0.0, "entropy": 0.0})
                continue

            perplexity, entropy = self._calculate_metrics(text)
            metrics.append({"ppl": perplexity, "ent": entropy})
            results.append({**seg, "perplexity": perplexity, "entropy": entropy})

        if not metrics:
            return results

        # Calculate burstiness (variance of perplexity across the whole document)
        avg_ppl = np.mean([m["ppl"] for m in metrics])
        std_ppl = np.std([m["ppl"] for m in metrics])
        
        for res in results:
            if "perplexity" in res and res["perplexity"] > 0:
                ppl = res["perplexity"]
                ent = res["entropy"]
                
                # AI Likelihood Factors:
                # 1. Low Perplexity (Predictable text)
                # 2. Low Entropy (Model was very confident)
                # 3. Low Burstiness (Monotonous sentence structure)
                
                ppl_score = max(0, min(1, (80 - ppl) / 70))
                ent_score = max(0, min(1, (4.5 - ent) / 2.5))
                burstiness = abs(ppl - avg_ppl) / (std_ppl + 1e-6)
                burst_score = max(0, min(1, (1.5 - burstiness) / 1.5))
                
                # Weighted average for final AI score
                ai_score = (ppl_score * 0.4) + (ent_score * 0.4) + (burst_score * 0.2)
                
                res["ai_score"] = round(ai_score, 2)
                res["burstiness"] = round(burstiness, 2)
            else:
                res["ai_score"] = 0.0
                res["burstiness"] = 0.0

        return results

    def _calculate_metrics(self, text: str) -> Tuple[float, float]:
        """
        Calculates both perplexity and token entropy for a given text.
        """
        encodings = self.tokenizer(text, return_tensors="pt")
        input_ids = encodings.input_ids.to(self.device)
        
        if input_ids.size(1) <= 1:
            return 0.0, 0.0

        with torch.no_grad():
            outputs = self.model(input_ids, labels=input_ids)
            loss = outputs.loss
            logits = outputs.logits # Shape: [batch, sequence, vocab]
            
            # Calculate Entropy: -sum(p * log(p))
            probs = torch.softmax(logits, dim=-1)
            entropy = -torch.sum(probs * torch.log(probs + 1e-12), dim=-1).mean().item()
            
            perplexity = torch.exp(loss).item()

        return round(perplexity, 2), round(entropy, 2)

# Singleton instance
analysis_service = None

def get_ai_analysis_service():
    global analysis_service
    if analysis_service is None:
        analysis_service = AIAnalysisService()
    return analysis_service
