import zipfile

def list_zip(path):
    try:
        with zipfile.ZipFile(path, 'r') as z:
            print(f"Contents of {path}:")
            for name in z.namelist():
                print(f"  {name}")
    except Exception as e:
        print(f"Failed to open as ZIP: {e}")

if __name__ == "__main__":
    list_zip('uploads/2370d409-4826-44b3-8dc5-29b6a990076c.docx')
