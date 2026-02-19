from db import get_db

OLD_URL = "https://apodictically-vitaminc-deja.ngrok-free.dev/webhook-test"
NEW_URL = "https://apodictically-vitaminic-deja.ngrok-free.dev/webhook-test"

db = get_db()
cur = db.cursor()

cur.execute("""
    UPDATE webhook_subscribers
    SET target_url = ?
    WHERE target_url = ?
""", (NEW_URL, OLD_URL))

db.commit()

print(f"✅ Updated {cur.rowcount} webhook subscriber(s)")

db.close()
