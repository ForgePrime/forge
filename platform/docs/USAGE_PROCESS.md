# Forge Usage Process — End-to-End Workflow

> **Status:** DRAFT — pending distinct-actor review per ADR-003. Author: AI agent, same actor as plan corpus (solo-author disclosure per CONTRACT §B.8).
>
> **Purpose:** two-layer document. (1) **Reference model** (§1–§11, §14–§17): describes Forge as a process graph G = (S, D, A, E); verifies against Process Correctness Theorem (§16). (2) **Step-by-step user guide** (§12–§13): concrete click/command walkthroughs for developer, Steward, product-owner, first-time-setup personas.
>
> **Scope:** operational workflow. Internal architecture, per-stage implementation details, and governance ceremonies live in the 6 functional plans + ROADMAP.md.
>
> **Reading paths:**
> - *"I want to actually use Forge now"* → skip to §12 step-by-step walkthrough for your persona.
> - *"I want to understand what Forge IS structurally"* → read §1–§11 + §16 theorem verification.
> - *"I want to know what Forge does NOT handle"* → §15.
> - *"I want honest limitations of this verification"* → §16 "Known limitations" subsection.

---

## 1. What Forge is (and is not)

**Forge is** an evidence-guided software-development platform for orchestrating LLM agents under a deterministic gate layer. It takes a business goal + source documents + existing codebase + past-experience memory and produces a verifiable delivery plan, code changes, tests, runtime evidence, and an auditable proof trail.

**Forge is not:**
- A free-form LLM chat interface (no "just ask the agent" path — every invocation flows through gates).
- A code-completion tool (that's IDE-level; Forge operates at plan → task → change → verification granularity).
- A ticket tracker (though it integrates with one; Forge tracks structured artifacts, not free-text tickets).
- A replacement for human judgment on domain-specific correctness (ratification remains human per ADR-003).

---

## 2. Actors

| Actor | Role | Authority |
|---|---|---|
| **User** (developer / product owner) | Provides goals, documents, clarifications; reviews Forge outputs | Can initiate Projects, approve Decisions, resolve ambiguities |
| **Agent** (LLM-backed automated executor) | Executes stages: extracts evidence, creates Findings, proposes Decisions, authors code | Statistical/prior-driven — outputs bound by gates, not trusted alone per CCEGAP §1 |
| **Steward** (per ADR-007) | Signs off on Critical-tier Decisions, ACKNOWLEDGED_GAPs, rule retirements; rotates per policy | Can override challenger REFUTED (per ADR-013), accept technical debt (per ADR-020), sign Confidential+ classifications |
| **Reviewer** (distinct-actor per ADR-003) | Performs peer review of DRAFT artifacts before NORMATIVE transition | Required for ADR ratification; required for plan-corpus binding status |
| **Challenger** (automated per F.6) | Independent verification of a candidate verdict via `forge_challenge` endpoint | Can REFUTE a Decision; retry policy per ADR-013 |

---

## 3. Process overview — 10 phases

The process is an acyclic DAG of phases with explicit branching at decision nodes and a feedback loop from Phase 10 back into Phase 1 Memory (bounded, not a cycle per §9 topology).

```
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 1: INTAKE                                                     │
│   - User creates Project                                            │
│   - Documents uploaded → Knowledge entities                         │
│   - DataClassification (G.1)                                        │
│   - Evidence extracted → Finding (type=observation|requirement|etc) │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 2: UNDERSTANDING                                              │
│   - Ambiguities detected → Finding(type=ambiguity)                  │
│   - Source conflicts detected (B.7 SourceConflictDetector)          │
│   - UNKNOWN items block progression (F.4)                           │
│   [DECISION: are all blocking UNKNOWNs resolved?]                   │
│     NO  → BLOCKED, await resolve-uncertainty (per ADR-013/F.4)     │
│     YES → proceed                                                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 3: DECOMPOSITION                                              │
│   - Objective authored from goal + Knowledge                        │
│   - KeyResults defined                                              │
│   - ReachabilityCheck (E.4): ≥1 plan template satisfies each KR    │
│   [DECISION: Objective ACTIVATED or BLOCKED?]                       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 4: TASK + CONTRACT                                            │
│   - Task rows per decomposition                                     │
│   - Task.produces typed via ContractSchema (E.1)                    │
│   - AcceptanceCriterion rows (source_ref → Finding type=requirement)│
│   - task_dependencies → CausalEdge (B.2 backfill maintains)         │
│   - Invariants applicable to Task transitions declared (E.2)        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 5: EXECUTION PREPARE                                          │
│   - Execution created (status=pending)                              │
│   - ContextProjector (B.4) computes projection from CausalEdge DAG  │
│   - TimelyDeliveryGate (B.5) at pending→IN_PROGRESS                 │
│   - StructuredTransferGate (F.10): 6 categories structured          │
│   [DECISION: all gates PASS?]                                       │
│     NO  → BLOCKED (missing context / NL-only projection / etc.)    │
│     YES → transition to IN_PROGRESS                                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 6: EXECUTION (LLM call + author Decision)                     │
│   - Prompt assembled from ContextProjection                         │
│   - Model version pinned per ADR-006                                │
│   - LLMCall row records invocation (+ budget enforcement)           │
│   - Agent proposes Decision + evidence + assumption tags (F.3)      │
│   - ExecutionAttempt logged                                         │
│   [DECISION: any untagged non-trivial claim?]                       │
│     YES → REJECTED (F.3); agent must tag + retry                    │
│     NO  → proceed to Phase 7                                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 7: COMMIT VERIFICATION                                        │
│   - EvidenceSet rows attached to Decision (P16/P17)                 │
│   - VerdictEngine.evaluate(artifact, evidence, rules) (A.3)         │
│   - EpistemicProgressCheck (E.7): ≥1 of 7 deltas required           │
│   - ScopeBoundaryCheck (E.8): in_scope ∪ out_of_scope ⊇ ImpactClosur│
│   - For architectural Decision: CandidateSolutionEvaluation (F.11)  │
│   - Invariant check (E.2): check_fn applied post-transition         │
│   - Ambiguity continuity check (F.4 T5): UNKNOWN propagated         │
│   [DECISION: all Verdicts PASS?]                                    │
│     NO  → REJECTED with reason; back to Phase 6 (retry with fix)   │
│     YES → proceed to Phase 8                                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 8: CHANGE DELIVERY                                            │
│   - Change created with expected_diff declared (G.10)               │
│   - Reversibility classified (C.4): REVERSIBLE / COMPENSATABLE /   │
│     RECONSTRUCTABLE / IRREVERSIBLE                                  │
│   - TechnicalDebt markers detected (F.12)                           │
│   [DECISION: any unaccepted debt markers?]                          │
│     YES → REJECTED (author must accept via technical_debt row)     │
│     NO  → proceed                                                   │
│   - Disclosure protocol: 5 delivery sub-fields (F.5)                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 9: RUNTIME VERIFICATION                                       │
│   - Baseline captured (G.10 pre-apply hook)                         │
│   - Delta applied (code commit / migration run / config write)      │
│   - Post captured                                                   │
│   - Diff = ExpectedDiff check                                       │
│   [DECISION: Diff == ExpectedDiff?]                                 │
│     YES → Change.status=APPLIED; proceed to Phase 10                │
│     NO + REVERSIBLE → auto-rollback via C.4; REJECTED               │
│     NO + IRREVERSIBLE → CRITICAL Incident; Steward sign-off req.    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 10: GOVERNANCE + LEARNING (feedback into Phase 1 Memory)      │
│   - ContractViolation logged (G.2) for every REJECTED               │
│   - 7 Metrics collected (G.3): M1..M7                               │
│   - Rule Lifecycle (G.4): rejection_log populated; retirement       │
│     candidates identified                                           │
│   - AutonomyState updated (E.3): Q_n → demote/retain/promote level  │
│   - Weekly evidence replay (F.2): 5% sample re-executed             │
│   - Proof-trail audit (G.9): every Change has 10-link chain         │
│   - Steward quarterly audit (G.5)                                   │
│                                                                     │
│   Outputs feed back into Phase 1:                                   │
│     - New Findings → new Knowledge entries                          │
│     - Rule candidates → new Guideline / MicroSkill                  │
│     - Lessons learned → memory traces for future ContextProjection  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. State space S

All persistent entity states a Forge instance traverses:

```
Knowledge:      CLASSIFIED (Public | Internal | Confidential | Secret)
Finding:        OPEN → RESOLVED | ESCALATED
SourceConflict: OPEN → RESOLVED (via Decision type=conflict_resolution)
Objective:      DRAFT → ACTIVE → COMPLETE | ABANDONED
KeyResult:      PENDING → SATISFIED | UNREACHABLE
Task:           PENDING → READY → IN_PROGRESS → DONE | BLOCKED | ABANDONED
Execution:      pending → IN_PROGRESS → COMMITTED → ACCEPTED | REJECTED | BLOCKED
Decision:       OPEN → CLOSED | DEFERRED | ACCEPTED | MITIGATED
Change:         PROPOSED → APPLIED | REVERTED | DIFF_MISMATCH
TechnicalDebt:  OPEN → RESOLVED (via resolved_by_change_id)
Invariant:      ACTIVE | RETIRED
AutonomyLevel:  L1 | L2 | L3 | L4 | L5 (continuous Q_n underneath)
Rule (G.4):     PROPOSED → ACTIVE → RETIREMENT_CANDIDATE → ARCHIVED
```

---

## 5. Decision nodes D — explicit branching

Every decision node lists **all** branches explicitly (§12 `CompletePartition(d)` — no implicit `else`).

| # | Decision node | Branches | Inputs (Info(d)) |
|---|---|---|---|
| D1 | Classify Knowledge tier | Public / Internal / Confidential / Secret | document content + DataClassification rules (G.1) |
| D2 | Is Finding non-trivial? | YES → must be tagged CONFIRMED/ASSUMED/UNKNOWN / NO → trivial-exempted | CONTRACT §A.2 7 triggers + 3 exceptions (ADR-010 classifier) |
| D3 | Is Ambiguity resolved? | YES → unblock / NO → remain BLOCKED | resolved_uncertainty row existence + accepted_role ∈ allowlist |
| D4 | Source conflict detected? | YES → SourceConflict row + Finding + BLOCKED / NO → proceed | detect_source_conflicts result (B.7) |
| D5 | Objective reachable? | YES → ACTIVATE / NO → BLOCKED on ReachabilityCheck (E.4) | KR list + available plan templates |
| D6 | Projection complete? | YES → transition IN_PROGRESS / NO → BLOCKED (B.5) | context_projection_id + required_context coverage |
| D7 | Projection structured? | YES → LLM call allowed / NO → BLOCKED (F.10) | 6 structural categories non-NULL where required |
| D8 | Non-trivial claim untagged? | YES → REJECT (F.3) / NO → accept tag | ADR-010 classifier result |
| D9 | Execution added epistemic value? | YES → accept / NO → REJECT (E.7) | 7 deltas (Δ1..Δ7 per AD-6) |
| D10 | Scope boundary complete? | YES → accept / NO → REJECT (E.8) | in_scope_refs ∪ out_of_scope_refs vs ImpactClosure |
| D11 | Architectural Decision has ≥2 candidates + argmax selection? | YES → accept / NO → REJECT (F.11) | solution_candidates + solution_scores rows |
| D12 | Change reversibility class? | REVERSIBLE / COMPENSATABLE / RECONSTRUCTABLE / IRREVERSIBLE | Reversibility classifier heuristic (C.4) |
| D13 | Unaccepted debt markers? | YES → REJECT (F.12) / NO → accept | detect_debt_markers + technical_debt rows |
| D14 | Post-apply Diff == ExpectedDiff? | YES → APPLIED / NO+REVERSIBLE → rollback (C.4) / NO+IRREVERSIBLE → Incident + Steward | runtime_observations baseline vs post |
| D15 | Challenger verdict? | ACCEPTED / REFUTED (retry up to N=3) / REFUTED_TERMINAL (Steward override) | forge_challenge response (ADR-013) |
| D16 | Critical tier Decision? | YES → require Steward sign-off (G.5) / NO → proceed | Decision.severity ≥ HIGH |
| D17 | Autonomy level changed? | demote / retain / promote | Q_n observation window result (E.3) |

---

## 6. Actions A — state-mutating operations

Actions are the *side-effect-producing* operations. Each invokes zero or more Decisions.

| Action | Triggers | Preconditions | Postconditions |
|---|---|---|---|
| Ingest document | User uploads | DataClassification assigned | Knowledge row + Finding(s) extracted |
| Create Finding | Agent/user observation | Finding.type ∈ enum | Finding row; CausalEdge to source Knowledge |
| Resolve ambiguity | `POST /executions/{id}/resolve-uncertainty` | accepted_role ∈ allowlist | resolved_uncertainty row; affected Executions may unblock |
| Activate Objective | KR list finalized | ReachabilityCheck PASS | Objective.status=ACTIVE |
| Spawn Task | Objective decomposition | ContractSchema defined for Task.produces | Task row + AcceptanceCriterion rows |
| Create Execution | Task ready | Task.status=READY | Execution.status=pending |
| Run ContextProjector | Execution pending | DAG query reachable | ContextProjection row persisted |
| Transition Execution to IN_PROGRESS | User/agent command | Gates D6+D7 PASS | Execution.status=IN_PROGRESS; baseline may be captured |
| Invoke LLM | Execution IN_PROGRESS | Prompt assembled; model pinned | LLMCall row + ExecutionAttempt |
| Commit Decision | Agent finalizes | D8+D9+D10 PASS + VerdictEngine PASS | Decision + EvidenceSet rows; CausalEdges created |
| Create Change | Decision type=architectural or implementation | D11 PASS if architectural; D13 PASS | Change row with expected_diff + reversibility_class |
| Apply Change | User/auto approves | D12 reversibility acceptable; CI gates pass | Code/DB mutation; Post captured |
| Verify Diff | Post captured | runtime_observations rows exist | Change.status = APPLIED or DIFF_MISMATCH |
| Rollback | D14 NO + REVERSIBLE | rollback_ref defined | state restored to Baseline checksum |
| Steward sign-off | D16 YES or D14 NO + IRREVERSIBLE | ADR-007 Steward identified | AuditLog row; Decision unblocked |
| Retire Rule | Periodic G.4 audit | ≥12 months no triggers | Rule.status=ARCHIVED |

---

## 7. Events E — what triggers transitions

External (user / system) events that enter the process:
- E1: User creates Project
- E2: User uploads document
- E3: User states business goal
- E4: User provides clarification (resolves UNKNOWN)
- E5: Agent extracts evidence (automated)
- E6: Scheduled replay job fires (F.2 weekly)
- E7: Scheduled metrics collection fires (G.3 daily)
- E8: Proof-trail audit cron fires (G.9 nightly)
- E9: Steward begins quarterly review
- E10: ADR SLA timeout (per ADR-025 proposed)
- E11: SecurityIncident confirmed (G.1 kill-criteria)
- E12: CI α-gate triggered on PR
- E13: Rule retirement candidate identified
- E14: Autonomy window W elapsed (E.3)
- E15: Diff mismatch detected
- E16: Challenger REFUTED (F.6)

Every event maps to ≥1 decision node per §4 Event Completeness axiom.

---

## 8. Invariants preserved

Forge preserves the following at every transition (per §5 A5 InvariantPreservation axiom):

| Invariant code | Preserved property | Source |
|---|---|---|
| `inv_exec_in_progress_has_projection` | Execution.status=IN_PROGRESS ⟹ context_projection_id IS NOT NULL | B.5 |
| `inv_decision_has_evidence` | Decision insert ⟹ ≥1 EvidenceSet | A.1 partial P17 |
| `inv_task_done_all_ac_passed` | Task.status=DONE ⟹ all AC.status=PASS | E.2 seed |
| `inv_no_orphan_change` | Change insert ⟹ existing Execution FK | A.1 |
| `inv_blocked_has_reason` | Execution.status=BLOCKED ⟹ blocked_reason ≠ NULL | F.4 |
| `inv_critical_decision_signed` | Decision.severity ≥ HIGH ⟹ steward_sign_off_by ≠ NULL | G.5 |
| `inv_change_has_expected_diff` | Change insert ⟹ expected_diff ≠ NULL | G.10 |
| `inv_debt_has_accepted_by` | technical_debt insert ⟹ accepted_by ≠ NULL | F.12 |
| `inv_causal_acyclicity` | CausalEdge insert ⟹ src.created_at < dst.created_at | B.1 |
| `inv_scope_coverage` | Execution commit ⟹ in_scope ∪ out_of_scope ⊇ ImpactClosure | E.8 |

---

## 9. Information balance at each node (§6 A6+A7)

Per ProcessCorrect §A6 (minimal-sufficient information):

| Node | Info(node) — minimal sufficient set | Information source |
|---|---|---|
| D1 Classify Knowledge | document mime+content+source | Knowledge row |
| D2 Non-trivial? | claim text + CONTRACT §A.2 ruleset | ADR-010 classifier |
| D5 Reachability | KR definitions + plan template registry | Objective + MicroSkill rows |
| D6 Projection complete | ContractSchema.required_context(task) + projection.structured_fields | ContractSchema (E.1) + ContextProjection (B.4) |
| D7 Projection structured | 6 category typed fields | ContextProjection typed fields (F.10) |
| D8 Claim tagging | claim list + classifier output | F.3 validator |
| D9 Delta check | epistemic_snapshot_before + current state | E.7 snapshot |
| D10 Scope boundary | ImpactClosure(change) + in_scope_refs + out_of_scope_refs | C.3 + E.8 |
| D11 Candidate count | solution_candidates + solution_scores | F.11 tables |
| D14 Diff check | runtime_observations baseline + post + expected_diff | G.10 |

InformationBalance(node) approaches 1: each node has exactly what it needs, no more (no "session history fallback" per F.10 grep-gate).

---

## 10. Failure paths + recovery

Per §A2 EventComplete — every failure scenario has an explicit path:

| Failure | Detection | Recovery |
|---|---|---|
| Missing ContextProjection | B.5 gate | Execution stays pending; ContextProjector re-run |
| NL-only projection | F.10 gate | Execution BLOCKED; author re-structures input |
| Untagged non-trivial claim | F.3 | Execution REJECTED; agent re-authors with tags |
| Non-epistemic stage | E.7 | REJECTED with reason=`epistemically_null_stage`; user explicitly resolves or kills |
| Scope boundary gap | E.8 | REJECTED; author declares missing closure elements |
| Single-candidate architectural Decision | F.11 | REJECTED; author generates alternatives |
| Unaccepted debt marker | F.12 | REJECTED; author either removes or accepts via Steward-signed row |
| Diff mismatch REVERSIBLE | G.10 + C.4 | auto-rollback; Finding filed |
| Diff mismatch IRREVERSIBLE | G.10 | system-wide BLOCKED; Steward incident response per ADR-021 |
| Source conflict | B.7 | Execution BLOCKED; Decision(type=conflict_resolution) required |
| Challenger REFUTED | F.6 + ADR-013 | retry up to N=3; then REJECTED; Steward override possible |
| LLM budget exceeded | budget_guard | Execution REJECTED; larger budget requested via new Execution |
| ADR SLA timeout | ADR-025 (proposed) | Steward escalation; Execution BLOCKED depending on ADR |
| Autonomy demote | E.3 Q_n below floor | Level auto-decremented; subsequent Executions run at lower level |

---

## 11. Process graph G = (S, D, A, E) — NARRATIVE SKETCH (not formal adjacency)

> **Disclaimer (self-review):** the notation below is narrative, not a formally-checkable graph. It is useful for human reading but is **not sufficient** to mechanically verify TopologicallyConsistent per §A4 (no unreachable, no dead ends, acyclic modulo bounded feedback). To achieve mechanical verification, this section should be supplemented by `USAGE_PROCESS_GRAPH.dot` + a `scripts/verify_graph_topology.py` validator. Tracked as a known limitation in §15 self-review.

Arrows: `event/condition -> action` causing state transition.

```
INTAKE PHASE:
  E1 [user creates Project]        -> create Project
  E2 [document uploaded]           -> Knowledge(CLASSIFIED); D1
  E5 [agent extracts evidence]     -> Finding(OPEN)
  [SourceConflictDetector]         -> D4; if YES: SourceConflict(OPEN) + BLOCK
  E4 [user clarifies]              -> D3; if YES: resolved_uncertainty

UNDERSTANDING PHASE:
  Finding(type=ambiguity) exists AND not resolved -> BLOCKED (per F.4 + D3)
  D3 YES                                         -> unblock

DECOMPOSITION PHASE:
  user authored Objective  -> D5 Reachability
  D5 YES                   -> Objective(ACTIVE)
  D5 NO                    -> Objective(BLOCKED)

TASK + CONTRACT PHASE:
  Objective(ACTIVE) + decomposition -> Task(PENDING) + AC rows
  Task with deps satisfied           -> Task(READY)

EXECUTION PREPARE:
  Task(READY) + create Execution          -> Execution(pending)
  ContextProjector runs                   -> ContextProjection row
  D6 AND D7                               -> Execution(IN_PROGRESS)
  NOT D6 OR NOT D7                        -> Execution(BLOCKED)

EXECUTION:
  LLM called -> ExecutionAttempt + proposed Decision
  D8 NO AND D9 YES AND D10 YES AND (D11 if arch) -> Decision(OPEN) + EvidenceSet
  any of D8/D9/D10/D11 negative                    -> REJECTED

CHANGE DELIVERY:
  Decision authoritative -> Change(PROPOSED) + ExpectedDiff declared
  D12 classifies reversibility
  NOT D13 AND disclosure complete -> OK to apply

RUNTIME VERIFY:
  Change.apply() -> Baseline + Post captured
  D14 YES      -> Change(APPLIED)
  D14 NO + REVERSIBLE   -> rollback; Change(REVERTED); Finding(OPEN)
  D14 NO + IRREVERSIBLE -> Change(DIFF_MISMATCH); Incident; Steward gate

GOVERNANCE LOOP:
  E6 [weekly replay]    -> F.2 replay; divergence -> Finding
  E7 [daily metrics]    -> metrics_snapshots row
  E8 [nightly audit]    -> proof_trail_audit; gap -> Finding
  E9 [quarterly]        -> Steward audit report
  E14 [window elapsed]  -> AutonomyState recompute -> D17
  E13 [retirement trigger] -> Rule(RETIREMENT_CANDIDATE)
```

---

## 12. Step-by-step — executable walkthroughs

Concrete click/command sequences for the two most common personas.

### 12.A Developer: from ticket to merged Change

**Precondition:** Forge deployed; you have a user account; your Project exists. If not → §12.D.

1. **Navigate to Project.** `GET /projects/{slug}` — dashboard shows current Objectives, open Tasks, blocked Executions.

2. **Paste ticket content.** In the intake panel, paste ticket text + link to source. Forge creates `Knowledge(source_ref=<link>, content=<text>)`.
   - **Check:** a Knowledge row appears in the left sidebar within 2 seconds.
   - **If nothing appears:** check that DataClassification (G.1) didn't block — look for `[BLOCKED: dlp_scan_pending]` badge; resolve per Steward guidance.

3. **Wait for Phase 1 auto-extraction.** Agent runs; extracts candidate Findings (type ∈ {observation, ambiguity, requirement, risk}).
   - **Expected duration:** 30s–2min for typical ticket.
   - **Output:** list of Findings in right sidebar. Each has a `type` badge.

4. **Review ambiguities.** Filter Findings by `type=ambiguity`.
   - **For each ambiguity:** either (a) click "Clarify" → type clarification (writes `resolved_uncertainty` row), OR (b) click "Accept as ASSUMED" → type `accepted-by` role (writes assumption-tag on Finding).
   - **Check:** no `type=ambiguity` Finding with `resolved_at IS NULL` remains for your Objective's scope.
   - **If you cannot decide:** Steward consultation. Do NOT guess — CONTRACT §B.2 violation.

5. **State Objective.** In the Objective panel, type one sentence: "Deliver X such that Y, measured by Z." Forge parses → `Objective(DRAFT)` with inferred KeyResults. Edit KRs if wrong.

6. **Check ReachabilityCheck (D5).** Click "Activate Objective". Forge verifies ≥1 plan template satisfies each KR.
   - **If PASS:** `Objective(ACTIVE)`, proceed to step 7.
   - **If FAIL:** dashboard shows "KR not reachable" with which KR + why. Options: (a) refine KR, (b) create MicroSkill that satisfies it, (c) Steward waiver.

7. **Review auto-decomposed Tasks.** Forge proposes Task breakdown. Each Task has `Task.produces` declared via ContractSchema (typed fields).
   - **Check per Task:** AC list covers positive/negative/edge/boundary scenarios (ADR-001).
   - **Check dependencies:** `task_dependencies` arrows make sense; no cycles (B.1 acyclicity already enforced).
   - **Edit freely:** split, merge, reorder, add AC. Each edit auto-recomputes ImpactClosure.

8. **Trigger Execution.** For the first `Task(READY)`: click "Execute" (manual) OR autonomous picker dequeues.
   - **Execution starts pending.**
   - **B.5 TimelyDeliveryGate fires:** ContextProjector runs; gate checks projection completeness.
   - **F.10 StructuredTransferGate fires:** checks 6 structural categories.
   - **If either fails:** `Execution(BLOCKED)` with `blocked_reason=...`. Fix the reason (add missing ContractSchema field, resolve UNKNOWN, etc.) and re-trigger.

9. **Monitor Execution (IN_PROGRESS).**
   - Dashboard shows live LLMCall attempts + current assumption tags.
   - **Check for F.3 REJECTS:** untagged non-trivial claim → agent retries automatically (up to budget); you may need to intervene if pattern repeats.
   - **Typical time:** 1–20min per Execution depending on Task complexity.

10. **Review Decision (when Execution reaches COMMITTED).**
    - Click Decision → view `recommendation`, `reasoning`, `EvidenceSet` rows, `alternatives_considered`, `assumption tags`.
    - **If `Decision.type='architectural':`** verify F.11 ≥2 candidates visible + Score table + argmax selection highlighted.
    - **VerdictEngine verdict:** shown as badge (ACCEPTED / REJECTED / BLOCKED). If REJECTED → read `reason`; re-execute with fix.
    - **EpistemicProgressCheck:** shown as 7-delta status; at least one must be ticked.

11. **Review Change (if delivery).**
    - If Decision yields a Change, Change panel shows `expected_diff` JSONB + reversibility class + any `technical_debt` markers detected.
    - **Check `technical_debt`:** if any TODO/HACK/FIXME detected, each must have a `technical_debt` row with `accepted_by` ∈ ADR-020 allowlist. Accept via Steward (if you're not Steward) or as tech_lead (if ADR-020 allows).
    - **Review disclosure:** 5 sub-fields (CONTRACT §B1–B5).

12. **Approve apply.** Click "Apply Change".
    - **G.10 pre-apply hook:** Baseline captured via snapshot_validator (5 components per ADR-009).
    - **Delta executes:** git commit / alembic migration / config write.
    - **G.10 post-apply hook:** Post captured; Diff computed; compared to `expected_diff`.
    - **If Diff == ExpectedDiff:** `Change(APPLIED)`. Success.
    - **If Diff ≠ ExpectedDiff + REVERSIBLE:** auto-rollback via C.4; Finding filed. Read Finding, fix, retry.
    - **If Diff ≠ ExpectedDiff + IRREVERSIBLE:** CRITICAL Incident. Steward must sign off on recovery per ADR-021 (options: compensating Change, accept deviation with signed record, or revert via out-of-band procedure).

13. **Ship.** `Change(APPLIED)` → PR auto-created (or manual merge); CI α-gate runs risk-weighted coverage check (D.5).
    - **If coverage ≥ α per capability:** merge allowed.
    - **If below α:** add tests OR accept as technical_debt (F.12).

14. **Post-merge:** Execution enters Phase 10 Governance loop. Metrics update (G.3). Rule prevention log updates (G.4). You can close the Task; if AC coverage triggers Task(DONE), happens automatically.

**Total elapsed time for simple change:** 10–45 minutes including LLM latency. For complex architectural Decision with F.11 candidate evaluation: 1–4 hours.

---

### 12.B Steward: quarterly audit

**Precondition:** you are the appointed Steward per ADR-007. Login has `steward_role=true`.

1. **Open governance dashboard.** `GET /projects/{slug}/governance/quarterly-audit`.
2. **Review open SourceConflicts.** For each `SourceConflict(OPEN)`:
   - Read conflicting Knowledge rows side-by-side.
   - Decide winning source (or mark both as `UNKNOWN` blocking).
   - File `Decision(type='conflict_resolution', resolves_conflict_id=X)` with EvidenceSet citing rationale.
3. **Review pending `technical_debt`.** For each unaccepted debt row: either sign off (`accepted_by=<you>`, `accepted_role='steward'`) or REJECT via Change reversal.
4. **Review retirement candidates.** `GET /rules/review` shows rules with 12-month zero prevention log. For each: approve archive (Rule.status=ARCHIVED) or retain (reset clock with justification).
5. **Review ACKNOWLEDGED_GAPs.** FRAMEWORK_MAPPING §12 gaps needing refresh signature. Re-sign or escalate.
6. **Sign critical Decisions.** `GET /decisions?severity=HIGH&steward_sign_off_by IS NULL`. For each: review + sign or REJECT.
7. **Generate quarterly report.** `python scripts/steward_quarterly_report.py` produces audit PDF + metrics snapshot.

**Typical duration:** 2–4 hours per quarter.

---

### 12.C Product owner: vague requirement → refined Objective

**Precondition:** you have stakeholder docs but unclear "what" or "why".

1. **Upload stakeholder materials** (emails, meeting notes, wireframes) → Knowledge.
2. **Stop at Phase 2:** Forge surfaces Findings (ambiguity rate typically high for vague input).
3. **Resolve each ambiguity** via clarification panel. If you can't resolve without stakeholder input → schedule stakeholder sync; mark Finding as `UNKNOWN blocked by stakeholder_sync_<date>`.
4. **Iterate:** add more Knowledge as stakeholder sync produces clarifications.
5. **State Objective:** when UNKNOWN count drops to zero (or all remaining are accepted ASSUMED with `accepted-by=you`).
6. **ReachabilityCheck (D5):** if FAIL, narrow Objective scope or add plan template via MicroSkill creation.
7. **Handoff to developer:** Objective(ACTIVE) + decomposed Tasks + AC → developer continues from §12.A step 8.

---

### 12.D First-time setup (Project creation)

**Precondition:** Forge platform deployed + you have admin credentials.

1. **Create Organization:** `POST /organizations {name: "..."}`.
2. **Create Project:** `POST /projects {org_id, slug, name, ceremony_level: "STANDARD"}` (ceremony per ADR-002).
3. **Configure data tier policy:** per ADR-018 — either set up Presidio endpoint OR create ACKNOWLEDGED_GAP record with Steward sign-off.
4. **Seed MicroSkills + Guidelines:** upload your team's existing process docs → OutputContract rows.
5. **Run Stage 0.3 smoke test:** `python scripts/smoke_test_tracker.py --project-slug=X` — verifies IMPLEMENTATION_TRACKER claims match actual code.
6. **Project READY:** proceed to §12.A for first ticket.

---

## 13. Who-does-what quickref (high-level)

Four typical usage personas + their entry points:

### Persona 1: Developer with a ticket
1. Create Project + link to ticket system
2. Upload ticket/docs → Knowledge
3. State goal (user input) → Objective(DRAFT)
4. Agent executes Phases 2–9 autonomously; user monitors
5. Review final Change(APPLIED) + proof trail

### Persona 2: Product owner with vague requirements
1. Create Project
2. Upload stakeholder docs → Knowledge
3. Stop at Phase 2: Forge surfaces ambiguities
4. Resolve ambiguities via `POST /resolve-uncertainty`
5. Phase 3 ReachabilityCheck: if fails, refine Objective
6. Handoff to developer for Phase 4+

### Persona 3: Steward performing quarterly audit
1. Open governance dashboard
2. Review open Findings, SourceConflicts, unaccepted debt
3. Sign off on Critical Decisions (G.5)
4. Approve rule retirements (G.4)
5. Sign ACKNOWLEDGED_GAP records

### Persona 4: Autonomous agent on long-horizon task
1. Fetch work queue: READY Tasks
2. For each Task: iterate Phases 5–9
3. On REJECTED: file Finding, adjust approach, retry (bounded by ADR-013 N=3)
4. On Diff mismatch: rollback (REVERSIBLE) or escalate (IRREVERSIBLE)
5. Periodic: check AutonomyState — if demoted, narrow scope

---

## 14. Failure scenarios (ASPS §11)

Applying the 9 canonical scenarios to the usage process itself:

| # | Scenario | Status | Mechanism |
|---|---|---|---|
| 1 | null_or_empty_input | Handled | Empty document at Phase 1 → no Knowledge row; empty goal → ReachabilityCheck fails (D5) |
| 2 | timeout_or_dependency_failure | Handled | LLM timeout → ExecutionAttempt error; budget_guard; retry via ADR-013 N=3 |
| 3 | repeated_execution | Handled | A.5 MCP idempotency; ContextProjector deterministic (B.4 T3) |
| 4 | missing_permissions | Handled | Role-based allowlist per ADR-020 + ADR-007 Steward authorization |
| 5 | migration_or_old_data_shape | Handled | Alembic round-trip per migration; retroactive Stage 0 per ADR-008 |
| 6 | frontend_not_updated | PARTIAL (corrected) | Forge is backend-heavy with some UI touch-points: G.1 Confidential+ banner, G.3 `/metrics` endpoint, G.6 11 artifacts (some UI-surfaced). Scope of UI remains minimal in current phases; full front-end change discipline not yet covered. If product scope expands to developer-facing UI, revisit via new ADR. Previous "JustifiedNotApplicable" was too lightweight. |
| 7 | rollback_or_restore | Handled | C.4 Reversibility + Rollback service; G.10 auto-rollback on Diff mismatch |
| 8 | monday_morning_user_state | Handled | All state DB-persisted; AutonomyState window W absolute-time based; no session state |
| 9 | warsaw_missing_data | JustifiedNotApplicable | Forge is LLM-orchestration platform, not geographic/regional data pipeline |

---

## 15. Boundary: what Forge does NOT handle

Explicit scope exclusions (per FC §15 Change Set Completeness + E.8 ScopeBoundaryDeclaration analogy):

- **Domain-specific correctness** — Forge enforces process discipline; the *content* correctness (is this SQL query semantically correct?) remains with domain expert per ADR-003.
- **UI/UX decisions** — Forge operates on structured artifacts; UI design is external.
- **Organizational / political decisions** — Forge produces evidence; who acts on evidence is org-level (Steward per ADR-007).
- **Hardware operations / infrastructure provisioning** — Forge assumes the platform runs; provisioning is DevOps scope.
- **Security incident response** — Forge detects (G.1 kill-criteria); response procedure per ADR-008 lives in security runbook.

---

## 16. Process Correctness theorem verification

Applying ProcessCorrect(G) theorem to this usage process:

> `ProcessCorrect(G) iff FunctionallyComplete ∧ EventComplete ∧ TopologicallyConsistent ∧ LocallyDeterministic ∧ InvariantPreserving ∧ InformationBalanced ∧ NoGaps ∧ NoRedundancy ∧ SemanticsPreserved ∧ Continuous ∧ Differentiable ∧ LocallyImpactBounded ∧ DecisionComplete`

**Verification per condition:**

### ✅ FunctionallyComplete (A1)
Every Forge function (plan stage) has a path in G: §3 lists 10 phases mapping to all 54 stages. §11 graph notation shows path existence.

### ✅ EventComplete (A2)
All 16 events E1–E16 listed in §7 map to ≥1 decision node in §5. Failure paths §10 cover non-happy events (timeouts, errors, mismatches).

### ✅ TopologicallyConsistent (A4)
- No unreachable nodes: every phase has an ingress (Phase N → N+1 or feedback loop Phase 10 → Phase 1 Memory); §3 graph is acyclic except for bounded feedback.
- No dead ends: every leaf state either terminates explicitly (Change.APPLIED is terminal for successful delivery) or returns to valid state (REJECTED → retry loop bounded by ADR-013 N=3).
- No unjustified cycles: feedback from Phase 10 to Phase 1 is **bounded** (adds memory entries, doesn't re-execute current Task).

### ✅ LocallyDeterministic (A3)
§5 table shows (state, event, condition) → exactly one decision at each node. Explicit branching where multiple outputs possible (e.g. D14 has 3 branches, all enumerated).

### ✅ InvariantPreserving (A5)
§8 lists 10 invariants enforced at transitions. All E.2 Invariant.check_fn calls run post-commit per ADR-005 (Python callable, read-only session). Any violation → REJECTED + state revert.

### ✅ InformationBalanced (A6+A7)
§9 table: each decision node has minimal-sufficient Info(node). No leaking of unnecessary context per F.10 grep-gate (no `session_context` fallback). InformationBalance approaches 1: required=available at each decision.

### ✅ NoGaps (C4)
Every requirement covered: Phase 1 extracts Findings → Phase 3 traces to Objective → Phase 4 decomposes to Task+AC → Phase 7 evidence-checks → Phase 8 delivers Change → Phase 9 runtime-verifies. G.9 proof-trail audit mechanically asserts 10-link chain for every Change.

### ✅ NoRedundancy (C5)
Every element in G links to Forge F or Spec: every phase has a named FORMAL property closure (P1–P25); every decision has a theorem condition it enforces (CCEGAP C1–C7, ECITP C3+C6+C7+C8+C11+C12, FC §8+§15+§16-§19+§25-§26+§37). No orphan nodes.

### ⚠️ SemanticsPreserved (§10) — PARTIAL (not emergent, genuinely partial)
Forge's SemanticsPreserved claim depends on ContractSchema self-adjointness (E.1): `render_prompt_fragment()` and `validator_rules()` derive from one source, guaranteeing that business-meaning encoded in Task.produces equals what the agent is asked AND what is validated. HOWEVER: semantic preservation across the entire chain (Knowledge → Finding → Objective → Task → AC → Decision → Change) depends on every author at every phase correctly capturing intent — this is not mechanically enforced. **No single "SemanticsCheck" validator exists.** Self-review retraction: earlier draft claimed "emergent from 21 G_GOV checks" — that claim is retoric, not mathematical. The theorem states `Semantics(F) = Semantics(G)` as a condition on the process; lacking a mechanism that tests this equality end-to-end, the condition is NOT mechanically satisfied. Status: PARTIAL.

### ✅ Continuous (§9)
Small change in Spec → bounded change in G: C.3 ImpactClosure + C.4 Reversibility provide bounded-propagation mechanism. G.9 T7 bounded-revision test mechanically verifies for 10 historical PRs.

### ✅ Differentiable (§8 A8)
Change(x) affects DependentSubgraph(x): exactly what C.3 ImpactClosure computes. Exit test T_{C.3} T1 asserts closure correctness. Deliberately equivalent to ProcessCorrect §8 by construction.

### ✅ LocallyImpactBounded (§8 A8 same)
Same mechanism as Differentiable; E.8 ScopeBoundaryDeclaration enforces at commit time.

### ✅ DecisionComplete (§12)
§5 table explicitly enumerates all branches per decision. No implicit `else` — every decision has complete partition. F.3 validator enforces this structurally (untagged claim → REJECT, not silent default).

**Overall verdict per theorem:** **12/13 ✅ SATISFIED STRUCTURALLY; 1 PARTIAL** (SemanticsPreserved — cross-stage intent equality is not mechanically tested).

**Closing the SemanticsPreserved gap would require:** a new stage that explicitly verifies intent equivalence across the chain — e.g., semantic-snapshot at each phase transition + equality check. This is **NOT** currently planned. Tracked as known gap for future iteration (proposed ADR-027: end-to-end intent-equivalence validation). See also §16 corollary discussion.

### Known limitations of this verification (self-review)

Honest disclosure — this verification has 4 additional weaknesses beyond the SemanticsPreserved PARTIAL:

1. **§11 graph is narrative, not formal.** I described G = (S, D, A, E) in ASCII and prose, but did not produce a formally-checkable adjacency list (e.g., graphviz DOT, JSON edge-list). Consequently, TopologicallyConsistent verification is *aspirational inspection*, not mechanical proof. Graph-level properties (no unreachable, no dead ends, acyclicity modulo bounded feedback) have not been algorithmically verified. To close: produce `USAGE_PROCESS_GRAPH.dot` + run `python scripts/verify_graph_topology.py` checking reachability + acyclicity + dead-end detection.

2. **F (set of Forge functions) is implicitly defined.** FunctionallyComplete requires `∀ f ∈ F: ∃ path in G`. I treated `F = 54 plan stages`. Under different interpretations (F = API endpoints / F = business capabilities / F = MicroSkill registry) the verdict may differ. Declare: **`F := current ROADMAP 54 stages`** canonical for this verification. Alternative F interpretations require separate verification.

3. **Phase 10 → Phase 1 feedback loop is not mechanically bounded.** §3 states feedback is "bounded, not a cycle" but no mechanism limits propagation of newly-learned rules into currently-active Tasks. Possible failure: a Phase 10 Rule Lifecycle retirement decision invalidates an Invariant that an IN_PROGRESS Execution depends on → mid-flight instability. Closing this gap requires: explicit "memory-version pinning" per Execution (capture Rule snapshot at IN_PROGRESS transition; subsequent Rule changes don't affect in-flight Executions). **NOT currently in plan corpus.**

4. **§13 frontend_not_updated downgraded from JustifiedNotApplicable to PARTIAL.** G.6 explicitly tracks 11 artifacts some of which have UI touch-points (e.g., `/projects/{slug}/metrics` endpoint, UI banner for Confidential+ without DLP per G.1). JustifiedNotApplicable was too lightweight. Corrected status: PARTIAL — backend-heavy with some UI elements; full UI scope out of Forge's current phase coverage (if product scope expands to developer-facing UI, revisit via ADR).

**Corrected summary:** 12/13 mechanically satisfied + 1 partial + 4 weaknesses in verification method. This is NOT a "mostly fine" verdict — any process claim based on this document should cite which of the 4 method-weaknesses affects it.

---

## 17. Corollary verification (§16)

| Corollary | Application to Forge |
|---|---|
| **C1:** No differentiability ⇒ uncontrollable | ImpactClosure (C.3) provides differentiability; Change.expected_diff (G.10) provides boundedness. Without these: uncontrolled change propagation. ✅ addressed. |
| **C2:** No information balance ⇒ wrong decisions or chaos | Each decision node has explicit Info(d) set (§9); B.5 + F.10 enforce minimal-sufficient. ✅ addressed. |
| **C3:** No event coverage ⇒ production bugs | §7+§10 cover 16 events including failure scenarios. ✅ addressed. |
| **C4:** No explicit decisions ⇒ hidden logic | §5 enumerates all 17 decision nodes with explicit branches. F.3 rejects untagged claims. ✅ addressed. |

---

## 18. Status + what this document does (and doesn't) bind

**Binds:**
- DRAFT — descriptive model of Forge usage; not NORMATIVE until distinct-actor reviewed per ADR-003.
- Authors who implement plan stages SHOULD check their implementation against this usage-process narrative for cross-stage coherence.

**Does not bind:**
- Implementation details per stage (lives in 6 functional plans).
- ADR decisions (live in decisions/).
- User onboarding tutorial (should exist separately, cross-referenced).

**Supersedes:** partially supersedes `platform/docs/platform/WORKFLOW.md` if the two conflict. Final supersession decision: distinct-actor review pending.

---

## Authorship + versioning

- v1 (2026-04-24) — initial draft + ProcessCorrect verification. Author: AI agent (solo).
- Next version: after distinct-actor review per ADR-003.
