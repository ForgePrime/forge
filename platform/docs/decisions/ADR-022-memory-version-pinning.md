# ADR-022 — Memory-version pinning per Execution (bounded Phase 10→1 feedback)

**Status:** CLOSED (content DRAFT — pending distinct-actor review per ADR-003) [ASSUMED: AI-recommendation, solo-author per CONTRACT §B.8]
**Date:** 2026-04-24
**Authored by:** Claude (Opus 4.7, 1M context)
**Decided by:** user (mass-accept) + AI agent (draft)
**Related:** USAGE_PROCESS.md §16 method-weakness #3, Phase 10 Governance + Learning loop, Phase B Memory/Context, ECITP §2.7 additive exploration, FC §36 Learning Loop.

## Context

### The problem

Per USAGE_PROCESS.md §16 self-review, the Phase 10 → Phase 1 feedback loop is mechanically unbounded. When G.4 Rule Lifecycle retirement / new MicroSkill / new Guideline / new Memory entry is produced in Phase 10, it becomes available to *all subsequent* ContextProjector invocations — including Executions currently IN_PROGRESS. This creates:

1. **Mid-flight instability** — an Execution started at t_0 with projection P(t_0) may be evaluated at t_1 against rules created between t_0 and t_1 it could not have incorporated.
2. **Non-reproducibility** — re-running the same Execution at t_1 vs t_0 produces different projection (different memory state), violating P6 determinism within the scope of "same task + same inputs".
3. **Silent learning cycles** — new rule retires old invariant → in-flight Execution depends on old invariant → invariant no longer active → Execution passes gate it should fail (or vice versa).

Per ProcessCorrect §A4 TopologicallyConsistent, "unjustified cycles" violate topology. Feedback is justified only if it is *bounded* — change at time t does not affect Executions started before t.

USAGE_PROCESS_GRAPH.dot marks the `A_MEMORY_UPDATE -> START` edge as `kind="bounded_feedback"` — this ADR specifies what "bounded" means operationally.

### Why this matters beyond "race conditions"

This is not a concurrency bug; it is an *epistemic* boundary. CCEGAP §C1 + ECITP §2.3 require that an Execution's `C_i` (context) is fixed at the start of stage i. If memory evolves between stage-start and stage-commit, the reasoning trace is logically incoherent — the agent's reasoning rests on context that no longer reflects the deployed ruleset. Hence ECITP §2.8 prior-substitution: agent's output cannot be grounded in its input context because the context is no longer the input context.

## Decision

**Per-Execution memory snapshot pinning at `pending → IN_PROGRESS` transition (B.5 TimelyDeliveryGate extension).**

### Mechanism

1. **Schema extension**:
   ```sql
   ALTER TABLE executions ADD COLUMN memory_version_pin JSONB NOT NULL DEFAULT '{}'::jsonb;
   -- Example structure:
   -- {
   --   "rule_version_ids": ["rule-abc123", "rule-def456", ...],
   --   "microskill_version_ids": ["ms-xyz789", ...],
   --   "guideline_version_ids": ["gl-pqr321", ...],
   --   "invariant_version_ids": ["inv-stu654", ...],
   --   "pinned_at": "2026-04-24T14:30:00Z",
   --   "pin_sha256": "<hash of sorted version_ids>"
   -- }
   ```

2. **Version-id columns on memory-carrying tables**:
   - `rules.version_id UUID NOT NULL`
   - `microskills.version_id UUID NOT NULL`
   - `guidelines.version_id UUID NOT NULL`
   - `invariants.version_id UUID NOT NULL`
   - Each new row = new `version_id` (immutable). Updates create new rows (append-only within the entity lifecycle), never mutate in-place.

3. **Pin capture at transition (B.5 extension)**:
   - When Execution transitions `pending → IN_PROGRESS`, B.5 TimelyDeliveryGate additionally captures `memory_version_pin` by snapshotting the current ACTIVE version_ids of rules/microskills/guidelines/invariants relevant to the task (filtered by `scope_tags ∪ requirement_refs`).
   - Pin is immutable after capture.

4. **ContextProjector + VerdictEngine read from pin**:
   - `ContextProjector.project(task, budget, memory_version_pin)` filters memory entities by `version_id IN pin.rule_version_ids` etc.
   - `VerdictEngine.evaluate(artifact, evidence, rules=resolve_rules(pin))` uses only pinned rule versions; new rules created post-pin are invisible to this Execution.
   - New Executions (post-pin creation) get current pin, reflecting latest memory.

5. **G.4 Rule Lifecycle behavior**:
   - Rule retirement creates `rules.status='ARCHIVED'` + new version_id (archived state). It does NOT delete rows.
   - In-flight Executions pinned to the ACTIVE version continue using it; their outcome references the pre-retirement version_id in audit trail.
   - New Executions (post-retirement) get pin without the retired rule.

6. **Pin expiration** (for terminated Executions):
   - Once Execution reaches terminal state (ACCEPTED / REJECTED / BLOCKED_RESOLVED), pin is retained for audit but no longer referenced by live code paths.
   - Archive policy: `memory_version_pin` retained for `audit_retention_period` (default 7 years per regulatory practice; ADR-028 if specialization needed).

### Exit-test contract (B.5 T7 strengthening)

- **T7a**: Execution with `memory_version_pin.rule_version_ids` referencing ARCHIVED rule → ContextProjector still includes that rule for this Execution (not the latest ACTIVE). Assertion: `pin-respect` property.
- **T7b**: Two Executions started minutes apart with a Rule retirement between them → Execution_A sees old rule, Execution_B sees no rule. Both Executions consistent within themselves.
- **T7c**: `memory_version_pin` immutable after transition → attempted mutation raises `ImmutablePinError`.
- **T7d**: Hypothesis property: for 10,000 random (task, N_memory_entities, retire_timing) combinations, pinned Executions complete deterministically.

## Rationale

1. **ProcessCorrect §A4 topology requirement** — unbounded feedback cycles violate TopologicallyConsistent. This ADR is the specification that makes `bounded_feedback` edge in USAGE_PROCESS_GRAPH.dot verifiable: bounded = pinned at entry, no mid-flight mutation.

2. **P6 determinism preservation** — same (task, inputs, pin) → same Verdict. Without pinning, determinism breaks across retries that span memory updates.

3. **ECITP §2.7 additive exploration alignment** — additive progression means *new* stages add to memory; they don't retroactively rewrite memory for *prior* stages. Pinning implements the "unless explicit invalidation is recorded" clause of §2.7 at Execution scope.

4. **Audit trail integrity** — every Verdict is attributable to a specific rule version. Future audit can reproduce the Execution's decision by resolving the pin → the exact memory state at decision time.

5. **Implementation simplicity** — memory entities already have `id` and can add `version_id` (UUID) without major schema changes. Immutability is enforced by append-only discipline; no complex transaction-isolation semantics required.

## Alternatives considered

### A. Runtime memory version lock via transaction isolation (SERIALIZABLE)

**Rejected.** Transaction isolation addresses concurrent-write-during-read; it does not address "memory rule updated between Execution-start and Execution-commit". SERIALIZABLE prevents inconsistent reads within a transaction, but Executions span many transactions (hours or days in Autonomous mode). Isolation is complementary, not substitute.

### B. Snapshot entire memory DB at transition (full-state pin)

**Rejected.** Full-DB snapshot is expensive + unnecessary for most Executions; pinning only *relevant* memory (filtered by `scope_tags`) satisfies the bound without O(DB) cost per Execution. Full snapshot remains available as opt-in for high-ceremony Executions (P0 risk or regulatory compliance scope) via future ADR extension.

### C. No pinning — accept mid-flight updates as "normal" with no guarantee

**Rejected.** Violates ProcessCorrect §A4 + P6 determinism. Matches current unbounded state = the problem this ADR is designed to solve.

### D. Pin only invariants, not rules (selective pinning)

**Rejected at current scope.** All memory categories (rules, microskills, guidelines, invariants) influence Executions equally. Partial pinning creates subtle gaps. May be revisited if performance cost of full pinning proves unacceptable.

## Consequences

### Immediate

1. 4 memory-carrying tables gain `version_id UUID NOT NULL` column (rules, microskills, guidelines, invariants).
2. `executions.memory_version_pin JSONB NOT NULL DEFAULT '{}'::jsonb` added.
3. B.5 TimelyDeliveryGate extended to capture pin at transition.
4. ContextProjector + VerdictEngine read-paths updated to use pin instead of latest-live.
5. USAGE_PROCESS_GRAPH.dot `bounded_feedback` edge on `A_MEMORY_UPDATE -> START` now has mechanical backing (verifier can check pin-presence in CI).

### Downstream

- G.4 Rule Lifecycle becomes append-only (retirement = new version, not UPDATE). Retirement workflow documentation updated.
- G.9 ProofTrailCompleteness audit includes pin verification: every Change's Execution had a valid pin.
- ADR-006 (model version pinning) is the *model-version* analogue of this ADR for *memory-version* pinning — both follow "capture at start, immutable during" pattern.
- R-GOV-01 class risks: pinning is additional mechanism against AI reasoning drifting from spec state.

### Risks

1. **Pin size growth** — for projects with thousands of memory entities, pin JSONB grows. Mitigation: pin stores only entities in `scope_tags ∪ requirement_refs` subgraph, typically 10-100 entries.
2. **Version_id proliferation** — append-only discipline means memory tables grow indefinitely. Mitigation: periodic vacuum (archive non-referenced version_ids after audit retention period).
3. **Testing burden** — every test scenario must consider pin state. Mitigation: test fixtures auto-generate pins for consistency.

### Reversibility

REVERSIBLE — pin reading can be disabled via feature flag `MEMORY_PIN_ENFORCEMENT=off` (reverts to latest-live behavior). However, any Executions completed WITH pinning retain their pinned audit trail; reverting only affects future Executions.

## Evidence

- **[CONFIRMED]** USAGE_PROCESS.md §16 method-weakness #3 text identifies this gap — direct quote:
  > "Phase 10 → Phase 1 feedback loop is not mechanically bounded. §3 states feedback is 'bounded, not a cycle' but no mechanism limits propagation of newly-learned rules into currently-active Tasks."
- **[CONFIRMED]** USAGE_PROCESS_GRAPH.dot edge `A_MEMORY_UPDATE -> START [kind="bounded_feedback", label="... (bounded per ADR-022)"]` — this ADR is the reference.
- **[CONFIRMED]** `scripts/verify_graph_topology.py` Check 3 passes with the bounded_feedback edge marked — test output on 2026-04-24: "no cycles except bounded-tagged edges".
- **[ASSUMED]** Size estimates (pin typically 10-100 entries) based on expected task-scope filtering; empirical measurement after 3 months production required.
- **[UNKNOWN]** Performance impact of pin-resolution at ContextProjector call — needs benchmark before finalization.

## Supersedes

none

## Versioning

- v1 (2026-04-24) — initial DRAFT, authored alongside USAGE_PROCESS_GRAPH.dot as the bounding mechanism for Phase 10→1 feedback.
