import hmac
import hashlib
import secrets

def generate_secret_key() -> str:
    """Generate a secure random secret key for webhook signing"""
    return secrets.token_urlsafe(32)

def generate_hmac_signature(payload: str, secret: str) -> str:
    """Generate HMAC SHA256 signature for webhook payload"""
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def verify_hmac_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify HMAC signature"""
    expected_signature = generate_hmac_signature(payload, secret)
    return hmac.compare_digest(expected_signature, signature)
