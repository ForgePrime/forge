"""P3.4 — per-objective KB scoping.
P3.5 — per-source last_read tracking.

`resolve_scoped_kb_ids(db, objective_id) -> list[int] | None`:
  - Returns the kb_focus_ids list when the objective specifies one (narrow scope).
  - Returns None when there is no scoping (caller should consult all KB).

`mark_read(db, knowledge_ids: list[int])`: bumps Knowledge.last_read_at to now()
for each id (idempotent, single UPDATE)."""
from __future__ import annotations

import datetime as dt
from typing import Iterable

from sqlalchemy.orm import Session


def resolve_scoped_kb_ids(db: Session, objective_id: int) -> list[int] | None:
    from app.models import Objective
    obj = db.query(Objective).filter(Objective.id == objective_id).first()
    if not obj:
        return None
    ids = obj.kb_focus_ids or None
    if ids is None:
        return None
    # Filter out any None / non-int junk defensively
    out: list[int] = []
    seen = set()
    for v in ids:
        try:
            iv = int(v)
        except (TypeError, ValueError):
            continue
        if iv in seen:
            continue
        seen.add(iv)
        out.append(iv)
    return out


def mark_read(db: Session, knowledge_ids: Iterable[int]) -> int:
    """Update Knowledge.last_read_at to NOW for each id. Returns rows updated."""
    from app.models import Knowledge
    ids = list({int(i) for i in knowledge_ids if i is not None})
    if not ids:
        return 0
    now = dt.datetime.now(dt.timezone.utc)
    n = (db.query(Knowledge)
           .filter(Knowledge.id.in_(ids))
           .update({Knowledge.last_read_at: now}, synchronize_session=False))
    db.commit()
    return n
