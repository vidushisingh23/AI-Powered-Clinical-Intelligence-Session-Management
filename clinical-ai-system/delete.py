from db import get_db

db = get_db()
cur = db.cursor()

print("Tables in database:")

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(cur.fetchall())

print("\nDeleting session 3 records...\n")

try:
    cur.execute("DELETE FROM email_logs WHERE session_id = 17")
    cur.execute("DELETE FROM clinical_sessions WHERE session_id = 17")

    db.commit()
    print("Session 3 removed successfully!")

except Exception as e:
    print("Error:", e)

db.close()
