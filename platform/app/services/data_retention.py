"""Data retention sweep — GDPR "storage limitation" principle (Article 5(1)(e)).

Personal data (incl. audit trails containing user identifiers and LLM
prompts containing arbitrary user input) should not be kept "for longer
than is necessary". This module provides a policy-driven sweep that
deletes rows older than a configurable TTL per entity type.

Policy is declared in `RETENTION_POLICIES` below. Each entry:
  model        — SQLAlchemy model class (lazy-imported to avoid circulars)
  timestamp_column — name of the column to check age against
  ttl_days     — rows older than this get deleted
  rationale    — why this TTL was chosen (for audit + adjustability)

Defaults chosen to be safe (generous):
  LLMCall          — 180 days (prompt bodies contain user input verbatim)
  PromptElement    — 180 days (content snapshots same reason)
  AuditLog         — 365 days (operational audit; regulator-friendly)
  OrchestrateRun   — 365 days (cost + run history)

Usage:
  sweep(db)                   → returns {entity: {deleted_count, cutoff}}
  sweep(db, dry_run=True)     → reports what WOULD be deleted, touches nothing
  sweep(db, entities=["LLMCall"])  → only that type

Never raises on a single entity failure — per-entity errors are captured
and returned in the report so the sweep is idempotent.
"""
from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    entity: str
    timestamp_column: str
    ttl_days: int
    rationale: str


# Default policies. Override via `sweep(db, overrides={...})`.
#
# PromptElement is deliberately omitted from defaults: the model does not
# currently mix-in TimestampMixin, so there's no `created_at` column to
# filter against. Adding it requires a schema migration (additive); once
# the migration lands, extend this list with the PromptElement policy
# mirroring LLMCall (180 days).
RETENTION_POLICIES: list[RetentionPolicy] = [
    RetentionPolicy(
        entity="LLMCall",
        timestamp_column="created_at",
        ttl_days=180,
        rationale="LLM prompts contain user input verbatim; 6 months aligns "
                  "with GDPR minimization while preserving cost-forensic window.",
    ),
    RetentionPolicy(
        entity="AuditLog",
        timestamp_column="created_at",
        ttl_days=365,
        rationale="Operational audit log; 12 months is standard for "
                  "SOC2-track compliance. Extend if legal requires longer.",
    ),
    RetentionPolicy(
        entity="OrchestrateRun",
        timestamp_column="finished_at",
        ttl_days=365,
        rationale="Run history for cost and orchestration trends; "
                  "12 months covers most analytical needs.",
    ),
]


def _resolve_model(name: str):
    """Lazy import to avoid circulars at module load."""
    from app import models
    return getattr(models, name, None)


def _count_expired(db: Session, policy: RetentionPolicy, now: dt.datetime) -> tuple[int, dt.datetime]:
    model = _resolve_model(policy.entity)
    if model is None:
        return 0, now

    col = getattr(model, policy.timestamp_column, None)
    if col is None:
        logger.warning("data-retention: %s has no column %s; skip",
                       policy.entity, policy.timestamp_column)
        return 0, now

    cutoff = now - dt.timedelta(days=policy.ttl_days)
    try:
        q = db.query(model).filter(col < cutoff)
        return q.count(), cutoff
    except Exception as e:  # pragma: no cover — defensive
        logger.warning("data-retention: count failed for %s: %s", policy.entity, e)
        return -1, cutoff


def _delete_expired(db: Session, policy: RetentionPolicy, now: dt.datetime) -> tuple[int, dt.datetime, str | None]:
    """Returns (deleted, cutoff, error_str_or_None)."""
    model = _resolve_model(policy.entity)
    if model is None:
        return 0, now, f"model {policy.entity} not found"

    col = getattr(model, policy.timestamp_column, None)
    if col is None:
        return 0, now, f"column {policy.timestamp_column} missing"

    cutoff = now - dt.timedelta(days=policy.ttl_days)
    try:
        q = db.query(model).filter(col < cutoff)
        count = q.count()
        if count:
            # synchronize_session=False — rows are being removed wholesale
            q.delete(synchronize_session=False)
            db.commit()
        return count, cutoff, None
    except Exception as e:
        db.rollback()
        return 0, cutoff, f"{type(e).__name__}: {str(e)[:200]}"


def sweep(
    db: Session,
    *,
    dry_run: bool = False,
    entities: list[str] | None = None,
    overrides: dict[str, int] | None = None,
    now: dt.datetime | None = None,
) -> dict:
    """Run the retention sweep.

    Args:
      dry_run: if True, report counts only; delete nothing
      entities: restrict to a subset of entity names
      overrides: {entity_name: ttl_days_int} — tighten or relax specific TTLs
      now: inject clock for tests (default: datetime.now(UTC))

    Returns structured report:
      {
        "executed_at": iso8601,
        "dry_run": bool,
        "policies": [{entity, ttl_days, cutoff, count, deleted, error}],
        "totals": {would_delete, deleted, errors}
      }
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    overrides = overrides or {}
    entities = set(entities) if entities else None

    results = []
    total_would = 0
    total_deleted = 0
    total_errors = 0

    for policy in RETENTION_POLICIES:
        if entities and policy.entity not in entities:
            continue
        effective = RetentionPolicy(
            entity=policy.entity,
            timestamp_column=policy.timestamp_column,
            ttl_days=overrides.get(policy.entity, policy.ttl_days),
            rationale=policy.rationale,
        )

        if dry_run:
            count, cutoff = _count_expired(db, effective, now)
            results.append({
                "entity": effective.entity,
                "ttl_days": effective.ttl_days,
                "cutoff": cutoff.isoformat(),
                "count": count,
                "deleted": 0,
                "error": None,
            })
            if count > 0:
                total_would += count
        else:
            deleted, cutoff, err = _delete_expired(db, effective, now)
            results.append({
                "entity": effective.entity,
                "ttl_days": effective.ttl_days,
                "cutoff": cutoff.isoformat(),
                "count": deleted,
                "deleted": deleted,
                "error": err,
            })
            if err:
                total_errors += 1
            total_deleted += deleted

    return {
        "executed_at": now.isoformat(),
        "dry_run": dry_run,
        "policies": results,
        "totals": {
            "would_delete": total_would,
            "deleted": total_deleted,
            "errors": total_errors,
        },
    }
