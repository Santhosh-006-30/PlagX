import zipfile
import xml.etree.ElementTree as ET

def debug_xml(path):
    try:
        with zipfile.ZipFile(path, 'r') as z:
            xml_content = z.read('word/document.xml')
        
        root = ET.fromstring(xml_content)
        print(f"Root tag: {root.tag}")
        
        tags = set()
        for elem in root.iter():
            tags.add(elem.tag)
        
        print("Unique tags found:")
        for tag in sorted(list(tags)):
            print(f"  {tag}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_xml('uploads/2370d409-4826-44b3-8dc5-29b6a990076c.docx')
