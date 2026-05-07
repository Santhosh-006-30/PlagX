import os
import re
import math
import numpy as np
import torch
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Tuple

# Limit threads to reduce process footprint
torch.set_num_threads(1)

class PlagiarismEngine:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the plagiarism detection engine.
        """
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        # Using IndexFlatIP for cosine similarity (with normalized vectors)
        self.index = faiss.IndexFlatIP(self.dimension)
        
        # Mapping from vector index to metadata (document id, text segment)
        self.metadata = []

    def clear_index(self):
        """Reset the index and metadata."""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []

    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """Normalize vectors for cosine similarity calculation."""
        faiss.normalize_L2(vectors)
        return vectors

    def split_text(self, text: str) -> List[str]:
        """
        Split text into individual sentences for granular matching.
        Preserves original formatting as much as possible for highlighting.
        """
        import re
        # Split by sentence endings but keep the punctuation and following whitespace
        # This regex matches sentence endings and captures them
        sentences = re.split(r'([.!?](?:\s+|$))', text)
        
        # Re-join the sentences with their punctuation
        results = []
        for i in range(0, len(sentences)-1, 2):
            s = sentences[i] + sentences[i+1]
            if len(s.strip()) > 10:
                results.append(s)
        
        # Add the last segment if it didn't end with a punctuation
        if len(sentences) % 2 == 1:
            last = sentences[-1]
            if len(last.strip()) > 10:
                results.append(last)
                
        return results

    def _generate_ngrams(self, text: str, n: int = 7) -> set:
        """Generate a set of n-gram hashes for exact matching."""
        import hashlib
        text = text.lower().replace('.', '').replace(',', '').split()
        if len(text) < n:
            return set()
        
        ngrams = []
        for i in range(len(text) - n + 1):
            gram = " ".join(text[i:i+n])
            ngrams.append(hashlib.md5(gram.encode()).hexdigest())
        return set(ngrams)

    def add_document(self, doc_id: str, text: str, category: str = "internet"):
        """
        Adds a document with Content Fingerprinting to prevent source inflation.
        """
        import hashlib
        import numpy as np
        content_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Check if content already exists to merge sources
        for meta in self.metadata:
            if meta.get("content_hash") == content_hash:
                return # Skip duplicate content
                
        sentences = self.split_text(text)
        if not sentences:
            return

        embeddings = self.model.encode(sentences)
        normalized_embeddings = self._normalize_vectors(np.array(embeddings).astype('float32'))

        self.index.add(normalized_embeddings)
        
        for sentence in sentences:
            self.metadata.append({
                "doc_id": doc_id,
                "text": sentence,
                "category": category,
                "ngrams": self._generate_ngrams(sentence),
                "content_hash": content_hash
            })

    # Common Academic Phrases to exclude from similarity scoring
    STOP_PHRASES = [
        "this paper proposes", "in this study", "experimental results", "the results show",
        "in conclusion", "it is observed that", "furthermore", "moreover", "consequently",
        "according to", "based on", "the study suggests", "previous research has",
        "the purpose of this", "as shown in figure", "with respect to", "it is important to note",
        "in terms of", "due to the fact that", "in order to", "as a result of"
    ]

    def _calculate_citation_credit(self, text: str, full_text: str, start_idx: int, is_exact: bool = False) -> Dict[str, Any]:
        """
        Hardened Asymmetric Citation Model with Credit Capping.
        Even with perfect proximity, Verbatim matches w/o quotes are capped at 80%.
        """
        import re
        import math
        has_quotes = bool(re.search(r'["\u201c\u201d].*?["\u201c\u201d]', text))
        
        citations = list(re.finditer(r'\(\w+,\s*\d{4}\)|\[\d+\]|\w+\s*\(\d{4}\)', full_text))
        
        best_credit = 0.0
        for cite in citations:
            # Distance from END of match to START of citation (Citation follows match)
            dist_back = cite.start() - (start_idx + len(text))
            # Distance from START of match to END of citation (Citation precedes match)
            dist_forward = start_idx - cite.end()
            
            if dist_back >= 0:
                credit = math.exp(-(dist_back**2) / (2 * 75**2))
            elif dist_forward >= 0:
                credit = math.exp(-(dist_forward**2) / (2 * 25**2))
            else:
                credit = 1.0
            best_credit = max(best_credit, credit)
        
        # ANTI-SHIELDING: Cap credit for exact matches without quotes
        if is_exact and not has_quotes:
            best_credit = min(0.80, best_credit)
        
        return {
            "has_quotes": has_quotes,
            "citation_credit": round(best_credit, 2)
        }

    def _calculate_novelty_score(self, text: str) -> float:
        """
        Distinguishes between Common Technical Knowledge and Plagiarism.
        Standard patterns receive a lower score (Novelty Penalty).
        """
        ck_patterns = [
            r'the rate of change', r'according to the second law',
            r'in a vacuum', r'data was normalized using',
            r'the significance level was set at', r'the results indicate that',
            r'consistent with previous studies', r'for the purpose of this analysis'
        ]
        text_lower = text.lower()
        matches = [1 for p in ck_patterns if re.search(p, text_lower)]
        
        # Base novelty: 1.0. Penalty reduced to 0.4 per pattern (multiplier 0.6), floor at 0.5
        return max(0.5, 1.0 - (len(matches) * 0.4))

    def _get_dynamic_threshold(self, sentence: str) -> float:
        """
        Calibrated thresholds for idea-level reuse.
        """
        length = len(sentence.split())
        if length < 8: return 0.20  # Lowered from 0.30
        if length > 30: return 0.10 # Lowered from 0.15
        return 0.15 # Lowered from 0.20

    def _detect_section(self, full_text: str, current_pos: int) -> str:
        """Heuristic to detect if we are in Introduction, Methodology, or Results."""
        sections = [
            (r'Methodology|Methods|Experimental|Implementation', 'methodology', 1.5),
            (r'Results|Discussion|Evaluation', 'results', 1.3),
            (r'Introduction|Background|Abstract', 'introduction', 1.0)
        ]
        
        # Look backwards from current_pos for the last header
        text_before = full_text[:current_pos].lower()
        last_found = 'introduction'
        last_pos = -1
        
        for pattern, name, weight in sections:
            match = list(re.finditer(pattern.lower(), text_before))
            if match and match[-1].start() > last_pos:
                last_pos = match[-1].start()
                last_found = name
        
        return last_found

    def _get_source_weight(self, source_id: str) -> float:
        """Assign weight based on source credibility (simulated for now)."""
        if ".edu" in source_id or ".gov" in source_id:
            return 1.2 # Higher weight for academic/official sources
        if ".org" in source_id or "journal" in source_id.lower():
            return 1.1
        return 1.0

    def _strip_bibliography(self, text: str) -> str:
        """Removes the bibliography/references section from analysis."""
        import re
        # Common bibliography headers
        headers = [
            r'\nReferences\b', r'\nBibliography\b', r'\nWorks Cited\b', 
            r'\nLITERATURE CITED\b', r'\nREFERENCES\b'
        ]
        for pattern in headers:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return text[:match.start()]
        return text

    def _is_stop_phrase(self, text: str) -> bool:
        """Checks if the sentence is primarily a common academic stop-phrase."""
        clean_text = text.lower().strip()
        return any(phrase in clean_text for phrase in self.STOP_PHRASES)

    def analyze_text(self, query_text: str, threshold: float = 0.35, exclude_doc_id: str = None) -> Dict[str, Any]:
        """
        Production-Grade Asymmetric Audit with Precision Hardening.
        """
        analyzable_text = self._strip_bibliography(query_text)
        query_sentences = self.split_text(analyzable_text)
        
        if not query_sentences or self.index.ntotal == 0:
            return {"similarity": 0, "matches": [], "source_breakdown": {}, "match_groups": {}}

        query_embeddings = self.model.encode(query_sentences)
        normalized_queries = self._normalize_vectors(np.array(query_embeddings).astype('float32'))

        D, I = self.index.search(normalized_queries, 10) 

        matches = []
        categories = {"internet": 0, "publications": 0, "student_papers": 0, "local": 0}
        match_types = {"not_cited": 0, "missing_quotes": 0, "missing_citation": 0}

        for i, (scores, indices) in enumerate(zip(D, I)):
            sentence_text = query_sentences[i]
            dynamic_threshold = self._get_dynamic_threshold(sentence_text)
            
            is_stop = self._is_stop_phrase(sentence_text)
            phrase_weight = 0.6 if is_stop else 1.0 # Multiplier 0.6 instead of zeroing out
            novelty_score = self._calculate_novelty_score(sentence_text)

            query_ngrams = self._generate_ngrams(sentence_text)
            start_pos = query_text.find(sentence_text)
            
            best_match = None
            max_weighted_sim = 0
            
            for score, idx in zip(scores, indices):
                if idx == -1: continue
                source_data = self.metadata[idx]
                if exclude_doc_id and str(source_data["doc_id"]) == str(exclude_doc_id):
                    continue
                
                intersect = query_ngrams.intersection(source_data["ngrams"])
                ngram_overlap = (len(intersect) / len(query_ngrams)) if query_ngrams else 0
                semantic_sim = float(score)
                
                cred_weight = self._get_source_weight(str(source_data["doc_id"]))
                weighted_sim = ((semantic_sim * 0.6) + (ngram_overlap * 0.4)) * \
                              cred_weight * phrase_weight * novelty_score
                
                if weighted_sim > dynamic_threshold:
                    if weighted_sim > max_weighted_sim:
                        max_weighted_sim = weighted_sim
                        is_exact = ngram_overlap > 0.4 or semantic_sim > 0.9
                        cite_status = self._calculate_citation_credit(sentence_text, query_text, start_pos, is_exact)
                        
                        best_match = {
                            "text": sentence_text,
                            "source": source_data["doc_id"],
                            "similarity": round(min(100.0, weighted_sim * 100), 2),
                            "match_type": "exact" if is_exact else "paraphrased",
                            "category": source_data["category"],
                            "citation_credit": cite_status["citation_credit"],
                            "section": self._detect_section(query_text, start_pos),
                            "novelty_score": novelty_score,
                            "has_quotes": cite_status["has_quotes"]
                        }

            if best_match:
                # Hardened Classification Logic
                if best_match["citation_credit"] < 0.15 and not best_match["has_quotes"]:
                    best_match["classification"] = "not_cited"
                elif best_match["match_type"] == "exact" and not best_match["has_quotes"]:
                    # Exact match + no quotes = missing_quotes even if credit is high
                    best_match["classification"] = "missing_quotes"
                elif best_match["citation_credit"] < 0.45:
                    best_match["classification"] = "missing_citation"
                else:
                    best_match["classification"] = "properly_cited"

                matches.append(best_match)
                categories[best_match["category"]] += 1
                if best_match["classification"] != "properly_cited":
                    match_types[best_match["classification"]] += 1

        return {
            "matches": matches,
            "source_breakdown": categories,
            "match_groups": match_types,
            "analyzed_length": len(analyzable_text)
        }

# Global singleton instance
engine = None

def get_plagiarism_engine():
    global engine
    if engine is None:
        engine = PlagiarismEngine()
    return engine

if __name__ == "__main__":
    # --- Demonstration / Runnable Module ---
    print("Initializing Plagiarism Engine...")
    engine = PlagiarismEngine()

    # Sample "database" of documents
    source_docs = {
        "doc_1": "FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints.",
        "doc_2": "Artificial Intelligence is transforming the world. Machine learning models like Transformers are used for natural language processing.",
        "doc_3": "Sentence-BERT (SBERT) is a modification of the pretrained BERT network that use siamese and triplet network structures to derive semantically meaningful sentence embeddings."
    }

    print("\nIndexing source documents...")
    for doc_id, content in source_docs.items():
        engine.add_document(doc_id, content)
    
    print(f"Index size: {engine.index.ntotal} vectors.")

    # Test Query
    test_query = "FastAPI is a very fast web framework for building APIs using Python 3.7+. It uses type hints. Also, BERT models are great for NLP."
    
    print(f"\nAnalyzing Query: '{test_query}'")
    report = engine.analyze_text(test_query)

    print(f"\nOVERALL SIMILARITY: {report['similarity_score']}%")
    print("\nMATCHES FOUND:")
    for m in report['matches']:
        print(f"- Match ({m['similarity']}%): '{m['query_segment'][:50]}...'")
        print(f"  Source: {m['source_doc_id']}")
