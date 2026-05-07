import os
import numpy as np
import torch
import faiss
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer

from app.services.fingerprint_engine import FingerprintEngine
from app.services.chunking import ChunkingService
from app.services.citation_filter import CitationFilter

# Limit threads to reduce process footprint
torch.set_num_threads(1)

class PlagiarismEngine:
    def __init__(self, model_name: str = 'BAAI/bge-large-en-v1.5'):
        """
        Initialize the enterprise-grade plagiarism detection engine.
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(model_name, device=self.device)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        # Using IndexFlatIP for cosine similarity (with normalized vectors)
        self.index = faiss.IndexFlatIP(self.dimension)
        
        # Mapping from vector index to metadata
        self.metadata = []
        
        # Helper services
        self.fingerprint_engine = FingerprintEngine(k_gram=5, window_size=4)
        self.chunker = ChunkingService()
        self.citation_filter = CitationFilter()
        
        # In-memory storage for fingerprints (In production, move to Postgres/Redis)
        self.fingerprint_db = {} # hash -> list of {doc_id, start_char, end_char}

    def clear_index(self):
        """Reset the index and metadata."""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []
        self.fingerprint_db = {}

    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """Normalize vectors for cosine similarity calculation."""
        faiss.normalize_L2(vectors)
        return vectors

    def add_document(self, doc_id: str, text: str, category: str = "internet"):
        """
        Adds a document to the index using both embeddings and fingerprints.
        """
        if not text:
            return

        # 1. Generate and store fingerprints (Exact Match)
        fingerprints = self.fingerprint_engine.winnow(text)
        for f in fingerprints:
            f_hash = f["hash"]
            if f_hash not in self.fingerprint_db:
                self.fingerprint_db[f_hash] = []
            self.fingerprint_db[f_hash].append({
                "doc_id": doc_id,
                "start": f["start_char"],
                "end": f["end_char"]
            })

        # 2. Generate and store embeddings (Semantic Match)
        # Using rolling window chunks for better semantic context
        chunks = self.chunker.create_rolling_chunks(text)
        if not chunks:
            return

        chunk_texts = [c["text"] for c in chunks]
        embeddings = self.model.encode(chunk_texts, batch_size=32, show_progress_bar=False)
        normalized_embeddings = self._normalize_vectors(np.array(embeddings).astype('float32'))

        self.index.add(normalized_embeddings)
        
        for i, chunk in enumerate(chunks):
            self.metadata.append({
                "doc_id": doc_id,
                "text": chunk["text"],
                "start": chunk["start_char"],
                "end": chunk["end_char"],
                "category": category
            })

    def analyze_text(self, query_text: str, exclude_doc_id: str = None) -> Dict[str, Any]:
        """
        Hybrid retrieval combining lexical fingerprints and semantic embeddings.
        """
        if not query_text:
            return {"matches": []}

        # --- Phase 1: Exact Match (Winnowing) ---
        query_fingerprints = self.fingerprint_engine.winnow(query_text)
        exact_matches = []
        
        for f in query_fingerprints:
            f_hash = f["hash"]
            if f_hash in self.fingerprint_db:
                for hit in self.fingerprint_db[f_hash]:
                    if exclude_doc_id and str(hit["doc_id"]) == str(exclude_doc_id):
                        continue
                        
                    exact_matches.append({
                        "query_start": f["start_char"],
                        "query_end": f["end_char"],
                        "source_id": hit["doc_id"],
                        "source_start": hit["start"],
                        "source_end": hit["end"],
                        "match_type": "exact",
                        "score": 1.0
                    })

        # --- Phase 2: Semantic Match (Embeddings) ---
        query_chunks = self.chunker.create_rolling_chunks(query_text)
        semantic_matches = []
        
        if query_chunks and self.index.ntotal > 0:
            chunk_texts = [c["text"] for c in query_chunks]
            query_embeddings = self.model.encode(chunk_texts, batch_size=32, show_progress_bar=False)
            normalized_queries = self._normalize_vectors(np.array(query_embeddings).astype('float32'))

            # Search top 10 candidates per chunk
            D, I = self.index.search(normalized_queries, 10)

            for i, (scores, indices) in enumerate(zip(D, I)):
                q_chunk = query_chunks[i]
                for score, idx in zip(scores, indices):
                    if idx == -1: continue
                    source_meta = self.metadata[idx]
                    
                    if exclude_doc_id and str(source_meta["doc_id"]) == str(exclude_doc_id):
                        continue
                        
                    if score > 0.7: # Initial semantic threshold
                        semantic_matches.append({
                            "query_start": q_chunk["start_char"],
                            "query_end": q_chunk["end_char"],
                            "query_text": q_chunk["text"],
                            "source_id": source_meta["doc_id"],
                            "source_text": source_meta["text"],
                            "source_start": source_meta["start"],
                            "source_end": source_meta["end"],
                            "match_type": "semantic",
                            "score": float(score)
                        })

        return {
            "exact_matches": exact_matches,
            "semantic_matches": semantic_matches,
            "excluded_ranges": self.citation_filter.get_excluded_ranges(query_text)
        }

# Singleton instance
engine = None

def get_plagiarism_engine():
    global engine
    if engine is None:
        engine = PlagiarismEngine()
    return engine
