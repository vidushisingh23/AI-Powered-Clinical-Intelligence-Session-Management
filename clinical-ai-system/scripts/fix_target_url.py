from db import get_db

db = get_db()
cur = db.cursor()

cur.execute("""
UPDATE webhook_subscribers
SET target_url = ?
""", ("https://apodictically-vitaminc-deja.ngrok-free.dev/webhook-test",))

db.commit()
db.close()

print("✅ target_url fixed")
