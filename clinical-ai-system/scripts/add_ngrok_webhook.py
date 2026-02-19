import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from db import get_db

db = get_db()
cur = db.cursor()

cur.execute("""
INSERT INTO webhook_subscribers (event_type, target_url, secret)
VALUES (?, ?, ?)
""", (
    "SESSION_CREATED",
    " https://apodictically-vitaminic-deja.ngrok-free.dev",  # 🔁 replace with YOUR ngrok URL
    "ngrok-test"
))

db.commit()
db.close()

print("✅ Ngrok test webhook subscriber added.")
