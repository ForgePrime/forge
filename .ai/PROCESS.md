# AI-Driven Software Development — End-to-End Process

> One document. Full lifecycle from request to retirement. Built for handover — a new person should be able to execute every stage from this file.
> Empirical base: ~30 days of work on this codebase, 18 incidents in `framework/PRACTICE_SURVEY.md`, weekly memory updates of surprises.
> Companion docs (don't duplicate): `CONTRACT.md` (disclosure), `RULES.md` (8 rules), `WORKFLOW.md` (lifecycle reference + examples), `standards.md` (code), `commands.md` (skills), `framework/` (governance), `templates/` (HOWTOs).

---

## Part 0 — How to use this document

| You are | Read |
|---|---|
| New to the team (Day 1) | Part 1 + Part 2 + Part 9 (Onboarding) |
| Picking up a task today | Part 2 (flow) + Part 3 (your work class) + Part 4 (gates) |
| Reviewing a PR | Part 4 + Part 6 |
| Process owner / on-call | All |
| Stuck in a loop | Part 4.3 (loop detection) + Part 4.4 (frame challenge) |

---

## Part 1 — Foundations

### 1.1 What "AI-driven" means here

The AI assistant is the primary code producer. The human does:
- Sets the **oracle** (what does success look like)
- **Routes** work (which class, which AI / human / hybrid)
- **Verifies** AI output (deterministic checks, not opinion)
- **Decides** trade-offs the AI can't see (business priority, political constraints)
- **Writes memory** of surprises so the AI does not repeat them

The AI does:
- Investigation, planning, code, tests, evidence collection
- Self-disclosure of uncertainty, scope, alternatives
- Independent verification when asked (separate session / subagent)

Bottleneck shift: typing speed → context budget + verification + decomposition. This process exists to manage the new bottleneck.

### 1.2 Core invariant

Every change is anchored to three things. Missing any → stop and pull it before code:

| Anchor | What | Without it |
|---|---|---|
| **ORACLE** | Measurable external truth (CSV file, invariant, CI, expected output) | Infinite iteration |
| **EVIDENCE** | What system does NOW (run, query, grep — literal output) | Guessing dressed as reasoning |
| **DELTA** | Gap in numbers ("1,500 rows differ") | "Lots of failures" — not actionable |

### 1.3 Five mantras (memorize)

1. **Oracle first. Code second.**
2. **Evidence in numbers. Not adjectives.**
3. **Decompose before deciding.**
4. **Verify externally. Solo-verifier is not verification.**
5. **Capture surprises only. Memory of facts is decoration.**

### 1.4 Roles

| Role | Owns |
|---|---|
| **Requester** | The oracle. The deadline. The acceptance criterion. |
| **Driver** | Stage transitions, evidence per stage, escalation. Holds the PR until merge. |
| **AI Assistant** | Generation: code, tests, planning, investigation. Disclosure of own state. |
| **Independent Verifier** | Reviews PLAN before code, reviews PR before merge. Different actor from Driver. |
| **Operator** | Deployment, monitoring, incident response. |
| **Process Owner** | Evolves the process based on metrics + memory + lessons. |

In a small team one human can hold multiple roles — but never Driver + Independent Verifier on the same change.

### 1.5 Artifacts

Every artifact has one purpose. If unclear which to write — stop and re-read this table.

| Artifact | Created when | Lives in |
|---|---|---|
| **Task brief** | Requester registers work | Issue tracker / TODO.md |
| **SPEC** (`.ai/SPEC_<feature>.md`) | Feature work, before plan | `.ai/` |
| **Validation file** (`.ai/validation/<name>.md` + `.csv`) | When external data drives correctness | `.ai/validation/` |
| **PLAN** (`.ai/PLAN_<name>.md`) | Non-trivial work, before code | `.ai/` |
| **Code + tests** | Stage execution | `backend/`, `frontend/`, etc. |
| **Evidence in PLAN** (per stage) | After each stage runs | Inline in the PLAN |
| **PR** | After last stage | GitHub |
| **Memory entry** (`feedback_*.md` or `project_*.md`) | When something surprised AI | `~/.claude/projects/.../memory/` |
| **Post-mortem** (`POST_MORTEM_*.md`) | After incident | `.ai/LESSONS_LEARNED.md` |

---

## Part 2 — End-to-end flow (15 stages)

```
[1]  INTAKE        ──► request registered, owner assigned
[2]  CLASSIFY      ──► work class identified (8 classes — Part 3)
[3]  ORACLE        ──► success criterion defined, in writing, measurable
[4]  CLARIFY       ──► requirements grilled until no UNKNOWN remains
[5]  PLAN          ──► PLAN.md with stages + scenarios + invariants + rollback
[6]  VERIFY PLAN   ──► independent reviewer (deep-verify or human) — REJECT stops here
[7]  EXECUTE       ──► stage by stage: code → run → evidence → next
[8]  PRE-COMMIT    ──► local gates pass (G1, G2, G3 — Part 4)
[9]  PR + REVIEW   ──► automated checks + independent reviewer
[10] MERGE         ──► main updated, PLAN status closed
[11] DEPLOY        ──► to env with rollback ready
[12] VALIDATE      ──► oracle still passes in target env
[13] MONITOR       ──► watch for incidents (window depends on class)
[14] CLOSE         ──► TODO closed, lessons captured, memory updated
[15] (INCIDENT)    ──► if failure: post-mortem → process update
```

Trivial work skips stages (see Part 3 per class). Production data work skips none.

### Stage 1 — Intake

**Input**: a request (bug report, feature ask, observation).
**Output**: registered task with **assigned Driver** and **target oracle type**.
**Anti-pattern**: starting code on a verbal "can you..." with no record. Empirical anchor: 9-fix-pendulum (`WORKFLOW.md` §2.1) — task started without registration, no Driver, no oracle.

### Stage 2 — Classify

Pick exactly one work class (Part 3). If unsure — ASK. Class drives:
- which gates fire
- which artifacts are needed
- which sub-process applies

**Anti-pattern**: applying full feature process to a UI tweak (waste) or vibe-coding a data reconciliation (incident). Class wrong = process wrong.

### Stage 3 — ORACLE

Write the oracle in one sentence with the measure.

| Bad | Good |
|---|---|
| "Settlement should match CREST" | "Settlement W17 per-invoice money sum equals CREST per-invoice money sum within $0.01 tolerance" |
| "Bug is fixed" | "Test case T-42 passes; regression suite green; original repro yields no error" |
| "Performance better" | "P95 endpoint latency < 200ms over 24h sample of production traffic" |

If you can't write the measurement — stop. The work is **not yet ready** to plan, let alone code.

### Stage 4 — Clarify

Run `/grill` or equivalent until every assumption is either `[CONFIRMED]` or explicitly `[ASSUMED: accepted-by=<role>, date=YYYY-MM-DD]` per `CONTRACT.md` §B.2.
No `[UNKNOWN]` survives this stage.

### Stage 5 — PLAN

For non-trivial work (`CONTRACT.md` §"What 'non-trivial' means"). Use `WORKFLOW.md` §5 template.

PLAN sections:
1. Context (why)
2. Evidence base (data + ground truth files)
3. Decisions (D1, D2 — each with ≥2 alternatives + chosen + reason)
4. **Test scenarios** ← MANDATORY, ≥1 per: happy / edge / boundary / failure / regression
5. **Invariants** ← must hold AFTER every stage
6. **Stages** ← code → run → evidence pattern
7. **Rollback plan**
8. Execution log (filled during Stage 7)

### Stage 6 — Verify PLAN

Independent actor runs `/deep-verify` or human review on the PLAN. Output: ACCEPT / NEEDS-WORK / REJECT.
REJECT → fix the plan, do not implement.

**Anti-pattern**: Driver verifying their own plan = solo-verifier (CONTRACT §B.8). Same priors → same blind spots.

### Stage 7 — Execute

Per stage in PLAN:
```
code  →  run  →  paste literal output into PLAN  →  invariant check  →  next stage
```

Do NOT skip evidence. "Stage 1 done" without literal output = declaration, not fact (RULES.md §3).

### Stage 8 — Pre-commit (G1+G2+G3 — Part 4)

Run all three gates. Empty Impact / empty Rollback = change rejected (no override).

### Stage 9 — PR + Review

PR description references PLAN, contains evidence per stage, lists FAILURE SCENARIOS (CONTRACT §B.5). Independent reviewer (different from Driver).

### Stage 10 — Merge

Driver updates PLAN status to ✅ MERGED, closes TODO entry, opens deploy ticket if needed.

### Stage 11 — Deploy

See Part 7. Rollback plan from PLAN §7 must be executable in <5 min.

### Stage 12 — Validate

Re-run oracle in target env. Confirm:
- The same measure used in Stage 3 still passes
- Telemetry / metrics match expected baseline
- No regression in adjacent areas

### Stage 13 — Monitor

Class-specific window (Part 3). For data work: 1 buy cycle. For features: 1 week. For infra: 24h.

### Stage 14 — Close

- TODO.md → closed
- PLAN status → MERGED + DEPLOYED
- If anything surprised → memory entry (Part 8)
- If systemic learning → `LESSONS_LEARNED.md`

### Stage 15 — Incident response (conditional)

If post-deploy validation fails OR monitoring fires:
1. Revert per rollback plan (or hotfix if revert is unsafe)
2. Confirm oracle restored
3. Post-mortem within 48h: timeline, root cause, prevention (`framework/PRACTICE_SURVEY.md` template)
4. Process update if pattern is new (Part 8.4)

---

## Part 3 — Work classes (8)

Different work needs different process weight. Identify class at Stage 2.

### 3.1 Bug fix (production code)

| Property | Value |
|---|---|
| Oracle | Failing test / repro that turns green |
| Min stages | 1, 3, 5 (light), 7, 8, 9, 10, 11, 12, 14 |
| Skip | None for prod data; planning can be inline for trivial |
| Risk | Defensive-fix loop (Gate G1) |
| Empirical anchor | TD-20..25 ladder (`LESSONS_LEARNED.md` 2026-04-25) — 5 fixes, 4 reverts, 5h wasted |

### 3.2 Feature (production code)

| Property | Value |
|---|---|
| Oracle | Acceptance criteria from Requester |
| Min stages | All 15 |
| Skip | None |
| Artifacts | SPEC + PLAN + validation/ if data-driven |
| Risk | Scope creep (CONTRACT §A.4 narrow scope) |
| Empirical anchor | `PLAN_settlement_event_log_refactor.md` (2026-04-22 success) vs 9-fix-pendulum (2026-04-13 failure) |

### 3.3 Refactor (no behavior change)

| Property | Value |
|---|---|
| Oracle | Behavior preservation: same inputs → same outputs (golden master) |
| Min stages | 3, 5, 6, 7, 8, 9, 10, 11, 12 |
| Skip | 4 (no requirements to clarify) |
| Risk | Hidden behavior changes — consumer impact (RULES.md §7) |
| Empirical anchor | Settlement v3 → v4 → v5 (`project_v3_architecture_validated_be_w17.md`) |

### 3.4 Investigation / Research

| Property | Value |
|---|---|
| Oracle | A question answered, with evidence — not code |
| Output | Document with findings + numbers + anchors |
| Min stages | 1, 3, 4, 7 (where execute = data queries), 14 |
| Skip | 5–13 if conclusion is "no code change needed" |
| Risk | Boiling-frog: investigation drifts into implementation without crossing Stage 5 gate |
| Empirical anchor | This session — credit memo decomposition before any code |

### 3.5 Data work / reconciliation

| Property | Value |
|---|---|
| Oracle | External file (CREST report, expected output CSV) — per-row OR per-key match |
| Min stages | All 15 |
| Skip | None |
| Mandatory | Validation file in `.ai/validation/` with ground truth |
| Risk | Filter parity — investigation script drifts from prod query (`feedback_simulation_must_match_filters.md`) |
| Empirical anchor | CA W17 24/24 PASS post credit-memo fix |

### 3.6 Infrastructure / DevOps

| Property | Value |
|---|---|
| Oracle | State machine in target state, monitored |
| Min stages | All 15, with extra weight on Stage 11–13 |
| Mandatory | Rollback rehearsed, monitoring confirmed |
| Risk | Stale code in container despite restart (`feedback_docker_rebuild_after_edit.md`) |
| Empirical anchor | Backend container no-volume-mount → silent stale-code regressions |

### 3.7 Prototype / experimental

| Property | Value |
|---|---|
| Oracle | Visual / qualitative (does it look right) |
| Min stages | 1, 3 (informal), 7, 14 |
| Skip | 5, 6, 8, 9, 11, 12, 13 OK |
| Mandatory | Marked as PROTOTYPE in code header — not for prod |
| Risk | Prototype shipped to prod ("just temporary" lasts 2 years) |
| Empirical anchor | `tmp/` scripts — must NEVER be merged |

### 3.8 Documentation

| Property | Value |
|---|---|
| Oracle | "A new person can execute / understand without asking the author" (RULES.md §5) |
| Min stages | 1, 3, 5 (= write doc), 6 (= reader review), 7 (revise), 10 |
| Skip | 8, 11, 12, 13 |
| Risk | Doc drifts from reality — no monitoring |
| Empirical anchor | `project_reappeared_business_rule.md` memory said "emit as collection" but empirically refuted — memory drift |

---

## Part 4 — Universal disciplines (every change)

### 4.1 Three gates

**G1 — Loop check (CONTRACT.md Gate 1)**

Latest commit on the file you're about to edit < 24h old? → run `/debug` Phase 1 LOOP CHECK literally before anything else.

Cost asymmetry: false positive = 30s; false negative = 5h pendulum (TD-20..25).

**G2 — Impact / Rollback (CONTRACT.md Gate 2)**

Before any non-trivial change:
```
IMPACT ESTIMATE:
  files affected:        N
  rows / users affected: N (or "must investigate first")
  production exposure:   YES / NO

ROLLBACK PLAN:
  revert command:        git revert <hash>
  revert time:           <minutes>
  data state after revert: unchanged / requires X cleanup
```
Empty Impact OR empty Rollback = change rejected.

**G3 — Decomposition (CONTRACT.md Gate 3)**

Every observed mismatch / failure has a counted, sampled, evidenced class. Class "edge cases" / "TODO" / "rare" = decomposition incomplete → investigate, do not implement.

Empirical anchor: 986 CREST_ONLY rows — 6 sessions of partial batches because no decomposition; 1 categorisation pass would have shown 71% single-class coverage.

### 4.2 Disclosure tags

Use literally:
- `[CONFIRMED]` — ran it, saw output, OR quoting `file:line`
- `[ASSUMED]` — inferring from code without execution
- `[UNKNOWN]` — STOP. Ask.

Never write "I checked" without one. Reading code = `[ASSUMED]`, not `[CONFIRMED]`.

### 4.3 Loop detection

Two signals → STOP:
1. **G1 trigger**: commit on same file < 24h ago
2. **Defensive fix N=2**: second fix whose justification is "undo regression from fix N-1"

After signal: full revert + re-baseline OR escalate to Requester with diagnosis. Do NOT continue with fix N+1 in same direction.

### 4.4 Frame challenge

5+ iterations in same frame failing? **The problem IS the frame.**

Step out. Re-question:
- Goal: are we solving the right problem?
- Metric: does the metric reflect what matters?
- Constraints: is anything we accepted as fixed actually negotiable?

Empirical anchor: Settlement v1→v5 chasing CREST per-row when business needed only Δ=0 (`feedback_frame_challenge_when_iterations_fail.md`).

### 4.5 Evidence-only decision (CONTRACT §E)

A decision is **valid** only if every condition holds:
- E1 evidence existence
- E2 evidence from Data ∪ Code ∪ Requirements (no intuition)
- E3 verifiable (citable, reproducible)
- E4 sufficient (not one sample / one log line)
- E5 hidden assumptions eliminated
- E6 traceable (re-derivable from record alone)
- E7 certain ∩ uncertain = ∅
- E8 deterministic (two reviewers reach same conclusion)

Defending an invalid decision is a CONTRACT §A.6 silence (false completeness).

---

## Part 5 — Working with AI (the assistant) effectively

### 5.1 Skills, commands, templates

| Tool | When |
|---|---|
| `/analyze` | Understand a system area before planning |
| `/grill` | Drive UNKNOWN → CONFIRMED in requirements |
| `/plan` | Generate a PLAN.md skeleton from a SPEC |
| `/deep-verify` | Independent verification of a plan or implementation |
| `/deep-risk` | High-stakes change (financial, regulatory, irreversible) |
| `/preflight` | Pre-commit gate check (file:line evidence) |
| `/review` | PR review — different actor from author |
| `/debug` | Phase 1 LOOP CHECK + structured debugging |

Skills compose. `commands.md` documents micro-skill compositions.

### 5.2 Memory — surprises only

| DO save | DO NOT save |
|---|---|
| Surprises (rule that wasn't obvious) | Code patterns (read the code) |
| Corrections from user | Architecture (it's in the code) |
| Empirical anchors that took hours to discover | Recent diffs (use git log) |
| External system quirks | Anything in CLAUDE.md / CONTRACT.md |
| Confirmed approaches (validate "good calls") | Ephemeral state |

Memory entry format: rule + **Why:** + **How to apply:** (see existing `feedback_*.md` files).

Memory is a SNAPSHOT. Verify against current state before acting on it. `project_reappeared_business_rule.md` had drift — memory said one thing, empirical refuted.

### 5.3 Subagents

When a task has a clear sub-output you'll consume — delegate. When the AI itself is investigating — do not.

Rules:
- Subagent's `[CONFIRMED]` becomes parent's `[ASSUMED]` until verified independently
- Side effects (writes, deletes, external calls) aggregate into parent's MODIFYING list
- Disclosure obligations are transitive (CONTRACT §B "Subagent delegation")

### 5.4 Prompt-first pattern (`WORKFLOW.md` §10)

For repetitive work, write the PROMPT first, verify it, then execute. The prompt becomes a reusable skill candidate. Don't re-derive the prompt from scratch each time.

### 5.5 Context budget

Context window is the bottleneck. Conserve:
- Use Read with line ranges, not whole files
- Use Grep with output_mode=files_with_matches when scanning
- Delegate broad searches to Explore subagent
- Capture intermediate results to memory if they'll be reused

When context is near full: stop, summarize state, start a fresh session with the summary.

---

## Part 6 — Verification & merge

### 6.1 Pre-commit

`/preflight` must pass. Required outputs:
- DID / DID NOT / CONCLUSION (CONTRACT §B.1)
- DONE / SKIPPED / FAILURE SCENARIOS (CONTRACT §B.5)
- All `[ASSUMED]` tags resolved or explicitly accepted
- Tests run, output pasted

### 6.2 PR description

| Section | Required |
|---|---|
| Link to PLAN | Yes |
| Stage-by-stage evidence | Yes (or PLAN reference) |
| Test commands run | Yes (with output snippet) |
| Rollback command | Yes |
| Failure scenarios (≥3) | Yes |
| AI attribution | NO (`feedback_no_ai_attribution.md`) |

### 6.3 Independent verification

Reviewer is NOT the Driver. Reviewer:
- Re-runs the tests independently
- Re-derives the conclusion from PLAN evidence (without consulting Driver)
- Verifies all `[ASSUMED]` tags
- Checks G1+G2+G3 compliance

If Reviewer's re-derivation diverges from Driver's conclusion → REJECT, not "discuss until aligned."

### 6.4 CI/CD integration

CI must enforce as hard gates (not warnings):
- Tests pass
- No `tmp/` files in diff
- No AI attribution strings in commits / files
- File:line references in commit message exist

If a rule lives only in markdown (level 1 per RULES.md §6) — it's decoration. Move it to a hook (level 2) or test (level 3).

---

## Part 7 — Deploy & operations

### 7.1 Pre-deploy checklist

Before deploy, in writing:

```
DEPLOY TARGET:    dev / staging / prod
SCOPE:            files / rows / users
ROLLBACK CMD:     <one line>
ROLLBACK TIME:    <minutes>
MONITOR:          which dashboard / metric / alert
GO / NO-GO:       criteria for stopping mid-rollout
```

If MONITOR is empty → you are deploying blind. Stop.

### 7.2 Rollout patterns

| Pattern | When | Caveat |
|---|---|---|
| Direct (everyone at once) | Trivial UI, doc | Not for data work |
| Country-by-country | Data work | Order: lowest risk first (e.g., PL/PT before US) |
| Canary (% traffic) | Web request path | Need session affinity if stateful |
| Feature flag | Reversible, opt-in | Forbidden as backwards-compat shim per CLAUDE.md |
| Dark launch | New code path | Compare against legacy before cutover |

### 7.3 Post-deploy validation (Stage 12)

Re-run oracle in deployed env. NOT "looks fine" — literal numbers.

For data work: regression suite against deployed env, per-country, current week.

### 7.4 Monitoring window (Stage 13)

| Class | Window | Watch |
|---|---|---|
| Bug fix | 24h | Original repro — not recurred |
| Feature | 1 week | Adoption + error rate |
| Refactor | 1 week | No behavior delta in adjacent code |
| Data work | 1 buy cycle (≤7d) | Per-invoice oracle stays at 100% |
| Infra | 24h | State machine stable |

### 7.5 Incident response (Stage 15)

Within 1h: revert OR contain.
Within 48h: post-mortem with: timeline / root cause / detection gap / prevention.
Within 1 week: process update IF the failure pattern is new.

Post-mortem structure: `framework/PRACTICE_SURVEY.md`.

### 7.6 Replay capability

For data pipelines: every operation must be **idempotent** AND **replayable** for a specific date. Bootstrap markers protected from delete. See `feedback_settlement_v5_permanent_experiment.md` and `tools/be_replay_2026_04_15.py`.

---

## Part 8 — Knowledge management

### 8.1 Memory of surprises (per-session)

Trigger to write: "this was non-obvious", "I was wrong about X", "user corrected me on Y", "the rule turned out to be Z, not what I thought".

Trigger NOT to write: "the code does X" (read it), "the architecture is Y" (it's in the diagram), "today we changed Z" (git log).

Format: see existing `feedback_*.md`.

### 8.2 Lessons learned (per-incident)

When a failure pattern is new: append to `LESSONS_LEARNED.md`. Include:
- 1-line summary
- Trigger commits / dates
- Root cause class (1 of 18 from `framework/PRACTICE_SURVEY.md`)
- Prevention added (which gate / hook / test)
- Empirical: did the prevention prevent recurrence?

### 8.3 Templates and skills

A repeated multi-step procedure (3+ uses) → promote to template (`templates/`) or skill (`.claude/skills/`).

A skill defaults to lazy-load: small description + body fetched on use.

### 8.4 When to evolve the process

Trigger: a failure mode happens 2+ times despite existing rules.
Action: add the rule at level 2 or 3 (RULES.md §6). Update this `PROCESS.md` Part 4 if universal, Part 3 if class-specific.

Process changes need same gates: CONTRACT §A.6 (false completeness on the previous version).

---

## Part 9 — Onboarding (4 weeks)

### Week 1 — Read + observe

| Day | Activity | Output |
|---|---|---|
| 1 | Read CONTRACT.md + PROCESS.md (this file) + RULES.md | None — comprehension only |
| 1 | Read 5 most recent `feedback_*.md` from memory | Notes: which surprised you most |
| 2 | Read WORKFLOW.md §1, §2, §5, §8 | None |
| 2 | Read 3 most recent PLAN_*.md files | None |
| 3 | Pair with Driver on a real task (observe, don't drive) | None — observation only |
| 4 | One trivial task end-to-end with all gates explicit (e.g., comment typo with G1+G2+G3 written out) | One PR — shows you grasp gates |
| 5 | Read `framework/PRACTICE_SURVEY.md` (18 incidents) | Pick 3 you'd most want to prevent |

Check at end of Week 1: can you state the 5 mantras (1.3) without looking?

### Week 2 — First bug fix solo

Pick a small bug from TODO.md.

| Day | Activity | Gate |
|---|---|---|
| 1 | Stage 1–4 (intake, classify, oracle, clarify) | Oracle in writing |
| 2 | Stage 5 (PLAN) | All sections present (CONTRACT.md template if needed) |
| 2 | Stage 6 (verify plan) — submit to senior reviewer | ACCEPT before code |
| 3 | Stage 7 (execute) — code → run → evidence per stage | Evidence in PLAN |
| 3 | Stage 8 (preflight) | G1+G2+G3 explicit |
| 4 | Stage 9 (PR) | Independent reviewer approves |
| 5 | Stage 10–13 (merge, deploy, validate, monitor) | Oracle holds |

Check at end of Week 2: did you trigger any anti-pattern in Part 4? Capture the lesson if yes.

### Week 3 — First feature with full plan

Pick a small feature from TODO.md.

Mandatory artifacts:
- SPEC_<feature>.md
- PLAN_<feature>.md (including test scenarios + invariants + rollback)
- validation/ files if data-driven

Submit PLAN to /deep-verify before any code. REJECT means iterate the plan, not skip to code.

Check at end of Week 3: did you skip any stage 1–10? If yes — what did it cost?

### Week 4 — Independent cycle

Drive a real task without senior intervention. Senior reviews PR only, not in-progress.

Check at end of Week 4 — readiness criteria:
- [ ] Oracle defined BEFORE editor opens
- [ ] Delta counted in numbers
- [ ] Classes listed without "edge cases"
- [ ] Re-derives on challenge instead of defending
- [ ] One memory entry captured from own surprise
- [ ] One process improvement suggested (anti-pattern noticed → rule moved to level 2/3)

If all 6 met: independent. If <6: extend by 2 weeks with focus on the gap.

---

## Part 10 — Metrics

What to measure. If a metric is not collected — the corresponding behavior is not managed.

### 10.1 Leading indicators (collect weekly)

| Metric | Source | Target |
|---|---|---|
| % PRs with PLAN.md before first commit | git log + `.ai/PLAN_*.md` mtime | >80% for non-trivial |
| % PRs with `[CONFIRMED]` in description | grep on PR text | 100% for prod data work |
| % stages with literal output evidence | grep PLAN files | 100% |
| Avg # commits per merged PR | git log | <5 (high → pendulum) |
| % defensive fixes (N≥2 in same area / 24h) | git log | <5% |

### 10.2 Lagging indicators (collect monthly)

| Metric | Source | Target |
|---|---|---|
| # incidents / month | LESSONS_LEARNED.md | trending down |
| # rollbacks / month | git revert log | <2 |
| Mean time to revert | git log + deploy log | <5 min |
| % oracle coverage gain per week | regression suite | growing |
| # repeat failures (same root cause class) | PRACTICE_SURVEY.md | 0 — repeat = process gap |

### 10.3 Process health checks (quarterly)

- Are memories from 90 days ago still valid? Audit + retire / update
- Has any `feedback_*.md` rule moved from level 1 → 2/3? (RULES.md §6)
- Did any anti-pattern from Part 4 appear in last 90 days? Why didn't gate catch it?
- New work classes in Part 3? (8 classes covers everything we've seen — but the world changes)

### 10.4 When to escalate

Escalate to Process Owner when:
- A rule fired but was overridden (was the override correct?)
- A gate was empty but PR merged (gate is decoration → fix)
- Same root-cause class hits 2+ times in a quarter
- Onboarding fails (someone hits Week 4 readiness with <4/6)

---

## Part 11 — Anti-patterns library (grow this)

| # | Anti-pattern | Anchor | Mitigation |
|---|---|---|---|
| 1 | Simulation without filter parity | `feedback_simulation_must_match_filters.md` | Replicate ALL prod query filters in any investigation script |
| 2 | A/B/C ask cycle to user | CONTRACT §B.13 | Investigate first; only ask when consequences are deterministically derivable |
| 3 | Local precision masking oracle gap | CONTRACT §B.12 | Always report % of oracle covered, not % of self-emit matched |
| 4 | Solo-verifier | CONTRACT §B.8 | Reviewer is different actor; re-derive without consulting author |
| 5 | Memory drift | `project_reappeared_business_rule.md` | Verify memory against current state before acting |
| 6 | Defending vs re-deriving | CONTRACT §A.6 | When challenged: re-derive from evidence, don't justify |
| 7 | Tool sprawl | `feedback_no_temp_sprawl.md` | One consolidated tool with subcommands |
| 8 | Stale code in container | `feedback_docker_rebuild_after_edit.md` | Rebuild + verify file:line in container |
| 9 | Float epsilon hiding sub-cent errors | `feedback_no_float_epsilon.md` | NUMERIC = decimal; exact comparison |
| 10 | Bootstrap markers in oracle diff | (multiple memory entries) | Filter init_was_* or apply window correctly |
| 11 | Prototype shipped to prod | (CLAUDE.md "no half-finished") | Mark PROTOTYPE in code header; CI rejects on main |
| 12 | Trust unverified categorization | This session — multi-week recurring artifact | Categorize once; verify count adds up to total |
| 13 | Disclosure-compliant but shallow | CONTRACT §A.8 (TD-20 anchor) | Decompose before deciding; min 3 hypotheses |

Append new anti-patterns here when discovered.

---

## Part 12 — One-page summary (cheat sheet)

```
INTAKE → CLASSIFY → ORACLE → CLARIFY → PLAN → VERIFY → EXECUTE
       → PRECOMMIT → PR → MERGE → DEPLOY → VALIDATE → MONITOR → CLOSE

GATES (every change):
  G1 last-commit < 24h ? → /debug Phase 1 first
  G2 IMPACT + ROLLBACK in writing — empty = rejected
  G3 every observation classified — "edge cases" = decomp incomplete

TAGS:
  [CONFIRMED]  ran + saw output / quoting file:line
  [ASSUMED]    inferred from code without run
  [UNKNOWN]    STOP. Ask.

MANTRAS:
  1. Oracle first. Code second.
  2. Evidence in numbers. Not adjectives.
  3. Decompose before deciding.
  4. Verify externally. Solo-verifier is not verification.
  5. Capture surprises only.

STOP CONDITIONS:
  Done when: oracle delta = 0 OR variance archived with ID
  Frame challenge: 5+ iterations failing → re-question goal
  Loop: defensive fix N=2 → revert + re-baseline

WORK CLASS DECIDES:
  Bug / Feature / Refactor / Investigation / Data / Infra / Prototype / Doc
  Each class has its own min-stages + risk profile (Part 3).

WHEN STUCK: re-read Part 4, then escalate to Requester.
```

---

## Part 13 — Reference map

| You need | Read |
|---|---|
| Disclosure / what to communicate | `CONTRACT.md` |
| 8 rules with empirical anchors | `RULES.md` |
| Detailed lifecycle examples (Settlement Report) | `WORKFLOW.md` §2 |
| PLAN structure template | `WORKFLOW.md` §5 + `templates/` |
| Code standards | `standards.md` |
| Skills, micro-skills, prompt-first pattern | `commands.md` + `WORKFLOW.md` §10 |
| Module map, business rules | `PROJECT_PLAN.md` |
| Active tasks | `TODO.md` |
| Post-mortems / failure history | `LESSONS_LEARNED.md` + `framework/PRACTICE_SURVEY.md` |
| HOWTOs (BQ migration, deployment, health checks) | `templates/` |
| Governance framework (CGAID) | `framework/` |
| Formal theorems | `theorems/` |

---

## Part 14 — Honesty about gaps

Things we know work (used and verified):
- Oracle-first + decomposition + 3 gates pattern
- Memory of surprises
- Empirical anchors per rule
- Independent verification

Things we suspect work but haven't fully validated:
- Onboarding 4-week target (sample size: small — track)
- Metrics in Part 10 (collection not yet automated for all)
- Quarterly process health check (cycle not yet completed)

Things this process does NOT yet cover:
- Multi-team coordination (single-team assumption holds today)
- External audit / regulatory sign-off (governance handled in `framework/` separately)
- AI model upgrade / re-baselining of skills when underlying model changes
- Cost / billing optimisation of AI usage at scale

When you hit a gap → add to `LESSONS_LEARNED.md` + Part 8.4 trigger to evolve.

---

> **Oracle first. Evidence in numbers. Decompose before deciding. Verify externally. Capture surprises only.**
