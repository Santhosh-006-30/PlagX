import re
from typing import List, Dict, Any

class CitationFilter:
    def __init__(self):
        # Patterns for common bibliography headers
        self.bib_headers = [
            r'^references$', r'^bibliography$', r'^works cited$', 
            r'^sources$', r'^references cited$'
        ]
        
        # Patterns for inline citations (APA, MLA)
        self.inline_patterns = [
            r'\(\w+ et al\., \d{4}\)',       # (Smith et al., 2020)
            r'\(\w+, \d{4}\)',               # (Smith, 2020)
            r'\[\d+\]',                       # [1], [12]
            r'\w+ \(\d{4}\)',                 # Smith (2020)
        ]
        
        # Pattern for quoted text
        self.quote_pattern = r'["\']{1}.*?["\']{1}'

    def detect_bibliography_section(self, text: str) -> int:
        """
        Detects where the bibliography section starts.
        Returns the character index of the start of the bibliography, or -1 if not found.
        """
        lines = text.split('\n')
        for i, line in enumerate(lines):
            clean_line = line.strip().lower()
            for pattern in self.bib_headers:
                if re.match(pattern, clean_line):
                    # Found it. Calculate character offset.
                    return text.find(line)
        return -1

    def get_excluded_ranges(self, text: str) -> List[Dict[str, int]]:
        """
        Finds ranges that should be excluded from plagiarism detection.
        """
        ranges = []
        
        # 1. Bibliography
        bib_start = self.detect_bibliography_section(text)
        if bib_start != -1:
            ranges.append({"start": bib_start, "end": len(text), "type": "bibliography"})
            
        # 2. Quotes
        for match in re.finditer(self.quote_pattern, text):
            ranges.append({"start": match.start(), "end": match.end(), "type": "quote"})
            
        # 3. Inline citations
        for pattern in self.inline_patterns:
            for match in re.finditer(pattern, text):
                ranges.append({"start": match.start(), "end": match.end(), "type": "citation"})
                
        return ranges

    def is_suppressed(self, start: int, end: int, excluded_ranges: List[Dict[str, int]]) -> bool:
        """
        Checks if a given match range falls within an excluded range.
        """
        for r in excluded_ranges:
            # If the match significantly overlaps with an excluded range
            overlap_start = max(start, r["start"])
            overlap_end = min(end, r["end"])
            
            if overlap_start < overlap_end:
                overlap_len = overlap_end - overlap_start
                match_len = end - start
                
                # If more than 50% of the match is inside an excluded range, suppress it
                if overlap_len / match_len > 0.5:
                    return True
        return False
