import sqlite3

def create_db():
    conn = sqlite3.connect("history.db")
    cursor = conn.cursor()
    
    # Create a table for storing the history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user_input TEXT,
            ai_response TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_db()
