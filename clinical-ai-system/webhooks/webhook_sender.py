import requests
import json
import hmac
import hashlib
import time

def generate_signature(secret: str, payload: dict) -> str:
    """
    Generate HMAC SHA256 signature
    """
    message = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


def send_webhook(url, secret, event_type, payload):
    data = {
        "event": event_type,
        "timestamp": int(time.time()),
        "data": payload
    }

    signature = generate_signature(secret, data)

    headers = {
        "Content-Type": "application/json",
        "X-HopeQure-Signature": signature
    }

    try:
        response = requests.post(
            url,
            json=data,
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        print(f"✅ Webhook sent → status {response.status_code}")

    except Exception as e:
        print(f"❌ Webhook failed: {e}")
