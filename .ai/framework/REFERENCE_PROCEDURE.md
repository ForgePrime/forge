# Reference Procedure — Framework-level Skill Specification

> **Status:** DRAFT — pending distinct-actor review per [`platform/docs/decisions/ADR-003`](../../platform/docs/decisions/ADR-003-human-reviewer-normative-transition.md). Becomes NORMATIVE on review sign-off.
> **Version:** v1 (2026-05-05). Adopted via [ADR-029](../../platform/docs/decisions/ADR-029-procedural-cards.md).
> **Scope:** procedural twin of `OPERATING_MODEL.md`. Where OPERATING_MODEL describes WHAT must hold (layers, stages, artifacts, metrics), REFERENCE_PROCEDURE describes HOW work executes step by step — implementation-agnostic, executable by human or platform.

---

## §0 Why this exists

OPERATING_MODEL §1–§7 define structure. They do not define a deterministic procedure for how a contributor proceeds from "task arrives" to "task closed." That procedure existed implicitly in `platform/docs/USAGE_PROCESS.md` and `platform/docs/MASTER_IMPLEMENTATION_PLAN.md` — but only as Forge-specific instantiations.

A framework that does not specify procedure cannot guarantee repeatability across teams, tools, or implementations. This document closes that gap by lifting Forge's procedural artifacts to framework abstraction.

Forge (`platform/`) becomes one specific instantiation of the procedure described here. Other implementations — manual, alternative tooling — are valid if they satisfy the same gates with the same evidence tiers.

---

## §1 Grammar — Procedural Card

A Procedural Card is a tuple:

```
Card = (
  card_id:    str,                  # unique identifier
  trigger:    Trigger,              # when this card fires
  prereq:     [Predicate],          # must hold before card starts
  steps:      [Step],               # ordered sequence
  exit_gate:  Predicate             # terminal condition
)

Trigger = (
  task_type:        TaskType,       # feature | bug | analysis | refactor | hotfix | classification
  ceremony_level:   CeremonyLevel,  # LIGHT | STANDARD | FULL
  optional_filters: dict            # e.g., ac_count, scope_threshold
)

Step = (
  step_id:              str,             # e.g., S1, S2
  cgaid_stage:          int,             # 0..4
  action_type:          ActionType,      # one of 6 (see §2)
  action_payload:       str,             # concrete action description
  manual_fallback:      str,             # how a human executes without tooling
  evidence_obligation:  EvidenceObligation,
  gate:                 [Predicate]      # blocks transition to next step
)
```

`manual_fallback` is a per-step attribute, **not a separate action_type**. Every step has one. This is what makes the procedure executable without Claude or Forge.

---

## §2 Action types — six

| # | action_type | When to use | Evidence character |
|---|---|---|---|
| 1 | `direct_skill` | An existing skill in `.claude/skills/` covers this action | Skill output (artifact + tags) |
| 2 | `meta_prompt` | Task requires deep context that a single prompt won't capture; spawn an Agent to write a prompt with explicit knowledge gathering, then execute | Audited Agent report with file:line citations |
| 3 | `opinion_prime` | Domain framing not covered by skills; persona-based prompting | Audited persona output with concrete findings |
| 4 | `theorem_check` | Verification against a formal correctness criterion | Mechanical pass/fail report against theorem conditions |
| 5 | `rubric_check` | Verification against a decision tree / rubric (no theorem available) | Mechanical pass/fail against rubric branches |
| 6 | `risk_probe` | Adversarial / risk surfacing | Risk register entries with composite scores |

**Compositionality:** action_types 2 and 3 (`meta_prompt`, `opinion_prime`) are orthogonal layers of prompt construction (WHAT structure × WHO the agent thinks it is) and may compose in a single step. Empirical validation of composition is deferred to first use [ASSUMED].

**Non-determinism warning:** action_types 2 and 3 are non-deterministic — output depends on Agent interpretation. Their `evidence_obligation` MUST therefore produce an auditable artifact (file:line claims, not "agent said OK"). See R1, R2 in §4.

---

## §3 evidence_obligation schema

```
EvidenceObligation = (
  artifact:    str,       # concrete product (file path, record id, artifact name)
  claims:      [Claim],   # what the artifact must establish
  min_tier:    Tier,      # T1 | T2 | T3
  unknowns:    [str],     # open [UNKNOWN] items
  freshness:   str,       # step | card | session
  trace_link:  str        # archive location
)

Claim = (
  statement:   str,
  epistemic:   CONFIRMED | ASSUMED | UNKNOWN,
  tier:        Tier,
  acceptance:  str        # deterministic predicate over artifact
)

Tier ∈ {T1, T2, T3}
  T1 = citation file:line — quotable evidence (lowest cost)
  T2 = execution + observable output — reproducible by re-running same command
  T3 = independent reproduction by distinct actor (strictest; satisfies P18)
```

Tier semantics align with `CONTRACT.md §B.2` (CONFIRMED admits both citation and execution) and `platform/docs/FORMAL_PROPERTIES_v2.md` P18 (Verifiability — strictest at T3).

---

## §4 Invariant rules — auditable

A card is well-formed iff all six rules hold. Each is mechanically checkable.

| # | Rule | Check |
|---|---|---|
| R1 | Non-empty artifact | `evidence_obligation.artifact != ""` for every step |
| R2 | Non-empty claims | `evidence_obligation.claims != []` for every step |
| R3 | Build minimum tier T2 | every step with `cgaid_stage == 3` has `min_tier ≥ T2` |
| R4 | Verify minimum tier T3 | every step with `cgaid_stage == 4` has `min_tier == T3` |
| R5 | UNKNOWN closure | `unknowns == []` at exit_gate; otherwise card transitions to BLOCKED |
| R6 | Trace link present | `trace_link != ""` (E6 traceability per `CONTRACT.md §E`) |

A validator script (see backlog B3) parses this YAML and asserts R1–R6.

---

## §5 CGAID Stage → Theorem index

| Stage | Theorem subdir(s) | Count | Oracle for `theorem_check` |
|---|---|---|---|
| 0 — Data Classification | — | **0** | **GAP — uses `rubric_check` against `DATA_CLASSIFICATION.md`. See backlog B1.** |
| 1 — Evidence | `theorems/analysis/`, `theorems/decide/`, `theorems/business analysis/` | 5 | available |
| 2 — Plan | `theorems/plan/`, `theorems/decide/`, `theorems/spec/` | 4 | available |
| 3 — Build | `theorems/develop/`, `theorems/debug/`, `theorems/UX/`, `theorems/test/` | 9 | available |
| 4 — Verify | `theorems/verify/` | 4 | available |

Total **21 theorems** across stages 1–4. Stage 0 is the only stage without a theorem.

---

## §6 Three starting cards — MVP

Full taxonomy is `task_type × ceremony_level` ≤ 18 cells. MVP starts with three; add more only when an actual task fails to match an existing card (Rule 11 — no premature population).

### §6.1 Card: `feature_STANDARD`

```yaml
card_id: feature_STANDARD
trigger:
  task_type: feature
  ceremony_level: STANDARD
  optional_filters:
    ac_count: "<=3"
    new_external_integration: false
prereq:
  - "Stage 0 classification recorded for input material (or material declared Public/Internal explicitly)"

steps:

  S1:
    cgaid_stage: 1
    action_type: meta_prompt
    action_payload: |
      Spawn Agent (subagent_type=Explore) with prompt:
        "Read <task_description>. Find:
         (a) places impacted — grep callers,
         (b) similar existing solutions in repo,
         (c) related ADRs in platform/docs/decisions/,
         (d) applicable theorems from theorems/analysis/.
         Return: file:line list + reasoning + open questions."
    manual_fallback: |
      Human executes the same query manually: grep callers, read decisions/, list applicable theorems.
      Output written to evidence_pack_<task_id>.md with same structure.
    evidence_obligation:
      artifact: "evidence_pack_<task_id>.md"
      claims:
        - statement: "All impact sites identified"
          epistemic: CONFIRMED
          tier: T1
          acceptance: "every site has file:line + grep query that found it"
        - statement: "No hidden logical dependencies"
          epistemic: ASSUMED
          tier: T1
          acceptance: "explicit list of 'what grep cannot catch' + verification plan"
        - statement: "Applicable theorem cited"
          epistemic: CONFIRMED
          tier: T1
          acceptance: "file:line from theorems/analysis/Evidence-Driven Iterative Analysis Closure Theorem.md"
      min_tier: T1
      unknowns: []
      freshness: card
      trace_link: "platform/docs/evidence_packs/<task_id>.md"
    gate:
      - "rubric_check: evidence_pack >= 3 sources, zero unaccepted UNKNOWNs"
      - "theorem_check: vs theorems/analysis/Evidence-Driven Iterative Analysis Closure Theorem.md — all conditions ticked"

  S2:
    cgaid_stage: 2
    action_type: direct_skill
    action_payload: "/plan <task_description>"
    manual_fallback: |
      Human writes plan.md following CONTRACT.md §B.3 template:
      ASSUMING / VERIFIED / ALTERNATIVES (>=2). One ADR per non-trivial decision.
    evidence_obligation:
      artifact: "Plan + ADR(s) + Edge-Case Test Plan"
      claims:
        - statement: ">=2 alternatives compared with pros/cons"
          epistemic: CONFIRMED
          tier: T1
          acceptance: "ALTERNATIVES block has >=2 entries with explicit choice rationale"
        - statement: "Distinct-actor APPROVE recorded"
          epistemic: CONFIRMED
          tier: T3
          acceptance: "APPROVE record from actor != plan author (P23)"
      min_tier: T1
      unknowns: []
      freshness: card
      trace_link: "platform/docs/decisions/ADR-<n>.md + plan_<task_id>.md"
    gate:
      - "theorem_check: vs theorems/plan/Evidence_Constrained_Planning_Theorem.md"
      - "risk_probe: /deep-risk → no HIGH+ risk without mitigation"
      - "P23 APPROVE from distinct actor"

  S3:
    cgaid_stage: 3
    action_type: direct_skill
    action_payload: "/develop with /guard active"
    manual_fallback: |
      Human writes code following plan + Edge-Case Test Plan.
      Tags every non-trivial claim CONFIRMED/ASSUMED/UNKNOWN.
      Maintains MODIFYING list ≡ git diff.
    evidence_obligation:
      artifact: "code commits + tests"
      claims:
        - statement: "Every non-trivial claim tagged"
          epistemic: CONFIRMED
          tier: T2
          acceptance: "grep CONFIRMED|ASSUMED|UNKNOWN in PR description matches non-trivial change count"
        - statement: "Tests cover scenario_types from Edge-Case Test Plan"
          epistemic: CONFIRMED
          tier: T2
          acceptance: "test report shows coverage per scenario_type"
        - statement: "MODIFYING list ≡ git diff"
          epistemic: CONFIRMED
          tier: T2
          acceptance: "diff of MODIFYING list vs git diff returns empty"
      min_tier: T2
      unknowns: []
      freshness: card
      trace_link: "git commit SHAs + test report path"
    gate:
      - "GUARD CHECK pass"
      - "tests green"
      - "theorem_check: vs theorems/develop/Forge Unified Development Theorem.md"

  S4:
    cgaid_stage: 4
    action_type: "theorem_check + opinion_prime"
    action_payload: |
      (a) /deep-verify against theorems/verify/Engineer_Soundness_Completeness.md — mechanical pass.
      (b) Spawn Agent with opinion-primed prompt:
          "You are a senior reviewer with 20 years of experience known for catching
           edge cases others miss. Read the diff and the plan. Find >=3 issues OR
           explain why none exist. Cite file:line for each."
    manual_fallback: |
      Distinct human reviewer runs theorem checklist manually + adversarial review.
      Records findings in review_<task_id>.md.
    evidence_obligation:
      artifact: "verification record + reviewer report"
      claims:
        - statement: "All conditions of Engineer_Soundness_Completeness theorem hold"
          epistemic: CONFIRMED
          tier: T3
          acceptance: "mechanical checklist ticked by distinct actor"
        - statement: "Reviewer findings recorded"
          epistemic: CONFIRMED
          tier: T3
          acceptance: ">=3 findings OR explicit zero-finding justification, each with file:line"
      min_tier: T3
      unknowns: []
      freshness: card
      trace_link: "platform/docs/reviews/review_<task_id>.md"
    gate:
      - "23 mechanical checks from PLAN_GOVERNANCE terminal gate pass"
      - "distinct-actor sign-off (NOT solo-verifier per CONTRACT §B.8)"
      - "business-outcome evidence attached (P8)"

exit_gate:
  - "all 4 steps complete"
  - "all evidence_obligation.unknowns == []"
  - "all gate predicates pass"
  - "trace_links archived"
  - "R1–R6 invariant check pass"
```

### §6.2 Card: `bug_STANDARD`

```yaml
card_id: bug_STANDARD
trigger:
  task_type: bug
  ceremony_level: STANDARD
prereq:
  - "Defect reproduces deterministically (or root-cause hypothesis with sampling per CONTRACT Rule 9)"

steps:

  S1:
    cgaid_stage: 1
    action_type: direct_skill
    action_payload: "/grill on defect report"
    manual_fallback: "Human writes Reproducer Pack: minimal repro, failing test, observed vs expected."
    evidence_obligation:
      artifact: "reproducer_pack_<bug_id>.md"
      claims:
        - statement: "Defect reproduces deterministically"
          epistemic: CONFIRMED
          tier: T2
          acceptance: "reproducer command + output captured"
        - statement: ">=3 root-cause hypotheses (CONTRACT Rule 10)"
          epistemic: CONFIRMED
          tier: T1
          acceptance: "each hypothesis has confirming + refuting evidence + ranking"
      min_tier: T2
      unknowns: []
      freshness: card
      trace_link: "platform/docs/bugs/<bug_id>.md"
    gate:
      - ">=3 hypotheses (CONTRACT Rule 10)"
      - "theorem_check: vs theorems/debug/Error_Discovery.md"

  S2:
    cgaid_stage: 2
    action_type: direct_skill
    action_payload: "/plan fix with selected hypothesis"
    manual_fallback: "Human writes fix plan with >=2 alternatives, identifies cascade per CONTRACT A.7."
    evidence_obligation:
      artifact: "fix plan + ADR (if non-trivial)"
      claims:
        - statement: "Cascade identified per CONTRACT A.7"
          epistemic: CONFIRMED
          tier: T1
          acceptance: "list of all places where fix should propagate"
      min_tier: T1
      unknowns: []
      freshness: card
      trace_link: "plan_<bug_id>.md"
    gate:
      - "P23 APPROVE if non-trivial fix"

  S3:
    cgaid_stage: 3
    action_type: direct_skill
    action_payload: "/develop fix; add regression test BEFORE fix"
    manual_fallback: "Human writes failing test first, then fix, then verifies test passes."
    evidence_obligation:
      artifact: "code + regression test"
      claims:
        - statement: "Regression test fails before fix, passes after"
          epistemic: CONFIRMED
          tier: T2
          acceptance: "test run before/after with output captured"
        - statement: "Cascade applied"
          epistemic: CONFIRMED
          tier: T2
          acceptance: "all sites from S2 cascade list modified or explicitly excluded"
      min_tier: T2
      unknowns: []
      freshness: card
      trace_link: "git commit SHA + test report"
    gate:
      - "GUARD CHECK pass"
      - "regression test green"

  S4:
    cgaid_stage: 4
    action_type: theorem_check
    action_payload: "/deep-verify against theorems/debug/Completeness and Error Discovery.md"
    manual_fallback: "Distinct human reviewer verifies fix completeness mechanically."
    evidence_obligation:
      artifact: "verification record"
      claims:
        - statement: "Defect class fully covered, not just instance"
          epistemic: CONFIRMED
          tier: T3
          acceptance: "review confirms cascade applied + theorem conditions met"
      min_tier: T3
      unknowns: []
      freshness: card
      trace_link: "platform/docs/reviews/review_<bug_id>.md"
    gate:
      - "distinct-actor sign-off"

exit_gate:
  - "regression test in CI"
  - "Finding → FailureMode promotion (per OM §4.3 v1.5)"
  - "R1–R6 pass"
```

### §6.3 Card: `analysis_LIGHT`

```yaml
card_id: analysis_LIGHT
trigger:
  task_type: analysis
  ceremony_level: LIGHT
  optional_filters:
    output_form: "report or evidence pack, no code change"
prereq: []

steps:

  S1:
    cgaid_stage: 1
    action_type: meta_prompt
    action_payload: |
      Spawn Agent (subagent_type=Explore) with prompt:
        "Investigate <topic>. Read <listed sources>. Return: findings with file:line,
         contradictions, open questions. Do not propose action — analysis only."
    manual_fallback: "Human reads sources directly, writes findings.md with file:line citations."
    evidence_obligation:
      artifact: "findings_<topic>.md"
      claims:
        - statement: "All listed sources read"
          epistemic: CONFIRMED
          tier: T1
          acceptance: "each source has >=1 file:line citation in findings"
        - statement: "Contradictions surfaced"
          epistemic: CONFIRMED
          tier: T1
          acceptance: "contradictions section non-empty OR explicit 'none found' with reasoning"
      min_tier: T1
      unknowns: []
      freshness: card
      trace_link: "findings_<topic>.md"
    gate:
      - "theorem_check: vs theorems/analysis/Evidence-Driven Iterative Analysis Closure Theorem.md"

  S2:
    cgaid_stage: 4
    action_type: opinion_prime
    action_payload: |
      Spawn Agent with prompt:
        "You are a domain expert. Read findings_<topic>.md. Are findings sufficient
         for downstream decisions? List gaps. Cite file:line."
    manual_fallback: "Distinct human reads findings, lists gaps."
    evidence_obligation:
      artifact: "review of findings"
      claims:
        - statement: "Findings sufficient OR gaps explicitly listed"
          epistemic: CONFIRMED
          tier: T3
          acceptance: "review record by distinct actor"
      min_tier: T3
      unknowns: []
      freshness: card
      trace_link: "review_findings_<topic>.md"
    gate:
      - "distinct-actor sign-off"

exit_gate:
  - "findings + review archived"
  - "R1–R6 pass"
```

LIGHT skips Stages 2 and 3 by design — analysis produces no code change. Stage 4 verification is preserved.

---

## §7 Synchronization with platform/

`platform/docs/USAGE_PROCESS.md` is the Forge-specific instantiation of this procedure. Drift between the two is a framework-level violation per `OPERATING_MODEL.md §4.5`.

Each material change to either document requires:

1. ADR per OM §9.2.
2. Hash check in `platform/scripts/verify_graph_topology.py` — assert that `USAGE_PROCESS_GRAPH.dot` declared cards match `REFERENCE_PROCEDURE.md` `card_id`s.
3. Distinct-actor review per ADR-003.

---

## §8 Backlog

- **B1 (HIGH):** Stage 0 theorem (Data Classification soundness). Currently Stage 0 cards use `rubric_check` against `DATA_CLASSIFICATION.md` decision tree only. Theorem should establish: soundness (each input → exactly one tier), dispute resolution convergence, routing matrix completeness, composition (compound material → highest tier). Target location: new subdir `theorems/classify/` or extend `theorems/spec/`.
- **B2:** Cards for `refactor`, `hotfix`, `feature_FULL`, `feature_LIGHT`, `bug_FULL`, `bug_LIGHT`, `analysis_STANDARD`, `analysis_FULL`, `classification_*`. Add as actually needed (Rule 11 — no premature population).
- **B3:** Mechanical validator script (`platform/scripts/validate_cards.py`) that parses card YAML and asserts R1–R6.

---

## §9 Version trail

- v1 (2026-05-05) — initial. Grammar, 6 action types, evidence_obligation schema with T1/T2/T3 tiers, 6 invariant rules, 3 starting cards. Adopted via [ADR-029](../../platform/docs/decisions/ADR-029-procedural-cards.md).
