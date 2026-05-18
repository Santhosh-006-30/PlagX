import spacy
import nltk
import textstat
import numpy as np
from typing import Dict, Any, List

# Ensure models are loaded
try:
    nlp = spacy.load("en_core_web_sm")
except:
    import os
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

class StylometryEngine:
    """
    Analyzes writing style for consistency and potential AI generation.
    """
    def __init__(self):
        self.nltk_data = ["punkt", "averaged_perceptron_tagger"]
        for data in self.nltk_data:
            try:
                nltk.data.find(f"tokenizers/{data}" if "punkt" in data else f"taggers/{data}")
            except LookupError:
                nltk.download(data)

    def analyze_document(self, text: str) -> Dict[str, Any]:
        doc = nlp(text)
        sentences = list(doc.sents)
        
        if not sentences:
            return {}

        # 1. Sentence Length Variance
        sent_lengths = [len(sent) for sent in sentences]
        sent_length_var = float(np.std(sent_lengths))
        
        # 2. Lexical Richness (Type-Token Ratio)
        words = [token.text.lower() for token in doc if token.is_alpha]
        lexical_richness = len(set(words)) / len(words) if words else 0
        
        # 3. Readability Metrics
        readability = textstat.flesch_reading_ease(text)
        
        # 4. Passive Voice Usage
        passive_count = 0
        for token in doc:
            if token.dep_ == "nsubjpass":
                passive_count += 1
        passive_voice_ratio = passive_count / len(sentences) if sentences else 0
        
        # 5. Punctuation Entropy
        puncs = [token.text for token in doc if token.is_punct]
        punc_dist = nltk.FreqDist(puncs)
        punc_entropy = float(self._calculate_entropy(list(punc_dist.values())))
        
        return {
            "sentence_length_var": round(sent_length_var, 2),
            "lexical_richness": round(lexical_richness, 3),
            "punctuation_entropy": round(punc_entropy, 3),
            "readability_score": round(readability, 2),
            "passive_voice_ratio": round(passive_voice_ratio, 3)
        }

    def _calculate_entropy(self, counts: List[int]) -> float:
        if not counts:
            return 0.0
        total = sum(counts)
        probs = [c / total for c in counts]
        return -sum(p * np.log2(p) for p in probs if p > 0)
