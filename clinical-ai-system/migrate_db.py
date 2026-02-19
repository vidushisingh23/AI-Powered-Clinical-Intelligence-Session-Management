from db import get_db

db = get_db()
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS webhook_subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    target_url TEXT NOT NULL,
    secret TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

db.commit()
db.close()
