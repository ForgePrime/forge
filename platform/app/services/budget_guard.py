"""P2.4/P2.5 — pure helpers for budget + veto enforcement.

Exported:
  remaining_usd(config, spent_usd)   → float remaining in the run budget
  warn_level(config, spent_usd)      → 'ok' | 'warn' | 'over'
  veto_match(config, path)           → bool — does the path glob-match any veto rule?

All functions accept a plain dict (project.config) so callers don't need DB.
Defaults mirror the API defaults (1.00 per task, 5.00 per run, warn at 80%)."""
from __future__ import annotations

import fnmatch


def _get(cfg: dict | None, key: str, default):
    if not isinstance(cfg, dict):
        return default
    v = cfg.get(key)
    return default if v is None else v


def task_budget_usd(cfg: dict | None) -> float:
    return float(_get(cfg, "budget_task_usd", 1.0))


def run_budget_usd(cfg: dict | None) -> float:
    return float(_get(cfg, "budget_run_usd", 5.0))


def warn_threshold_pct(cfg: dict | None) -> int:
    return int(_get(cfg, "warn_at_pct", 80))


def remaining_usd(cfg: dict | None, spent_usd: float) -> float:
    """How much USD is left in the run budget."""
    cap = run_budget_usd(cfg)
    return max(cap - float(spent_usd), 0.0)


def warn_level(cfg: dict | None, spent_usd: float) -> str:
    """Return 'ok' | 'warn' | 'over' for the current spend vs run budget."""
    cap = run_budget_usd(cfg)
    if cap <= 0:
        return "ok"
    pct = float(spent_usd) / cap * 100.0
    if pct >= 100.0:
        return "over"
    if pct >= warn_threshold_pct(cfg):
        return "warn"
    return "ok"


def veto_patterns(cfg: dict | None) -> list[str]:
    raw = _get(cfg, "veto_paths", []) or []
    if not isinstance(raw, list):
        return []
    return [str(p).strip() for p in raw if str(p).strip()]


def veto_match(cfg: dict | None, path: str) -> str | None:
    """Return the FIRST matching veto pattern for `path`, or None.

    Matches are fnmatch-style against the path as given (so glob both absolute
    and relative paths if the pattern is shaped that way). Case-insensitive on
    Windows-style paths is NOT done — patterns must mirror the conventions
    your project uses.
    """
    if not path:
        return None
    for pat in veto_patterns(cfg):
        if fnmatch.fnmatch(path, pat):
            return pat
    return None
