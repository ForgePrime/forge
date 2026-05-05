# MVP_SCOPE.md — Minimum Viable First Ship

> **Status:** DRAFT — pending distinct-actor review per ADR-003.
> **Parent:** MASTER_IMPLEMENTATION_PLAN.md §7 Phase 1.

## 1. The MVP scenario

**Target:** Python developer receives a GitHub Issue describing a small behavior change needed in a backend service. Forge takes the Issue, understands the task, generates proposed code, runs tests, opens a PR with evidence trail. Developer reviews + merges.

**Concrete example (the "smoke test" scenario for demo):**

> GitHub Issue #42: "The `/api/users/{id}/orders` endpoint should return a 404 when the user_id does not exist, instead of the current empty array."

Forge flow:
1. User creates Project in Forge, links GitHub repo
2. Forge watches repo for new Issues labeled `forge-task`
3. Issue #42 detected → Forge ingests → Knowledge entity
4. Forge extracts: goal, actor (API consumer), process (order-listing), requirement, risks
5. Developer reviews Findings, clarifies 1 ambiguity ("what if user exists but has no orders — empty array or 404?")
6. Objective activated: "Orders endpoint returns 404 for non-existent users, [] for existing-but-empty"
7. Tasks decomposed: T1 modify route handler, T2 add test cases
8. Execution: Forge reads route file, proposes Decision with 2 alternative implementations, selects argmax per F.11
9. Change proposed with expected_diff: modifies 1 file, adds 3 test cases
10. Forge opens PR with structured commit message + evidence trail + test results
11. CI runs on PR → G.10 Baseline/Post check → Diff matches ExpectedDiff
12. Developer reviews PR in GitHub → approves → merges

**Total latency target: < 15 min** from Issue creation to PR open.
**Cost target: < $2** per complete Task.

## 2. What's in MVP scope

### L1 Governance — minimal stages

From 57 ROADMAP stages, MVP implements:
- Pre-flight: ADR-003 RATIFIED ✓; ADR-004 placeholder values seeded
- **A.1** EvidenceSet entity (already skeleton at c8d82ae)
- **A.2** GateRegistry (populated with ~20 transition rules for MVP flow)
- **A.3** VerdictEngine in shadow mode only (no A.4 cutover yet)
- **A.5** MCP idempotency (required to avoid double-Execution on webhook retries)
- **B.1** CausalEdge table + minimal insert gate
- **B.4** ContextProjector (simple BFS + priority-based pruning)
- **B.5** TimelyDeliveryGate (WARN mode only — REJECT deferred to post-MVP)
- **C.1** ImportGraph (static Python AST walk only)
- **C.3** ImpactClosure (basic — no dynamic dispatch)
- **C.4** Reversibility (REVERSIBLE/IRREVERSIBLE classifier only — skip COMPENSATABLE/RECONSTRUCTABLE)
- **D.1** Deterministic test harness
- **D.2** 3 property tests (determinism, acyclicity, idempotence)
- **D.4** ≥5 adversarial fixtures from expected MVP edge cases
- **E.1** ContractSchema minimal (hard-coded schemas for 2 task types: `code_change`, `add_test`)
- **E.2** 3 seed Invariants
- **F.1** Evidence kind constraint
- **F.3** Assumption tags (WARN mode)
- **F.4** BLOCKED state + resolve-uncertainty endpoint
- **G.10** Baseline/Post minimal (file checksum diff only — not full 5-component snapshot)

**Explicitly OUT of MVP:**
- A.4 enforcement cutover (stays shadow)
- All of B.2 (backfill) — MVP starts with empty DAG
- B.3 CausalGraph (query layer) — B.4 uses raw queries
- B.6 SemanticRelationTypes — generic relation='depends_on' only
- B.7 SourceConflictDetector — single-source Knowledge only at MVP
- B.8 Actor+Process entities — MVP uses free-text references
- D.3 Metamorphic tests, D.5 FailureMode entity, D.6 CriticalPath
- All E.3–E.9 except E.1+E.2
- F.2, F.5–F.12 except F.1/F.3/F.4
- G.1–G.9 except G.10
- G.11 Error propagation

These defer to Phase 2+ per MASTER_IMPLEMENTATION_PLAN §7.

### L2 Execution Engine — full MVP

- VerdictEngine.evaluate() pure function
- GateRegistry static dict, ~20 MVP transitions
- RuleAdapter Protocol + 5 concrete adapters:
  - `EvidenceSourceKindAdapter` (F.1)
  - `AssumptionTagAdapter` (F.3)
  - `UncertaintyBlockedAdapter` (F.4)
  - `ContractSchemaValidator` (E.1)
  - `ContextProjectionCompleteAdapter` (B.5)
- Execution lifecycle manager (state machine)
- Event bus (in-process EventEmitter, async)
- MCP idempotency via `(execution_id, tool_call_id)` unique constraint

### L3 LLM Orchestration — minimal

- 3 prompt templates: `code_change_generate`, `ambiguity_extract`, `candidate_evaluate`
- 5 tools: `read_file`, `edit_file`, `run_tests`, `git_diff`, `check_spec`
- Model routing: Sonnet only (Haiku/Opus deferred)
- Context budget: simple token-counting (tiktoken-based)
- Failure recovery: 1 retry on timeout, 2 retries on malformed output
- Cost tracking via `llm_calls` table

### L4 UX — developer persona only

**CLI (5 commands):**
- `forge init <repo-url>` — create Project linked to GitHub repo
- `forge objective show [--id]` — list/show Objectives
- `forge execute <task-id>` — trigger Execution manually
- `forge status` — project health snapshot
- `forge audit <change-id>` — show evidence trail for Change

**Web dashboard (3 pages):**
- `/` — Project list
- `/projects/{slug}` — Project overview (Objectives + active Executions + recent Changes)
- `/executions/{id}` — Execution detail (LLMCalls + Findings + Decision + Change)

No login yet (assumes single-user local deployment for MVP demo).

### L5 Integration — GitHub only

- GitHub App / OAuth: read Issues, write PRs
- Webhook handler: Issue created with `forge-task` label → trigger Forge flow
- Local git operations (clone, branch, commit, push)
- No CI integration yet (tests run locally via subprocess)
- No issue tracker other than GitHub

### L6 Operations — local + basic hosting

- Docker Compose for local dev (Postgres + Redis + Python worker + Next.js web)
- Deploy to Render.com free tier (or Railway / Fly.io)
- Structured JSON logs to stdout
- Health endpoint `/health` returns Forge + DB + LLM provider status
- No monitoring dashboard yet (logs + manual grep)

### L7 Quality Evaluation — 3-task benchmark

**Canonical benchmark Tasks (auto-gradable):**

1. **Task-bench-01:** Add a boundary check to an existing endpoint (similar to MVP scenario). Expected: endpoint returns 404 on invalid input, tests pass.
2. **Task-bench-02:** Fix a bug in a pure function (e.g., off-by-one in pagination). Expected: specific existing test transitions from FAIL to PASS.
3. **Task-bench-03:** Add input validation to a form handler. Expected: new test cases for invalid inputs all PASS.

Each benchmark Task has:
- Starting code state (git commit hash)
- Target AC (testable)
- Reference solution
- Auto-grader: compares Forge's solution to reference via test pass rate + AST similarity

**Quality threshold MVP:** Score ≥ 0.6 on all 3 benchmark Tasks.

## 3. Explicitly OUT of MVP scope

- **Multi-tenancy** — MVP is single-user local or single-tenant hosted
- **Authentication beyond OAuth-to-GitHub** — no user management, no teams
- **Multi-agent concurrency** — one Execution at a time per Project
- **Non-Python languages** — MVP demonstrates on Python backend only; TypeScript/Go/etc. deferred
- **Large codebases** — MVP target: < 10k LOC per project (small services, libraries)
- **Complex architectures** — single monorepo, no microservices orchestration
- **Deep IDE integration** — no VS Code extension yet
- **Steward workflows** — MVP flow is single-developer; Steward role added post-MVP
- **Compliance audit reports** — full audit UI deferred; MVP has CLI `forge audit <change-id>` with JSON output
- **Cost optimization beyond Sonnet-only** — no model routing sophistication
- **Analytics / usage tracking** — basic metrics only
- **Custom task types** — MVP ships with 2 hardcoded task types (`code_change`, `add_test`)

## 4. MVP success criteria (hard gate)

**Before ship (Phase 1 exit criteria per MASTER §7):**

- [ ] 1 real GitHub Issue → merged PR end-to-end, on camera (demo recording)
- [ ] Benchmark score ≥ 0.6 on all 3 Task-bench tests
- [ ] Cost < $2 P95 per Task (measured over 10 Executions)
- [ ] Latency P95 < 15 min per Task (Issue creation → PR open)
- [ ] Onboarding < 1 hour (1 test user from scratch to first Execution)
- [ ] All Phase 0 + Phase 1 tests GREEN (unit + property + adversarial + integration + 14 layer-connectivity)
- [ ] Layer Connectivity Theorem: all 14 L_i ↔ L_j contract tests GREEN
- [ ] Closure(System) = true: all 7 layers EXIST + CONNECTED + CONTROLLED + MEASURED + RECOVERABLE at MVP scope level
- [ ] 0 P0 bugs, ≤ 2 P1 bugs in backlog
- [ ] `docker-compose up` → `curl localhost:8000/health` → all green in < 2 min on fresh clone

## 5. Validation plan — first 5 users

Post-MVP-ship (Phase 2 beginning), recruit 5 design-partner developers:

1. **User 1 (internal):** team member who built it, validates it works
2. **User 2 (friendly external):** engineer acquaintance, Python backend
3. **User 3-5 (ICP match):** regulated-industry or compliance-conscious team (fintech/healthtech SME)

Feedback collection:
- 30-min structured interview per user after 2-week trial
- NPS + specific use-case fit scoring
- Feature request + pain-point log

Gate for Phase 2 continuation:
- ≥ 3 of 5 users rate "would use weekly" score ≥ 4/5
- Observable usage: ≥ 10 real Tasks processed across users (not test Tasks)

Below this → Phase 2 scope re-evaluated. May pivot ICP or narrow further.

## 6. Risks specific to MVP

| Risk | Mitigation |
|---|---|
| Sonnet-only model limits quality on complex Tasks | Route to Opus for Tasks rated ceremony=FULL |
| ContextProjector under-fills for larger codebases | MVP cap at 10k LOC; clear error if exceeded |
| GitHub rate limits on API | Use GitHub App with increased limits; cache reads |
| Ambiguity extraction LLM quality inconsistent | Accept via `resolve-uncertainty` user override path; iterate with production data |
| Test runner subprocess timing flaky | Subprocess uses pytest `-x` fail-fast; reasonable timeout |
| Demo failure mid-recording | Pre-record 3 takes; use canonical benchmark tasks |
| Feature creep during Phase 1 | Phase 1 exit criteria hard-coded; no scope additions without Phase 2 re-plan |
| Cost overrun per Task | budget_guard pre-flight estimate; halt Execution if projected > $5 |
| LLM output non-determinism masks bugs | Temperature=0, seed-reproducible tests, golden-file comparisons |

## 7. Branching discipline

- MVP work on `docs/forge-plans-soundness-v1` branch until ADR-003 review complete for all MVP-scope docs
- Then branch `impl/mvp` for implementation commits
- Short-lived feature branches per Stage: `impl/mvp-stage-a1`, `impl/mvp-stage-b4`, etc.
- Merge to `main` only after Phase 1 exit gate GREEN

## 8. Authorship + versioning

- v1 (2026-04-24) — initial MVP scope + success criteria + validation plan.
- Updates during Phase 1 require explicit version bump.
