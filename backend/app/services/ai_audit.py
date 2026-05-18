import torch
import numpy as np
import re
from transformers import GPT2LMHeadModel, GPT2Tokenizer, pipeline
from typing import List, Dict, Any, Tuple

# Limit threads to reduce process footprint
torch.set_num_threads(1)

class AIAuditService:
    def __init__(self, gpt_model: str = "gpt2", cls_model: str = "Hello-SimpleAI/chatgpt-detector-roberta"):
        """
        Unified AI Audit Service combining Perplexity (GPT-2) and Classification (RoBERTa).
        """
        self.device = 0 if torch.cuda.is_available() else -1
        self.torch_device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Perplexity Model (GPT-2)
        self.tokenizer = GPT2Tokenizer.from_pretrained(gpt_model)
        self.model = GPT2LMHeadModel.from_pretrained(gpt_model).to(self.torch_device)
        self.model.eval()
        
        # Classifier Model (RoBERTa)
        self.classifier = pipeline("text-classification", model=cls_model, device=self.device)

    async def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Full document AI analysis using an ensemble approach.
        """
        if not text or len(text.strip()) < 50:
            return {"ai_score": 0.0, "details": "Text too short"}

        # 1. Classification Score (RoBERTa)
        cls_result = self._detect_classification(text)
        
        # 2. Perplexity/Entropy Metrics (GPT-2)
        # Split into sentences for depth
        sentences = [s.strip() for s in re.split(r'[.!?]\s+', text) if len(s.strip()) > 30]
        
        if not sentences:
            return {"ai_score": cls_result, "ai_probability": cls_result}

        # Sample up to 10 sentences for balanced speed/accuracy
        sample_size = min(10, len(sentences))
        sample_indices = np.linspace(0, len(sentences)-1, sample_size, dtype=int)
        
        metrics = []
        for i in sample_indices:
            ppl, ent = self._calculate_metrics(sentences[i])
            metrics.append({"ppl": ppl, "ent": ent})

        avg_ppl = np.mean([m["ppl"] for m in metrics])
        avg_ent = np.mean([m["ent"] for m in metrics])
        std_ppl = np.std([m["ppl"] for m in metrics]) # Burstiness
        
        # AI Likelihood from Perplexity Factors
        # Low Perplexity (< 40) and Low Entropy (< 3.5) indicate AI
        ppl_score = max(0, min(100, ((80 - avg_ppl) / 60) * 100))
        ent_score = max(0, min(100, ((4.5 - avg_ent) / 2.0) * 100))
        
        # Ensemble Score: 70% Classifier, 30% Statistical Metrics
        stat_score = (ppl_score * 0.5) + (ent_score * 0.5)
        ensemble_score = (cls_result * 0.7) + (stat_score * 0.3)
        
        return {
            "ai_score": round(ensemble_score, 2),
            "ai_probability": round(cls_result, 2),
            "perplexity": round(avg_ppl, 2),
            "entropy": round(avg_ent, 2),
            "burstiness": round(std_ppl, 2)
        }

    def _detect_classification(self, text: str) -> float:
        """Samples the document for classification."""
        text_len = len(text)
        segments = []
        if text_len <= 1200:
            segments.append(text)
        else:
            segments.append(text[:1200])
            mid = text_len // 2
            segments.append(text[mid-600:mid+600])
            segments.append(text[-1200:])
        
        scores = []
        for segment in segments:
            results = self.classifier(segment, truncation=True, max_length=512)
            ai_score = 0.0
            for res in results:
                if res['label'] in ['ChatGPT', 'AI']:
                    ai_score = res['score']
                elif res['label'] == 'Human':
                    ai_score = 1.0 - res['score']
            scores.append(ai_score)
        
        return (sum(scores) / len(scores)) * 100

    def _calculate_metrics(self, text: str) -> Tuple[float, float]:
        """Calculates GPT-2 metrics."""
        encodings = self.tokenizer(text, return_tensors="pt")
        input_ids = encodings.input_ids.to(self.torch_device)
        
        if input_ids.size(1) <= 1:
            return 0.0, 0.0

        with torch.no_grad():
            outputs = self.model(input_ids, labels=input_ids)
            loss = outputs.loss
            logits = outputs.logits
            
            probs = torch.softmax(logits, dim=-1)
            entropy = -torch.sum(probs * torch.log(probs + 1e-12), dim=-1).mean().item()
            perplexity = torch.exp(loss).item()

        return perplexity, entropy

# Singleton
_audit_service = None

def get_ai_audit_service():
    global _audit_service
    if _audit_service is None:
        _audit_service = AIAuditService()
    return _audit_service
