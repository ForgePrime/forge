---
name: plan
description: >
  Decompose a defined business scope into executable tasks with dependency-aware
  structure, verifiable AC, and test plans. Use when planning a business area
  or objective with requirements and architectural decisions already known.
  Input: objective description, existing codebase context, known constraints.
  Output: approved task graph in Forge pipeline. Triggers on: "plan this",
  "break this into tasks", "create tasks for X", "/plan", "/plan I-NNN",
  "/plan O-NNN".
---

# Plan Skill

Decompose a defined scope into tasks that execute without follow-up questions.

**The only test**: paste the first task's `instruction` into a blank context.
Does the agent know which file to open first — without asking anything?
If not — the plan is not done.

---

## Step 0 — Read and tag the input

**Do this before any decomposition. Do not skip.**

Read every piece of input: objective description, requirements, codebase context,
constraints. Tag every statement:

| Tag | Meaning | Goes to |
|-----|---------|---------|
| `[REQ]` | Something the system must do | task instruction + AC |
| `[CONSTRAINT]` | Hard limit — tech, compliance, must-guideline | task instruction |
| `[DECISION]` | Architecture/tech choice already made | task instruction (follow, don't revisit) |
| `[SCOPE-OUT]` | Explicitly excluded | Out of scope in Step 1 |
| `[IMPLICIT]` | Assumed but not stated | write explicitly before planning |
| `[CONFLICT]` | Two statements contradict each other | **hard stop** — ask before planning |
| `[VAGUE]` | Too ambiguous to act on as written | **hard stop** — clarify or make explicit assumption |

**Output of Step 0** (write this before proceeding to Step 1):

```
Tagged input:
[REQ] user can create an order with products and delivery address
[REQ] confirmation email sent after order saved
[CONSTRAINT] follow existing Express + TypeScript patterns in src/api/
[DECISION] use BullMQ for async jobs (established in codebase)
[IMPLICIT] order status = 'pending' on creation — if wrong: model changes
[IMPLICIT] email sent async via queue — if wrong: endpoint latency doubles
[VAGUE] "products" → resolved: [{product_id: UUID, quantity: int}], no price in scope
```

Rules:
- Every `[VAGUE]` must become an explicit assumption before continuing. Write:
  "I assume X because Y. If wrong, Z changes."
- Every `[CONFLICT]` is a hard stop. Do not plan until resolved.
- Every `[IMPLICIT]` must be written down with consequence if wrong.

---

## Step 1 — Check existing state and load context

```bash
ls forge_output/ 2>/dev/null
python -m core.lessons read-all --severity critical --limit 15
python -m core.guidelines read {project} --weight must
python -m core.guidelines scopes {project}
python -m core.knowledge read {project}
```

If planning from idea (`/plan I-NNN`):
```bash
python -m core.ideas show {project} {idea_id}
python -m core.research context {project} --entity {idea_id}
```

If planning from objective (`/plan O-NNN`):
```bash
python -m core.objectives show {project} {objective_id}
python -m core.research context {project} --entity {objective_id}
python -m core.knowledge read {project} --category requirement
```

**Must-guidelines are non-negotiable**: if a must-guideline says "all endpoints
need rate limiting" → include it in the relevant task. Record a decision if a
must-guideline conflicts with the goal — never silently ignore.

**Research readiness gate**: check for unfinished explorations:
```bash
python -m core.decisions read {project} --type exploration
```
If any linked exploration has `ready_for_tracker: false` and status OPEN → **BLOCK**:
```
BLOCKED: Cannot plan — {N} exploration(s) not ready.
  - D-NNN: {issue}
Resolve: /discover {entity_id} OR mark ready manually.
```

Also warn (do not block) on HIGH-severity open risks without mitigation.

---

## Step 2 — Define scope boundaries

Using tagged input from Step 0:

```
Scope: [one sentence — what business capability this delivers]
In scope:  [REQ items being implemented, concrete list]
Out of scope: [SCOPE-OUT items + related things explicitly excluded]
Entry point: [what triggers this — user action, API call, event, job]
Exit point: [what this produces — HTTP response, DB state, event, email]
Assumptions:
  - [each IMPLICIT resolved] → if wrong: [what changes]
```

---

## Step 3 — Assess complexity

| Track | Criteria | Tasks |
|-------|----------|-------|
| **Quick** | Single concern, ≤3 files, no architectural decisions | 1–3 |
| **Standard** | Multiple concerns, known patterns | 3–7 |
| **Complex** | Cross-cutting, architectural decisions needed | 5–12 |

State track and reasoning. Confirm with user before decomposing.
>12 tasks = scope too broad — split the objective first.

---

## Step 4 — Readiness check (mandatory before decomposing)

Produce this table from tagged input:

```
| # | I ASSUME that...          | BASIS                        | Severity |
|---|--------------------------|------------------------------|----------|
| 1 | DB has users table       | read migrations/001_users.sql | LOW      |
| 2 | Auth middleware on /api/* | read app.ts:15               | HIGH     |
| 3 | Frontend expects {token} | GUESSING from other responses | HIGH     |
```

**Severity** (apply here, not from memory):
- **HIGH**: wrong assumption changes task structure, data model, or architecture
- **MED**: wrong assumption changes one component's implementation
- **LOW**: wrong assumption changes an implementation detail

**When in doubt: HIGH.** MED/LOW require a positive justification.
"Probably fine" = HIGH.

**Hard stop thresholds:**
- 0–2 HIGH: proceed
- 3–4 HIGH: proceed, add `⚠️ High assumption risk` to draft header
- **5+ HIGH: STOP.** Do not decompose. List HIGH assumptions as questions.

Pass to `draft-plan` with `--assumptions`:
```bash
python -m core.pipeline draft-plan {project} --data '[...]' \
  --assumptions '[{"assumption":"...","basis":"...","severity":"HIGH"}]'
```
5+ HIGH → `draft-plan` exits with error. Draft not saved.

---

## Step 5 — Decompose into tasks

**Core rule: vertical slices, not horizontal layers.**

A vertical slice delivers one piece of end-to-end value testable independently.
Exception: within a single domain, layer splitting is allowed if each layer is
<1 day and produces a verifiable output (migration → `psql -c "\d table"` works,
model → unit test passes, endpoint → curl returns expected HTTP code).

**Never split by**: frontend/backend/tests as separate tasks for one feature.

**Splitting patterns** — apply in order, stop when one fits:

| Pattern | Signal | Example |
|---------|--------|---------|
| Workflow steps | Sequential user journey | Create order → Add payment → Send email |
| CRUD | Goal says "manage X" | Create / Read / Update / Delete |
| Business rule variations | Same feature, different rules | Standard shipping / Express |
| Simple → complex | Core first, variations later | Basic create → Add validation |
| Defer performance | Correctness before speed | Works → Optimize to <200ms |
| Spike | Uncertainty blocks splitting | Investigation task, then re-split |

---

## Step 6 — Write each task

Every field mandatory. Vague values not accepted.

```json
{
  "id": "_1",
  "name": "kebab-case-descriptive-name",
  "description": "WHAT in one sentence. Boundary if ambiguous: 'This IS X. NOT Y.'",
  "instruction": "HOW — numbered steps with exact file paths",
  "depends_on": ["_2"],
  "uses_from_dependencies": {
    "_2": "OrderModel from src/models/Order.ts — call OrderModel.create(data) returning Promise<Order>"
  },
  "produces": {
    "endpoint": "POST /api/orders → 201 {id: uuid, status: 'pending', created_at: ISO8601}",
    "errors": "400 {error: string, field: string}, 401 {error: 'unauthorized'}"
  },
  "acceptance_criteria": [],
  "test_plan": {
    "unit": true,
    "integration": false,
    "e2e": false,
    "notes": "specific cases listed here — not 'unit tests'"
  },
  "scopes": ["backend", "database"],
  "knowledge_ids": ["K-001"],
  "source_requirements": [
    {"knowledge_id": "K-003", "text": "...", "source_ref": "spec.md:section-3"}
  ],
  "alignment": {
    "goal": "single sentence goal",
    "boundaries": {"must": [], "must_not": [], "not_in_scope": []},
    "success": "how user verifies done"
  },
  "conflicts_with": [],
  "exclusions": []
}
```

---

### instruction — cold start test

Paste instruction into blank context. Does the agent know the first file to
open? If not — rewrite.

Every instruction must contain:
- Numbered steps
- Exact files to create (full paths)
- Exact files to modify (full paths)
- Exact files NOT to touch (`Do NOT modify src/api/routes/auth.ts — owned by _3`)
- Pattern file to follow (`follow pattern in src/api/routes/invoices.ts`)

| ❌ Vague | ✅ Concrete |
|---------|-----------|
| "Implement order creation" | "1. Create `src/api/routes/orders.ts` following `src/api/routes/invoices.ts`. 2. Add `POST /api/orders` handler: validate body with `OrderCreateSchema`, call `OrderModel.create()` from `src/models/Order.ts` (_1), return 201. 3. Register in `src/api/routes/index.ts` after invoices. Do NOT modify `src/api/routes/auth.ts`." |
| "Add email job" | "1. Create `src/jobs/order-confirmation.ts` using BullMQ pattern from `src/jobs/invoice-reminder.ts`. 2. Job receives `{order_id, customer_email}`. 3. Load `src/templates/order-confirmation.hbs`. 4. Send via `EmailService.send()` from `src/services/email.ts`. 5. In `src/api/routes/orders.ts` (_2): after `OrderModel.create()`, enqueue: `confirmationQueue.add({order_id, customer_email})`." |

---

### uses_from_dependencies — mandatory when depends_on is non-empty

For each dependency, state exactly what this task takes from it:

```json
"uses_from_dependencies": {
  "_1": "OrderModel from src/models/Order.ts — OrderModel.create({products, address, email}) → Promise<Order>",
  "_3": "confirmationQueue from src/jobs/order-confirmation.ts — call .add({order_id, customer_email})"
}
```

**Rule**: `depends_on` non-empty + `uses_from_dependencies` empty = validation
error. The referenced artifact must also appear by name in `instruction`.
If it doesn't — the dependency is decorative. Fill it or remove the arrow.

---

### acceptance_criteria — Given/When/Then/verify format

Every AC must follow:
```
Given [starting state],
When [exact action with exact input],
Then [observable result],
verify: [exact command that confirms this — pasteable into terminal]
```

| ❌ Unverifiable | ✅ Given/When/Then/verify |
|----------------|--------------------------|
| "Order creation works" | Given DB empty, When `curl -X POST /api/orders -H "Authorization: Bearer $T" -d '{"products":[{"product_id":"<uuid>","quantity":2}],"address":"ul. X 1","email":"a@b.com"}'`, Then 201 `{"id":"<uuid>","status":"pending"}`, verify: `curl ... \| jq .status` outputs `"pending"` |
| "Validation rejects bad input" | Given valid token, When `curl -X POST /api/orders -d '{"products":[]}'`, Then 400 `{"error":"products cannot be empty","field":"products"}`, verify: `curl -s -o /dev/null -w "%{http_code}" -X POST ...` outputs `400` |
| "Email is sent" | Given order id=X created, When confirmation job runs, Then `SELECT count(*) FROM email_log WHERE order_id='X'` = 1, verify: `psql $DATABASE_URL -c "SELECT count(*) FROM email_log WHERE order_id='X'"` outputs `1` |

Minimum per task: 1 happy path + 1 error/edge case. No exceptions.
Config task minimum: Given `DATABASE_URL` missing, When app starts, Then exits
code 1 with stderr `"DATABASE_URL required"`, verify: `DATABASE_URL="" node dist/index.js; echo $?` outputs `1`.

---

### test_plan — notes must list specific cases

```json
"test_plan": {
  "unit": true,
  "integration": true,
  "e2e": false,
  "notes": "unit: OrderCreateSchema — valid body, empty products, quantity=0, invalid UUID format, missing email | integration: POST happy path → 201 + DB row + job enqueued, POST invalid body → 400, POST no token → 401 (testcontainers postgres + supertest)"
}
```

- `unit: true` → notes must list specific cases by name
- `integration: true` → notes must name the integration point
- `e2e: true` → notes must describe the full user flow
- All false → write why: `"pure config — covered by _3 integration test"`

---

## Step 7 — Dependency graph + exit gates

**Write graph before writing phases:**

```
_1 (order-model)       → no dependencies
_2 (create-endpoint)   → depends on: _1
_3 (confirmation-job)  → depends on: _1
_4 (wire-job)          → depends on: _2, _3

Layers:
Layer 1: _1
Layer 2: _2, _3  ← parallel
Layer 3: _4
```

**Hidden dependency check** — for every task:
- Writes data → depends on task that defines the schema?
- Reads data → depends on task that creates that data?
- Calls external system → depends on config/credential task?
- Needs auth context → depends on auth middleware task?

Any "yes" without `depends_on` = missing edge. Add it.
Max 3 dependencies per task. More = task too large, split it.

**Exit gate per layer** — one terminal command, binary pass/fail:

```
Layer 1 exit gate:
  command: npx ts-node -e "import('./src/models/Order').then(m=>m.OrderModel.create({products:[{product_id:'00000000-0000-0000-0000-000000000001',quantity:1}],address:'T',email:'a@b.com'}).then(r=>console.log(r.status)).catch(e=>{console.error(e.message);process.exit(1)}))"
  expected: outputs "pending", exit code 0

Layer 2 exit gate:
  command: curl -s -X POST http://localhost:3000/api/orders -H "Authorization: Bearer $TEST_TOKEN" -d '{"products":[{"product_id":"00000000-0000-0000-0000-000000000001","quantity":1}],"address":"ul. T 1","email":"t@t.com"}' | jq .status
  expected: outputs "pending"
```

Do not proceed to next layer until current exit gate passes.

---

## Step 8 — Coverage check

Every requirement from source must be:
- **COVERED** — a task implements it, instruction mentions it
- **DEFERRED** — postponed, with reason
- **OUT_OF_SCOPE** — excluded, with reason

No MISSING. If not covered and can't justify deferring → add to a task.

Pass to `draft-plan` with `--coverage`:
```bash
python -m core.pipeline draft-plan {project} --data '[...]' \
  --coverage '[
    {"requirement":"order creation","status":"COVERED","covered_by":"_2"},
    {"requirement":"order history","status":"DEFERRED","reason":"separate objective"}
  ]'
```
Any MISSING status → `draft-plan` exits with error. DEFERRED/OUT_OF_SCOPE
require `reason` field — no reason = error.

---

## Step 9 — Quality actions (not questions)

Perform these actions. Each has a binary result: pass or fail.

**Action 1 — instruction file count:**
Take `_1.instruction`. Count file paths (strings containing `/` or `.ts/.py/.sql`).
If count < 2 → fail. Rewrite instruction before continuing.

**Action 2 — AC verify command:**
Take any AC from any task. Write the `verify:` command.
If you cannot write a pasteable terminal command → fail. Rewrite AC.

**Action 3 — dependency contract:**
Take any task with `depends_on`. Find the artifact named in `uses_from_dependencies`.
Search for that artifact name in `instruction` text.
If not found → fail. Add reference or remove the dependency.

**Action 4 — test plan specificity:**
Take `test_plan.notes` from any task with `unit: true`.
Count specific named test cases (e.g. "valid body", "empty products", "quantity=0").
If count < 2 → fail. Add specific cases.

**Action 5 — exit gate executability:**
Take Layer 1 exit gate command. Are all variables defined within the command
itself or standard env vars? If it references an undefined variable → fail. Fix it.

All 5 pass → proceed. First fail → fix → restart from Action 1.

---

## Step 10 — Store and deliver

Store Impact Map as knowledge object:
```bash
python -m core.knowledge add {project} --data '[{
  "title": "Impact Map: {goal}",
  "category": "architecture",
  "scopes": ["{scopes}"],
  "content": "{dependency graph + exit gates + coverage table}"
}]'
```

Draft plan:
```bash
# From idea:
python -m core.pipeline draft-plan {project} --data '[...]' --idea {idea_id} \
  --assumptions '[...]' --coverage '[...]'

# From objective:
python -m core.pipeline draft-plan {project} --data '[...]' --objective {obj_id} \
  --assumptions '[...]' --coverage '[...]'
```

Present to user:
```
## Draft Plan: {goal}
Track: Quick / Standard / Complex
Tasks: N across N layers
Assumption risk: [none / ⚠️ high]

[task list: _N name — description]

Layer exit gates: [paste from Step 7]
Coverage: [N covered, N deferred, N out of scope]
```

Wait for approval. When approved:
```bash
python -m core.pipeline approve-plan {project}
python -m core.pipeline status {project}
```

---

## What NOT to produce

- `instruction` without exact file paths (minimum 2)
- AC without `verify:` terminal command
- `depends_on` non-empty with empty `uses_from_dependencies`
- `test_plan.notes` = "add unit tests" or "cover edge cases"
- Exit gates that reference undefined variables
- Plans with >12 tasks without splitting the objective first
- Draft when 5+ HIGH assumptions exist
- Draft with MISSING requirements in coverage
