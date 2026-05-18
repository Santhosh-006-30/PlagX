import asyncio
import os
import sys

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.fingerprinting import WinnowingEngine
from app.services.semantic import SemanticEngine
from app.services.ai_audit import AIAuditService

class PlagXBenchmark:
    """
    Validation suite for detection accuracy.
    """
    
    def __init__(self):
        self.winnowing = WinnowingEngine()
        self.semantic = SemanticEngine()
        self.ai = AIAuditService()

    async def run_suite(self):
        print("🚀 Starting PlagX Enterprise Benchmark Suite...")
        
        tests = [
            {"name": "Exact Match", "text1": "The quick brown fox jumps over the lazy dog.", "text2": "The quick brown fox jumps over the lazy dog.", "expected_sim": 1.0},
            {"name": "Paraphrase", "text1": "The quick brown fox jumps over the lazy dog.", "text2": "A rapid auburn canine leaps across a lethargic hound.", "expected_sim": 0.8},
            {"name": "AI Content", "text1": "A large language model is trained on diverse datasets to predict the next token in a sequence.", "is_ai": True}
        ]
        
        for test in tests:
            print(f"\nRunning: {test['name']}")
            
            if "text2" in test:
                # Similarity test
                fp1 = self.winnowing.get_fingerprints(test["text1"])
                fp2 = self.winnowing.get_fingerprints(test["text2"])
                exact_sim = self.winnowing.calculate_similarity(fp1, fp2)
                
                # Semantic
                self.semantic.add_documents([{"id": "ref", "text": test["text1"]}])
                sem_matches = self.semantic.search([test["text2"]])
                sem_sim = sem_matches[0]["semantic_score"] if sem_matches else 0
                
                print(f"  - Exact Score: {exact_sim:.2f}")
                print(f"  - Semantic Score: {sem_sim:.2f}")
                
            if test.get("is_ai"):
                res = await self.ai.analyze_text(test["text1"])
                print(f"  - AI Probability: {res['ai_probability']:.2f}%")

if __name__ == "__main__":
    benchmark = PlagXBenchmark()
    asyncio.run(benchmark.run_suite())
