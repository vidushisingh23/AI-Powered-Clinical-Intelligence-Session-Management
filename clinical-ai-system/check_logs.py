from db import get_db
from crypto_utils import decrypt_text

db = get_db()
cur = db.cursor()

print("\n--- FIXING CORRUPTED recipient_type DATA ---\n")

cur.execute("SELECT log_id, recipient_type FROM email_logs")
rows = cur.fetchall()

fixed = 0

for log_id, recipient in rows:
    if recipient not in ("LOW", "MEDIUM", "HIGH"):
        print(f"Fixing log_id={log_id} | corrupted value detected")

        text = recipient.lower()

        if "high" in text or "suicid" in text or "self harm" in text:
            new = "HIGH"
        elif "moderate" in text or "medium" in text:
            new = "MEDIUM"
        else:
            new = "LOW"

        cur.execute(
            "UPDATE email_logs SET recipient_type=? WHERE log_id=?",
            (new, log_id)
        )
        fixed += 1

db.commit()
db.close()

print(f"\n✔ Repair completed. Total rows fixed: {fixed}\n")

