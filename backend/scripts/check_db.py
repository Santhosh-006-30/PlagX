import sqlite3

def check_db():
    conn = sqlite3.connect('plagx.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, title, status, word_count FROM documents")
        rows = cursor.fetchall()
        print("ID | Title | Status | Word Count")
        print("-" * 50)
        for row in rows:
            print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_db()
