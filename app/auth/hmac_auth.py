"""HMAC-SHA256 request signature verification (Issue #3).

Message format:  "{timestamp}:{nonce}:{chat_id}"
Headers expected:
  X-Request-Timestamp  – unix epoch seconds (str)
  X-Nonce              – uuid4 string
  X-Signature          – HMAC-SHA256 hex digest

Replay protection: ±300 s timestamp window (stateless, no nonce DB).
"""
import hashlib
import hmac
import time
from typing import Optional


TIMESTAMP_TOLERANCE_SECONDS = 300


def verify_request_signature(
    secret: str,
    chat_id: str,
    timestamp: Optional[str],
    nonce: Optional[str],
    signature: Optional[str],
) -> bool:
    """Return True if the signature is valid and the timestamp is fresh.

    Returns False (rather than raising) so the caller can return a 401.
    """
    if not all([timestamp, nonce, signature]):
        return False

    # Validate timestamp is an integer and within tolerance window
    try:
        ts = int(timestamp)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return False

    now = int(time.time())
    if abs(now - ts) > TIMESTAMP_TOLERANCE_SECONDS:
        return False

    message = f"{timestamp}:{nonce}:{chat_id}".encode()
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)  # type: ignore[arg-type]
