"""P3.1 — small `humanize`-style relative-time helper, no deps.

Output examples:
   "just now"  (< 5s)
   "12s ago"
   "3m ago"
   "2h ago"
   "3d ago"
   "2w ago"
   "5mo ago"
   "1y ago"
Future timestamps render as "in 3m" etc. Naive datetimes are assumed UTC."""
from __future__ import annotations

import datetime as dt


def reltime(value, now: dt.datetime | None = None) -> str:
    """Accept ISO string, datetime, or None. Return short relative string."""
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        try:
            ts = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value  # fallback — unparseable, render verbatim
    elif isinstance(value, dt.datetime):
        ts = value
    else:
        return str(value)

    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)

    delta = now - ts
    secs = int(delta.total_seconds())
    future = secs < 0
    secs = abs(secs)

    if secs < 5:
        return "just now"
    if secs < 60:
        unit = f"{secs}s"
    elif secs < 3600:
        unit = f"{secs // 60}m"
    elif secs < 86400:
        unit = f"{secs // 3600}h"
    elif secs < 604800:
        unit = f"{secs // 86400}d"
    elif secs < 2_592_000:  # 30d
        unit = f"{secs // 604800}w"
    elif secs < 31_536_000:  # 365d
        unit = f"{secs // 2_592_000}mo"
    else:
        unit = f"{secs // 31_536_000}y"
    return f"in {unit}" if future else f"{unit} ago"
