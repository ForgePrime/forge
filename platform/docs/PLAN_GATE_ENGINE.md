# PLAN: Gate Engine — Deterministic Gating & Idempotency

**Status:** DRAFT — pending distinct-actor review per ADR-003.
**Date:** 2026-04-23
**Depends on:** PLAN_PRE_FLIGHT complete (G_0 = PASS).
**Must complete before:** PLAN_MEMORY_CONTEXT (B.1 needs VerdictEngine enforcement), PLAN_CONTRACT_DISCIPLINE (F stages need gate infrastructure).
**ROADMAP phases:** A.1 → A.5.
**Source spec:** FORMAL_PROPERTIES_v2.md P1, P6, P7, P8, P16, P17.
**Soundness theorem source:** `.ai/theorems/Context-Complete Evidence-Guided Agent Process.md` — conditions 1–7 (RequiredInfo⊆C_i, Suff, temporal ordering, ambiguity explicit, deterministic T_i, gate discipline, Missing→Stop). Also cross-references `Engineer_Soundness_Completeness.md` §1 (determinism), §4 (impact closure), §5 (invariant preservation).

---

## Soundness conditions addressed

| Theorem condition | What "addressed" means | Closed in |
|---|---|---|
| **5** — ∃ T_i: Eval(O_i, T_i) deterministic | VerdictEngine is a pure function; same inputs → same verdict; replay harness verifies this | Stage A.3 exit |
| **6** — O_i propagates only if G_i = pass | All 75 direct `.status=` assignments replaced by `VerdictEngine.commit()` — no bypass path | Stage A.4 exit |
| **3** (partial) — O_i derived from E_<i | Every Decision requires a linked EvidenceSet; no evidence → no Decision write | Stage A.1 exit |
| **1** (partial) — RequiredInfo ⊆ C_i | EvidenceSet captures what evidence was present at decision time; audit trail grounded | Stage A.1 |

Conditions 1 (full), 2, 4, 7 are NOT closed by this plan. They depend on PLAN_MEMORY_CONTEXT (1, 2) and PLAN_CONTRACT_DISCIPLINE (4, 7).

---

## Theorem variable bindings

```
For each stage i ∈ {A.1, A.2, A.3, A.4, A.5}:

C_i = codebase state after previous stage + ADR-004 calibration constants
R_i = formal property requirements from FORMAL_PROPERTIES_v2 §3 (P1, P6, P7, P8, P16, P17)
A_i = ambiguities explicitly listed per stage below
T_i = deterministic test (pytest + grep) per stage — no LLM-in-loop
O_i = code artifact produced (migration / module / flag flip)
G_i = all T_i pass AND existing 420 tests green AND distinct-actor sign-off on divergence log
```

**Condition 5 enforcement:** T1–T5 automated checks per stage are either a `pytest` invocation with fixed seed and hermetic DB, or a `grep` returning 0 or non-0 matches — no LLM-evaluated condition. T_{A.3} T6 is a distinct-actor human review (shadow divergence log); human review is a stronger gate than automated grep, excluded from condition 5 by design — it satisfies CONTRACT §B.8, not condition 5.

**Condition 6 enforcement:** G_i blocks propagation to next stage. Stage A.4 is the critical gate: until grep returns 0 matches for direct `.status=`, condition 6 is not satisfied for any transition in the system.

---

## Stage A.1 — EvidenceSet entity

**Closes:** P16 (evidence existence), partial P17 (DB schema `kind` constraint only — application-level enforcement in Phase F.1 per ROADMAP §9), partial P8.

**Entry conditions:**
- G_0 = PASS (Pre-flight complete).
- `uv run alembic current` exits 0.
- ADR-004 calibration constants CLOSED (TTL value needed for idempotency table in A.5).

**A_{A.1} (ambiguities at this stage):**
- `EvidenceSet.kind` enum values — resolved by ADR-001 (CLOSED). [CONFIRMED]
- Column names and types — resolved by CHANGE_PLAN_v2 §2.2.1. [CONFIRMED via read]
- Whether `sufficient_for` is JSONB or typed FK — [ASSUMED: JSONB per CHANGE_PLAN_v2 §2.2.1; typed FK deferred to Phase E ContractSchema]

**Work:**
1. Alembic migration: `evidence_sets(id, artifact_type, artifact_id, kind, provenance, checksum_at_capture, reproducer_ref, rule_ref, sufficient_for_json, created_at)`.
2. `kind` column: `CHECK (kind IN ('data_observation','code_reference','requirement_ref','test_output','command_output','file_citation'))` — no `kind='assumption'`.
3. `app/models/evidence_set.py` SQLAlchemy model.
4. App-level gate: `Decision` write rejects if no `EvidenceSet` link exists (FK or trigger).
5. Feature flag `VERDICT_ENGINE_MODE=off` default — engine code present but not invoked.

**Exit test T_{A.1} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
# exits 0

# T2: model test
pytest tests/test_evidence_set_model.py -x
# PASS: insert, query, delete round-trip

# T3: P16 invariant
pytest tests/test_decision_evidence_invariant.py -x
# PASS: Decision insert without EvidenceSet link → raises IntegrityError

# T4: P17 constraint
pytest tests/test_evidence_kind_constraint.py -x
# PASS: insert kind='assumption' → raises CheckViolation

# T5: regression
pytest tests/ -x --ignore=tests/test_evidence_set_model.py
# all 420 existing tests green
```

**Gate G_{A.1}:** T1–T5 all pass → PASS.

---

## Stage A.2 — GateRegistry

**Closes:** structural prerequisite for P7; no runtime enforcement yet.

**Entry conditions:**
- G_{A.1} = PASS.

**A_{A.2}:**
- Complete list of valid transitions per entity — [ASSUMED: derived from existing `CheckConstraint` scan; must be verified against DB before writing]. Mitigation: T_{A.2} validates count matches.

**Work:**
1. `app/validation/gate_registry.py` — pure Python dict, no DB calls, no imports from `app/services/`.
2. Entries for 6 entities: `Execution` (8 transitions), `Task` (5), `Decision` (6), `Finding` (3), `KeyResult` (3), `OrchestrateRun` (states).
3. Format: `(entity_type, from_state, to_state) → List[rule_ref]`.

**Exit test T_{A.2} (deterministic):**
```bash
# T1: registry integrity
pytest tests/test_gate_registry.py -x
# PASS: every (entity, from, to) in registry matches a CheckConstraint in DB schema
# PASS: no DB calls during registry import (mock DB, still imports)

# T2: purity check
grep -r "import.*db\|session\|engine" app/validation/gate_registry.py
# exits 1 (no matches — pure module)

# T3: regression
pytest tests/ -x
# all existing + A.1 tests green
```

**Gate G_{A.2}:** T1–T3 pass → PASS.

---

## Stage A.3 — VerdictEngine in shadow mode

**Closes:** P6 (deterministic evaluation), P7 prerequisite (engine exists before cutover).

**Entry conditions:**
- G_{A.2} = PASS.

**A_{A.3}:**
- `plan_gate` signature: `validate_plan_requirement_refs(tasks_data, *, project_has_source_docs)` — [CONFIRMED via GAP_ANALYSIS_v2 §P6]. RuleAdapter must wrap this without changing its signature.
- `contract_validator` signature — [ASSUMED: similar to plan_gate; must grep before implementing RuleAdapter]. STOP if signature grep returns unexpected shape.
- VerdictEngine purity: no wall-clock, no rand, no network. Any `datetime.now()` inside wrapped validators → [UNKNOWN → must check before wrapping; if found, extract to adapter boundary].

**Work:**
1. `app/validation/verdict_engine.py`:
   - `evaluate(artifact, evidence_set, rules) → Verdict{verdict, failed_rules, missing_evidence, risk}` — pure function.
   - `commit(entity, target_state, verdict)` — single write path.
   - Zero wall-clock/rand/network in `evaluate`.
2. `app/validation/rule_adapter.py` — `RuleAdapter` protocol wrapping `plan_gate` + `contract_validator`.
3. Feature flag: `VERDICT_ENGINE_MODE=shadow` — engine runs in parallel with existing `.status=` paths; divergences logged to `verdict_divergences` table (migration required).
4. Shadow run: deploy with `VERDICT_ENGINE_MODE=shadow`. Run for ≥ 1 week on real traffic.

**Exit test T_{A.3} (deterministic):**
```bash
# T1: purity — no wall-clock/rand/network in evaluate()
grep -n "datetime\|random\|requests\|httpx\|time\.sleep" app/validation/verdict_engine.py
# exits 1 (no matches)

# T2: replay harness — determinism
pytest tests/test_verdict_replay.py -x
# PASS: 100 historical executions re-evaluated → bit-identical verdicts

# T3: shadow mode active
pytest tests/test_verdict_shadow.py -x
# PASS: shadow mode logs to verdict_divergences without affecting production writes

# T4: adapter signatures verified
pytest tests/test_rule_adapters.py -x
# PASS: plan_gate + contract_validator wrapped without signature change

# T5: regression
pytest tests/ -x
# all existing tests green

# T6: 1-week shadow production gate
# [MANUAL] distinct actor reviews verdict_divergences table: zero unexplained divergences
# Record: docs/reviews/review-shadow-divergences-by-<actor>-<date>.md
```

**Gate G_{A.3}:** T1–T5 automated pass + T6 distinct-actor review record filed → PASS.
**Note on T6:** This is the only non-automated step in this plan. It cannot be replaced by a grep — it requires a human reading the divergence log. This is explicit per condition 5: LLM-in-loop review is excluded; human review of divergence log is the required distinct actor check (CONTRACT §B.8).

---

## Stage A.4 — Enforcement cutover

**Closes:** P7 (universal gating) — **condition 6 of the soundness theorem fully closed here**.

**Entry conditions:**
- G_{A.3} = PASS including T6 (zero shadow divergences confirmed by distinct actor).

**A_{A.4}:**
- Exact count of `.status=` sites: [CONFIRMED: 75 across 9 files per GAP_ANALYSIS_v2 §0 correction 3].
- Files: `execute.py`, `pipeline.py`, `projects.py`, `tier1.py`, `ui.py`, `hooks_runner.py`, `orphan_recovery.py`, `pipeline_state.py`, `templates/base.html`.
- `templates/base.html` — HTML file. Direct status assignment in template is [ASSUMED: a template variable render, not a Python assignment]. Must check before wrapping: if it's `{{ execution.status }}` (read-only render), it does not need wrapping.

**Work:**
1. Flag flip: `VERDICT_ENGINE_MODE=shadow` → `enforce`.
2. Wrap all 75 `.status = "..."` Python sites behind `VerdictEngine.commit()`.
3. Verify `templates/base.html` — if read-only render, exclude from wrapping. Document exclusion.
4. Pre-commit grep hook: rejects any new `\.status\s*=\s*['"]` outside `app/validation/verdict_engine.py`.
5. Canary: 48h green production traffic.

**Exit test T_{A.4} (deterministic):**
```bash
# T1: zero bypass paths
grep -rn '\.status\s*=\s*["'"'"']' app/ --include="*.py" | grep -v verdict_engine.py
# exits 1 (no matches)

# T2: pre-commit hook active
cat .pre-commit-config.yaml | grep "status.*="
# exits 0 (hook defined)

# T3: HTML exclusion documented
grep -n "status" platform/templates/base.html
# manual check: confirm read-only renders only; document in stage notes

# T4: 48h canary
# [MANUAL] no new errors in production logs for 48h after flag flip
# Record: canary sign-off note in this plan's stage notes

# T5: regression
pytest tests/ -x
# all tests green
```

**Gate G_{A.4}:** T1 grep returns 0 Python matches + T2 hook defined + T3 base.html exclusion confirmed and documented + T5 regression suite green + T4 canary signed off → PASS.
**Condition 6 achieved** [ASSUMED: Q3 resolves to read-only render in base.html; verified by T3 before gate can pass]: from this point, no state transition in the system can occur without passing through a registered gate. If T3 reveals a Python write in base.html that was missed, wrapping of that site is required before condition 6 is valid — do not declare condition 6 satisfied until T3 confirms.

---

## Stage A.5 — MCP idempotency

**Closes:** P1 (idempotence).

**Entry conditions:**
- G_{A.1} = PASS (DB foundation available).
- G_{A.3} = PASS (VerdictEngine interface exists — A.5 integration tests depend on it; per ROADMAP A.5 note "test dep on VerdictEngine"). A.5 *implementation* (DB table, middleware, MCP signatures) may proceed in parallel with A.4 from G_{A.1} + G_{A.3}; A.5 *tests* require VerdictEngine present.
- ADR-004 TTL value CLOSED (required for `expires_at` calculation).

**A_{A.5}:**
- TTL value — [CONFIRMED: ADR-004 CLOSED per Pre-flight]. Specific value read from ADR-004 before implementing.
- 4 mutating MCP tools: `forge_execute`, `forge_deliver`, `forge_decision`, `forge_finding` — [CONFIRMED: listed in CHANGE_PLAN_v2 §2.2.6]. Verify no 5th mutating tool exists before shipping.

**Work:**
1. Alembic migration: `idempotent_calls(id, tool, idempotency_key, args_hash, result_ref, expires_at)`. Unique constraint on `(tool, idempotency_key, args_hash)`.
2. Middleware in `mcp_server/server.py`: on incoming call, check `(tool, key, args_hash)` within TTL → return original result; else execute and record.
3. Add `idempotency_key: str` parameter to `forge_execute`, `forge_deliver`, `forge_decision`, `forge_finding`.

**Exit test T_{A.5} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# T2: idempotency within TTL
pytest tests/test_mcp_idempotency.py -x
# PASS: two identical forge_deliver(idempotency_key="k1") calls within TTL → one row in DB, identical response

# T3: idempotency after TTL
pytest tests/test_mcp_idempotency_expired.py -x
# PASS: same call after TTL expiry → new row created (expected, documented)

# T4: all 4 tools accept idempotency_key
grep -n "def forge_execute\|def forge_deliver\|def forge_decision\|def forge_finding" mcp_server/server.py
# 4 matches, each with idempotency_key in signature

# T5: no 5th mutating tool missed
grep -n "def forge_" mcp_server/server.py | grep -v "forge_challenge\|forge_get\|forge_list\|forge_status"
# manual check: list remaining forge_ functions; document any new mutating tools found

# T6: regression
pytest tests/ -x
# all tests green
```

**Gate G_{A.5}:** T1–T4 automated pass + T5 manual exclusion list documented → PASS.

---

## Phase A exit gate (G_A)

```
G_A = PASS iff:
  G_{A.1} = PASS  (EvidenceSet live, P16/P17 enforced)
  AND G_{A.2} = PASS  (GateRegistry defined)
  AND G_{A.3} = PASS  (VerdictEngine shadow, replay determinism confirmed, distinct-actor review)
  AND G_{A.4} = PASS  (enforcement cutover, zero bypass paths)
  AND G_{A.5} = PASS  (MCP idempotency)
  AND pytest tests/ -x → all existing 420 + new tests green
  AND grep '\.status\s*=\s*["'"'"']' app/ --include="*.py" | grep -v verdict_engine.py → 0 matches
```

**Soundness conditions closed at G_A:**
- **Condition 5** — `∃ T_i: Eval(O_i, T_i) deterministic`: VerdictEngine is a pure function; replay harness confirms bit-identical verdicts on 100 historical cases. [T_{A.3} T2]
- **Condition 6** — `O_i propagates only if G_i = pass`: all state transitions gated through VerdictEngine.commit(); grep invariant = 0. [T_{A.4} T1]
- **Condition 3 (partial)** — EvidenceSet required for every Decision write; no evidence = rejected at gate. [T_{A.1} T3]

**What remains open after Phase A:**
- Condition 1 (RequiredInfo ⊆ C_i): no ContextProjector yet → PLAN_MEMORY_CONTEXT.
- Condition 2 (Suff(C_i, R_i)): no ContractSchema yet → PLAN_CONTRACT_DISCIPLINE.
- Condition 4 (A_i explicit + propagated): assumption tags warn but don't block → PLAN_CONTRACT_DISCIPLINE.
- Condition 7 (Missing→Stop): no BLOCKED state in Execution → PLAN_CONTRACT_DISCIPLINE.

---

## Open questions (UNKNOWN — condition 7 applies, block execution if not resolved)

| # | Question | Blocks |
|---|---|---|
| Q1 | `contract_validator` exact function signature — grep before implementing RuleAdapter | Stage A.3 |
| Q2 | Any `datetime.now()` calls inside `plan_gate` or `contract_validator` — grep before wrapping | Stage A.3 |
| Q3 | Is `templates/base.html` `.status` a read-only render or a Python write? | Stage A.4 |
| Q4 | Are there any mutating `forge_` tools beyond the 4 listed? | Stage A.5 |

Each Q above is tagged [UNKNOWN] per CONTRACT §B.2. Resolution = grep/read the relevant file before the stage that depends on it. If unresolved: STOP stage, do not fill with plausible default.
