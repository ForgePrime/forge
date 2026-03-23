---
name: plan
description: >
  Decompose a defined scope into executable tasks for an LLM agent. Use when
  you have a document, spec, IMP-001, or verbal description and need to produce
  a task graph ready for immediate execution — no follow-up questions needed.
  Input: any document or description. Output: tasks with exact file paths,
  enforced dependency contracts, structured AC with verify commands, and
  phase exit gates as runnable commands.
  Triggers: "plan this", "break into tasks", "create tasks for X", "/plan".
---

# Plan Skill

Produce tasks that an LLM agent can execute without asking a single question.

**The only test**: take task `_1`. Can you open an editor right now and know
exactly which file to open first — without reading anything else? If not, the
plan is not done.

---

## Step 0 — Read and tag the input

**GATE: Do not write a single task until this step is fully complete.**
If you skip tagging and start planning, you are planning your assumptions,
not the input. The output will look like a plan but won't be one.

### 0a. Inventory what you have

List every input source:

```
Input inventory:
- [name / description, format, apparent freshness]
```

Assign trust to each source:

| Trust | Source type | Rule |
|-------|-------------|------|
| HIGH  | Architecture decisions, existing codebase, signed specs | Use as-is |
| MEDIUM | PRDs, design docs, IMP-001 | Use, but flag aspirational claims |
| LOW | Chat notes, emails, brainstorm dumps | Flag every statement |

No date and can't determine freshness → treat as LOW.
Two sources conflict → higher trust wins. Same trust → more specific wins.
Write every conflict explicitly as `[CONFLICT]`.

### 0b. Tag every statement — do not summarize

Read each input source. For every statement, assign exactly one tag.
Write tagged statements as a list. Do not paraphrase — tag verbatim extracts.

| Tag | Meaning | What to do |
|-----|---------|-----------|
| `[REQ]` | System must do this | Becomes a task or part of a task |
| `[CONSTRAINT]` | Cannot be changed | Constrains every task in that domain |
| `[DECISION]` | Technical choice already made | Goes into task instructions as given |
| `[SCOPE-OUT]` | Explicitly excluded or "v2/later/nice-to-have" | Goes into Out of Scope block only — never into tasks |
| `[IMPLICIT]` | Assumed but never written | Becomes an explicit assumption |
| `[CONFLICT]` | Contradicts another source | Flag, pick one interpretation, document reason |
| `[VAGUE]` | Too ambiguous to act on | Must become an assumption before planning |

**Hunt for `[IMPLICIT]` actively.** Missing implicits are the most common cause
of broken plans. For every `[REQ]`, ask:

- What data model does this require that is not described?
- What happens on error — is error handling anywhere in the input?
- What user roles or permissions are assumed?
- What already exists vs. what must be built?
- What triggers this — user action, API call, scheduled job, event?
- What does this produce — UI state, API response, DB change, event?

### 0c. Completeness gate — answer each question before moving to Step 1

Answer every question. Write "YES: [answer]" or "NO → Assumption [AN]".

```
[ ] Deployment target / environment?          YES/NO
[ ] Primary tech stack?                       YES/NO
[ ] What persists and where?                  YES/NO
[ ] How does data enter the system?           YES/NO
[ ] How is data consumed or exited?           YES/NO
[ ] What already exists and must not change?  YES/NO
[ ] What does "done" look like observably?    YES/NO
[ ] Entry point (what triggers the system)?   YES/NO
[ ] Exit point (what the system produces)?    YES/NO
```

For every NO, write:
```
Assumption [AN]: [what I assumed] — reason: [why this is most likely]
Risk: HIGH (changes architecture if wrong) / MED (changes component design) / LOW (changes detail)
```

**HARD STOP: if you have 3 or more HIGH-risk assumptions, do not proceed.**
Output: "Cannot plan. Need answers to: [list the HIGH-risk questions]." Then stop.

### 0d. Scope block — fill before Step 1

Fill every field. If a field is blank because you don't know → write
"ASSUMED [AN]" referencing your assumption. If more than 3 fields reference
HIGH-risk assumptions → HARD STOP (same rule as 0c).

```
Scope: [one sentence — what business capability this delivers]
In scope: [concrete list of things being built]
Out of scope: [items tagged [SCOPE-OUT] + anything not in In scope]
Already exists (do not build): [list]
Entry point: [what triggers this]
Exit point: [what this produces]
Stack: [runtime, DB, framework, deployment — from [DECISION] and [CONSTRAINT] tags]
```

---

## Step 1 — Split into tasks

**Core rule: vertical slices, not horizontal layers.**

A vertical slice delivers one piece of end-to-end value testable independently.
A horizontal layer (frontend task + backend task for the same feature) delivers
nothing alone and cannot be verified until both are done.

**Exception**: within a single technical domain (pure backend, pure DB), you
may split by layer if each task is under 1 day and produces a verifiable
artifact:
- Migration → table exists and is queryable
- Model → CRUD works via unit test
- Endpoint → HTTP response testable with curl

**How to split** — apply patterns in order, stop when one fits:

| Pattern | When to use | Example |
|---------|------------|---------|
| Workflow steps | Feature has sequential user journey | Submit → Validate → Persist → Notify |
| CRUD | Goal says "manage X" | Create / Read / Update / Delete as separate tasks |
| Business rule variations | Same feature, different rules | Base price / Member discount |
| Simple → complex | Core works first, then edge cases | Basic search → Add filters |
| Defer non-critical | Correctness before optimization | Feature works → Optimize to <100ms |
| Spike | Uncertainty blocks splitting | Time-boxed investigation, then re-plan |

**Never split by**: frontend / backend / tests as separate tasks for the same
feature. Tests are part of the task that produces the tested behavior.

**Task count limits:**
- Simple scope: 1–3 tasks
- Medium scope: 3–7 tasks
- Complex scope: 5–12 tasks
- **>12 tasks: stop. Split the objective into sub-scopes, plan each separately.**

---

## Step 2 — Write each task

Every field is mandatory. "TBD", blank, or "see above" = invalid.

```json
{
  "id": "_1",
  "name": "kebab-case-name",
  "description": "WHAT in one sentence. If boundary is ambiguous: 'This IS X. This is NOT Y.'",
  "instruction": "...",
  "depends_on": [],
  "uses_from_dependencies": {},
  "produces": {},
  "acceptance_criteria": [],
  "test_plan": {}
}
```

---

### `instruction` — must pass the cold start test

Read the instruction as if you have never seen this codebase.
**Which file do you open first? Can you name it without reading anything else?**

Every instruction must contain all five of these:

1. **Exact files to create or modify** — full paths. "The model file" = invalid.
2. **Exact files NOT to touch** — name what a sibling task owns.
3. **Pattern to follow** — name the existing file to use as a model, or write
   "no existing pattern — create from scratch."
4. **Concrete steps** — not "implement X" but "add function Y to file Z that does W."
5. **Reference to dependency output** — if `depends_on` is non-empty, the
   instruction MUST say "using [what dependency produces, by name]."

| ❌ Vague | ✅ Concrete |
|---------|-----------|
| "Implement invoice creation" | "Add `POST /api/invoices` to `src/api/routes/invoices.ts` following the pattern in `src/api/routes/orders.ts`. Create `src/models/Invoice.ts` with fields: id, customer_id, amount, status, created_at." |
| "Add validation" | "In `src/models/Invoice.ts`, add Zod schema `InvoiceCreateSchema` validating: amount > 0, customer_id is UUID, status is enum('draft','sent'). Return `400 {error: string, field: string}` on failure." |
| "Do not touch auth" | "Do NOT modify `src/auth/`, `src/middleware/auth.ts`, or any file in `src/api/routes/` except `invoices.ts`." |
| "Set up the job" | "Create `src/jobs/invoice-reminder.ts` using the BullMQ pattern from `src/jobs/payment-retry.ts`. Schedule: daily at 08:00 UTC. Query: invoices where status='sent' AND created_at < NOW()-7days." |

---

### `uses_from_dependencies` — mandatory when `depends_on` is non-empty

This field is the enforcement mechanism that separates real dependencies from
decorative ones.

**Rule**: for every task ID in `depends_on`, `uses_from_dependencies` must name
exactly what this task takes from that dependency's `produces` field — by the
same key name. The instruction must also reference it by name.

```json
"depends_on": ["_1"],
"uses_from_dependencies": {
  "_1": "Invoice model from src/models/Invoice.ts — fields: id, customer_id, amount, status"
}
```

**Test**: can you point to the line in the instruction that uses the named item?
If no such line exists → the dependency is decorative. Fix the instruction or
remove the dependency.

If `depends_on` is empty → `"uses_from_dependencies": {}` is correct.

---

### `produces` — the downstream contract

Use when other tasks will depend on this task's output. Be specific enough
that a downstream task can fill `uses_from_dependencies` without guessing.

```json
"produces": {
  "endpoint": "POST /api/invoices → 201 {id: uuid, status: string, created_at: ISO8601}",
  "model": "Invoice — src/models/Invoice.ts — fields: id, customer_id, amount, status, created_at",
  "errors": "400 {error, field}, 401 {error}, 409 {error}"
}
```

If no task depends on this → `"produces": {}` is valid.

---

### `acceptance_criteria` — structured with verify command

Every AC must have all four parts. Missing any part = invalid.

```
Format:
  Given: [starting state]
  When:  [action taken]
  Then:  [observable result — HTTP status + body shape, OR DB row, OR file content, OR terminal output]
  Verify: [exact command to run — pasteable into terminal right now]
```

"Works correctly", "handles edge cases", "is properly validated" are not
observable results. Rewrite them as concrete outputs.

```json
"acceptance_criteria": [
  {
    "id": "AC1",
    "given": "invoices table is empty",
    "when": "POST /api/invoices with {customer_id: '550e8400-e29b-41d4-a716-446655440000', amount: 100}",
    "then": "response 201 {id: uuid, status: 'draft', created_at: ISO8601} AND row exists in invoices table",
    "verify": "curl -s -X POST $BASE_URL/api/invoices -H 'Content-Type: application/json' -d '{\"customer_id\":\"550e8400-e29b-41d4-a716-446655440000\",\"amount\":100}' | jq '{status: .status, has_id: (.id != null)}'"
  },
  {
    "id": "AC2",
    "given": "any state",
    "when": "POST /api/invoices with {amount: -1}",
    "then": "response 400 {error: 'must be positive', field: 'amount'} AND no row inserted in invoices table",
    "verify": "curl -s -o /dev/null -w '%{http_code}' -X POST $BASE_URL/api/invoices -d '{\"amount\":-1}'"
  }
]
```

**Minimum per task**: 1 happy path AC + 1 error/edge case AC. No exceptions.

"Boring" tasks need ACs too:
- Config: "Given missing `DB_URL`, app exits with `Error: DB_URL is required`, not a stack trace."
  Verify: `DB_URL= node src/index.js 2>&1 | grep 'DB_URL is required'; echo $?` → exits 0
- Migration: "After running migration, `invoices` table exists. Running twice does not fail."
  Verify: `psql $DB_URL -c "\d invoices"` → lists columns

---

### `test_plan` — name cases, not types

```json
"test_plan": {
  "unit": true,
  "integration": false,
  "e2e": false,
  "notes": "unit: InvoiceCreateSchema — (1) valid input passes, (2) amount=0 fails with 'must be positive', (3) amount negative fails, (4) missing customer_id fails, (5) customer_id not UUID format fails"
}
```

Rules:
- `unit: true` → `notes` must list specific test case names. "Add unit tests" = invalid.
- `integration: true` → `notes` must name the integration point (e.g. "DB write + read roundtrip via `invoices` table").
- `e2e: true` → `notes` must describe the user flow end-to-end.
- All false → write why (e.g. "pure config — tested via _2 integration tests").

---

## Step 3 — Build the dependency graph

### 3a. Draw the graph before writing phases

```
_1 (DB migration)     → no dependencies
_2 (Invoice model)    → depends on: _1  (uses: table schema from migration)
_3 (Create endpoint)  → depends on: _2  (uses: Invoice model from src/models/Invoice.ts)
_4 (List endpoint)    → depends on: _2  (uses: Invoice model from src/models/Invoice.ts)
_5 (Reminder job)     → depends on: _2  (uses: Invoice model from src/models/Invoice.ts)

Layer 0 (no deps): _1
Layer 1 (deps on L0): _2
Layer 2 (deps on L1): _3, _4, _5  ← parallel execution possible
```

### 3b. Hidden dependency check — for every task, answer each question

Every "yes" without a `depends_on` = missing dependency. Add it.

- Writes to a table → depends on the task that created that table?
- Reads data created by another task → depends on that task?
- Calls an internal API → depends on the task that defines that endpoint?
- Uses a model/type defined by another task → depends on that task?
- Needs config or env vars set up by another task → depends on that task?
- References a file created by another task in this plan → depends on that task?

### 3c. Dependency contract check — for every `depends_on` arrow

For every dependency arrow, verify all three:

1. Is `uses_from_dependencies` filled for this dependency?
2. Does `uses_from_dependencies` reference a key that exists in the dependency's `produces`?
3. Does the instruction name that item explicitly?

Write the check inline:
```
_3 depends_on _2
  _2.produces has: { model: "Invoice — src/models/Invoice.ts" }
  _3.uses_from_dependencies._2: "Invoice model from src/models/Invoice.ts"  ← key matches ✓
  _3.instruction references: "using Invoice model from src/models/Invoice.ts" ✓
```

If any check fails → fix before proceeding. Do not write "✓" without verifying.

### 3d. Max dependency rule

Max 3 `depends_on` per task. More = task is doing too much. Split it.

---

## Step 4 — Organize into phases with exit gates

### 4a. Phase rules

- Each layer from Step 3a = one phase (or merged if trivial)
- Phase name = what it delivers, not the technology
  - ✅ "Working data model", "User-facing API", "Background processing"
  - ❌ "Backend", "Phase 2", "Database work"
- 2–6 tasks per phase. 7+ → split the phase. 1 task → merge with adjacent unless it is a hard gate.

### 4b. Exit gate — mandatory for every phase

An exit gate is a **command you can paste into a terminal right now** that
produces a binary pass/fail result.

Structure:
```
Command: [exact shell command with no placeholders except documented env vars]
Expected output: [exact string or pattern that means PASS]
Fail condition: [what FAIL looks like — do not write "anything else"]
```

Example:
```
Phase 1 exit gate:
  Command: psql $DB_URL -c "\d invoices" 2>&1
  Expected output: table "public.invoices" with columns id, customer_id, amount, status, created_at
  Fail condition: "relation does not exist" or any psql error
```

**Invalid exit gates:**
- "Run tests and check they pass" — not a command
- "Phase is done when everything works" — not binary
- "Check that the endpoint returns 200" — missing the command

If you cannot write a pasteable command → the phase deliverable is not concrete
enough. Redefine what the phase produces.

---

## Step 5 — Quality checks (run as actions, not as questions)

These are not questions to answer "yes" to.
Each check is an action you perform and document. Write the output of each
action inline. If you cannot write the output, the check failed.

**Check 1 — Cold start, first task:**
Action: copy `_1`'s instruction into a blank context. Write: "First file to open: [path]."
If you cannot name an exact path → instruction is invalid. Fix it before continuing.

**Check 2 — Cold start, last task:**
Action: same for the last task. Write: "First file to open: [path]."
Planning fatigue makes last tasks the vaguest. Fix it.

**Check 3 — Dependency contracts:**
Action: for every `depends_on` arrow, write:
```
_N depends_on _M
  _M.produces key: [key name]
  _N.uses_from_dependencies._M value: [value] — matches key? [YES/NO]
  _N.instruction references this item? [YES: line X / NO]
```
Any NO = contract broken. Fix before continuing.

**Check 4 — AC verify commands:**
Action: for every AC, write the verify command and its expected output:
```
[task id] AC[n] verify: [paste the exact command from the AC]
Expected: [what pass looks like]
```
If you cannot paste the command from the AC field → AC is missing its verify. Fix it.

**Check 5 — Test plan specificity:**
Action: for every `unit: true`, count the named test cases in `notes` and write:
"[task id] unit tests: [N] cases named — [list them]"
Count = 0 → fail. Fix before continuing.
For every `integration: true`, write: "[task id] integration point: [named point]"
Missing → fail.

**Check 6 — Exit gate executability:**
Action: for every phase exit gate, write:
"Phase [N] exit gate: [paste command]. Pass condition: [exact string]. Binary? [YES/NO]"
Binary = NO → rewrite the gate.

**Check 7 — Scope leak:**
Action: list every item tagged `[SCOPE-OUT]` in Step 0.
For each, write: "Is there a task that implements this? [task id / NONE]"
Any answer other than NONE → remove that task.

**All 7 checks must produce written output. Unwritten = not done.**

---

## Step 6 — Deliver

```
## Plan: [scope name]

Scope: [one sentence]
In scope: [list]
Out of scope: [list]
Entry point → Exit point: [trigger] → [output]
Stack: [runtime, DB, deployment]

Assumptions:
- [A1] [assumption] — risk: HIGH/MED/LOW
- [A2] ...

Tasks: N | Layers: N | Phases: N

---

### _N — [task name]
Description: [one sentence. Ambiguous boundary: "This IS X. This is NOT Y."]

Instruction:
  [Exact files to create or modify — full paths]
  [Exact files NOT to touch]
  [Pattern to follow: existing file name, or "no existing pattern — create from scratch"]
  [Step-by-step: add function Y to file Z that does W]
  [If depends_on non-empty: "using [dependency output name] from [dependency produces key]"]

Depends on: [list or "none"]
Uses from dependencies:
  [_M]: [exactly what, from which key in _M.produces]

Produces:
  [key]: [value — specific enough for downstream uses_from_dependencies]

AC:
  AC1:
    Given:  [state]
    When:   [action]
    Then:   [observable result]
    Verify: [exact pasteable command]
  AC2: [error/edge case — same format]

Test plan: unit=[true/false], integration=[true/false], e2e=[true/false]
  Notes: [named cases or integration points — not "add unit tests"]

---

Dependency graph:
  Layer 0: _N
  Layer 1: _N, _N
  Layer 2: _N
  → parallel execution possible within each layer

---

### Phase N: [What this delivers]
Depends on: Phase N-1 exit gate / nothing
Tasks: _N, _N
Exit gate:
  Command: [exact shell command]
  Expected output: [exact string or pattern = PASS]
  Fail condition: [what FAIL looks like]
```

Wait for approval. Offer to adjust granularity, merge, split, or reorder.

---

## What NOT to produce

- Instructions without exact file paths
- Instructions that say "implement X" where X is the whole task
- `depends_on` without `uses_from_dependencies`
- `uses_from_dependencies` that references a key not in the dependency's `produces`
- AC without a `verify` command
- AC with "works correctly", "handles edge cases", "is properly validated"
- Test plans that say "add unit tests" without naming cases
- Exit gates without an exact pasteable command
- Exit gates without a binary pass/fail condition
- Tasks that implement `[SCOPE-OUT]` items from Step 0
- Plans with >12 tasks (split the objective first)
- Quality checks answered with "yes" instead of written output
- Assumptions left implicit instead of written as [AN]
