from db import get_db
from webhooks.webhook_sender import send_webhook

def dispatch_event(event_type, payload):
    print(f"\n🚀 dispatch_event called → {event_type}")

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT target_url, secret
        FROM webhook_subscribers
        WHERE event_type = ? AND active = 1
    """, (event_type,))

    subscribers = cur.fetchall()
    db.close()

    print(f"📡 Subscribers found: {len(subscribers)}")

    for url, secret in subscribers:
        print(f"➡️ Sending webhook to {url}")
        send_webhook(
            url=url,
            secret=secret,
            event_type=event_type,
            payload=payload
        )
