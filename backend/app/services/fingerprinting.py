import hashlib
import re
from typing import List, Set, Tuple

class WinnowingEngine:
    def __init__(self, k: int = 50, w: int = 4):
        """
        k: k-gram size (length of substrings to hash)
        w: window size (number of hashes in a window to pick the minimum from)
        """
        self.k = k
        self.w = w

    def _normalize(self, text: str) -> str:
        """Lowercase and remove all non-alphanumeric characters."""
        return re.sub(r'[^a-z0-9]', '', text.lower())

    def get_fingerprints(self, text: str) -> Set[Tuple[int, int]]:
        """
        Generates a set of (hash, offset) tuples.
        Returns only the 'winnowed' hashes as per the algorithm.
        """
        normalized = self._normalize(text)
        if len(normalized) < self.k:
            return set()

        # 1. Generate k-grams and their hashes
        hashes = []
        for i in range(len(normalized) - self.k + 1):
            kgram = normalized[i:i + self.k]
            # Use MD5 and convert to int for comparison
            h = int(hashlib.md5(kgram.encode()).hexdigest(), 16)
            hashes.append(h)

        # 2. Winnowing: sliding window of size w
        fingerprints = set()
        min_idx = -1
        
        for i in range(len(hashes) - self.w + 1):
            window = hashes[i:i + self.w]
            
            # Find the minimum hash in the window
            # If multiple equal mins, pick the rightmost one
            min_val = window[0]
            curr_min_idx = i
            for j in range(1, self.w):
                if window[j] <= min_val:
                    min_val = window[j]
                    curr_min_idx = i + j
            
            if curr_min_idx != min_idx:
                # Store (hash, approximate_offset)
                # Offset is approximate because we stripped characters
                fingerprints.add((min_val, curr_min_idx))
                min_idx = curr_min_idx
                
        return fingerprints

    def calculate_similarity(self, fingerprints1: Set[int], fingerprints2: Set[int]) -> float:
        """Jaccard similarity between two sets of fingerprint hashes."""
        if not fingerprints1 or not fingerprints2:
            return 0.0
        # Convert set of tuples to set of hashes
        f1 = {f[0] for f in fingerprints1}
        f2 = {f[0] for f in fingerprints2}
        intersection = f1.intersection(f2)
        union = f1.union(f2)
        return len(intersection) / len(union)

if __name__ == "__main__":
    engine = WinnowingEngine(k=20, w=4)
    text1 = "The quick brown fox jumps over the lazy dog near the river bank."
    text2 = "A quick brown fox jumped over a lazy dog near a river bank."
    
    fp1 = engine.get_fingerprints(text1)
    fp2 = engine.get_fingerprints(text2)
    
    sim = engine.calculate_similarity(fp1, fp2)
    print(f"Text 1 Fingerprints: {len(fp1)}")
    print(f"Text 2 Fingerprints: {len(fp2)}")
    print(f"Jaccard Similarity: {sim:.2%}")
