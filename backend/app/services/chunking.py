import spacy
from typing import List, Dict, Any

class ChunkingService:
    def __init__(self, model: str = "en_core_web_sm"):
        try:
            self.nlp = spacy.load(model)
        except OSError:
            # Fallback if model not downloaded during build
            import os
            os.system(f"python -m spacy download {model}")
            self.nlp = spacy.load(model)

    def segment_sentences(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into sentences with original offsets.
        """
        doc = self.nlp(text)
        sentences = []
        for sent in doc.sents:
            sentences.append({
                "text": sent.text,
                "start_char": sent.start_char,
                "end_char": sent.end_char
            })
        return sentences

    def create_rolling_chunks(self, text: str, window_size: int = 3, overlap: int = 1) -> List[Dict[str, Any]]:
        """
        Create overlapping chunks of N sentences for semantic retrieval.
        """
        sentences = self.segment_sentences(text)
        if not sentences:
            return []

        chunks = []
        for i in range(0, len(sentences), window_size - overlap):
            window = sentences[i : i + window_size]
            if not window:
                continue
                
            chunk_text = " ".join([s["text"] for s in window])
            chunks.append({
                "text": chunk_text,
                "start_char": window[0]["start_char"],
                "end_char": window[-1]["end_char"],
                "sentence_count": len(window)
            })
            
            # If we reached the end, stop
            if i + window_size >= len(sentences):
                break
                
        return chunks

    def paragraph_chunking(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text by double newlines (paragraphs) while preserving offsets.
        """
        paragraphs = []
        start = 0
        for p_text in text.split("\n\n"):
            if not p_text.strip():
                continue
            
            p_start = text.find(p_text, start)
            p_end = p_start + len(p_text)
            paragraphs.append({
                "text": p_text,
                "start_char": p_start,
                "end_char": p_end
            })
            start = p_end
            
        return paragraphs
