import numpy as np
import torch
import faiss
from sentence_transformers import SentenceTransformer, CrossEncoder
from typing import List, Dict, Any, Tuple
from app.config import settings

class SemanticEngine:
    def __init__(self, 
                 bi_encoder_name: str = 'BAAI/bge-large-en-v1.5',
                 cross_encoder_name: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'):
        """
        bi_encoder: Used for fast retrieval (generating embeddings for FAISS).
        cross_encoder: Used for high-precision reranking of top-K results.
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.bi_encoder = SentenceTransformer(bi_encoder_name, device=self.device)
        self.cross_encoder = CrossEncoder(cross_encoder_name, device=self.device)
        
        self.dimension = self.bi_encoder.get_sentence_embedding_dimension()
        # IndexFlatIP for Cosine Similarity (vectors must be normalized)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []

    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        faiss.normalize_L2(vectors)
        return vectors

    def add_documents(self, documents: List[Dict[str, Any]]):
        """Batch adds multiple documents to the index."""
        all_segments = []
        all_metadata = []
        
        for doc in documents:
            text = doc["text"]
            doc_id = doc["id"]
            # Simple sentence splitting
            segments = [s.strip() for s in text.split('.') if len(s.strip()) > 20]
            for seg in segments:
                all_segments.append(seg)
                all_metadata.append({"doc_id": doc_id, "text": seg})
        
        if all_segments:
            embeddings = self.bi_encoder.encode(all_segments, normalize_embeddings=True)
            self.index.add(np.array(embeddings).astype('float32'))
            self.metadata.extend(all_metadata)

    def add_segments(self, doc_id: str, segments: List[str]):
        """Embeds and indexes segments for a document."""
        if not segments:
            return
            
        embeddings = self.bi_encoder.encode(segments, normalize_embeddings=True)
        self.index.add(np.array(embeddings).astype('float32'))
        
        for segment in segments:
            self.metadata.append({
                "doc_id": doc_id,
                "text": segment
            })

    def search(self, query_segments: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Hybrid Semantic Search:
        1. Retrieval: Find top-K candidates using Bi-Encoder + FAISS.
        2. Reranking: Use Cross-Encoder to score query against each candidate.
        """
        if not query_segments or self.index.ntotal == 0:
            return []

        # 1. Retrieval
        query_embeddings = self.bi_encoder.encode(query_segments, normalize_embeddings=True)
        D, I = self.index.search(np.array(query_embeddings).astype('float32'), top_k)
        
        results = []
        for i, (scores, indices) in enumerate(zip(D, I)):
            query_text = query_segments[i]
            candidates = []
            
            for score, idx in zip(scores, indices):
                if idx == -1: continue
                candidates.append(self.metadata[idx])
            
            if not candidates:
                continue

            # 2. Reranking with Cross-Encoder
            # Pairs: [[query, doc1], [query, doc2], ...]
            pairs = [[query_text, c["text"]] for c in candidates]
            cross_scores = self.cross_encoder.predict(pairs)
            
            # Find best candidate after reranking
            best_idx = np.argmax(cross_scores)
            best_score = float(torch.sigmoid(torch.tensor(cross_scores[best_idx])).item()) # Convert logit to probability
            
            if best_score > settings.SEMANTIC_THRESHOLD:
                results.append({
                    "query_text": query_text,
                    "match_text": candidates[best_idx]["text"],
                    "source_id": candidates[best_idx]["doc_id"],
                    "semantic_score": best_score,
                    "retrieval_score": float(scores[best_idx])
                })
                
        return results
