"""Integration tests for HmacMiddleware (Issue #3).

Tests exercise the full HTTP stack via ASGI test client.
The middleware only fires on requests that carry X-Telegram-Chat-Id.
"""

import hashlib
import hmac
import time

import pytest

from app.config import get_settings


SECRET = "integration-test-secret"
CHAT_ID = "42"


def _sign(secret: str, chat_id: str, offset: int = 0) -> dict:
    """Return the three HMAC headers for a fresh request."""
    ts = str(int(time.time()) + offset)
    nonce = "test-nonce-integration"
    message = f"{ts}:{nonce}:{chat_id}".encode()
    sig = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return {
        "X-Request-Timestamp": ts,
        "X-Nonce": nonce,
        "X-Signature": sig,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_hmac_secret(monkeypatch):
    """Enable HMAC enforcement for these tests only."""
    settings = get_settings()
    monkeypatch.setattr(settings, "HMAC_SECRET", SECRET)
    yield
    # get_settings() is lru_cached so the monkeypatch on the instance suffices.


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_chat_id_header_passes_through(client):
    """Requests without X-Telegram-Chat-Id are never checked — /health should 200."""
    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_valid_signature_accepted(client):
    """A correctly signed request must not be rejected by the middleware."""
    headers = {"X-Telegram-Chat-Id": CHAT_ID, **_sign(SECRET, CHAT_ID)}
    # /health has no auth dependency so we get 200 rather than 403
    resp = await client.get("/health", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_missing_hmac_headers_returns_401(client):
    """X-Telegram-Chat-Id present but no signature headers → 401."""
    resp = await client.get("/health", headers={"X-Telegram-Chat-Id": CHAT_ID})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid request signature"


@pytest.mark.asyncio
async def test_wrong_secret_returns_401(client):
    headers = {"X-Telegram-Chat-Id": CHAT_ID, **_sign("wrong-secret", CHAT_ID)}
    resp = await client.get("/health", headers=headers)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_expired_timestamp_returns_401(client):
    """A timestamp older than the tolerance window must be rejected."""
    headers = {"X-Telegram-Chat-Id": CHAT_ID, **_sign(SECRET, CHAT_ID, offset=-400)}
    resp = await client.get("/health", headers=headers)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_tampered_signature_returns_401(client):
    sig_headers = _sign(SECRET, CHAT_ID)
    sig_headers["X-Signature"] = "0" * 64  # wrong hex
    headers = {"X-Telegram-Chat-Id": CHAT_ID, **sig_headers}
    resp = await client.get("/health", headers=headers)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dev_mode_skips_check(client, monkeypatch):
    """When HMAC_SECRET is empty the middleware is a no-op."""
    settings = get_settings()
    monkeypatch.setattr(settings, "HMAC_SECRET", "")
    # Send X-Telegram-Chat-Id with no signature headers — should still pass
    resp = await client.get("/health", headers={"X-Telegram-Chat-Id": CHAT_ID})
    assert resp.status_code == 200
