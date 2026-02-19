from db import get_db

db = get_db()
cur = db.cursor()

cur.execute("""
UPDATE webhook_subscribers
SET event_type = ?
WHERE event_type = ?
""", ("session.created", "SESSION_CREATED"))

db.commit()
db.close()

print("✅ event_type fixed")
