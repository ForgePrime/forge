"""P3.1 — reltime helper + filter registration."""
import datetime as dt

import pytest

from app.services.time_format import reltime


_NOW = dt.datetime(2026, 4, 19, 12, 0, 0, tzinfo=dt.timezone.utc)


def test_just_now_under_5s():
    ts = _NOW - dt.timedelta(seconds=2)
    assert reltime(ts, now=_NOW) == "just now"


def test_seconds_ago():
    ts = _NOW - dt.timedelta(seconds=42)
    assert reltime(ts, now=_NOW) == "42s ago"


def test_minutes_ago():
    ts = _NOW - dt.timedelta(minutes=7, seconds=30)
    assert reltime(ts, now=_NOW) == "7m ago"


def test_hours_ago():
    ts = _NOW - dt.timedelta(hours=3)
    assert reltime(ts, now=_NOW) == "3h ago"


def test_days_ago():
    ts = _NOW - dt.timedelta(days=5)
    assert reltime(ts, now=_NOW) == "5d ago"


def test_weeks_ago():
    ts = _NOW - dt.timedelta(days=21)
    assert reltime(ts, now=_NOW) == "3w ago"


def test_months_ago():
    ts = _NOW - dt.timedelta(days=90)
    assert reltime(ts, now=_NOW) == "3mo ago"


def test_years_ago():
    ts = _NOW - dt.timedelta(days=400)
    assert reltime(ts, now=_NOW) == "1y ago"


def test_future_renders_as_in():
    ts = _NOW + dt.timedelta(minutes=15)
    assert reltime(ts, now=_NOW) == "in 15m"


def test_iso_string_input():
    ts_iso = (_NOW - dt.timedelta(hours=2)).isoformat()
    assert reltime(ts_iso, now=_NOW) == "2h ago"


def test_iso_with_z_suffix():
    ts = "2026-04-19T11:00:00Z"
    assert reltime(ts, now=_NOW) == "1h ago"


def test_naive_datetime_assumed_utc():
    ts = dt.datetime(2026, 4, 19, 11, 30, 0)  # naive
    assert reltime(ts, now=_NOW) == "30m ago"


def test_none_returns_empty():
    assert reltime(None) == ""
    assert reltime("") == ""


def test_unparseable_string_returns_verbatim():
    assert reltime("not-a-date") == "not-a-date"


def test_reltime_filter_registered_in_jinja():
    """The filter must be wired into the templates env so {{ x|reltime }} works."""
    from app.api.ui import templates
    assert "reltime" in templates.env.filters
    # Use a dynamic "now" so the result is guaranteed "past" regardless of system clock.
    actual_now = dt.datetime.now(dt.timezone.utc)
    rendered = templates.env.from_string("{{ ts|reltime }}").render(
        ts=(actual_now - dt.timedelta(minutes=10)).isoformat()
    )
    assert rendered.endswith("ago") or rendered.endswith("now"), f"got: {rendered}"
