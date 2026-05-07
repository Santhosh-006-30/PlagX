import io
import zipfile
import xml.etree.ElementTree as ET

def test_fallback(file_path):
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            xml_content = z.read('word/document.xml')
        
        root = ET.fromstring(xml_content)
        namespaces = [
            {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'},
            {'w': 'http://purl.oclc.org/ooxml/wordprocessingml/main'}
        ]
        
        text_parts = []
        for ns in namespaces:
            for t in root.findall('.//w:t', ns):
                if t.text:
                    text_parts.append(t.text)
            if text_parts:
                break
        
        text = " ".join(text_parts).strip()
        print(f"Fallback Success! Extracted {len(text)} characters.")
        print("First 100 chars:", text[:100])
    except Exception as e:
        print(f"Fallback failed: {e}")

if __name__ == "__main__":
    test_fallback('uploads/2370d409-4826-44b3-8dc5-29b6a990076c.docx')
