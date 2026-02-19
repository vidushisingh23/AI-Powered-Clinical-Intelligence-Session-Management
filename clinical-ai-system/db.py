import sqlite3

DB_NAME = "clinic.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row   # ⭐ THIS FIXES EVERYTHING
    return conn
