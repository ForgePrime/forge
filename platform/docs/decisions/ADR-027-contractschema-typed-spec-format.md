# ADR-027 — ContractSchema typed-spec format (E.1)

**Status:** PROPOSED (draft) — open for distinct-actor review per ADR-003. Not yet ratified; not yet CLOSED.
**Date:** 2026-04-25
**Authored by:** Claude (Opus 4.7, 1M context)
**Decided by:** [pending — user / distinct-actor]
**Related:** PLAN_CONTRACT_DISCIPLINE Stage E.1 (this ADR ratification unblocks E.1 implementation), FORMAL_PROPERTIES_v2 P12 (self-adjointness), PLAN_LLM_ORCHESTRATION L3.1 (PromptAssembler depends on E.1), existing `Task.produces JSONB` field.

> **Why this ADR exists:** PLAN_CONTRACT_DISCIPLINE Stage E.1 names ContractSchema as the source-of-truth that produces both `render_prompt_fragment()` (consumed by L3.1 PromptAssembler) and `validator_rules()` (consumed by VerdictEngine adapters). FORMAL P12 requires they come from the same source so that mutating a field changes both lockstep. The implementation cannot start until the *format* is decided.
>
> Current state: `Task.produces` is JSONB free-form. Existing rows have heterogeneous shape. Any decision here imposes migration pressure.

---

## Context

### What ContractSchema needs to represent

For each `Task.type` (feature / bug / chore / develop / etc.) the schema must declare:

1. **Required output fields** (e.g. for type=feature: `reasoning`, `changes`, `ac_evidence`, `assumptions`, `impact_analysis`, `failure_scenarios`).
2. **Per-field constraints** (`reasoning.min_length=200`, `reasoning.must_reference_file=true`, etc.).
3. **Per-field rendering hints** (how the field becomes a prompt section).
4. **Per-field validator rules** (how the field is checked post-LLM).
5. **Per-field structural categories for F.10 StructuredTransferGate** (requirements, evidence_refs, ambiguity_state, test_obligations, dependency_relations, hard_constraints).

### Constraints (FORMAL P12 + existing code)

- **P12 self-adjointness**: `render_prompt_fragment()` and `validator_rules()` MUST derive from the *same* schema instance. Mutating any field updates both. Drift test in PLAN_CONTRACT_DISCIPLINE T_{E.1} T2 fails otherwise.
- **Backward compatibility**: 100+ existing Task rows have free-form `Task.produces` JSONB. Migration must either tolerate them (legacy_exempted flag) or coerce them.
- **`output_contracts` table already exists** (4 contracts seeded — feature/STANDARD, feature/FULL, bug/LIGHT, default). The ContractSchema is conceptually a *typed superset* of what's already in `output_contracts.required` JSONB.
- **CONTRACT §B determinism**: rendering + validation must be pure functions; no LLM in the schema-to-prompt or schema-to-validator path.

### Why decision matters now

Three downstream pieces are blocked:

1. **L3.1 PromptAssembler** — cannot deterministically render a typed prompt fragment without knowing the schema's shape.
2. **F.10 StructuredTransferGate** — cannot enforce 6-category structural transfer without typed `required_context_categories(task)`.
3. **E.10 TestSynthesizer (P25)** — already specified to walk ContractSchema fields → emit hypothesis strategies; needs a typed walkable structure.

Without ratification, these stay deferred indefinitely.

---

## Decision (PROPOSED — pending ratification)

**Hybrid: Pydantic model as the canonical form + auto-derived JSONSchema for runtime + DB storage in `output_contracts.spec_jsonb`.**

### Schema

```python
# app/validation/contract_schema.py (proposed; not yet implemented)

from pydantic import BaseModel, Field
from typing import Literal


class FieldConstraint(BaseModel):
    """Per-field rules. Maps to validator + prompt fragment + F.10 category."""

    name: str
    type: Literal["str", "list[dict]", "list[str]", "dict", "bool", "int"]
    required: bool = True

    # Validator-side constraints (consumed by ContractValidatorRuleAdapter):
    min_length: int | None = None
    must_reference_file: bool = False
    must_contain_keyword: list[str] = Field(default_factory=list)
    reject_patterns: list[str] = Field(default_factory=list)

    # Prompt-rendering hints (consumed by L3.1 PromptAssembler):
    prompt_section_name: str  # e.g. "REASONING", "CHANGES"
    prompt_intro: str  # e.g. "Provide a step-by-step reasoning..."
    prompt_priority: int = 50  # priority within ContextBudget bucket

    # F.10 structural category (consumed by StructuredTransferGate):
    structural_category: Literal[
        "requirements", "evidence_refs", "ambiguity_state",
        "test_obligations", "dependency_relations", "hard_constraints",
        "free_form",  # explicit opt-out for fields that aren't structurally categorized
    ] = "free_form"


class ContractSchema(BaseModel):
    """Typed spec for a Task.type x ceremony combination.

    Single source of truth — render_prompt_fragment() and
    validator_rules() are pure derivations.
    """

    task_type: Literal["feature", "bug", "develop", "chore", "investigation"]
    ceremony_level: Literal["LIGHT", "STANDARD", "FULL", "CRITICAL"]
    fields: list[FieldConstraint]
    schema_version: int = 1  # bump on breaking change

    def render_prompt_fragment(self) -> str:
        """Pure: ordered prompt section from fields."""
        ...

    def validator_rules(self) -> list[FieldConstraint]:
        """Pure: returns fields directly (validators consume FieldConstraint)."""
        return self.fields

    def required_context_categories(self) -> set[str]:
        """For F.10: which structural categories this task needs."""
        return {f.structural_category for f in self.fields if f.structural_category != "free_form"}
```

### Storage

- **In code**: ContractSchema instances live as Python literals in `app/validation/contract_schemas/` (one file per (task_type, ceremony_level), e.g. `feature_full.py`).
- **In DB**: `output_contracts.spec_jsonb` (new column on existing table) stores the JSON-serialized ContractSchema. Auto-derived from Python via `model_dump_json()` on app startup; DB row is the cached form for ad-hoc queries (e.g. dashboards) but Python is canonical.
- **Drift test**: at startup, `model_dump_json(python_form) == output_contracts.spec_jsonb` per (task_type, ceremony). Drift → CI fails per E.1 T2.

### Migration of existing `Task.produces` JSONB

- `Task.produces` is the *output* shape the AI produced; ContractSchema is the *spec* for what should be produced. They are different roles; `Task.produces` does NOT migrate to ContractSchema.
- `output_contracts.required` (existing JSONB) IS the closest analog and IS migrated:
  - Phase E.1 migration script reads each `output_contracts` row, attempts to coerce to ContractSchema.
  - Successful coercion: stored to `output_contracts.spec_jsonb`; original `required` retained for backward-compat read.
  - Coercion failure: `Finding(severity=HIGH, kind='contract_schema_migration_failed')` emitted; row marked `legacy_exempted_contract_schema=true`. Validator falls back to legacy path for that contract type.
- Existing `Task.produces` rows: untouched. Validator continues to validate against `output_contracts.required` (legacy path) until E.1 cutover. ContractSchema is additive at first.

---

## Alternatives considered

Per FC §16+§17+§18+§19 (PLAN_CONTRACT_DISCIPLINE F.11 mandate) — at minimum 2 candidates with explicit rejection reasons:

### Alternative A: **Pure Pydantic** (no JSONB shadow)

ContractSchema lives as Python literal only; never serialized to DB. Validators read directly from Python.

- **Pros**: simplest; one source of truth literally in code.
- **Cons**: dashboards / external tools cannot query the contract spec. Rebuild-from-source required for any inspection.
- **Rejected because**: G.6 11-artifacts mapping requires queryable architecture inventory. ContractSchema as a queryable artifact is the natural fit. JSONB shadow gives this for ~zero ongoing cost (auto-derived).

### Alternative B: **Pure JSONSchema (declarative file format)**

Schemas as `.json` files; runtime parses + validates. No Pydantic.

- **Pros**: language-agnostic; tooling rich (json-schema validators in many languages).
- **Cons**: Python boundary loses type information; render_prompt_fragment() either becomes a string-template engine (more failure surface) or duplicates the schema in code. P12 self-adjointness harder to enforce mechanically because the rendering side needs ad-hoc traversal.
- **Rejected because**: P12 is the dominant constraint. Pydantic gives static-type guarantees on the Python side that JSONSchema cannot match without additional codegen.

### Alternative C: **Status quo (free-form JSONB everywhere)**

Defer the decision; keep `output_contracts.required` JSONB; let validators continue ad-hoc parsing.

- **Pros**: zero migration risk; nothing breaks today.
- **Cons**: PLAN_CONTRACT_DISCIPLINE E.1, L3.1 PromptAssembler, F.10 StructuredTransferGate, E.10 TestSynthesizer all stay blocked. Self-adjointness P12 cannot be enforced because no typed schema exists.
- **Rejected because**: blocks 4 downstream stages indefinitely. The cost of *not* deciding compounds.

### Alternative D: **Chosen — Hybrid (Pydantic primary + JSONB shadow)**

See above.

- **Pros**: P12 self-adjointness via pure-Python; queryable JSONB shadow for tooling; backward-compat migration path for existing `output_contracts.required`; auto-derived (no manual sync).
- **Cons**: drift-test required (one extra CI step); two storage forms (mitigated by auto-derive — Python is canonical, JSONB is cache).

---

## Consequences

### Immediate
- E.1 implementation can begin: ~0.5d to write ContractSchema base classes + 4 seed contract files (matching existing `output_contracts` rows).
- L3.1 PromptAssembler unblocked: ~0.5d to wrap schema rendering.
- E.10 TestSynthesizer (already shipped — commit cec5faa peer) unblocked for actual structural walk (currently the harness uses synthetic schemas).

### Downstream
- Every new task_type added requires authoring a ContractSchema file — explicit cost, but bounded.
- Existing `output_contracts` table extended with `spec_jsonb` column — additive, no down-migration risk.
- Validators stop reading `output_contracts.required` for any contract that has migrated — clean cutover per contract.

### Reversibility
**REVERSIBLE** — if ContractSchema turns out wrong:
- Drop `spec_jsonb` column, ContractSchema files, dependent code.
- Validators fall back to `output_contracts.required` legacy path.
- Cost: ~0.3d to revert + clean up tests.

### Risks
- **Drift between Python and JSONB**: caught by E.1 T2 drift test (model_dump_json vs spec_jsonb).
- **Migration coercion failures on legacy `output_contracts` rows**: explicit Finding + legacy_exempted flag (no silent skip).
- **Schema versioning when fields change**: schema_version int + bump-on-breaking convention. Phase 2: ADR for migration policy when schema_version increments.

---

## Evidence captured

- **[CONFIRMED via PLAN_CONTRACT_DISCIPLINE.md L66-68]** ContractSchema is named as the typed Pydantic model for `Task.produces`.
- **[CONFIRMED via FORMAL_PROPERTIES_v2.md P12 binding]** "ContractSchema owned by Task.produces. Renders prompt_constraint and validator_rules from one source."
- **[CONFIRMED via grep]** existing `output_contracts` table (4 contracts seeded — `feature/STANDARD`, `feature/FULL`, `bug/LIGHT`, `default` per IMPLEMENTATION_TRACKER).
- **[CONFIRMED via grep]** existing usage `validate_delivery(delivery, contract, task.type, ...)` at app/api/execute.py:277, app/api/pipeline.py:1051 — `contract` is a dict from `output_contracts.required`. Migration target.
- **[ASSUMED]** 100+ existing `Task.produces` rows are heterogeneous; no migration audit run yet. Pre-migration audit script needed before E.1 cutover.
- **[UNKNOWN]** how many distinct `Task.type` × `ceremony_level` combinations need ContractSchemas seeded on day 1. Initial 4 cover the existing `output_contracts` rows; full enumeration pending PLAN_CONTRACT_DISCIPLINE A_{E.1}.

---

## Ratification path

This ADR is **PROPOSED (DRAFT)**. Two paths to RATIFIED:

### Path 1 (recommended): user/distinct-actor review

- Reviewer reads §Decision + §Alternatives + §Consequences.
- Files `docs/reviews/review-ADR-027-by-<actor>-<date>.md` per `_template.md`.
- Verdict ACCEPT → status flips to CLOSED (content-DRAFT) → unblocks E.1 implementation.
- Verdict ACCEPT-WITH-CHANGES → author addresses, version bumps to v2, re-review.
- Verdict REJECT → ADR stays DRAFT; alternative explored.

### Path 2: domain-expert override (Steward path)

If E.1 implementation is time-pressing and reviewer unavailable, Steward (per ADR-007) may sign off as `[ASSUMED: accepted-by=steward, date=YYYY-MM-DD]`. Acceptance does not transmute into [CONFIRMED] per CONTRACT §B.2; status flips to CLOSED but stays content-DRAFT until Path 1 review completes.

### Until ratification

- E.1 implementation BLOCKED.
- L3.1 PromptAssembler BLOCKED.
- F.10 StructuredTransferGate full enforcement BLOCKED (current code uses 6-category seed per F.10 A_{F.10} fallback).
- E.10 TestSynthesizer (already shipped) operates on test fixtures; no production ContractSchema input.

---

## Versioning

- v1 (2026-04-25) — initial PROPOSED draft. Authored solo by AI agent per CONTRACT §B.8 disclosure. Awaiting distinct-actor review.
