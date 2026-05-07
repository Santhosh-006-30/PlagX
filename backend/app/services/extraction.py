"""
Service for extracting text from various file formats.
"""
import io
import docx
import pypdf
import re
from typing import List, Dict, Any, Tuple

class ExtractionService:
    @staticmethod
    async def extract_text_with_metadata(content: bytes, file_type: str) -> Dict[str, Any]:
        """
        Extracts text and maintains a map of segments with character indices.
        """
        print(f"DEBUG: Extracting text from {file_type}...")
        if file_type == "txt":
            text = content.decode("utf-8")
            return {
                "full_text": text,
                "segments": ExtractionService._segment_text(text)
            }
        elif file_type == "pdf":
            return ExtractionService._extract_pdf_with_metadata(content)
        elif file_type == "docx":
            text = ExtractionService._extract_docx(content)
            print(f"DEBUG: Extracted {len(text)} characters from DOCX")
            return {
                "full_text": text,
                "segments": ExtractionService._segment_text(text)
            }
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    @staticmethod
    def _segment_text(text: str, page: int = 1) -> List[Dict[str, Any]]:
        """
        Splits text into sentences and returns their indices.
        """
        segments = []
        # Split by sentence endings but preserve them
        sentence_matches = re.finditer(r'([^.!?]+[.!?]?(?:\s+|$))', text)
        
        for match in sentence_matches:
            segment_text = match.group(0)
            if len(segment_text.strip()) > 5: # Ignore very short noise
                segments.append({
                    "text": segment_text,
                    "start_index": match.start(),
                    "end_index": match.end(),
                    "page": page
                })
        print(f"DEBUG: Segmented text into {len(segments)} segments")
        return segments

    @staticmethod
    def _extract_pdf_with_metadata(content: bytes) -> Dict[str, Any]:
        try:
            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
            full_text = ""
            all_segments = []
            current_offset = 0
            
            for i, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text() or ""
                if page_text:
                    full_text += page_text + "\n"
                    page_segments = ExtractionService._segment_text(page_text, page=i+1)
                    
                    # Adjust indices for global offset
                    for seg in page_segments:
                        seg["start_index"] += current_offset
                        seg["end_index"] += current_offset
                        all_segments.append(seg)
                    
                    current_offset += len(page_text) + 1 # +1 for the newline
            
            print(f"DEBUG: Extracted {len(full_text)} characters from PDF")
            return {
                "full_text": full_text.strip(),
                "segments": all_segments
            }
        except Exception as e:
            print(f"DEBUG: PDF Extraction failed: {e}")
            return {"full_text": "", "segments": []}

    @staticmethod
    def _extract_docx(content: bytes) -> str:
        try:
            doc = docx.Document(io.BytesIO(content))
            text = "\n".join([para.text for para in doc.paragraphs]).strip()
            if text: return text
            raise ValueError("No text found in paragraphs")
        except Exception as e:
            print(f"DEBUG: Primary DOCX extraction failed: {e}. Trying Deep Scan fallback...")
            import zipfile
            import xml.etree.ElementTree as ET
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    # Try to find the document XML in common locations
                    xml_path = None
                    for path in ['word/document.xml', 'word/document2.xml', 'document.xml']:
                        if path in z.namelist():
                            xml_path = path
                            break
                    
                    if not xml_path:
                        print(f"DEBUG: Could not find document XML in: {z.namelist()[:5]}...")
                        return ""

                    xml_content = z.read(xml_path)
                    root = ET.fromstring(xml_content)
                    
                    # Extract all text nodes
                    text_parts = []
                    for node in root.iter():
                        if node.tag.endswith('}t') or node.tag == 't':
                            if node.text:
                                text_parts.append(node.text)
                    
                    text = "".join(text_parts).strip()
                    print(f"DEBUG: Deep Scan extracted {len(text)} characters")
                    return text
            except Exception as e2:
                print(f"DEBUG: Deep Scan extraction failed: {e2}")
                return ""

    @staticmethod
    async def extract_text(content: bytes, file_type: str) -> str:
        res = await ExtractionService.extract_text_with_metadata(content, file_type)
        return res["full_text"]
