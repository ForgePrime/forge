"""Tests for EvidenceSet model — Phase A Stage A.1 (shadow mode).

Per PLAN_GATE_ENGINE.md T_{A.1}:
  T1: migration round-trip (DB schema test; covered once alembic versions/ exists)
  T2: CHECK constraint rejects kind='assumption'
  T3: CHECK constraint rejects EvidenceSet without provenance
  T4: FK cascade behavior (Decision delete → EvidenceSet rows deleted)

Blocked on: ADR-003 RATIFIED + alembic initial migration (out of scope for
skeleton PR — these tests define the contract for when the migration lands).
"""

import pytest
from sqlalchemy.exc import IntegrityError


pytestmark = pytest.mark.skip(
    reason="EvidenceSet migration not yet generated; skeleton-only — "
    "tests activate once alembic revision is created. See PLAN_GATE_ENGINE "
    "Stage A.1 for full exit test spec."
)


def test_insert_requires_valid_kind(db_session):
    """T2: EvidenceSet.kind not in valid enum → IntegrityError.

    Valid kinds per FORMAL_PROPERTIES_v2 P17:
    {test_output, command_output, api_response, log_output, metric,
     file_citation, code_reference, runtime_snapshot}
    kind='assumption' must raise IntegrityError.
    """
    from app.models.evidence_set import EvidenceSet

    with pytest.raises(IntegrityError):
        es = EvidenceSet(
            decision_id=1,  # assumes fixture
            kind="assumption",  # rejected by CHECK constraint
            provenance_path="/tmp/fake",
        )
        db_session.add(es)
        db_session.flush()


def test_insert_requires_provenance(db_session):
    """T3: both provenance_url and provenance_path NULL → IntegrityError.

    CHECK constraint 'provenance_required' enforces at least one is populated.
    """
    from app.models.evidence_set import EvidenceSet

    with pytest.raises(IntegrityError):
        es = EvidenceSet(
            decision_id=1,
            kind="test_output",
            # both provenance fields omitted
        )
        db_session.add(es)
        db_session.flush()


def test_insert_happy_path(db_session):
    """Sanity: valid EvidenceSet inserts cleanly."""
    from app.models.evidence_set import EvidenceSet

    es = EvidenceSet(
        decision_id=1,
        kind="test_output",
        provenance_path="/tests/test_foo.py::test_bar",
        reproducer_ref="pytest tests/test_foo.py::test_bar",
        content={"output": "PASSED", "duration_ms": 42},
    )
    db_session.add(es)
    db_session.flush()
    assert es.id is not None


def test_cascade_delete(db_session):
    """T4: Decision delete → EvidenceSet rows deleted (ondelete=CASCADE)."""
    # Placeholder — implementation requires Decision fixture; covered at
    # integration-test level once A.1 migration is live.
    pass
