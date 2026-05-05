# Agent Task: Comprehensive Change Plan for Forge Platform
> **Version:** 2 — revised after deep-verify (REJECT 11.2, 2 CRITICAL) and deep-risk (6 CRITICAL risks ≥26).
> **Date:** 2026-04-23

---

## Pre-flight declaration (CONTRACT §B.3 — this prompt's own ASSUMING/VERIFIED/ALTERNATIVES)

```
ASSUMING:
  - Executing agent has file-read AND shell/grep access (if wrong → all [CONFIRMED] citations
    based on grep must be downgraded to [ASSUMED: file-read only])
  - Platform smoke tests (Stage 0.3) have NOT been run (if wrong → remove [ASSUMED: Stage-0.3-not-run]
    tags where Stage 0.3 has completed)
  - ADR-003 is NOT yet ratified (if wrong → output status may transition from DRAFT
    to PEER-REVIEWED after distinct-actor sign-off)

VERIFIED:
  - All theorem files exist in .ai/theorems/ (confirmed by glob: 7 files present including
    "Context-Complete Evidence-Guided Agent Process.md")
  - Highest current ADR number is ADR-003 (confirmed by decisions/README.md index)
  - All 6 PLAN_*.md files and source specs exist in platform/docs/

ALTERNATIVES considered for this prompt design:
  A. Single-session full synthesis (chosen): agent reads all 17 docs + produces output in one session.
     Pro: no cross-session epistemic loss. Con: context budget may prune late docs; solo-verifier
     risk applies to all analytical conclusions.
  B. Two-session split (read-only → synthesize): reduces context budget risk. Con: cross-session
     loss destroys reasoning trace (AUTONOMOUS_AGENT_FAILURE_MODES §2.1).
  Choice: A — context budget risk is lower than cross-session loss risk for this corpus size.
```

---

## Your identity and constraints

You are a senior software architect and adversarial reviewer. You operate under the Forge operational contract (`.ai/CONTRACT.md`).

**Tagging rules (from CONTRACT):**
- `[CONFIRMED: source=file:line]` — you executed a grep or directly read and quote the specific line.
- `[ASSUMED: rationale]` — you infer from reading without execution, or source is DRAFT/unratified.
- `[UNKNOWN: blocks=what]` — you cannot determine this without information not in your context. STOP on UNKNOWN — do not fill with a plausible default.

**Solo-verifier rule (CONTRACT §B.8):** You cannot mark your own analytical conclusions `[CONFIRMED]`. Your inferential syntheses (Sections 2, 3, 4, 5, 7) are `[ASSUMED: agent-analysis, requires-distinct-actor-review]`. Only direct file citations may carry `[CONFIRMED]`. This document is DRAFT by definition — mark it so.

**DRAFT inputs rule (CONTRACT §B.2 subagent delegation):** Every source document you read is DRAFT and solo-authored. Per CONTRACT §B.2: "A subagent's `[CONFIRMED]` is `[ASSUMED]` at your level until you independently verify it." Tag every claim sourced from a DRAFT document as `[ASSUMED: source=DRAFT-doc, ratified=NO]` unless you independently verify it via grep/read.

**GAP_ANALYSIS_v2 code-state claims:** Per ROADMAP Stage 0.3 (R-GAP-02), GAP_ANALYSIS_v2 rests on self-reported IMPLEMENTATION_TRACKER claims not yet smoke-tested. Tag every code-state claim (line counts, site counts, validator behavior) from GAP_ANALYSIS_v2 as `[ASSUMED: source=GAP_ANALYSIS_v2, Stage-0.3-not-run]` unless you grep the source file and confirm.

---

## Context you must read before starting (in this order)

**Note on file paths:** All framework/governance files: `.ai/...` (in forge repo root) | All Forge platform files: `forge/platform/docs/...` | Relative to repo root: `<repo-root>`

### Mandatory reads — theorems and contract first:

1. `.ai/CONTRACT.md` — operational contract: tagging rules, disclosure protocol, solo-verifier constraint, non-trivial definition (7 triggers + 3 trivial exceptions)
2. `.ai/theorems/Context-Complete Evidence-Guided Agent Process.md` — **12-condition soundness theorem (C1–C12) + 3 theorems + 5 lemmas**. Read the FULL file. Every C_i citation in your output must quote the exact sentence from THIS file, not from the ECA summary.
3. `.ai/theorems/Engineer_Soundness_Completeness.md` — 8 engineering soundness conditions (§1–§8). Same rule: cite this file directly for any §_j attribution.

### Mandatory reads — platform assessment and spec:

4. `forge/platform/docs/EPISTEMIC_CONTINUITY_ASSESSMENT.md` — 12-condition platform assessment (ECA). **Read as a DRAFT synthesis of theorems 2–3 above, not as a primary source.** Where ECA and the theorem files differ, the theorem files take precedence.
5. `forge/platform/docs/FORMAL_PROPERTIES_v2.md` — 25 atomic properties (P1–P25)
6. `forge/platform/docs/GAP_ANALYSIS_v2.md` — current state vs spec. Read with R-GAP-02 caveat: code-state claims are self-reported.
7. `forge/platform/docs/ROADMAP.md` — 7-phase operational plan with stages and exit tests
8. `forge/platform/docs/AUTONOMOUS_AGENT_FAILURE_MODES.md` — failure analysis for autonomous agent

### Functional plans to analyze:

9. `forge/platform/docs/PLAN_PRE_FLIGHT.md`
10. `forge/platform/docs/PLAN_GATE_ENGINE.md`
11. `forge/platform/docs/PLAN_MEMORY_CONTEXT.md`
12. `forge/platform/docs/PLAN_QUALITY_ASSURANCE.md`
13. `forge/platform/docs/PLAN_CONTRACT_DISCIPLINE.md`
14. `forge/platform/docs/PLAN_GOVERNANCE.md`

### Supporting context:

15. `forge/platform/docs/CHANGE_PLAN_v2.md` — phase rationale and blast-radius analysis
16. `forge/platform/docs/DEEP_RISK_REGISTER.md` — 29 risks, current status
17. `forge/platform/docs/decisions/README.md` — ADR index (read to confirm current highest ADR number before writing Section 6)

**Confirm your reads:** In the output header, list every file you opened via a tool call with the first quoted line of that file as `[CONFIRMED: file:line]`. If any mandatory file was not read, state it explicitly as `[UNKNOWN: file not read — findings dependent on this file are [ASSUMED]]`.

---

## Your task

Produce: `forge/platform/docs/CHANGE_PLAN_COMPREHENSIVE.md`

Status: **DRAFT** — mark it so in the header. This document cannot be used to drive implementation decisions until it receives distinct-actor review per ADR-003.

The document must contain the following sections:

---

### Section 0: Status block and read confirmation

```
Status: DRAFT — not binding. Requires distinct-actor review per ADR-003 before any
        implementation decision may reference this document.
Date: YYYY-MM-DD
Source documents read: [list each with confirmed first-line citation]
Source documents NOT read: [explicit list — do not omit]
Calibration constants status: ADR-004 [OPEN/CLOSED] — if OPEN, all boundary
  threshold judgments in Section 2b are [UNKNOWN: blocked by ADR-004]
Stage 0.3 smoke tests: [COMPLETE/NOT-RUN] — if NOT-RUN, all GAP_ANALYSIS_v2
  code-state claims are [ASSUMED: Stage-0.3-not-run]
```

---

### Section 1: What the existing plans got right

For each of the 6 PLAN files:
- What it correctly identifies — cite the specific exit test `T_i` or gate condition
- Which theorem condition (C1–C12) or property (P1–P25) it correctly closes
- Cite as `[CONFIRMED: PLAN_X.md:section]` for each claim

Do not summarize. If a plan claims to close a condition but its exit test does not mechanically enforce it, say so here (do not save it for Section 2 — flag it in both places).

---

### Section 2: Adversarial analysis — what is wrong or missing

**Tagging protocol for this section:** Every finding must have:
- An exact quote from the source plan (cite as `[CONFIRMED: file:section]`)
- The C_i or §_j violated (with a one-sentence quote from the theorem file — NOT from ECA)
- Severity: CRITICAL / IMPORTANT / MINOR
- A specific, testable fix (one sentence minimum)

**2a. Edge cases not covered by exit tests (find ≥5 across all 6 plans):**

For each: name the exit test, state what semantic guarantee it implies, construct a concrete realistic scenario where the test passes but the guarantee fails. Apply the Constructive Counterexample method: is this scenario realistically producible, not pathological?

**2b. Boundary conditions (find ≥3):**

Identify where a gate is technically satisfied but the property it claims to close is not achieved. If the judgment requires a calibration constant (α, τ, W, q_min), and ADR-004 is not CLOSED: tag as `[UNKNOWN: threshold requires ADR-004]` and state what question ADR-004 must answer.

**2c. Failure modes from AUTONOMOUS_AGENT_FAILURE_MODES.md not addressed by any plan (find ≥3):**

For each: name the failure mode with its section reference (e.g., §1.1 Calibration undefined), state which plan's stages should address it but don't, propose a specific addition.

**2d. Silent assumptions that break under adversarial conditions (find ≥3):**

For each: name the plan and the assumption, describe the adversarial condition that breaks it (must be realistic — production-level concurrency, clock skew, partial failure), state the consequence if not addressed.

**2e. Misclassified ASSUMED claims — claims that should be UNKNOWN (find what the documents actually support; state the count honestly):**

Apply CONTRACT's 7 non-trivial triggers to each plan's ASSUMED list. For each claim that meets a non-trivial trigger but is tagged [ASSUMED] instead of [UNKNOWN]: name it, cite the trigger, state what information would resolve it.

**Do not pad to meet a quota.** If a plan has only 1 genuinely misclassified assumption, report 1. If you reach genuine exhaustion before the minimum, write: "Exhaustive search complete — N found across all plans." CONTRACT §A.6 (false completeness) prohibits fabricating findings to meet a floor.

**2f. Cross-plan dependency gaps (find ≥4):**

Where does Plan X depend on a specific output from Plan Y, but Plan Y's exit gate does not guarantee that specific output? Trace the dependency chain precisely: cite both the dependency claim in Plan X and the exit test in Plan Y that should but does not cover it.

---

### Section 3: Root causes — synthesis

Identify 3–5 deepest structural issues. **Do not list findings from Section 2** — synthesize across them.

For each root cause:
- One precise paragraph stating the structural issue
- Which C_i / C_j conditions it violates (quote from theorem file, not ECA)
- Which P_i atomic properties remain unsatisfied because of it
- Why symptom-level fixes (existing plan stages) won't close it
- Evidence: cite file:section for each claim

Tag the entire section: `[ASSUMED: agent-synthesis — requires distinct-actor review. Structural diagnoses cannot be self-verified.]`

---

### Section 4: Required additions

For each addition:
- Which existing plan it belongs to (or mark NEW PLAN if nothing covers it)
- What specifically to add — one implementable action
- A deterministic exit test `T_new` (grep / pytest / DB query). If manual review is unavoidable, state why automated is impossible and require a distinct-actor review record as the gate artifact.
- The C_i / P_j it closes
- Severity if not done: CRITICAL / IMPORTANT / MINOR

**Quantity guidance:** Find as many as the documents support. Minimum 10. If you find fewer, state "Exhaustive search complete." If you find more than 25, prioritize — retain only those where the exit test is genuinely novel (not derivable from existing T_i).

---

### Section 5: Test gap specifications

For each new test specification:
- Name: `test_{plan}_{what}.py`
- One-sentence description
- Why the existing T_i does not cover it (cite the closest existing T_i and state the gap)
- Type: unit / integration / property-based / adversarial
- Which C_i or §_j it closes when it passes

Mandatory categories:
- ≥3 property-based (hypothesis-style) — state the property being tested, not just "test that X works"
- ≥3 adversarial (from AUTONOMOUS_AGENT_FAILURE_MODES.md §1–§5 failure modes, or PRACTICE_SURVEY incidents — **read** `.ai/framework/PRACTICE_SURVEY.md` for the latter; it is not in the mandatory read list above, add it if you need it)
- ≥3 boundary condition tests (at the edge of a gate's defined range)
- ≥3 cross-plan integration tests (testing that Plan X's exit state satisfies Plan Y's entry precondition)

Minimum 15 total. **Do not pad** — apply the same no-false-completeness rule as Section 2e.

---

### Section 6: ADR requirements

Read `forge/platform/docs/decisions/README.md` to confirm the current highest ADR number before writing this section. State it as `[CONFIRMED: decisions/README.md:line]`.

For each new decision required:
- ADR number (continue from confirmed highest + 1)
- Decision question — precise, answerable
- Which plan and stage it blocks
- Which C_i / P_j it affects
- Consequence of getting it wrong (one sentence)
- Urgency: BLOCKING (plan cannot start without it) / IMPORTANT (plan degrades without it) / MONITORING

---

### Section 7: Updated priority ordering

Produce a revised priority ordering. Justify each position by:
1. Soundness condition severity (CRITICAL C_i per ECA §2.1: C4, C5, C6, C10)
2. Dependencies (what blocks what — cite the exact gate condition)
3. Blast radius relative to other items of equal severity

**Mandatory:** For any deviation from the existing ROADMAP order, state: "DEVIATION from ROADMAP §N: [reason with evidence]." If you find no justified deviation, state that explicitly — do not manufacture differences.

Tag the section: `[ASSUMED: agent-priority-ordering — requires distinct-actor review of Sections 3 and 7 before any plan is actioned]`

---

### Section 8: Mandatory adversarial self-check

Before completing the document, apply this check to your output. Document results inline in this section.

**8a. For every CRITICAL or IMPORTANT finding in Section 2, answer all four challenges:**
1. **Alternative Explanation:** What other explanation accounts for the same evidence? Does it invalidate the finding?
2. **Hidden Context:** What domain knowledge would make the observed pattern actually correct?
3. **Domain Exception:** Is there a legitimate case where the finding is wrong (not a pathological exception — a real production case)?
4. **Confirmation Bias:** Did you only look for evidence supporting this finding, or did you also look for disconfirming evidence?

Decision rule: if ≥2 challenges substantially weaken the finding → DOWNGRADE by one severity level and state why. If all 4 weaken it → REMOVE and explain.

**8b. For every test in Section 5, confirm:**
- Name the closest existing T_i (from the 6 PLAN files)
- State in one sentence why the new test is not derivable from that T_i
- If it is derivable: remove the test from Section 5

**8c. Steel-man the opposite verdict:**
Construct the strongest argument that the existing 6 plans are sufficient and no additions from Section 4 are needed. State specifically why that argument fails — with evidence from the theorem files, not from ECA.

---

## Output requirements

### Format
- Output file: `forge/platform/docs/CHANGE_PLAN_COMPREHENSIVE.md`
- Status block required at top (Section 0 above)
- Every section of conclusions preceded by CONTRACT §B.1 evidence-first: `DID: / DID NOT: / CONCLUSION:`
- Close with CONTRACT §B.5 format:
  ```
  DONE: [list with evidence per item]
  SKIPPED: [list with rationale — apply no-false-completeness rule]
  FAILURE SCENARIOS:
    1. [what happens if ADR-003 is never ratified and this plan is used as normative]
    2. [what happens if Stage 0.3 reveals major divergences from GAP_ANALYSIS_v2]
    3. [what happens if the executing agent's model version changes before Section 7 is acted on]
  ```

### What you must NOT do
- Do not mark your own analytical inferences `[CONFIRMED]` — only direct file citations qualify
- Do not cite ECA (EPISTEMIC_CONTINUITY_ASSESSMENT.md) as the source for a theorem condition — cite the theorem file directly
- Do not produce a finding without quoting exact text from the source plan
- Do not propose a fix without a testable acceptance criterion
- Do not list findings to meet a quota — apply CONTRACT §A.6 (false completeness prohibition)
- Do not call any ordering choice in ROADMAP.md "wrong" without citing the theorem condition it violates

### README update
Append one line to `forge/platform/docs/README.md` status table:
```
| [`CHANGE_PLAN_COMPREHENSIVE.md`](CHANGE_PLAN_COMPREHENSIVE.md) | DRAFT | no | Comprehensive adversarial analysis of 6 functional plans. Not binding until distinct-actor review per ADR-003. |
```
