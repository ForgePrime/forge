# MASTER IMPLEMENTATION PLAN — Forge as Closure-Compliant 7-Layer System

> **Status:** DRAFT — pending distinct-actor review per ADR-003.
>
> **Purpose:** single authoritative plan covering end-to-end Forge delivery. Satisfies Implementation Closure Theorem (all 7 required layers L1-L7 exist, connect, have control + quality + recovery) and upstream theorems already addressed (CCEGAP, ECITP, Engineer Soundness, ASPS, Forge Complete, ProcessCorrect, AIOS, AI-SDLC).
>
> **Principle:** testing-first + parallel layer build + vertical-slice MVP first, horizontal expansion second. Each element has tests at creation; edge-focused adversarial regression runs continuously.
>
> **Solo-verifier disclosure:** AI-authored. All claims [ASSUMED: agent-synthesis, requires distinct-actor review]. ADR-003 RATIFIED; per-layer specs require their own reviews before NORMATIVE.

---

## 1. Implementation Closure compliance map

The Closure theorem requires 7 layers. Current state + target state:

| Layer | Required | Current state | Target state (post-plan) |
|---|---|---|---|
| **L1 Governance** | Validators, gates, audits, invariants, state machines | ✅ 58 plan stages + 27 ADRs + ADR-003 RATIFIED | ✅ FULL (already) |
| **L2 Execution Engine** | VerdictEngine, GateRegistry, state transitions, idempotency | ⚠️ Skeleton (c8d82ae) | ✅ FULL implementation |
| **L3 LLM Orchestration** | Prompts, tools, context budget, model routing, failure recovery | ❌ MISSING | ✅ FULL (new spec + code) |
| **L4 UX** | CLI + web dashboard + onboarding + error messages | ❌ MISSING | ✅ FULL (spec + impl) |
| **L5 Integration** | Git, CI, issue tracker, deployment, notifications | ❌ MISSING | ✅ FULL (spec + adapters) |
| **L6 Operations** | Deployment topology, scaling, security, monitoring, DR | ❌ MISSING | ✅ FULL (spec + infra) |
| **L7 Quality Evaluation** | Output quality metrics, score thresholds, benchmarks | ❌ MISSING | ✅ FULL (spec + instrumentation) |

**Closure(System) target = true iff all 7 layers EXIST + CONNECTED + CONTROLLED + MEASURED + RECOVERABLE.**

---

## 2. Testing strategy (pre-phase — testing discipline comes first)

Per user requirement: "każdy element musi mieć swoje testy, testy uruchamiać po każdym etapie, regression edge-focused".

### 2.1 Per-element test obligation

Every code element (function, endpoint, gate, validator, tool-use handler) gets ≥ 3 tests at creation:

1. **Happy path** — typical input → expected output
2. **Edge boundary** — at least one edge case (empty, max, min, unicode, concurrent)
3. **Failure mode** — invalid input → deterministic error (not crash)

Extra for stateful components:
4. **Property-based** (hypothesis) — invariant holds over random inputs
5. **Idempotency** — `f(f(x)) = f(x)` where applicable

### 2.2 Regression test taxonomy (edge-focused)

Five test tiers running continuously in CI:

| Tier | Purpose | Runs | Budget |
|---|---|---|---|
| T-unit | per-function contract | every commit | < 30s |
| T-property | hypothesis-based, random inputs | every commit | < 2min |
| T-adversarial | PRACTICE_SURVEY incidents + known failure modes | every commit | < 5min |
| T-boundary | exact threshold values (α, max_depth, LOC limits) | every commit | < 1min |
| T-integration | cross-layer flows | nightly | < 30min |
| T-soak | long-running multi-agent concurrency | weekly | hours |
| T-mutation | mutmut on critical modules | weekly | hours |

### 2.3 Regression fault-detection optimization

Per AIOS A14 + FC §23: `TestSet* = argmax Probability(DetectFailure)`.

Test-case generation priority:
1. **Mutation-surviving gaps** — every mutant that tests don't kill → new test
2. **Production-incident seeds** — every real bug discovered → adversarial fixture
3. **Boundary cases** — test cases for exact thresholds (α boundary, max_depth=5 boundary, LOC=50 boundary, token budget boundary)
4. **State-transition combinatorics** — every (from_state, event, condition) triple in GateRegistry gets a test
5. **Adversarial inputs** — SQL injection, overflow values, malformed JSON, malformed LLM responses

### 2.4 Test invocation discipline

```bash
# After every stage-complete:
uv run pytest tests/ -x --hypothesis-seed=0    # must be GREEN
uv run pytest tests/adversarial/ -x             # must be GREEN
uv run pytest tests/property/ -x                # must be GREEN
python scripts/verify_graph_topology.py ...     # must be PASS 5/5
python scripts/compute_critical_path.py ...     # no CritPath violations
python scripts/proof_trail_audit.py             # no 10-link gaps
```

Every PR requires all green + mutation_smoke.py documented output.

---

## 3. Layer specifications (L1-L7) — what each layer delivers

### L1 Governance (COMPLETE — 58 stages already planned)
Per existing plan corpus. ADR-003 RATIFIED. Status: ✅ no further spec needed for MVP, continue per ROADMAP.

### L2 Execution Engine (skeleton exists; needs full implementation)

**Mandate:** deterministic state-machine infrastructure connecting Governance decisions to runtime execution.

**Components:**
- `VerdictEngine.evaluate(ctx, rules) → Verdict` — pure function (already stub at c8d82ae)
- `GateRegistry` — static (entity, from_state, to_state) → rules (empty at skeleton; populate)
- `RuleAdapter` implementations for all registered validators
- `Execution` lifecycle manager (pending → IN_PROGRESS → COMMITTED → ACCEPTED / REJECTED / BLOCKED)
- Event bus for state transitions (publishes events consumed by L3/L4/L5)
- Idempotency keys (A.5 pattern) + MCP tool call ledger

**L2 ↔ other layers:**
- L2 ↔ L1: Gates consult L1 Invariants + ContractSchema
- L2 ↔ L3: L2 triggers LLM calls via L3 orchestrator
- L2 ↔ L5: L2 writes events (webhooks, git commits) via L5 adapters
- L2 ↔ L7: L2 captures quality metrics on every Execution outcome

### L3 LLM Orchestration (NEW — critical missing layer)

**Mandate:** every LLM invocation is structured, bounded, tool-equipped, cost-controlled.

Per theorem: `valid(LLM_call) ⇔ structured(prompt) ∧ bounded(context) ∧ defined(tools) ∧ constrained(budget)`.

**Components:**

#### L3.a Prompt Templates
- Per-`(task_type, ceremony_level, capability)` prompt template
- Sections: `system`, `context` (from ContextProjector), `constraints` (from ContractSchema), `examples` (few-shot), `task`, `output_format`
- Assembly deterministic: same inputs → same prompt bytes
- Template registry: `prompt_templates(id, task_type, ceremony_level, capability, version_id, sections JSONB)`

#### L3.b Tool Registry
```python
TOOLS = {
    "read_file": {"schema": ..., "authority": ["participant", "system_automation"]},
    "write_file": {"schema": ..., "authority": ["decision_maker", "system_automation"]},
    "edit_file": {"schema": ..., "authority": ["decision_maker"]},
    "run_tests": {"schema": ..., "authority": ["participant"]},
    "git_diff": {"schema": ..., "authority": ["observer"]},
    "git_commit": {"schema": ..., "authority": ["approver"]},
    "query_db": {"schema": ..., "authority": ["observer"]},
    "check_spec": {"schema": ..., "authority": ["observer"]},
    "fetch_causal_graph": {"schema": ..., "authority": ["observer"]},
    "check_invariant": {"schema": ..., "authority": ["observer"]},
    "compute_impact_closure": {"schema": ..., "authority": ["observer"]},
}
```
- Each tool has: JSON Schema input/output, authority_level requirement, rate limit, audit log hook
- Tool calls logged to `llm_tool_calls(execution_id, tool_name, input_json, output_json, duration_ms, called_at)`

#### L3.c Context Budget Algorithm
```
project(task, budget_tokens) → ContextProjection with budget discipline:
  Priority order (per FORMAL_PROPERTIES_v2 P15):
    1. MUST: contract_schema, required_refs, hard_invariants
    2. SHOULD: ambiguity_state, dependency_relations, scope_tags
    3. NICE: past_decisions, similar_tasks, guidelines

  Algorithm:
    - Tokenize each candidate section via model's tokenizer (per ADR-006)
    - Fill MUST bucket first; if doesn't fit → Execution BLOCKED (budget too small)
    - Fill SHOULD until budget exceeded; truncate last section deterministically
    - Fill NICE with remaining budget; drop lowest-priority first
    - Emit ContextProjection with manifest of included + dropped sections
```

#### L3.d Model Routing
```
route_model(task) → model_id:
  if task.ceremony_level == 'LIGHT' and task.scope_size < 10: Haiku
  elif task.ceremony_level == 'STANDARD': Sonnet
  elif task.ceremony_level == 'FULL' or task.severity == 'Critical': Opus
  else: Sonnet (default)

  Override via Task.force_model_pin if author specifies.
  Challenger model (F.6) always different from primary (distinct-actor per ADR-012).
```

#### L3.e Failure Recovery Within Execution
- Timeout: retry once with exponential backoff; 2nd timeout → BLOCKED
- Malformed output: pre-parse validation; if invalid → retry with format hint (max 3); then REJECTED
- Tool call error: log + continue if non-critical; halt + REJECTED if critical tool
- Partial result: accept if structural fields populated; mark incomplete in Finding

#### L3.f Cost Tracking
- `llm_calls(execution_id, model_id, prompt_tokens, completion_tokens, cost_usd_cached, called_at)`
- `budget_guard` enforces per-Task budget (from ADR-004 calibration)
- Monthly cost report per Project

**Exit criteria L3:** same task+context → same prompt bytes (determinism); tool catalog tested with authority-level rejection scenarios; budget algorithm correctness on 100 fixtures; model routing deterministic; failure recovery integration-tested with mocked LLM timeouts.

### L4 UX (NEW)

**Mandate:** developer/steward/PO/admin can use Forge end-to-end via CLI + web dashboard.

**Components:**

#### L4.a CLI (`forge`)
```bash
forge init                          # create Project
forge knowledge add <file>          # upload docs
forge objective define "goal"       # create Objective
forge task list                     # list Tasks
forge execute <task_id>             # run Execution
forge decision review <id>          # review proposed Decision
forge change apply <id>             # apply Change after verification
forge steward queue                 # Steward: pending sign-offs
forge status                        # project health dashboard
forge audit proof-trail --change <id>
forge metrics                       # show 7 metrics + 4 Tier-1 metrics
```

#### L4.b Web Dashboard (minimal)
- Project list + create
- Objective view: goals + KRs + reachability status
- Task board: PENDING / READY / IN_PROGRESS / DONE / BLOCKED (kanban)
- Execution detail: state + LLMCall history + Finding list + Decision + Change + evidence
- Finding review: ambiguity / risk / requirement → accept/clarify/block
- Change review: expected_diff + runtime observations + apply/reject
- Steward queue: pending critical sign-offs + ACKNOWLEDGED_GAP reviews
- Metrics dashboard: 7 G.3 metrics + CritPath slippage + cascade blast radius + debt categories
- Constellation map (`/map`) — DAG view of Objective → KR → AC → Task → TestRun → Source with live AI-activity highlighting, isolation focus, 8 filters. **Phase 2 per UX_DESIGN.md §11**; Phase 1 minimum subset (§11.11) specified but not enacted unless scope expansion approved

#### L4.c Onboarding
- First-run wizard (3 steps): create Project, upload first doc, define first Objective
- In-app tutorial: guided first Execution
- Documentation site (docusaurus): reference docs + tutorial videos

**Exit criteria L4:** all 4 personas complete their typical flow in < 30 min; error messages have actionable fix instructions; accessibility minimal (keyboard navigation, readable contrast).

### L5 Integration (NEW)

**Mandate:** Forge connects to developer's actual toolchain.

**Components:**

#### L5.a Git Adapter
- Read: clone/pull repo, read file at commit, compute diff between commits
- Write: create branch, commit Changes with structured message, push, open PR (GitHub/GitLab API)
- Webhook: receive push/PR events → trigger re-audit of affected Tasks
- Authentication: SSH key / OAuth token per Project

#### L5.b CI Adapter
- `.github/workflows/forge.yml` template: runs G_GOV checks on PR
- GitHub Actions custom action: `forge-verify-pr@v1`
- GitLab CI YAML template equivalent
- Webhook: CI result → Execution status update

#### L5.c Issue Tracker Adapters
- GitHub Issues: `gh issue → Knowledge + Objective(DRAFT)` auto-import
- Linear: similar via Linear API
- Jira: via REST API + AuthN via OAuth
- Generic webhook: accept JSON with mapping to (Knowledge, Objective) schema

#### L5.d Deployment Hooks
- Post-APPLIED Change → trigger deployment webhook (user-configured URL)
- Support: Kubernetes (kubectl apply), AWS (CodeDeploy), custom scripts

#### L5.e Notification Channels
- Slack: per-channel routing (e.g., `#forge-stewards` for pending sign-offs)
- Email: daily digest + immediate for CRITICAL
- In-app: real-time via SSE/WebSocket

**Exit criteria L5:** end-to-end from GitHub Issue → merged PR works with GitHub + GitHub Actions only (MVP); other adapters ship incrementally.

### L6 Operations (NEW)

**Mandate:** Forge runs in production reliably.

**Components:**

#### L6.a Deployment Topology
- **Phase 1 (MVP):** Single-tenant SaaS; Postgres + Redis + Python workers + Next.js frontend; 1 instance per customer
- **Phase 2:** Multi-tenant SaaS with project-level isolation
- **Phase 3:** Self-hosted option (Docker Compose + Helm chart)
- **Cost target:** < $100/month per small project (10 Executions/day)

#### L6.b Scaling Targets
| Tier | Projects | Concurrent Executions | Knowledge entries | SLA |
|---|---|---|---|---|
| MVP | 10 | 5 | 1000 | 99% |
| Growth | 1000 | 50 | 100k | 99.5% |
| Scale | 10k | 500 | 10M | 99.9% |

#### L6.c Security Posture
- Auth: OAuth (GitHub, Google, Microsoft) + SAML for enterprise
- Authz: Role-based per Project + Actor.authority_level enforcement
- Encryption: at-rest (AES-256 DB encryption) + in-transit (TLS 1.3)
- Audit log: all state mutations → `audit_log` table + 7-year retention
- DLP: per ADR-018 Path B ACKNOWLEDGED_GAP; upgrade to Presidio when scope expands
- Secrets: per-Project KMS-managed, never in code

#### L6.d Monitoring + Alerting
- Metrics (Prometheus + Grafana): latency, error rate, LLM cost, budget exhaustion, CritPath slippage
- Logs (structured JSON): correlation IDs across Execution → Decision → Change → LLM call
- Traces (OpenTelemetry): span per Stage
- Alerts: PagerDuty integration; tier-1 pages for CRITICAL Incidents (ADR-008 kill-criteria)

#### L6.e Backup + DR
- RPO: 1 hour (Postgres point-in-time recovery)
- RTO: 4 hours for full restoration
- Region failover: Phase 3+
- Runbook: documented recovery procedures

**Exit criteria L6:** MVP deployed on small-scale managed Postgres + Render/Railway + Vercel; security audit passed before first paying customer; monitoring surfaces all CRITICAL incidents within 1 minute.

### L7 Quality Evaluation (NEW)

**Mandate:** measure output quality, not just process compliance.

Per theorem: `Quality(output) ≥ acceptable`, `Score(candidate_best) ≥ minimal_quality`.

**Components:**

#### L7.a Quality Metrics
- **Output correctness** (per-Change): does it do what was requested?
- **Output safety** (per-Change): no introduced security/performance regressions
- **Output efficiency** (per-Change): LOC added vs functionality delivered
- **Output maintainability**: complexity metrics (cyclomatic, cognitive) vs prior version
- **Stakeholder satisfaction** (post-deployment): user feedback scores

#### L7.b Benchmark Suite
- Held-out problem set: 20 canonical Tasks with known-good outputs
- Automated grading: Forge's output compared to reference via:
  - Test pass rate (if AC convertible to tests)
  - AST similarity to reference (modulo stylistic variation)
  - Manual grading for 5 random samples per week (Steward time)
- Regression: benchmark score tracked per Forge version; > 5% degradation → release blocked

#### L7.c Score Thresholds (per F.11 + ADR-019)
- Candidate evaluation requires `Score(candidate_best) ≥ 0.6` (normalized)
- Below threshold → Finding + Execution REJECTED (quality gate, not just argmax)
- Threshold recalibrated quarterly based on benchmark drift

#### L7.d User Feedback Loop
- Every APPLIED Change triggers 48h feedback request: "Did this work as expected?" (yes/no/partial)
- Feedback → `user_feedback` table → G.4 Rule Lifecycle incorporates patterns
- Negative feedback > 10% on a capability → capability auto-demoted to lower autonomy per E.3

#### L7.e Cost/Latency Targets
- P95 Execution latency: < 5 min for LIGHT tasks, < 30 min for FULL
- P95 cost per Execution: < $0.50 LIGHT, < $5.00 FULL
- LLM cost breakdown in monthly report

**Exit criteria L7:** benchmark suite runs on every release; quality score trend dashboard; user feedback loop integrated; score threshold enforced at F.11 evaluation.

---

## 4. Layer Connectivity Matrix (required interactions per Layer Connectivity Theorem)

| Interaction | Interface | Test |
|---|---|---|
| L1↔L2 | L1 Invariants/Schemas consulted by L2 Gates via `InvariantRegistry.lookup()` | Contract test: every Gate invocation reads current invariants |
| L2↔L3 | L2 triggers LLM via `L3.Orchestrator.execute(task, context) → Result` | Contract test: deterministic prompt on same input |
| L2↔L5 | L2 publishes events to `EventBus`; L5 adapters subscribe | Contract test: event fan-out to all subscribed adapters |
| L2↔L7 | L2 captures Quality scores per Execution via `L7.MetricsCollector.record()` | Contract test: every Execution has score row |
| L3↔L4 | L3 streams LLMCall progress to L4 dashboard via SSE | Contract test: dashboard shows real-time token count |
| L3↔L5 | L3 tools call L5 adapters (git, filesystem) | Contract test: tool call → adapter invocation traced |
| L3↔L6 | L3 reports LLM costs + latency to L6 monitoring | Contract test: Prometheus metric updates on every LLM call |
| L3↔L7 | L3 output graded by L7 benchmark if Task matches benchmark set | Contract test: benchmark score assigned on graded Tasks |
| L4↔L1 | L4 dashboard surfaces L1 Findings + Decisions + AC status | Contract test: every L1 entity has L4 view |
| L4↔L5 | L4 authn via L5 OAuth adapters | Contract test: login flow works |
| L4↔L6 | L4 API calls L6 hosted backend | Contract test: request routing |
| L5↔L6 | L5 adapter webhooks → L6 worker queue | Contract test: webhook event processed within SLA |
| L5↔L7 | L5 CI results feed L7 quality signals | Contract test: CI green/red reflected in Quality score |
| L6↔L7 | L6 operational metrics feed L7 reliability component of Value | Contract test: SLA breach → Quality score decrement |

**Tested via `tests/integration/test_layer_connectivity.py`** — 14 contract tests (one per interaction).

---

## 5. Execution Continuity Guarantee (per theorem)

`Request → Plan → Execution → Result → Feedback → Next Iteration`

Every step must be `executable(s) ∧ recoverable(s)`:

| Step | Executable | Recoverable |
|---|---|---|
| Request | User ticket via L5 adapters | If malformed → BLOCKED + clarify endpoint |
| Plan | L1 Objective + Tasks + AC | If reachability fails → user refines or cancels |
| Execution | L2 Execution + L3 LLM call | If LLM timeout → retry; if max retries → REJECTED |
| Result | L3 parsed output → Decision + Change | If malformed → re-execute with format hint |
| Feedback | L7 quality score + user feedback | If below threshold → new Execution proposed |
| Next iteration | L2 spawns follow-up Task if needed | State persisted; resumable after crash |

**Crash recovery**: every state transition persists to DB before ack; on restart, incomplete Executions resume from last committed state; orphaned Executions (> 1h no progress) auto-BLOCKED with Finding.

---

## 6. Real Value Theorem targets

`Value = f(OutputQuality, Cost, Latency, UX, Reliability)` must exceed threshold.

Concrete targets for MVP:

| Component | MVP target | Measurement |
|---|---|---|
| **OutputQuality** | ≥ 0.7 / 1.0 on benchmark suite (20 canonical Tasks) | L7.b benchmark auto-grader |
| **Cost** | < $2 per average Task | L7.e LLM cost tracking |
| **Latency** | P95 < 15 min end-to-end | L6 metrics |
| **UX** | Developer can complete first Change in < 1 hour (new user) | Onboarding telemetry + 5 user interviews |
| **Reliability** | 99% SLA on Forge API + Zero data loss | L6 monitoring |

Below threshold on ANY component → MVP not deployable.

---

## 7. Phased implementation plan (5 phases + parallel layers)

Testing-first discipline: every phase EXITS when all tests pass.

### Phase 0 — Foundations (2-3 weeks, parallel across layers)

**Purpose:** enable testing early; scaffolding for everything that follows.

| Layer | Phase 0 deliverable | Test requirement |
|---|---|---|
| L1 | Minimal validator seed (2 invariants + 5 gates) | 3 tests per validator |
| L2 | VerdictEngine + GateRegistry functional (extends c8d82ae skeleton) | Determinism property test (D.2-analog), idempotency test (D.2-analog) |
| L3 | Prompt template registry (5 canonical templates) + Tool registry (5 critical tools) + Model router | Determinism test (same input → same prompt), authority-level enforcement test |
| L4 | CLI skeleton (5 commands); web dashboard scaffold (1 page) | CLI invocation tests; dashboard smoke test |
| L5 | Git read adapter only + local filesystem adapter | Adapter contract tests |
| L6 | Docker Compose local dev stack + structured logging | `docker-compose up` → full stack runnable |
| L7 | Metrics collector stub + 5 benchmark Task definitions | Benchmark loader test |

**Exit criteria Phase 0:**
- All layer scaffolding in place
- 14 layer-connectivity contract tests GREEN
- Full test suite runs in < 5 min
- Developer can spin up Forge locally via `docker-compose up + python -m forge.cli init`

### Phase 1 — Vertical-slice MVP (3-4 weeks)

**Purpose:** smallest end-to-end flow that exercises L1-L7 on a real Task.

**MVP scenario:** "Python developer receives GitHub Issue, Forge generates proposed code change, runs tests, opens PR."

Minimal stages implemented (subset of 58):
- Pre-flight: ADR-003 mechanism (already RATIFIED); ADR-004 placeholder values for MVP
- Phase A: A.1 EvidenceSet + A.2 minimal GateRegistry + A.3 VerdictEngine + A.4 shadow-mode only (no cutover yet)
- Phase B: B.1 CausalEdge + B.4 ContextProjector minimal
- Phase C: C.1 ImportGraph (static only) + C.4 Reversibility (REVERSIBLE/IRREVERSIBLE only)
- Phase D: D.1 harness + D.2 minimal property tests + D.4 ≥5 adversarial fixtures (from user stories)
- Phase E: E.1 ContractSchema minimal + E.2 3 seed invariants
- Phase F: F.1 evidence source + F.3 assumption tags (WARN only) + F.4 BLOCKED state
- Phase G: G.10 Baseline+Post (basic diff check)

**L3-L7 deliverables for Phase 1:**
- L3: Full orchestrator for "Python code Change" capability; 3 tool implementations (`read_file`, `edit_file`, `run_tests`); Sonnet-only routing
- L4: Dashboard + CLI for developer persona only (steward/PO/admin deferred)
- L5: GitHub adapter (Issues → Objective; PR creation)
- L6: Deployed on Render.com free tier with Postgres; basic health check
- L7: 3-Task benchmark auto-grader; quality score surfaced in dashboard

**Exit criteria Phase 1 (hard gate):**
- 1 real GitHub Issue → merged PR end-to-end (demo)
- All tests GREEN (unit + property + adversarial + integration)
- Benchmark score ≥ 0.6 on all 3 MVP tasks
- Cost < $2 per Task (measured)
- Latency < 15 min P95 (measured)
- Developer onboarding < 1 hour (1 test user)

### Phase 2 — Horizontal expansion (4-6 weeks)

**Purpose:** widen each layer to cover more scenarios, more personas, more integrations.

Added stages:
- A.5 MCP idempotency (full implementation)
- B.2 CausalEdge backfill + B.3 CausalGraph service + B.5 TimelyDeliveryGate + B.7 SourceConflictDetector + B.8 Actor+Process entities
- C.2 SideEffectRegistry + C.3 ImpactClosure (full)
- D.3 Metamorphic + D.5 FailureMode α-gate + D.6 CritPath
- E.3 Autonomy + E.4 Reachability + E.7 EpistemicProgress + E.8 ScopeBoundary + E.9 Architecture
- F.2 Evidence verifiability + F.5 Root cause + F.6 Challenger + F.10 StructuredTransfer + F.11 CandidateEval + F.12 Debt tracking
- G.1 DataClassification + G.2 ContractViolation + G.3 Metrics + G.4 Rule Lifecycle + G.9 ProofTrail

**L3-L7 expansion:**
- L3: 10+ tool implementations; all 3 model tiers (Haiku/Sonnet/Opus); challenger model routing
- L4: Steward + PO + admin personas; full dashboard
- L5: GitLab adapter; Linear + Jira issue adapters; Slack notifications
- L6: Multi-tenant mode; SLA monitoring; security audit pass
- L7: 15-Task benchmark suite; weekly quality trend report; feedback loop wired

**Exit criteria Phase 2:**
- 4 personas can complete their respective flows
- Benchmark ≥ 0.7
- Cost < $1 per Task (optimized)
- SLA 99% measured over 2 weeks
- First paying customer design-partner agreement signed

### Phase 3 — Depth + edge cases (6-8 weeks)

**Purpose:** strengthen every layer against production reality.

Added stages:
- B.6 SemanticRelationTypes (REJECT mode via G.9 promotion)
- F.7/F.8/F.9 SR-1/SR-2/SR-3
- G.5 Steward + G.6 11 artifacts + G.7 Adaptive Rigor + G.8 Snapshot + G.11 ErrorPropagation

**Per-layer hardening:**
- L3: Cost optimization (prompt caching), failure recovery edge cases, parallel tool calls
- L4: Accessibility, mobile, i18n
- L5: Deployment hooks, custom webhook, enterprise OAuth (SAML)
- L6: Multi-region, DR procedures tested
- L7: Benchmark expanded to 30 Tasks; adversarial benchmark (intentionally broken inputs)

**Testing adjusted:**
- Mutation smoke on all critical modules (D.5 T4 generalized)
- Property test coverage ≥ 80% of VerdictEngine rules
- Adversarial fixtures ≥ 30 (PRACTICE_SURVEY + production incidents)
- Soak test: 48h continuous load test weekly
- Concurrency test: 20 concurrent Executions (per AIOS concurrency concern)

**Exit criteria Phase 3:**
- Benchmark ≥ 0.8
- All 57 stages implemented + test-green
- G_GOV all 23 checks green on demo project
- Soak test: zero crashes in 48h

### Phase 4 — Production readiness (4-6 weeks)

**Purpose:** Deployable per Deployability theorem.

Per `Deployable ⇔ Closure(System) ∧ Quality ≥ threshold ∧ Cost ≤ budget ∧ UX acceptable ∧ Operations stable`:

| Gate | Criterion | Status check |
|---|---|---|
| Closure | All 7 layers + 14 connectivity tests GREEN | `make verify-closure` |
| Quality | Benchmark ≥ 0.8; user feedback > 80% positive | L7 reports |
| Cost | < $1 P50 per Task | L7.e tracking |
| UX | Onboarding < 30 min; 5-user interview NPS > 30 | Survey data |
| Operations | SLA 99.5%; MTTR < 1h; zero data loss in 30-day soak | L6 metrics |

**Launch prerequisites:**
- Security audit (external)
- Load test to 10x expected launch traffic
- Runbooks for all CRITICAL incident types
- Customer support flow (Zendesk/Intercom)
- Legal: ToS, privacy policy, DPA template

**Exit criteria Phase 4:**
- All Deployability gates GREEN
- 3 design-partner customers using daily
- No P0 bugs in backlog

### Calendar estimate

| Phase | Duration | Cumulative |
|---|---|---|
| 0 Foundations | 2-3 weeks | 3 weeks |
| 1 Vertical MVP | 3-4 weeks | 7 weeks |
| 2 Horizontal | 4-6 weeks | 13 weeks |
| 3 Depth | 6-8 weeks | 21 weeks |
| 4 Production | 4-6 weeks | **27 weeks (~6.5 months)** |

**With solo-developer + 1 AI pair:** 27 weeks realistic; could be 35-40 with interruptions.
**With 2-3 dedicated engineers + AI:** 16-20 weeks.
**This assumes no major pivots.** Pivot risk high at Phase 1 exit; re-evaluate scope after first paying customer signal.

---

## 8. Recovery paths per failure mode (per Closure theorem requirement)

`∀ failure f : ∃ recovery_path(f)`:

| Failure class | Recovery path |
|---|---|
| LLM timeout | Retry × 2; if persistent → Execution BLOCKED + notify user |
| LLM malformed output | Format-hint retry × 3; then REJECTED → user re-executes with different model |
| Tool call failure (non-critical) | Log + continue; Finding emitted |
| Tool call failure (critical: git write, file write) | Execution REJECTED + rollback partial state |
| Gate validation failure | REJECTED with reason; author addresses; re-execute |
| DB connection loss | Retry via SQLAlchemy pool; if persistent → health check fails → deployment rollback |
| Integration webhook failure (e.g., GitHub API down) | Retry with backoff; 10+ failures → Finding + manual retry endpoint |
| Deployment failure post-APPLIED | C.4 Rollback for REVERSIBLE; Steward incident for IRREVERSIBLE per ADR-021 |
| Quality score below threshold | Re-execute with feedback; if persistent → capability demoted per E.3 |
| Cost/budget exceeded | budget_guard halt + Finding; user raises budget or narrows scope |
| SLA breach | Alert oncall; Steward incident review; post-mortem updates runbooks |
| Security incident (Confidential+ leak) | G.1 kill-criteria: system-wide BLOCKED; Steward sign-off for recovery |
| Data corruption | Point-in-time Postgres restore per L6.e; RPO = 1h |
| Forge service outage | Status page; failover region (Phase 3+); graceful degradation |

Every recovery path has its own test in `tests/recovery/` directory.

---

## 9. Theorem compliance matrix for this plan

| Theorem requirement | How this plan satisfies |
|---|---|
| **Closure(System) = true** | All 7 layers L1-L7 specified in §3 with deliverables + exit criteria |
| **∀ L : exists(L) ∧ connected(L)** | §4 Layer Connectivity Matrix specifies all 14 cross-layer interactions + tests |
| **specified ∧ executable ∧ observable ∧ verifiable** | Every component has: spec (§3), implementation plan (§7), monitoring hooks (L6), tests (§2) |
| **Execution Continuity** | §5 maps every step of Request→...→NextIteration to executable + recoverable |
| **Recovery path ∀ failure** | §8 enumerates recovery paths per failure class |
| **Real Value > threshold** | §6 concrete MVP targets for 5 Value components |
| **Quality ≥ acceptable** | §3 L7 defines benchmark + score thresholds enforced at F.11 |
| **valid(LLM_call) structured+bounded+defined+constrained** | §3 L3.a-f covers all 4 LLM-call properties |
| **Cost + Time ≤ budget + SLA** | §3 L7.e + §6 targets; budget_guard + latency SLO |
| **Deployable iff all gates pass** | §7 Phase 4 explicit Deployability gate check |
| **Edge-focused regression tests** | §2.3 fault-detection optimization: mutation-survivor gaps + incident seeds + boundary values + adversarial |
| **Tests per element** | §2.1 ≥3 tests per code element at creation |
| **Tests after each stage** | §2.4 CI invocation discipline |
| **No missing layer** | §1 Closure compliance map: all 7 layers planned to FULL state |

---

## 10. What I will produce (execution order)

When you confirm "go":

### Week 1 (Phase 0 start)

**Day 1-2:**
- `platform/docs/PLAN_LLM_ORCHESTRATION.md` (L3 spec full)
- `platform/docs/UX_DESIGN.md` (L4 spec full)
- `platform/docs/INTEGRATIONS.md` (L5 spec full)
- `platform/docs/OPERATIONS.md` (L6 spec full)
- `platform/docs/QUALITY_EVALUATION.md` (L7 spec full)
- `platform/docs/MVP_SCOPE.md` (Phase 1 MVP definition)
- `platform/docs/PRODUCT_VISION.md` (ICP + value prop + business model)

**Day 3-5:**
- L2 Full implementation: VerdictEngine + GateRegistry + RuleAdapter + event bus + full test suite
- L3 Minimal: prompt template engine + 5 tools + model router + tests
- L4 Minimal: CLI skeleton + 1 web page + tests
- L5 Minimal: git read adapter + tests
- L6 Minimal: docker-compose + logging + tests
- L7 Minimal: metrics collector + 3 benchmark Tasks + tests

### Week 2-3 (Phase 0 complete)
- All 14 layer-connectivity contract tests GREEN
- Alembic migrations for all planned entities
- CI pipeline runs full suite per PR
- Local dev environment fully functional

### Week 4-7 (Phase 1 vertical slice)
- GitHub Issues → merged PR demo
- First user test
- Benchmark ≥ 0.6
- Cost + latency targets met

### Beyond
Per §7 phase plan.

---

## 11. Immediate next decision

User choice on start mode:

### Option A — Full parallel burn (recommended per user stated preference)
I start Phase 0 immediately: produce 7 spec documents (L3-L7 + MVP + Product) in sequence during Week 1, then begin layer implementation Week 2. Each commit includes tests.

### Option B — Spec-first, code-second
Produce all 7 specs first (3-5 days), then code Phase 0 foundations.

### Option C — Code-first, spec-alongside
Start L2 + L3 code immediately using current plan corpus as spec. Fill in spec documents during implementation.

### Option D — Narrow to MVP
Skip full layer specs; pick narrow MVP scenario; implement only what's needed for that MVP; expand after first user test.

**My recommendation:** **Option A** per user's "wszystko realizowane na raz" preference, but with vertical-slice discipline within each phase — deliver end-to-end working slice before widening. This maximizes test-ability and feedback velocity.

---

## 12. Status + disclosures

**Status:** DRAFT — this plan itself requires distinct-actor review per ADR-003 before driving implementation decisions.

**Solo-verifier disclosure:** AI-authored; same actor as plan corpus. All analytical conclusions [ASSUMED: agent-synthesis, requires review]. Only direct file citations carry [CONFIRMED].

**Versioning:**
- v1 (2026-04-24) — initial DRAFT covering all 7 layers + 5 phases + testing discipline + theorem compliance.
