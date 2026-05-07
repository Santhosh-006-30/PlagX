from transformers import pipeline
from typing import Dict

class AIDetector:
    def __init__(self, model_name: str = "Hello-SimpleAI/chatgpt-detector-roberta"):
        """
        Initialize the AI detection pipeline.
        """
        self.pipe = pipeline("text-classification", model=model_name)

    def detect(self, text: str) -> Dict[str, float]:
        """
        Detect the probability that the text was AI-generated.
        Samples multiple parts of the document for a more stable score.
        """
        if not text or len(text.strip()) < 50:
            return {"ai_probability": 0.0}

        # Model limit is usually 512 tokens (~1500-2000 chars)
        # We sample the beginning, middle, and end if the text is long
        segments = []
        text_len = len(text)
        
        if text_len <= 1500:
            segments.append(text)
        else:
            # Sample beginning
            segments.append(text[:1500])
            # Sample middle
            mid = text_len // 2
            segments.append(text[mid-750:mid+750])
            # Sample end
            segments.append(text[-1500:])
        
        try:
            scores = []
            for segment in segments:
                results = self.pipe(segment)
                
                ai_score = 0.0
                for res in results:
                    if res['label'] == 'ChatGPT' or res['label'] == 'AI':
                        ai_score = res['score']
                    elif res['label'] == 'Human':
                        ai_score = 1.0 - res['score']
                scores.append(ai_score)
            
            # Average the scores from different segments
            final_score = sum(scores) / len(scores)
            
            return {"ai_probability": round(final_score * 100, 2)}
        except Exception as e:
            print(f"AI Detection error: {e}")
            return {"ai_probability": 0.0}

# Singleton instance
detector = None

def get_ai_detector():
    global detector
    if detector is None:
        detector = AIDetector()
    return detector
