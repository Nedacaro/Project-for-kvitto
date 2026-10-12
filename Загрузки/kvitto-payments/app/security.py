import hashlib
import hmac
import os


def webhook_secret() -> str | None:
    return os.getenv("WEBHOOK_SECRET") or None


def compute_signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_signature(secret: str, body: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    expected = compute_signature(secret, body)
    return hmac.compare_digest(expected.encode(), signature.strip().lower().encode())
