# Workflow for a new team member

> This describes **how we work step by step**. Not abstract principles — concrete actions: which skill to invoke, which file to create, which test to run, which evidence to paste.
>
> If you only have time for one thing: read §1 (full cycle) + §2 (Settlement Report example) + §5 (PLAN structure). The rest is reference.
>
> Date: 2026-04-23. Sources: git log (22 days of work), skills in `.claude/skills/`, `commands.md`, PLANs in `.ai/`, memory.

---

## §1 — Full task cycle: from "you have a task" to "merged"

Ten steps. Each has a concrete output. Skipping any one of them ends in a rollback within a few days — verified empirically.

```
[1] Task arrives        ────────►  [2] /analyze       (understand what you need)
                                        │
                                        ▼
[3] /grill  ◄──── if something is unclear — before planning
                                        │
                                        ▼
[4] Evidence base ────►  validation/*.md + .csv       (when touching data)
                                        │
                                        ▼
[5] /plan ────► PLAN_<feature>.md with stages + test scenarios
                                        │
                                        ▼
[6] /deep-verify PLAN (before code) ◄─── stops on REJECT
                                        │
                                        ▼
[7] /develop stage 1  ──►  code + run test + paste evidence into PLAN
                                        │
[7] /develop stage 2  ──►  code + run test + paste evidence into PLAN
                                        │
[7] /develop stage N  ──►  code + run test + paste evidence into PLAN
                                        │
                                        ▼
[8] /preflight (pre-commit gate with file:line evidence)
                                        │
                                        ▼
[9] commit + PR + /review
                                        │
                                        ▼
[10] merge → update PLAN Status → close TODO
                                        │
                     if general lesson → add to LESSONS_LEARNED.md
```

**Why so many steps?** Because each one answers a specific question whose absence cost us a production incident (`framework/PRACTICE_SURVEY.md` has a list of 18 incidents — each = a skipped step).

---

## §2 — Real example: Settlement Report (2026-04-13 → 2026-04-22)

This is the **archetype** of what work looks like when **a PLAN + evidence base are missing**. I show what went wrong first (because it teaches fastest), then what the same thing done correctly looks like.

### 2.1 The wrong version (2026-04-13, without a PLAN)

Task: "Settlement Report does not match CREST".

It went like this (actual commits within one day):

```
3ded3eb  Exclude settled/partial_settlement from settlement purchased CTE
6ee9561  Fix settlement report: remove incorrect date filter
         that excluded 96% of settlements
4450ff1  Fix settlement Row Type 1: include collected_amount via LEFT JOIN
2247357  Fix settlement Row Type 1/2: include all purchased document types
6cad33c  Add report beginning balance row + fix structure
05376c1  Fix report beginning balance: use NET outstanding
482312f  Fix PP report: show all outstanding with NET amounts
3996b9a  Fix double-counting: revert beginning_balance and PP to RAW amounts
32c200a  Settlement Reports
```

**9 commits in 1 day. Each fix revealed the next case.** `3996b9a` reverts to the state before `482312f/05376c1` — meaning the previous fixes were wrong. Classic pendulum: fix A breaks B, fix B breaks C, fix C reverts to A.

**What did not happen:**
- `/analyze` was not done → all consumers of the settlement CTE were not mapped
- Evidence base was not done → nobody knew what the result SHOULD be vs what it IS
- PLAN with test scenarios was not done → every edge case was discovered on the fly
- No stages with hard evidence → "fix A works" was declared, but there was no output "for AU W17 gross_out = X, CREST = X"

### 2.2 The correct version (2026-04-22, with a PLAN)

After 9 days of stabilization — the same area, done as `PLAN_settlement_event_log_refactor.md`. What changed:

**Step 1 — Evidence base BEFORE the plan:**
4 files in `.ai/validation/`:
- `crest_treatment_rules_au.md` — 5 authoritative test cases from Treasury
- `crest_history_ground_truth_au_w17.md` — 59-day timelines for 15 residual invoices
- `event_projection_proof_au_w17.md` — per-invoice mapping proof, 13/15 MATCH
- `event_projection_proof_au_w17.csv` — raw CSV for diffing

Every formula in the plan derived from **these data**, not from intuition.

**Step 2 — PLAN with stages and hard evidence per stage:**

Excerpt from `PLAN_settlement_event_log_refactor.md` section **Phase 1-2 empirical validation** (quoted verbatim):

```
1. POST /api/maintenance/load-data AU 8 dates (W17):
     +281,158 rows in raw, 9 doc_types all present
2. Markers emitted per MR A:
     settled_return=356, settled_payment=199,
     partial_settlement_return=24, partial_settlement_payment=8
3. POST /api/buying/run-process AU 2026-04-13 + 2026-04-20:
     34,052 purchased invoices, 2 execution_ids
4. Backend build_settlement_sql(["AU_001"]) executed:
     10,864 rows output
5. Consumer filter test:
     output doc_types = {invoice, payment, return} only —
     no pipeline-derived marker leak
6. Compare vs CREST AU W17 Economic AUD:
     gross_out  -9,411,761.07    -9,411,761.07    0.00 ✅ EXACT MATCH
```

**This is the pattern "stage = code + run + evidence".** Each number is a separate stage, each ends with a concrete number from the system (not "works", but `+281,158 rows`, `356 markers`, `10,864 rows`, `0.00 delta`).

**Step 3 — /deep-verify of the plan before code:**
The PLAN was verified by `/deep-verify` and `/deep-risk` before coding started. Result: architecture v0.6 "ETL-time vs Report-time emission" — the decision was **not** based on intuition, only on analyzed alternatives.

### 2.3 Takeaway

**Work without PLAN + evidence + stage evidence = 9 commits in one day, each reverting the previous.**
**Work with PLAN + evidence + stage evidence = 1 merge with exact numbers.**

This is not bureaucracy. This is the **difference between a production incident and a closed task**.

---

## §3 — When to use which skill

Each skill answers a specific question. Table ordered by the **sequence** of a typical task.

| # | Skill | When I invoke it | What I get | What it does NOT do |
|---|---|---|---|---|
| 1 | `/analyze` | Task is **unclear from a business perspective** or module is **unknown**. Before `/plan`. | Requirements analysis PRD-style with C/A/U tags (CONFIRMED/ASSUMED/UNKNOWN). Each UNKNOWN blocks further progress. | Does not write code. Does not create a plan — only defines the problem. |
| 2 | `/grill` | I have a rough plan in mind but **sense ambiguities**. Before `/plan`. | Interview one question at a time, with a recommended answer. Eliminates hidden assumptions. | Does not give a ready plan — gives alignment. |
| 3 | `/deep-align` | We work as a team and there are **different understandings of the same thing**. | Shared understanding, concept mapping. | Does not resolve technically. |
| 4 | `/deep-explore` | I have **3+ options** and don't know which to choose. | Decision tree with criteria + recommendation. | This is not a plan. |
| 5 | `/deep-architect` | I am designing a new **system / module / bounded context**. | Design document with alternatives and trade-offs. | Does not write code. |
| 6 | `/plan` | Work has ≥ 2 stages. **Always before code** for feature / refactor / pipeline. Implementation is BLOCKED until APPROVE. | `PLAN_<feature>.md` with stages, scenarios, invariants, rollback. | Does not code. |
| 7 | `/deep-verify` | I have an **artifact** (plan, spec, claim, code) and want to **verify correctness**. | Score + findings + adversarial review + verdict ACCEPT/UNCERTAIN/REJECT. | Does not create a plan — only verifies. |
| 8 | `/deep-risk` | PLAN ready, I want a **risk list** with 5D scoring + cascade + Cobra Effect (mitigation breaks something else). | Risk ranking and counter-plans. | Does not verify logical correctness. |
| 9 | `/deep-aggregate` | I have **several analyses** (risk + feasibility + architecture) and need a **GO/NO-GO**. | One decision based on the aggregate. | Does not do new analyses. |
| 10 | `/develop` | PLAN **approved**. Entering implementation. | Phases with cross-referenced artifacts. py_compile check. | Does not plan. |
| 11 | `/test` | Writing tests. Each test = **proof + rejected alternative**. Mandatory pytest output paste. | System-level tests, edge cases, 10x scale architecture. | Not unit-only — the whole system. |
| 12 | `/preflight` | **Before commit.** Gate with file:line evidence. | Checklist with greppable evidence per rule. | Does not commit — gate only. |
| 13 | `/review` | PR ready → review. | Code review with CONTRACT discipline. | Does not catch everything — verifies details. |
| 14 | `/guard` | **ALWAYS ACTIVE** — auto-invoked before every code edit. | GUARD CHECK with layer classification + violation scan. HARD RULE block. | You don't invoke manually (except for audit). |

### Typical sequence for a full feature

```
/analyze "<feature>"
    ↓ (if you have unresolved assumptions)
/grill
    ↓
[Create evidence/validation/<name>.md if external data]
    ↓
/plan "<feature>"
    ↓
/deep-verify <plan path>   ← if REJECT → fix plan → re-verify
    ↓ (if high-stake)
/deep-risk <plan path>
    ↓
/develop <stage 1>
    ↓ RUN TEST → paste evidence into PLAN
/develop <stage 2>
    ↓ RUN TEST → paste evidence into PLAN
...
/test "verify-existing <module>"
    ↓
/preflight
    ↓
git commit + push + /review
```

### When fewer skills — for a class (a) bugfix

Single-file bug, known fix, no cascade — skill sequence shortens to:

```
/analyze (quickly — understand where)
    ↓
/develop (fix)
    ↓ RUN TEST → output
/preflight
    ↓
commit + PR
```

No PLAN, no evidence base. But **runtime test with output is mandatory**.

---

## §4 — commands.md: micro-skills as building blocks

`commands.md` has 80+ "reputation-frame" prompts (like *"If someone said you were the best X, what would you have to do?"*). You don't write a prompt from scratch — **you copy 3–4 blocks + CONTRACT** and paste them to Claude.

### 4.1 Why this pattern works (from `LESSONS_LEARNED §1`)

1. **Reputation-frame sets the standard, not the action.** The difference between *"debug this"* and *"if you were the best debugger who never fixes the symptom, only the root cause..."*. The second forces thinking before action.
2. **Modularity.** Each block is standalone. You combine them like LEGO.
3. **CONTRACT ALWAYS at the end.** Micro-skills say what to aim for. CONTRACT says what is NOT allowed. Together = bounded space of ambition.
4. **The library lives.** After every incident, you add a block.

### 4.2 Ready-made compositions

**Debugging:**
```
#2 (Debugger – root cause master)
+ #18.3 (Trace execution)
+ #18.5 (Hypotheses and elimination)
+ CONTRACT
```

**Business analysis (new feature, spec):**
```
#26.1 (Business Analyst – absolute level)
+ #26.3 (Requirements Precision)
+ #26.6 (Scenario & Edge Case Expert)
+ CONTRACT
```

**Implementation:**
```
#27.1 (Developer – absolute level)
+ #27.5 (Contract-First)
+ #27.7 (Impact-Aware)
+ CONTRACT
```

**Data engineering / BQ refactor:**
```
#3 (Data Engineer – quality without compromise)
+ #12 (Data Quality Guardian)
+ #21 (Cost Optimization – Cloud/BigQuery)
+ CONTRACT
```

**Architecture / new module:**
```
#4 (Architect – system without weak points)
+ #11 (Data Model Architect)
+ #15 (Schema Governance)
+ CONTRACT
```

**Before a high-stakes decision:**
```
#8 (Evidence-driven engineer)
+ #9 (Production-grade owner)
+ #23 (Change Impact Analyst)
+ CONTRACT
```

### 4.3 How to physically use it

1. Open `.ai/commands.md`.
2. Identify the category (debug / analysis / implementation / data / architecture).
3. **Copy 3–4 blocks** (full blocks with headings — do not paraphrase).
4. Append at the end the **full CONTRACT.md** or reference "apply `.ai/CONTRACT.md`".
5. Append the **specific task** ("task: fix settlement report that does not match CREST AU W17").
6. Paste everything to Claude as the first prompt.

Effect: Claude gets a *thinking frame* (micro-skills) + *constraints* (CONTRACT) + *specifics* (task). The output is qualitatively different from "debug this".

### 4.4 When you add a new block

A new failure category appears (e.g. AI skips observations without an explicit question). You write a new `#NN.X` with `"If someone said you were X who..."` and add it to `commands.md`. Rule of three: if a block is used 3× → it stays in the library.

---

## §5 — PLAN: mandatory structure

Every PLAN has these sections. **In this order.** Empty section = SKIP BLOCK with justification (shorter than filling it in).

### 5.1 Full template (copy, adapt)

```markdown
# PLAN — <name> (short description of what and why)

**Status**: <DRAFT | APPROVED | IN PROGRESS | COMPLETE | SUPERSEDED>
**Version**: v0.1
**Date**: YYYY-MM-DD
**Owner**: <nick>
**Supersedes**: <PLAN_X.md> (if _v2)

---

## 1. Context — why we are doing this

<2-3 sentences: current state, problem, business goal. No code here.>

---

## 2. Evidence base

<Table: File | Contents | Status>
| File | Contents | Status |
|---|---|---|
| validation/X.md | Ground truth for AU W17 | [CONFIRMED] by Treasury |
| validation/X.csv | Raw data for diff | [CONFIRMED] |

If there is NO evidence → write why (e.g. "pure type refactor, semantics untouched").

---

## 3. Decisions

### D1. <concise decision heading>

**Alternative considered:**
- Option A: <description>. Pro: X. Con: Y.
- Option B: <description>. Pro: X. Con: Y.

**Choice:** <A / B / C>

**Rationale:** <why, based on evidence>

**Implication:** <which files/places will be updated>

### D2. ...

---

## 4. Test scenarios  ← MANDATORY, BEFORE STAGES

List of scenarios that MUST work after ship. Each = concrete input + expected output.

### 4.1 Happy path
- **S1:** user calls `POST /api/buying/run` for AU 2026-04-13 → response 200, body.counts.purchased == 34052.

### 4.2 Edge cases
- **E1:** empty dataset (0 rows in open_invoice_AU_001) → response 200, counts.purchased == 0, no write to buy_run.
- **E2:** single row (exactly 1 invoice) → normal flow, purchased == 1.
- **E3:** all invoices already purchased earlier (anti-join excludes all) → counts.purchased == 0.
- **E4:** mixed: 50% settled + 50% active → purchased == 50% of input.

### 4.3 Boundaries
- **B1:** date boundary — invoice on exactly `buy_date` → included (inclusive boundary).
- **B2:** date boundary — invoice on `buy_date - 1 day` → included.
- **B3:** date boundary — invoice on `buy_date + 1 day` → NOT included.
- **B4:** amount = 0 → excluded by filter `amount > 0`.
- **B5:** amount MAX float → no overflow in sum.
- **B6:** string length — legal_entity_code 0 chars → error 422.
- **B7:** string length — legal_entity_code 256 chars → truncation check.

### 4.4 Failure modes
- **F1:** BQ timeout (30s) → 504 to FE, no partial write.
- **F2:** Firestore lock taken → 409, retry message.
- **F3:** concurrent run for the same country → second request gets 409.
- **F4:** network partition mid-write → idempotency key checks for duplicate.

### 4.5 Regression scenarios
- **R1:** Old happy path from previous version (commit X) still works — we did not break it.
- **R2:** Settlement Report gross_out == CREST for AU W17 (from `validation/...`).

---

## 5. Invariants  ← Must be TRUE after every stage

### I1. Unique marker per composite key
```sql
ASSERT (SELECT COUNT(*) FROM markers
        WHERE is_active=TRUE
        GROUP BY invoice_id, legal_entity_code, document_type
        HAVING COUNT(*) > 1) = 0
```

### I2. No future-dated markers
```sql
ASSERT (SELECT MAX(event_date) FROM markers) <= CURRENT_DATE()
```

---

## 6. Stages — every STAGE ends with RUN + EVIDENCE

### Stage 1 — <what we are changing>

**Files touched:**
- backend/app/modules/X/service.py:123-145 (add filter)
- backend/app/modules/X/repository.py:45 (add column)

**Code change summary:**
<1-2 sentences: what the change consists of>

**Executable test (command to run):**
```bash
docker compose exec backend python -c "
from app.modules.X.service import do_thing
print(do_thing(country='AU', date='2026-04-13'))
"
```

**Expected output pattern:**
- Count > 0
- No exceptions
- keys match: invoice_id, amount, ...

**Hard evidence (paste LITERAL output after running):**
```
<paste here — concrete numbers, concrete JSON, concrete SQL output>
Count: 10,864
Sample:
{"invoice_id": "AU0001234", "amount": 1423.50, ...}
```

**Invariants checked:**
- I1: ✅ PASS (query returned 0)
- I2: ✅ PASS (max date 2026-04-22 ≤ today)

**Test scenarios covered in this stage:**
- S1, E1, E3, B1

**Status:** ✅ COMPLETE [CONFIRMED runtime 2026-04-22 14:35]

---

### Stage 2 — ...

Same pattern. You do not close a Stage without evidence.

---

## 7. Rollback plan

Per stage: how to revert the change. `git revert <sha>` + data migration if needed.

- Stage 1 rollback: `git revert <sha1>`, BQ rollback not required (soft-delete, is_active=FALSE).
- Stage 2 rollback: `git revert <sha2>` + manual setting of Firestore flag Y.

---

## 8. Execution progress log

| Stage | Status | Date | Evidence commit |
|---|---|---|---|
| 1 | ✅ COMPLETE | 2026-04-22 | `d536e47` |
| 2 | 🔄 IN PROGRESS | — | — |
| 3 | ⏳ PENDING | — | — |
```

### 5.2 Section **4. Test scenarios** — why it is mandatory and how to generate them

Without this section you repeat the Settlement Report scenario from §2.1: 9 fixes in one day. Every edge case must be known **before code**, not discovered at runtime.

**How to generate scenarios (deterministically):**

1. **Happy path** — what the user expects. Minimum 1 scenario.
2. **Edge cases** — combinatorial extremes:
   - empty collection (0)
   - single element (1)
   - everything "already processed" (no-op)
   - mixed (50/50)
   - everything "inactive" (is_active=FALSE)
3. **Boundaries** — type and date limits:
   - date exactly on the boundary (inclusive/exclusive?)
   - amount = 0 / negative / max
   - string empty / 1-char / MAX-char
   - timezone boundary
   - month/quarter/year boundary
4. **Failure modes** — what can break in infra:
   - timeout
   - lock taken (concurrent)
   - partial write / network mid-request
   - external API down (Warsaw, bank)
   - partial data (Warsaw late)
5. **Regression** — old scenarios must still work:
   - scenario from the previous version (referenced by commit)
   - ground truth comparison (evidence base)

**Rule:** min 3 + 3 + 3 + 3 + 2 = **≥ 14 scenarios** in a PLAN of type (b) feature / (d) pipeline / (e) restore. For a bugfix (a) min 3 (happy + 1 edge + 1 regression).

Empty sections = SKIP BLOCK longer than writing the scenario. **You write scenarios, not a skip block.**

### 5.3 Section **6. Stages** — pattern "code → run → evidence"

No phase without a test. No test without evidence. No evidence without literal output.

**Incorrect stage closure:**
> *Stage 1 done — filter works.*

**Correct stage closure:**
```
Stage 1 — COMPLETE

Executable test: POST /api/buying/run-process {country: "AU", date: "2026-04-13"}
Literal output:
  HTTP 200
  body.counts.purchased = 34052
  body.counts.skipped = 142
  body.execution_id = "2026-04-13T09:15:00Z_AU"

Invariants:
  I1 unique key — query returned 0 ✅
  I2 no future date — MAX(date) = 2026-04-22 ≤ today ✅

Scenarios covered: S1 (happy), E3 (all-purchased boundary)
Status: [CONFIRMED runtime 2026-04-22 14:35:12]
```

The difference: the second you can verify a week later — you see what happened. The first is a word without evidence.

---

## §6 — File creation order for a new feature

Specifically, step by step, for a new feature of type (b) or (d). Small bugfix → shortened to steps 6-9.

### Step 1: Research (you don't create files yet)

```bash
# Read related files
cat .ai/PROJECT_PLAN.md | grep -A 2 "<module>"
ls .ai/PLAN_*.md                            # is there an active plan?
grep -r "<keyword>" .ai/ memory/             # is anything already known?
```

### Step 2: If requirements are unclear → `/analyze` or `/grill`

**You don't write a SPEC until all UNKNOWNs are resolved.** `/analyze` produces PRD-style output with C/A/U. Each UNKNOWN → question to the business stakeholders (see `memory/reference_meeting_contacts.md`).

### Step 3: Create `.ai/SPEC_<feature>.md` (if a feature)

Sections: Inputs · Outputs · Formula · Edge cases · Acceptance criteria · Out of scope · Verified with.

Verification with business BEFORE code. Spec is the acceptance criterion.

### Step 4: If external data → `.ai/validation/<name>.md` + `.csv`

```bash
# Get ground truth NOW, not later
bq query --format=csv 'SELECT ... FROM ...' > .ai/validation/baseline_AU.csv
# Or from CREST xlsx → export to CSV → manually verify 15 cases
```

Add MD with mapping rules (formula) + source citation ("Treasury confirmed 2026-04-22").

### Step 5: `/plan <feature>` → creates `.ai/PLAN_<feature>.md`

Use the template from §5.1. **Do not skip Test scenarios (§4)** or **Stages (§6)**.

### Step 6: `/deep-verify .ai/PLAN_<feature>.md`

If REJECT → fix the plan → re-verify. Don't proceed.

### Step 7 (optional): `/deep-risk` if high-stakes

Plan with 5D risk scoring, cascade, Cobra Effect.

### Step 8: Implementation stage by stage

Per each stage:
1. Branch `features/<name>` (already exists, or create from main)
2. Code per `Files touched` in the stage
3. `/preflight` before committing
4. Commit msg in style `Stage N: <what>` (imperative, specific)
5. **Run `Executable test` from the PLAN**
6. **Paste LITERAL output into the PLAN section Stage N → Hard evidence**
7. **Mark Status: COMPLETE** in `Execution progress log`
8. Next stage

### Step 9: After the last stage

- `/test verify-existing <module>` — regression
- `/preflight` — final gate
- `git push` + `gh pr create`
- `/review` — review before merge

### Step 10: After merge

- PLAN Status → COMPLETE
- TODO entry closed
- If general lesson → `LESSONS_LEARNED.md` new section
- If reusable pattern → `templates/HOWTO-*.md` or `PATTERN-*.md`

---

## §7 — Red flags: when to STOP and ask

Each point = an incident that actually happened.

| Signal | Consequence if ignored | Ref |
|---|---|---|
| *"I think I know what's needed, I'll start coding"* without `/analyze` | Settlement-style 9 fixes in one day | §2.1 |
| Test scenarios empty in the PLAN | Edge case discovered in production (commit `6ee9561`: 1-line filter excluded 96% of data) | git log |
| Stage closed without literal output | Claim "it works" without evidence → rollback after a week | `CONTRACT §B1` |
| Mutating endpoint on live env with "fake ID" | `refresh_after_disable_operations` disabled NL auto-buy 2026-04-19 | `memory/feedback_live_side_effects.md` |
| `UNKNOWN` in CONTRACT tags without STOP | Assumption becomes truth until the incident | `CONTRACT §B2` |
| Hook blocked commit → you use `--no-verify` | HARD RULE violation | `CONTRACT §Change discipline` |
| PLAN without ALTERNATIVES (min 2) | First idea becomes a decision | `CONTRACT §B3` |
| `PLAN_X.md` + `PLAN_X_new.md` side by side | Someone works from the old version → merge conflict / regression | §5.1 `Supersedes:` |
| `except Exception: pass` "temporarily" | Hook blocks; masks the real error | `standards.md §2.6.2` |
| Large refactor of neighboring code without user request | Scope creep; PR fails review | `CONTRACT §Change discipline` |
| Destructive `git reset --hard` / `push --force` without asking | Loss of work — irreversible | `CONTRACT §Change discipline` |
| commit msg `updates` / `wip` / `fixes` | No way to tell what changed → undifferentiated | §6.2 (old), git log |

---

## §8 — Onboarding: what you do in the first month

### Day 1 — environment + reading

1. `docker compose -f docker-compose.local.yml up --build` — environment works (backend `:8000`, frontend `:3000`)
2. Read: `PROJECT_PLAN.md` · `CONTRACT.md` · this file (WORKFLOW) · `LESSONS_LEARNED.md §1`
3. `ls .ai/` — see what is there. Don't read everything.
4. `git log --oneline -30` — see the recent work rhythm.
5. **Don't commit anything.** Observe.

### Day 2–3 — first micro-commit

Goal: go through the `edit → commit → PR → merge` loop on something trivial.

1. Find a typo / unused import / comment you want to remove
2. Branch: `bugfix/onboarding-<your-name>`
3. Edit
4. `/preflight` — pass the gate
5. Commit in project style (imperative, EN, no AI)
6. PR → merge

**Don't create a PLAN for this.** Goal: learn `/preflight` + commit discipline.

### Week 1 — first PLAN (small bugfix)

Mentor points to a class (a) bug from TODO. You create a full PLAN — even for something small — to practice the structure.

Stages:
1. `/analyze <bug>` — understand where
2. `/plan <bug>` — mini-PLAN (sections: Context, Decisions, **Test scenarios min 3**, **Stages min 1 with evidence**, Rollback)
3. `/deep-verify` the PLAN
4. `/develop` stage 1
5. Run test, paste evidence into PLAN
6. `/preflight`
7. Commit + PR + merge
8. Close PLAN Status = COMPLETE

**Review with mentor:** does every stage have evidence? Were the test scenarios realistic?

### Week 2 — first SPEC + PLAN for a feature

1. Mentor gives a class (b) feature
2. `/analyze` → `/grill` → `SPEC_<feature>.md`
3. SPEC verification with mentor (they liaise with business)
4. `PLAN_<feature>.md` with full test set (min 14 scenarios)
5. `/deep-verify` → if REJECT → plan v2
6. Implementation stage by stage with evidence
7. Merge

### Month 1 — independent cycle

Class (b) feature with optional evidence base. Without mentor assisting in real time (review before merge still required).

Success = 48h after deploy without a hot-fix. Failure = commit msg `Fix: ...` within the first 48h — means test scenarios were incomplete, go back to the PLAN to update.

### After a month — you know it by heart

- Draw the diagram from §1 (10 steps) without looking
- Invoke 4-5 skills from §3 at the right stage without a cheat sheet
- Compose 4 blocks from `commands.md` + CONTRACT for a specific task type (§4.2)
- Write a PLAN with all sections (§5.1) without a template
- Generate 14+ test scenarios for a feature (§5.2)
- Close a stage with evidence and literal output (§5.3)
- Recognize 5+ red flags from §7 during work — not after the fact

---

## §9 — Cheatsheet

### Which skill?

| What you want | Skill |
|---|---|
| Understand requirements | `/analyze` |
| Clear up ambiguities | `/grill` |
| Plan | `/plan` |
| Check correctness of an artifact | `/deep-verify` |
| Count risks | `/deep-risk` |
| Design a new system | `/deep-architect` |
| Implement | `/develop` |
| System-level test | `/test` |
| Pre-commit gate | `/preflight` |
| Review PR | `/review` |

### Which file?

| What is happening | File |
|---|---|
| Feature with 2+ MRs | `.ai/PLAN_<feature>.md` |
| Business requirement | `.ai/SPEC_<feature>.md` |
| External data for comparison | `.ai/validation/<name>.md + .csv` |
| AI rule | `.ai/CONTRACT.md` edit / memory auto |
| Code rule | `.ai/standards.md` edit |
| Repeatable procedure (3×) | `.ai/templates/HOWTO-*.md` |
| Post-mortem | `.ai/LESSONS_LEARNED.md` section |
| Active tasks | `.ai/TODO.md` |

### What micro-skill composition from commands.md?

| Task type | Blocks | + CONTRACT |
|---|---|---|
| Debug | #2 + #18.3 + #18.5 | ✓ |
| Business analysis | #26.1 + #26.3 + #26.6 | ✓ |
| Implementation | #27.1 + #27.5 + #27.7 | ✓ |
| Data / BQ | #3 + #12 + #21 | ✓ |
| Architecture | #4 + #11 + #15 | ✓ |
| High-stake decision | #8 + #9 + #23 | ✓ |
| **Writing a prompt for another agent** | **#24 + #26.3 + #26.6 + #26.5** | **✓** |

### Prompt-first pattern (§10) — when to use

| Situation | Action |
|---|---|
| Task touches ≥ 2 modules | Write prompt first → verify → execute |
| Task requires a PLAN | Write prompt first → `/deep-verify` → execute |
| Requirements feel clear but scope could be wider | Write prompt first → `/grill` → execute |
| Simple 1-file bugfix with known cause | Go directly |

Verification sequence for a written prompt: `/deep-verify` → `/deep-risk` (if high-stakes) → `/analyze` or `/grill` (if ambiguous) → execute.

### How many test scenarios in a PLAN?

- Bugfix (a): ≥ 3 (happy + edge + regression)
- Feature (b) / Pipeline (d) / Restore (e) / Cross-layer (c): ≥ 14 (1 happy + 4 edge + 7 boundaries + 4 failure + 2 regression)
- UI-only (f): ≥ 3 + 1 regression screenshot

### What must be in every Stage?

1. Files touched (list with line numbers)
2. Code change summary (1-2 sentences)
3. Executable test (specific command)
4. Expected output pattern
5. **Hard evidence — literal output after running**
6. Invariants checked (list PASS/FAIL)
7. Test scenarios covered (reference to PLAN section 4)
8. Status with date and runtime timestamp

Without any one of these — the stage is NOT closed.

---

*Living document. After every onboarding of a new person — extend §8 with the places where they got stuck. After every new work pattern — add to §3 (skill) / §4 (commands.md) / §5 (PLAN) / §6 (file order).*

---

## §10 — Prompt-first pattern: write the instruction before executing it

For non-trivial tasks — instead of telling the AI what to do directly, you first ask the AI to **write a complete, detailed prompt** for the task. Then you verify that prompt before execution.

This pattern was used repeatedly in this project for complex features, plan preparation, and multi-stage implementations.

### Why this works

Directly issuing a vague instruction produces vague output. Writing the instruction first forces:
- explicit scope definition (what's in, what's out)
- identification of inputs, outputs, edge cases, and boundaries
- detection of inconsistencies before any code is written
- a verifiable artifact you can gate before execution

The cost of a bad prompt is low. The cost of a bad implementation is high.

### Step 1 — Ask AI to write the prompt

Use the reputation-frame from `commands.md` to set the standard:

```
If someone said you write the best prompts for AI agents — prompts that:
- contain all necessary context and constraints
- define inputs, outputs, and acceptance criteria precisely
- include test scenarios (edge cases, boundaries, failure modes — not just happy path)
- detect inconsistencies before execution
- follow the operational contract
- leave no room for assumption

what exactly would you write as a complete prompt for the following task:

TASK: [describe what you want the agent to do]
CONTEXT: [relevant files, business rules, known constraints]
```

The output is a **draft prompt** — not the implementation.

### Step 2 — Verify the prompt before execution

Before giving the prompt to an agent, run it through verification:

| Check | Tool | When |
|---|---|---|
| Is the prompt logically complete? | `/deep-verify <prompt text>` | Always |
| Are there hidden risks or cascade effects? | `/deep-risk <prompt text>` | High-stakes tasks |
| Are requirements clear and non-ambiguous? | `/analyze <prompt text>` | New features, unclear scope |
| Are there hidden assumptions? | `/grill` | Anything with ASSUMED tags |

If `/deep-verify` returns REJECT → fix the prompt, re-verify. Do not execute.

### Step 3 — Execute with the verified prompt

Only after the prompt passes verification:
1. Copy the verified prompt
2. Start a new session or invoke the relevant skill
3. Paste the prompt as the first message

### Example — preparing a plan prompt

Instead of:
> "Plan the settlement report refactor"

You write:
> "Write a complete prompt for an AI agent that will create a PLAN for refactoring the settlement report. The prompt must include: business context (what CREST is, what the current mismatch is), evidence base requirements (what validation files must exist before planning starts), all mandatory PLAN sections from `.ai/WORKFLOW.md §5`, test scenarios (minimum 14 — edge cases, boundaries, failure modes, regression), stage structure with hard evidence per stage, rollback plan, and operational contract."

Then `/deep-verify` that meta-prompt. Then execute.

### When to use this pattern

| Situation | Use prompt-first? |
|---|---|
| Task touches ≥ 2 modules or ≥ 2 files | YES |
| Task involves data transformation or business logic | YES |
| Task requires a PLAN before implementation | YES |
| Requirements feel clear but scope could be wider | YES |
| Simple 1-file bugfix with known cause | NO — go directly |
| Trivial rename or cosmetic change | NO — go directly |

### Cheatsheet — prompt-writing micro-skill composition

Compose from `commands.md` when writing the meta-prompt:

```
#24 (Documentation & Knowledge Engineer — completeness)
+ #26.3 (Requirements Precision — unambiguous, testable)
+ #26.6 (Scenario & Edge Case Expert — full scenario coverage)
+ #26.5 (Inconsistency Hunter — detect conflicts before execution)
+ CONTRACT
```

This combination produces prompts that: define scope precisely, cover edge cases, detect inconsistencies in requirements, and are honest about assumptions.
