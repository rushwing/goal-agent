"""Unit tests for app.auth.hmac_auth.verify_request_signature (Issue #3)."""
import hashlib
import hmac
import time

import pytest

from app.auth.hmac_auth import TIMESTAMP_TOLERANCE_SECONDS, verify_request_signature


SECRET = "test-secret"
CHAT_ID = "12345"


def _make_sig(secret: str, timestamp: str, nonce: str, chat_id: str) -> str:
    message = f"{timestamp}:{nonce}:{chat_id}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def _valid_args(
    secret: str = SECRET,
    chat_id: str = CHAT_ID,
    offset: int = 0,
) -> tuple[str, str, str, str, str]:
    """Return (secret, chat_id, timestamp, nonce, signature) for a fresh request."""
    ts = str(int(time.time()) + offset)
    nonce = "test-nonce-uuid4"
    sig = _make_sig(secret, ts, nonce, chat_id)
    return secret, chat_id, ts, nonce, sig


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_valid_signature_accepted():
    secret, chat_id, ts, nonce, sig = _valid_args()
    assert verify_request_signature(secret, chat_id, ts, nonce, sig) is True


def test_valid_signature_at_positive_boundary():
    """Timestamp exactly at +tolerance should be accepted."""
    secret, chat_id, ts, nonce, sig = _valid_args(offset=TIMESTAMP_TOLERANCE_SECONDS - 1)
    assert verify_request_signature(secret, chat_id, ts, nonce, sig) is True


def test_valid_signature_at_negative_boundary():
    """Timestamp exactly at -tolerance should be accepted."""
    secret, chat_id, ts, nonce, sig = _valid_args(offset=-(TIMESTAMP_TOLERANCE_SECONDS - 1))
    assert verify_request_signature(secret, chat_id, ts, nonce, sig) is True


# ---------------------------------------------------------------------------
# Replay / expiry
# ---------------------------------------------------------------------------


def test_expired_timestamp_rejected():
    offset = -(TIMESTAMP_TOLERANCE_SECONDS + 1)
    secret, chat_id, ts, nonce, sig = _valid_args(offset=offset)
    assert verify_request_signature(secret, chat_id, ts, nonce, sig) is False


def test_future_timestamp_beyond_tolerance_rejected():
    offset = TIMESTAMP_TOLERANCE_SECONDS + 1
    secret, chat_id, ts, nonce, sig = _valid_args(offset=offset)
    assert verify_request_signature(secret, chat_id, ts, nonce, sig) is False


# ---------------------------------------------------------------------------
# Wrong credentials
# ---------------------------------------------------------------------------


def test_wrong_secret_rejected():
    _, chat_id, ts, nonce, sig = _valid_args()
    assert verify_request_signature("wrong-secret", chat_id, ts, nonce, sig) is False


def test_wrong_chat_id_rejected():
    secret, _, ts, nonce, sig = _valid_args()
    assert verify_request_signature(secret, "99999", ts, nonce, sig) is False


def test_tampered_signature_rejected():
    secret, chat_id, ts, nonce, _ = _valid_args()
    assert verify_request_signature(secret, chat_id, ts, nonce, "deadbeef") is False


# ---------------------------------------------------------------------------
# Missing headers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "timestamp,nonce,signature",
    [
        (None, "nonce", "sig"),
        ("123", None, "sig"),
        ("123", "nonce", None),
        (None, None, None),
    ],
)
def test_missing_headers_rejected(timestamp, nonce, signature):
    assert verify_request_signature(SECRET, CHAT_ID, timestamp, nonce, signature) is False


def test_non_integer_timestamp_rejected():
    assert verify_request_signature(SECRET, CHAT_ID, "not-a-number", "nonce", "sig") is False
