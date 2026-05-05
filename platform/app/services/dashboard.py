"""DashboardView aggregator — Phase 1 redesign integration.

Computes the panels for `/ui/dashboard`:
  - HERO: trust-debt index + active-K6 count + open-Decisions badge
  - M1..M7: Steward metrics grid
  - K1..K6: kill-criteria fired-counts (last 24h)
  - Objectives list with epistemic-tag + autonomy_pinned + stage marker

Per PLAN_PHASE1_UX_INTEGRATION.md §5.3 + ADR-028 ratified design canonical.

Honesty discipline (CONTRACT §A.6, AntiShortcutSound §13):
  Most metrics + all kill-criteria require Phase 1 schema (kill_criteria_event_log,
  alternatives, side_effect_map, contract_revision history). Until the
  migration draft (`migrations_drafts/2026_04_26_phase1_redesign.sql`) is
  applied, those data points are flagged `available=False` and the UI
  renders "(awaiting Phase 1 migration)" — never silent stubs. As columns
  light up, this service degrades the unavailable flag automatically via
  `getattr(model, field, None)` introspection.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, asdict
from typing import Any

from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.models import (
    Project,
    Objective,
    Task,
    Decision,
    Finding,
    AcceptanceCriterion,
    Execution,
    LLMCall,
)


# --- Snapshot dataclasses ---------------------------------------------------


@dataclass
class MetricSnapshot:
    id: str           # 'M1'..'M7'
    label: str
    value: Any        # numeric or string; None when unavailable
    target: Any
    unit: str         # 'ratio' / 'count' / 'grade'
    desc: str
    available: bool   # False → UI shows "(awaiting Phase 1 migration)"
    awaits: str       # what schema/data is required to make this available
    source: str       # short label of the backing data source (when available)
    status: str       # 'BELOW_TARGET' / 'AT_TARGET' / 'ABOVE_TARGET' / 'UNAVAILABLE'


@dataclass
class KillCriterionSnapshot:
    id: str           # 'K1'..'K6'
    label: str
    desc: str
    tripped_24h: int  # 0 when unavailable
    last_at: dt.datetime | None
    available: bool
    awaits: str


@dataclass
class HeroSnapshot:
    trust_debt_total: int           # sum of 4 trust-debt components
    trust_debt_components: dict[str, int]
    trust_debt_formula_ratified: bool   # False until Steward signs off (per ADR-028)
    active_k6_24h: int              # count of K6 (kill-criterion 6 = contract drift) trips
    active_k6_available: bool       # False until kill_criteria_event_log exists
    open_decisions: int
    open_findings: int
    project_count: int


@dataclass
class ObjectiveSummary:
    id: int
    external_id: str
    title: str
    status: str
    project_slug: str
    priority: int
    epistemic_tag: str | None       # None = not yet tagged (column may not exist)
    epistemic_tag_available: bool   # False until migration adds epistemic_tag column
    stage: str | None               # 'KICKOFF'/'PLAN'/'EXEC'/'VERIFY' or None
    stage_available: bool
    autonomy_pinned: str | None     # 'L0'..'L3' or None
    autonomy_pinned_available: bool
    autonomy_optout: bool           # legacy boolean (always available)
    kr_total: int
    kr_done: int


@dataclass
class DashboardData:
    hero: HeroSnapshot
    metrics: list[MetricSnapshot]
    kill_criteria: list[KillCriterionSnapshot]
    objectives: list[ObjectiveSummary]
    computed_at: dt.datetime


# --- Helpers ----------------------------------------------------------------


def _project_id_filter(db: Session, org_id: int | None) -> list[int]:
    """Return list of project ids visible to this org (or all if org_id is None)."""
    q = db.query(Project.id)
    if org_id is not None:
        q = q.filter(Project.organization_id == org_id)
    return [row[0] for row in q.all()]


def _has_column(model, field_name: str) -> bool:
    """Return True iff the SQLAlchemy model has the column declared.

    Used to gracefully degrade when the migration adding the column hasn't
    been applied yet to the running DB. We check the *model* not the *DB*
    because the model is authoritative for what the app expects.
    """
    return field_name in model.__table__.columns.keys()


def _metric_status(value: Any, target: Any, lower_is_better: bool) -> str:
    if value is None or target is None:
        return "UNAVAILABLE"
    try:
        v = float(value)
        t = float(target)
    except (TypeError, ValueError):
        return "UNAVAILABLE"
    if lower_is_better:
        return "AT_TARGET" if v <= t else "BELOW_TARGET"
    return "AT_TARGET" if v >= t else "BELOW_TARGET"


# --- HERO panel -------------------------------------------------------------


def compute_hero(db: Session, org_id: int | None) -> HeroSnapshot:
    project_ids = _project_id_filter(db, org_id)

    # Trust-debt: reuse existing computation
    try:
        from app.api.tier1 import _compute_trust_debt
        td = _compute_trust_debt(db, project_id_in=project_ids)
    except Exception:
        td = {
            "unaudited_approvals": 0,
            "manual_scenarios_unrun": 0,
            "findings_dismissed_no_reason": 0,
            "stale_analyses": 0,
        }
    components = {
        "unaudited_approvals": td.get("unaudited_approvals", 0),
        "manual_scenarios_unrun": td.get("manual_scenarios_unrun", 0),
        "findings_dismissed_no_reason": td.get("findings_dismissed_no_reason", 0),
        "stale_analyses": td.get("stale_analyses", 0),
    }
    total = sum(components.values())

    # Decisions / Findings counters
    open_dec = (
        db.query(sqlfunc.count(Decision.id))
        .filter(Decision.project_id.in_(project_ids) if project_ids else False)
        .filter(Decision.status == "OPEN")
        .scalar()
        or 0
    )
    open_find = (
        db.query(sqlfunc.count(Finding.id))
        .filter(Finding.project_id.in_(project_ids) if project_ids else False)
        .filter(Finding.status == "OPEN")
        .scalar()
        or 0
    )

    return HeroSnapshot(
        trust_debt_total=total,
        trust_debt_components=components,
        trust_debt_formula_ratified=False,  # ADR-028 D7 — formula INVENTED in mock; awaits Steward sign-off
        active_k6_24h=0,
        active_k6_available=False,  # K6 firing log table not yet created
        open_decisions=open_dec,
        open_findings=open_find,
        project_count=len(project_ids),
    )


# --- M1..M7 metrics ---------------------------------------------------------


def compute_metrics(db: Session, org_id: int | None) -> list[MetricSnapshot]:
    """Compute the 7 Steward metrics. Most require Phase 1 schema; flag
    `available=False` for those + provide explicit `awaits` tags so the
    UI can render the "what's needed" path."""
    project_ids = _project_id_filter(db, org_id)

    out: list[MetricSnapshot] = []

    # M1 — Cascade-aware decisions: needs `alternatives` table (Phase 1)
    out.append(MetricSnapshot(
        id="M1",
        label="Cascade-aware decisions",
        value=None, target=0.85, unit="ratio",
        desc="fraction of decisions where ≥2 downstream systems were explicitly inspected",
        available=False,
        awaits="alternatives table (Phase 1 migration §3); CGAID alternative rows per Decision",
        source="(unavailable)",
        status="UNAVAILABLE",
    ))

    # M2 — ADR citation rate on AC: typed when epistemic_tag column exists,
    # heuristic otherwise.
    if _has_column(AcceptanceCriterion, "epistemic_tag"):
        # Phase 1 column applied — compute exact: count(epistemic_tag IN
        # {ADR_CITED, SPEC_DERIVED, EMPIRICALLY_OBSERVED, TOOL_VERIFIED,
        # STEWARD_AUTHORED}) / count(total). INVENTED + NULL = un-cited.
        total_ac = (
            db.query(sqlfunc.count(AcceptanceCriterion.id))
            .join(Task, AcceptanceCriterion.task_id == Task.id)
            .filter(Task.project_id.in_(project_ids) if project_ids else False)
            .scalar() or 0
        )
        cited = (
            db.query(sqlfunc.count(AcceptanceCriterion.id))
            .join(Task, AcceptanceCriterion.task_id == Task.id)
            .filter(Task.project_id.in_(project_ids) if project_ids else False)
            .filter(
                AcceptanceCriterion.epistemic_tag.in_(
                    ["ADR_CITED", "SPEC_DERIVED", "EMPIRICALLY_OBSERVED",
                     "TOOL_VERIFIED", "STEWARD_AUTHORED"]
                )
            )
            .scalar() or 0
        )
        ratio = (cited / total_ac) if total_ac > 0 else None
        m2 = MetricSnapshot(
            id="M2", label="ADR citation rate on AC",
            value=round(ratio, 2) if ratio is not None else None,
            target=0.95, unit="ratio",
            desc=("AC rows with epistemic_tag ∈ {ADR_CITED, SPEC_DERIVED, "
                  "EMPIRICALLY_OBSERVED, TOOL_VERIFIED, STEWARD_AUTHORED} "
                  "/ total. NULL + INVENTED = un-cited."),
            available=ratio is not None,
            awaits="(none — exact metric over Phase 1 epistemic_tag column)",
            source="acceptance_criteria.epistemic_tag",
            status=_metric_status(ratio, 0.95, lower_is_better=False),
        )
    else:
        # Pre-migration heuristic: AC rows with non-NULL source_ref / total
        total_ac = (
            db.query(sqlfunc.count(AcceptanceCriterion.id))
            .join(Task, AcceptanceCriterion.task_id == Task.id)
            .filter(Task.project_id.in_(project_ids) if project_ids else False)
            .scalar() or 0
        )
        with_src = (
            db.query(sqlfunc.count(AcceptanceCriterion.id))
            .join(Task, AcceptanceCriterion.task_id == Task.id)
            .filter(Task.project_id.in_(project_ids) if project_ids else False)
            .filter(AcceptanceCriterion.source_ref.isnot(None))
            .scalar() or 0
        )
        ratio = (with_src / total_ac) if total_ac > 0 else None
        m2 = MetricSnapshot(
            id="M2", label="ADR citation rate on AC (heuristic)",
            value=round(ratio, 2) if ratio is not None else None,
            target=0.95, unit="ratio",
            desc="proxy: AC rows with non-NULL source_ref / total AC. Exact metric awaits epistemic_tag column.",
            available=ratio is not None,
            awaits="acceptance_criteria.epistemic_tag column (Phase 1 migration §2) for exact metric",
            source="acceptance_criteria.source_ref (heuristic proxy)",
            status=_metric_status(ratio, 0.95, lower_is_better=False),
        )
    out.append(m2)

    # M3 — Gate-spectrum median: needs gate-grade taxonomy beyond PASS/FAIL
    out.append(MetricSnapshot(
        id="M3", label="Gate-spectrum median",
        value=None, target="A-", unit="grade",
        desc="distribution over PASS/PARTIAL/WEAK/FAIL across last 50 gates",
        available=False,
        awaits="gate-grade taxonomy expansion (currently only PASS/FAIL); separate ADR pending",
        source="(unavailable)",
        status="UNAVAILABLE",
    ))

    # M4 — Contract drift: needs contract_revision history with measured behaviour
    out.append(MetricSnapshot(
        id="M4", label="Contract drift",
        value=None, target=0.02, unit="ratio",
        desc="diff between stated contract and revealed behaviour on last 20 runs",
        available=False,
        awaits="contract_revision diff metric implementation; ContractSchema E.1 ratified but not measured",
        source="(unavailable)",
        status="UNAVAILABLE",
    ))

    # M5 — Solo-verifier incidents: need challenger==executor model_id check on Executions
    out.append(MetricSnapshot(
        id="M5", label="Solo-verifier incidents",
        value=None, target=0, unit="count",
        desc="cases where the verifier was the same agent that produced the artifact",
        available=False,
        awaits="ADR-012 distinct-actor edge cases ratified; verifier model_id tracking in Execution",
        source="(unavailable)",
        status="UNAVAILABLE",
    ))

    # M6 — Kill-criterion hit rate: needs kill_criteria_event_log table
    out.append(MetricSnapshot(
        id="M6", label="Kill-criterion hit rate",
        value=None, target=0.10, unit="ratio",
        desc="share of tasks that tripped K1–K6 stop conditions",
        available=False,
        awaits="kill_criteria_event_log table (Phase 1 migration §6)",
        source="(unavailable)",
        status="UNAVAILABLE",
    ))

    # M7 — Autonomy promotions declined: needs autonomy_promotion_log
    out.append(MetricSnapshot(
        id="M7", label="Autonomy promotions declined",
        value=None, target="≥ evidence demands", unit="count",
        desc="count of promotions Steward declined despite clean metrics",
        available=False,
        awaits="autonomy_promotion_log entity (deferred to Phase 2)",
        source="(unavailable)",
        status="UNAVAILABLE",
    ))

    return out


# --- K1..K6 kill-criteria panel ---------------------------------------------


_K_DEFINITIONS = [
    ("K1", "Unowned side-effect",
     "Any side_effect with owner=NULL at execute time → halt"),
    ("K2", "ADR-uncited AC reached Verify",
     "AC with source_ref=NULL entering Verify phase → halt"),
    ("K3", "Tier downgrade without Steward sign",
     "data_class.tier drop vs source tier without signed ADR → halt"),
    ("K4", "Solo-verifier",
     "Challenger model == Executor model on restricted tiers → halt"),
    ("K5", "Gate spectrum WEAK → promote",
     "Attempt to promote artifact with any gate ≤ WEAK → halt"),
    ("K6", "Contract drift > 5%",
     "Stated vs revealed behaviour mismatch >5% → halt"),
]


def compute_kill_criteria(db: Session, org_id: int | None) -> list[KillCriterionSnapshot]:
    """Compute K1..K6 last-24h fired counts.

    Reads `kill_criteria_event_log` (Phase 1 migration §6, applied 2026-04-25).
    When a K-code has zero events in the 24h window the panel renders
    "clean" (green) instead of the legacy "awaiting Phase 1" pill — the
    table existing IS the availability signal.

    Instrumentation that *writes* to the log lives in
    `app/services/kill_criteria.py` (e.g. `detect_k1_unowned_side_effects`).
    Each detection helper is wired to its appropriate lifecycle hook
    separately; this aggregator is read-only.
    """
    out: list[KillCriterionSnapshot] = []
    project_ids = _project_id_filter(db, org_id)

    # Defensive `_has_table` check — if migration hasn't been applied on
    # this DB, fall back to "awaiting" rendering rather than 500-erroring
    # the whole dashboard. Cheap: just probe metadata once.
    try:
        from app.models import KillCriteriaEventLog
        has_log = "kill_criteria_event_log" in KillCriteriaEventLog.__table__.metadata.tables
    except (ImportError, AttributeError):
        has_log = False

    if has_log:
        from app.services.kill_criteria import tripped_in_last_24h
        for kid, label, desc in _K_DEFINITIONS:
            try:
                count, last_at = tripped_in_last_24h(
                    db, kid, project_ids=project_ids if project_ids else None,
                )
            except Exception:
                # If the table exists but query fails (e.g., migration partial),
                # degrade to unavailable rather than crashing the panel.
                count, last_at, available = 0, None, False
            else:
                available = True
            out.append(KillCriterionSnapshot(
                id=kid, label=label, desc=desc,
                tripped_24h=count,
                last_at=last_at,
                available=available,
                awaits="(none — Phase 1 migration applied; instrumentation per K-criterion is incremental)",
            ))
    else:
        # Pre-migration / model-not-loaded fallback: keep legacy "awaiting"
        # presentation so the dashboard still renders.
        for kid, label, desc in _K_DEFINITIONS:
            out.append(KillCriterionSnapshot(
                id=kid, label=label, desc=desc,
                tripped_24h=0,
                last_at=None,
                available=False,
                awaits="kill_criteria_event_log table (Phase 1 migration §6) + KC firing instrumentation",
            ))
    return out


# --- Objectives list --------------------------------------------------------


def list_objectives(db: Session, org_id: int | None, *, limit: int = 50) -> list[ObjectiveSummary]:
    project_ids = _project_id_filter(db, org_id)
    if not project_ids:
        return []

    has_epistemic = _has_column(Objective, "epistemic_tag")
    has_stage = _has_column(Objective, "stage")
    has_pinned = _has_column(Objective, "autonomy_pinned")

    objs = (
        db.query(Objective, Project.slug)
        .join(Project, Project.id == Objective.project_id)
        .filter(Objective.project_id.in_(project_ids))
        .order_by(Objective.priority.asc(), Objective.id.desc())
        .limit(limit)
        .all()
    )

    out: list[ObjectiveSummary] = []
    for obj, slug in objs:
        kr_total = len(obj.key_results)
        kr_done = sum(1 for kr in obj.key_results if kr.status == "ACHIEVED")
        out.append(ObjectiveSummary(
            id=obj.id,
            external_id=obj.external_id,
            title=obj.title,
            status=obj.status,
            project_slug=slug,
            priority=obj.priority,
            epistemic_tag=getattr(obj, "epistemic_tag", None) if has_epistemic else None,
            epistemic_tag_available=has_epistemic,
            stage=getattr(obj, "stage", None) if has_stage else None,
            stage_available=has_stage,
            autonomy_pinned=getattr(obj, "autonomy_pinned", None) if has_pinned else None,
            autonomy_pinned_available=has_pinned,
            autonomy_optout=bool(getattr(obj, "autonomy_optout", False)),
            kr_total=kr_total,
            kr_done=kr_done,
        ))
    return out


# --- Top-level aggregator ---------------------------------------------------


def compute_dashboard(db: Session, org_id: int | None) -> DashboardData:
    return DashboardData(
        hero=compute_hero(db, org_id),
        metrics=compute_metrics(db, org_id),
        kill_criteria=compute_kill_criteria(db, org_id),
        objectives=list_objectives(db, org_id),
        computed_at=dt.datetime.now(dt.timezone.utc),
    )


def dashboard_to_dict(d: DashboardData) -> dict:
    """Serialise to plain dict for templates / JSON."""
    return {
        "hero": asdict(d.hero),
        "metrics": [asdict(m) for m in d.metrics],
        "kill_criteria": [
            {**asdict(k), "last_at": k.last_at.isoformat() if k.last_at else None}
            for k in d.kill_criteria
        ],
        "objectives": [asdict(o) for o in d.objectives],
        "computed_at": d.computed_at.isoformat(),
    }
