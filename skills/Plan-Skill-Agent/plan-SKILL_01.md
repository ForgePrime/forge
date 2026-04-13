---
name: plan
description: >
  Decompose a defined business scope into executable tasks. Use when you have
  a clear objective with known requirements and architectural decisions already
  made, and need to split it into concrete work items with instructions, AC,
  and test plans. Triggers on: "plan this", "break this into tasks", "create
  tasks for X", "/plan". Input: objective description, existing codebase
  context, known constraints. Output: task graph ready for execution.
---

# Plan Skill

Decompose a defined scope into tasks that execute without follow-up questions.

**The only test**: paste the first task's `instruction` into a fresh context
with no other information. Does the agent know which file to open first?
If not — the plan is not done.

---

## Step 0 — Read and tag the input

**Do this before any decomposition. Do not skip.**

Read every piece of input (objective description, requirements, context,
constraints). Tag every statement:

| Tag | Meaning | Goes to |
|-----|---------|---------|
| `[REQ]` | Something the system must do | task instruction + AC |
| `[CONSTRAINT]` | Hard limit — tech, time, compliance | task instruction, dependency ordering |
| `[DECISION]` | Architecture/tech choice already made | task instruction (follow it, don't revisit) |
| `[SCOPE-OUT]` | Explicitly excluded | Out of scope in Step 1 |
| `[IMPLICIT]` | Assumed but not stated | write it down explicitly before planning |
| `[CONFLICT]` | Two statements contradict each other | stop — ask which is correct before planning |
| `[VAGUE]` | Too ambiguous to act on as written | stop — ask for clarification or make explicit assumption |

**Output of Step 0** (write this before proceeding):

```
Tagged input:
[REQ] user can create an order with products and delivery address
[REQ] confirmation email sent after order saved
[IMPLICIT] order has a status field (assumed: 'pending' on creation)
[IMPLICIT] email sent async (assumed: via queue, not blocking HTTP response)
[CONSTRAINT] follow existing Express + TypeScript patterns in src/api/
[DECISION] use BullMQ for async jobs (established in codebase)
[VAGUE] "products" — assumed: list of {product_id, quantity}, no price validation in this scope
```

**Rules:**
- Every `[VAGUE]` must become an explicit assumption before you continue.
  Write the assumption: "I assume X because Y. If wrong, Z changes."
- Every `[CONFLICT]` is a hard stop. Do not plan until resolved.
- Every `[IMPLICIT]` must be written down. Silent assumptions become bugs.

---

## Step 1 — Define scope boundaries

Using the tagged input from Step 0, produce this block:

```
Scope: [one sentence — what business capability this delivers]
In scope:
  - [REQ items being implemented]
Out of scope:
  - [SCOPE-OUT items + anything mentioned but not in this objective]
Entry point: [what triggers this — user action, API call, event, scheduled job]
Exit point: [what this produces — HTTP response, DB state, event emitted, email sent]
Assumptions made:
  - [IMPLICIT items resolved] → if wrong: [what changes]
```

If any field is unclear after tagging — ask one specific question before proceeding.

---

## Step 2 — Split into tasks

**Core rule: vertical slices, not horizontal layers.**

A vertical slice delivers one piece of end-to-end value testable independently.
A horizontal layer (backend task + frontend task for one feature) delivers
nothing by itself and cannot be verified.

**Exception**: within a single technical domain (pure backend, pure DB), layer
splitting is allowed if each layer is <1 day and produces a verifiable output:
- migration → schema exists, queryable: `psql -c "\d orders"` exits 0
- model → CRUD works: unit test passes
- endpoint → HTTP response: `curl -s -o /dev/null -w "%{http_code}"` returns expected code

**Splitting patterns** — apply in order, stop when one fits:

| Pattern | Signal | Example |
|---------|--------|---------|
| Workflow steps | Sequential user journey | Create order → Add payment → Send confirmation |
| CRUD | Goal says "manage X" | Create / Read / Update / Delete |
| Business rule variations | Same feature, different rules | Standard shipping / Express shipping |
| Simple → complex | Core first, then edge cases | Basic create → Add validation → Add idempotency |
| Defer performance | Correctness before speed | Works → Optimize to <200ms |
| Spike | Uncertainty blocks splitting | Investigation task first, then re-split |

**Task count:** 1–3 simple / 3–7 medium / 5–12 complex. >12 = split the objective first.

---

## Step 3 — Write each task

Every field below is mandatory. Vague values are not accepted.

```json
{
  "id": "_1",
  "name": "kebab-case-descriptive-name",
  "description": "WHAT in one sentence. Boundary if ambiguous: 'This IS X. NOT Y.'",
  "instruction": "HOW — numbered steps, exact file paths, pattern to follow",
  "depends_on": ["_2"],
  "uses_from_dependencies": {
    "_2": "Invoice model from src/models/Invoice.ts — fields: id, customer_id, amount, status"
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
    "notes": "exact cases listed here"
  }
}
```

---

### Field: instruction

**Must pass this test**: paste the instruction into a blank context.
Does the agent know the first file to open? If not — rewrite it.

Every instruction must contain:
- Numbered steps
- Exact file paths to create (`src/api/routes/orders.ts`)
- Exact file paths to modify (`src/api/routes/index.ts`)
- Exact file paths NOT to touch (`src/api/routes/auth.ts — owned by _3`)
- Pattern file to follow (`follow pattern in src/api/routes/invoices.ts`)

| ❌ Vague | ✅ Concrete |
|---------|-----------|
| "Implement order creation" | "1. Create `src/api/routes/orders.ts` following `src/api/routes/invoices.ts`. 2. Add `POST /api/orders` handler: validate body with `OrderCreateSchema` (step 3), write to `orders` table via `OrderModel.create()` (from _1), return 201 with created row. 3. Register route in `src/api/routes/index.ts` at line after invoices route. Do NOT modify `src/api/routes/auth.ts`." |
| "Add email notification" | "1. Create `src/jobs/order-confirmation.ts` using BullMQ pattern from `src/jobs/invoice-reminder.ts`. 2. Job receives `{order_id, customer_email}`. 3. Load template `src/templates/order-confirmation.hbs`. 4. Send via `EmailService.send()` from `src/services/email.ts`. 5. In `src/api/routes/orders.ts` (from _2): after `OrderModel.create()`, enqueue job: `orderConfirmationQueue.add({order_id: order.id, customer_email: order.email})`." |

---

### Field: uses_from_dependencies

**Mandatory when `depends_on` is non-empty.**

For each dependency, state exactly what this task takes from it:

```json
"uses_from_dependencies": {
  "_1": "OrderModel from src/models/Order.ts — use OrderModel.create(data) returning Promise<Order>",
  "_2": "POST /api/orders endpoint — enqueue job after OrderModel.create() succeeds"
}
```

**Rule**: if a task has `depends_on: ["_1"]` but `uses_from_dependencies` is
empty or missing — the dependency is decorative. Either fill it or remove the
dependency. An empty `uses_from_dependencies` is a validation error.

---

### Field: acceptance_criteria

**Format**: every AC must follow Given/When/Then/verify.

```
Given [starting state],
When [exact action with exact input],
Then [observable result],
verify: [exact command or assertion that confirms this]
```

| ❌ Unverifiable | ✅ Given/When/Then/verify |
|----------------|--------------------------|
| "Order creation works" | Given DB is empty, When `curl -X POST /api/orders -d '{"products":[{"id":"p1","qty":2}],"address":"ul. Testowa 1"}'`, Then response is `201 {"id":"<uuid>","status":"pending"}` and `SELECT count(*) FROM orders` returns 1, verify: `curl -s -X POST ... \| jq .status` outputs `"pending"` |
| "Email is sent" | Given order created with id=X, When confirmation job runs, Then `SELECT count(*) FROM email_log WHERE order_id='X'` returns 1, verify: `psql -c "SELECT count(*) FROM email_log WHERE order_id='X'"` returns `1` |
| "Validation rejects bad input" | Given valid auth token, When `curl -X POST /api/orders -d '{"products":[]}'`, Then response is `400 {"error":"products cannot be empty","field":"products"}`, verify: `curl ... \| jq .error` outputs `"products cannot be empty"` |

**Minimum per task**: 1 happy path + 1 error case. No exceptions.
Boring task minimum: config task AC: Given `DATABASE_URL` env var missing,
When app starts, Then process exits with code 1 and stderr contains
`"DATABASE_URL required"`, verify: `DATABASE_URL="" node dist/index.js; echo $?`
outputs `1`.

---

### Field: test_plan

`notes` must list specific cases — never just "unit tests":

```json
"test_plan": {
  "unit": true,
  "integration": true,
  "e2e": false,
  "notes": "unit: OrderCreateSchema — valid body, empty products array, missing address, product_id not UUID | integration: POST /api/orders happy path writes to DB and enqueues BullMQ job (use testcontainers postgres + bullmq mock)"
}
```

If all three are `false`: write why — e.g. "pure routing config, covered by
_3 integration test which calls this endpoint".

---

## Step 4 — Dependency graph

Write the graph before writing phases:

```
_1 (order-model)          → no dependencies
_2 (create-order-endpoint)→ depends on: _1
_3 (confirmation-job)     → depends on: _1
_4 (enqueue-after-create) → depends on: _2, _3

Layers:
Layer 1: _1
Layer 2: _2, _3   ← parallel
Layer 3: _4
```

**Hidden dependency check** — for every task answer:
- Writes data → depends on task that defines schema? (`[REQ]` data persistence)
- Reads data → depends on task that creates that data?
- Calls external system → depends on config/credential task?
- Needs auth context → depends on auth middleware task?

Any "yes" without corresponding `depends_on` = missing edge. Add it.

**Max 3 dependencies per task.** More = task is too large. Split it.

---

## Step 5 — Exit gates per layer

For every layer in the graph, write the exit gate: **one command** that
returns pass/fail before the next layer starts.

```
Layer 1 exit gate:
  command: npx ts-node -e "import('./src/models/Order').then(m => m.OrderModel.create({products:[],address:'test',email:'a@b.com'}).then(console.log))"
  expected: prints object with id, status='pending', no throw

Layer 2 exit gate:
  command: curl -s -X POST http://localhost:3000/api/orders -H "Authorization: Bearer $TEST_TOKEN" -d '{"products":[{"id":"p1","qty":1}],"address":"ul. Testowa 1","email":"test@test.com"}' | jq .status
  expected: outputs "pending"

Layer 3 exit gate:
  command: psql $DATABASE_URL -c "SELECT count(*) FROM email_log" && redis-cli LLEN bull:order-confirmation:wait
  expected: email_log count >= 1, queue length >= 0 (job consumed or waiting)
```

Exit gates are binary: pass = proceed to next layer, fail = stop and fix.
Do not proceed to the next layer until the current exit gate passes.

---

## Step 6 — Quality actions

These are actions to perform, not questions to answer.

**Action 1**: Take `_1.instruction`. Count the file paths mentioned.
If count = 0 → instruction fails. Rewrite before continuing.

**Action 2**: Take any AC from any task. Write the verify command.
If you cannot write a runnable command → AC fails. Rewrite before continuing.

**Action 3**: Take any task with `depends_on`. Read `uses_from_dependencies`.
Is the referenced artifact (file/endpoint/model) mentioned by name in `instruction`?
If not → dependency is decorative. Add the reference or remove the arrow.

**Action 4**: Take `test_plan.notes` from any task with `unit: true`.
Count specific test cases listed. If count = 0 → test plan fails. Add cases.

**Action 5**: Read Layer 1 exit gate. Can you paste it into a terminal right now?
If it references a variable that isn't defined in the gate itself → fix it.

All 5 actions must produce a pass result. First fail → fix → restart from Action 1.

---

## Step 7 — Deliver

```
## Plan: [scope name]
Tasks: N across N layers

[_N] task-name — one line description
  depends on: [_X, _Y] | parallel: yes/no

Dependency graph: [paste graph from Step 4]

Layer exit gates: [paste gates from Step 5]
```

Wait for approval before execution.

---

## What NOT to produce

- `instruction` without exact file paths (minimum 2 per task)
- AC without `verify:` command
- `depends_on` with empty or missing `uses_from_dependencies`
- `test_plan.notes` = "add unit tests" or "cover edge cases"
- Plans with >12 tasks without splitting the objective first
- Any `[CONFLICT]` from Step 0 unresolved
