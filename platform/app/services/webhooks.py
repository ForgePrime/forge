"""Outbound webhook dispatcher.

Fires HMAC-signed POST requests on subscribed events. Best-effort, async fire-and-forget.
"""

import hashlib
import hmac
import json
import secrets
import time
import urllib.request
import urllib.error
from typing import Any


def generate_secret() -> str:
    return secrets.token_urlsafe(32)


def sign_payload(secret: str, body: bytes) -> str:
    """HMAC-SHA256 hex of body."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def fire_webhook(url: str, event: str, payload: dict, secret: str, timeout: int = 5) -> dict:
    """Synchronous best-effort POST. Returns dict with status_code/error.
    Caller should call from background thread to avoid blocking.
    """
    body = json.dumps({"event": event, "ts": int(time.time()), "data": payload}).encode("utf-8")
    sig = sign_payload(secret, body)
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Forge-Signature": sig,
            "X-Forge-Event": event,
            "User-Agent": "Forge-Webhook/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"status_code": resp.status, "error": None}
    except urllib.error.HTTPError as e:
        return {"status_code": e.code, "error": str(e)[:300]}
    except Exception as e:
        return {"status_code": 0, "error": f"{type(e).__name__}: {str(e)[:300]}"}


def dispatch_event(db, organization_id: int, event: str, payload: dict) -> int:
    """Fire all enabled webhooks for an org subscribed to event. Returns count fired.
    Updates last_called_at/last_status/last_error per webhook.
    """
    from app.models import Webhook
    import datetime as _dt
    hooks = db.query(Webhook).filter(
        Webhook.organization_id == organization_id,
        Webhook.enabled == True,
    ).all()
    fired = 0
    for h in hooks:
        if event not in (h.events or []):
            continue
        result = fire_webhook(h.url, event, payload, h.secret)
        h.last_called_at = _dt.datetime.now(_dt.timezone.utc)
        h.last_status = result["status_code"]
        h.last_error = result["error"]
        fired += 1
    db.commit()
    return fired
