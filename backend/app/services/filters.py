import re
from typing import List, Tuple

class AcademicFilter:
    """
    Suppresses common academic phrases, bibliography, and cited material.
    """
    def __init__(self):
        # Common bibliography headers
        self.bib_headers = [
            r'\nReferences\b', r'\nBibliography\b', r'\nWorks Cited\b', 
            r'\nLITERATURE CITED\b', r'\nREFERENCES\b'
        ]
        
        # Academic common phrases (Low originality weight)
        self.common_phrases = [
            r'this study aims to', r'further research is needed',
            r'as shown in figure', r'the results indicate that',
            r'consistent with previous studies', r'it is important to note that',
            r'with respect to', r'in terms of', r'due to the fact that'
        ]
        
        # Citation patterns (APA, MLA, IEEE)
        self.citation_patterns = [
            r'\(\w+,\s*\d{4}\)',        # (Smith, 2020)
            r'\[\d+\]',                 # [1]
            r'\w+\s*\(\d{4}\)',          # Smith (2020)
            r'et al\.',                  # et al.
        ]

    def strip_bibliography(self, text: str) -> str:
        """Removes the bibliography section."""
        for pattern in self.bib_headers:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return text[:match.start()]
        return text

    def get_citation_spans(self, text: str) -> List[Tuple[int, int]]:
        """Returns character spans of detected citations."""
        spans = []
        for pattern in self.citation_patterns:
            for match in re.finditer(pattern, text):
                spans.append(match.span())
        return sorted(spans)

    def is_common_phrase(self, text: str) -> bool:
        """Checks if a segment is a known common phrase."""
        text_lower = text.lower().strip()
        for pattern in self.common_phrases:
            if re.search(pattern, text_lower):
                return True
        return False

    def get_quoted_spans(self, text: str) -> List[Tuple[int, int]]:
        """Finds quoted material."""
        spans = []
        # Support various quote marks
        for match in re.finditer(r'["\u201c\u201d\u0022].*?["\u201c\u201d\u0022]', text, re.DOTALL):
            spans.append(match.span())
        return spans
