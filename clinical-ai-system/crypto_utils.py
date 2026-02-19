import os
from dotenv import load_dotenv
from base64 import b64encode, b64decode
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


load_dotenv()

KEY = os.getenv("AES_SECRET_KEY")
if not KEY:
    raise Exception("AES_SECRET_KEY missing in .env")

KEY = KEY.encode()[:32].ljust(32, b"\0")


def encrypt_text(text: str) -> str:
    aes = AESGCM(KEY)
    nonce = os.urandom(12)
    cipher = aes.encrypt(nonce, text.encode(), None)
    return b64encode(nonce + cipher).decode()


def decrypt_text(cipher_text: str) -> str:
    try:
        raw = b64decode(cipher_text)
        nonce = raw[:12]
        ct = raw[12:]
        aes = AESGCM(KEY)
        return aes.decrypt(nonce, ct, None).decode()
    except Exception:
        return "<< Not encrypted or corrupted data >>"

