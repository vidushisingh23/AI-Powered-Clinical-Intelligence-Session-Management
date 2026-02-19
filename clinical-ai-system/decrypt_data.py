from db import get_db
from crypto_utils import decrypt_text

db = get_db()
cur = db.cursor()

print("\n--- DECRYPTED CLINICAL SESSION SUMMARIES ---\n")
cur.execute("SELECT * FROM clinical_sessions")
rows = cur.fetchall()

for r in rows:
    print("Session Row:")
    print(decrypt_text(r["short_summary"]))
    print("-" * 50)

print("\n--- DECRYPTED EMAIL LOGS ---\n")
cur.execute("SELECT * FROM email_logs")
rows = cur.fetchall()

for r in rows:
    print("Email Log Row:")
    print(decrypt_text(r["email_body"]))
    print("-" * 50)

db.close()
