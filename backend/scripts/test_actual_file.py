import docx
import os

def test_actual_file():
    file_path = "uploads/2370d409-4826-44b3-8dc5-29b6a990076c.docx"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    
    try:
        import io
        with open(file_path, "rb") as f:
            content = f.read()
        doc = docx.Document(io.BytesIO(content))
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        print(f"Success! Extracted {len(text)} characters.")
        print("First 100 chars:", text[:100])
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Failed to extract: {e}")

if __name__ == "__main__":
    test_actual_file()
