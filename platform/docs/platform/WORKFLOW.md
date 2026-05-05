# Forge Platform — Workflow

> **Status:** DRAFT per [`../decisions/ADR-003`](../decisions/ADR-003-human-reviewer-normative-transition.md). Reference only.

**Purpose:** describes how work flows through Forge end-to-end — from intent to delivered artifact. Maps to CGAID 5 stages (Stage 0 Data Classification + 4 Delivery Stages). Reference for contributors understanding the orchestration model.

## 1. Actors

| Actor | Role |
|---|---|
| **User / Developer** | Drives the session. Creates projects, approves plans, accepts deliverables. |
| **AI Agent (Claude via MCP)** | Executes tasks under contract; produces reasoning + evidence; fills AC verdicts. |
| **Challenger** | Independent AI instance (or human) that verifies the agent's delivery (`challenger.py`). |
| **Reviewer** | Human reviewer for PR + ADR content (per [`../decisions/ADR-003`](../decisions/ADR-003-human-reviewer-normative-transition.md)). |
| **Framework Steward** | Quarterly audit of CGAID compliance (OM §4.5). Not yet staffed for Forge. |
| **Platform** | Deterministic services: `VerdictEngine`, `contract_validator`, `plan_gate`, `coverage_analyzer`. |

## 2. End-to-end flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Stage 0: Data Classification (Phase G1 — not yet implemented)   │
│   Input material → tier (Public/Internal/Confidential/Secret)   │
│   → Routing matrix                                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│ Stage 1: Evidence                                               │
│   Slash commands: /ingest, /analyze, /grill                     │
│   → Knowledge (SRC-NNN) ingested                                │
│   → Inconsistencies + assumptions + unknowns surfaced           │
│   → Open questions escalated                                    │
│   Entity: Knowledge, Finding(kind=inconsistency)                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│ Stage 2: Plan                                                   │
│   /plan → Objective + KeyResult + Task graph + AC              │
│   → Decisions drafted (ADRs)                                    │
│   → Risks surfaced                                              │
│   → Business-Level DoD defined                                  │
│   → Edge-case test plan (scenario_type per AC)                  │
│   Entities: Objective, KR, Task, AC, Decision                   │
│   Gates: plan_gate (requirement_refs), ReachabilityCheck (P9)   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                 APPROVE gate (human)
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│ Stage 3: Build                                                  │
│   GET /execute → claim Task + assemble prompt                   │
│   Agent writes code + produces Execution delivery               │
│   POST /execute/{id}/deliver → validation                       │
│   Gates: contract_validator, test_runner, coverage_analyzer     │
│   Entities: Execution, PromptSection, PromptElement, Change     │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│ Stage 4: Verify                                                 │
│   POST /execute/{id}/challenge → Challenger asks questions     │
│   Human PR review (mandatory)                                   │
│   Business-outcome verification                                 │
│   If green: ACCEPTED → Task.status = DONE                      │
│   Entities: Execution.status ∈ {ACCEPTED, REJECTED}             │
│   Evidence: ExecutionAttempt.reasoning_hash                     │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Detailed per-stage flow

### Stage 0: Data Classification

> **NOT YET IMPLEMENTED.** Tracked in Phase G1 of [`../ROADMAP.md §10`](../ROADMAP.md). Until implemented, Forge is not certified for Confidential+ processing without deployed DLP (deep-risk R-FW-02).

Design (Phase G.1):
1. User uploads / pastes material into a project.
2. `DataClassification` row created (Public / Internal / Confidential / Secret).
3. Routing matrix decides which LLM tier may process (zero-retention required for Confidential+).
4. Provenance marker propagates to downstream `Knowledge`, `EvidenceSet` (Phase A), `Decision`.
5. Steward sign-off required for Confidential+.

### Stage 1: Evidence

**Slash commands:**
- `/ingest <file|url>` — pulls content into `Knowledge`, assigns `SRC-NNN` external id.
- `/analyze <src-id>` — extracts inconsistencies, assumptions, unknowns.
- `/grill <topic>` — forces disambiguation of unclear requirements (from `.ai/commands.md`).

**Entities written:**
- `Knowledge(source_ref='SRC-NNN', scope_tags, content)`
- `Finding(kind='inconsistency'|'assumption'|'unknown', source_llm_call_id)`

**Exit criteria:** no `[UNKNOWN]` carried silently; open questions in `Finding` with triage state OPEN.

**Current state:** `/ingest` + `/analyze` partial (`knowledge.py` model exists, endpoints per [`../archive/GAP_ANALYSIS.md`](../archive/GAP_ANALYSIS.md) — verify in Pre-flight Stage 0.3 smoke test).

### Stage 2: Plan

**Slash commands:**
- `/plan <feature or change>` — anti-shortcut planning (pre-commitment + code reading + phased plan). See `.claude/skills/plan/SKILL.md`.
- `/objective <text>` — creates `Objective` with measurable Key Results.
- `/decide <question>` — opens `Decision` (blocks plan approval if status OPEN).
- `/change-request <scope>` — modifies existing plan; `ImpactDiff` reports bounded delta (Phase C.5).

**Entities written:**
- `Objective(business_dod, reachability_evidence)` — Phase E.4 adds `ReachabilityCheck` gate.
- `KeyResult(kr_type ∈ {numeric, descriptive}, target_value, current_value)`.
- `Task(type, instruction, ceremony_level auto-detected, requirement_refs, completes_kr_ids, risks, produces)`.
- `AcceptanceCriterion(text, scenario_type, verification, test_path|command|source_ref)`.
- `Decision(issue, recommendation, alternatives_considered, severity, confidence, status)`.

**Gates:**
- `plan_gate.validate_plan_requirement_refs` — feature/bug tasks must cite `SRC-NNN` source docs when project has them (P5.3).
- ReachabilityCheck (Phase E.4) — each KR must have ≥ 1 candidate plan.
- `coverage_analyzer` — Knowledge SRC terms must appear in AC (source-term coverage).

**Human APPROVE gate** before Build begins. Implemented as UI step; endpoints that transition Objective → ACTIVE require approval token.

**Ceremony auto-detection** ([`app/api/execute.py:53-60`](../../app/api/execute.py)):
- `chore` / `investigation` → `LIGHT`
- `bug` with `ac_count ≤ 3` → `LIGHT`
- `feature` with `ac_count ≤ 3` → `STANDARD`
- default → `FULL`

Per [`../decisions/ADR-002`](../decisions/ADR-002-ceremony-level-cgaid-mapping.md), these map 1:1 to CGAID tiers: LIGHT → Fast Track, STANDARD → Standard, FULL → Critical.

### Stage 3: Build

**Entry:** Task in `TODO` state; objective approved; plan approved.

**Flow:**
1. Agent calls `GET /execute?project=<slug>&agent=<name>` → Forge claims next available Task (FIFO with dependency respect), transitions Task → `IN_PROGRESS`, creates `Execution` record.
2. Forge assembles prompt in 7 sections (P0–P7) via `prompt_parser.py`:
   - **P0** Reputation frame
   - **P1** Task instruction + AC
   - **P2** Micro-skills + Knowledge context + scenario stubs
   - **P3** (Knowledge context — shared with P2)
   - **P4** SHOULD guidelines (truncatable under budget)
   - **P5** Dependency context (produces + changes from deps)
   - **P6** Active risks
   - **P7** Business context (Objective + KRs)
   - **Reminder** section (recency bias)
   - **Operational contract** (LAST — CONTRACT.md mirror)
3. Prompt returned to agent with `contract` (required output shape) and lease expiration.
4. Agent writes code, runs tests, produces delivery:
   ```json
   {
     "reasoning": "<why + what + impact with [CONFIRMED]/[ASSUMED]/[UNKNOWN] tags>",
     "changes": [{file_path, action, lines_added, lines_removed, summary, reasoning}],
     "ac_evidence": [{ac_index, verdict, evidence, scenario_type}],
     "decisions": [{type, issue, recommendation, alternatives_considered}],
     "findings": [...],
     "assumptions": [...],
     "impact_analysis": "..."
   }
   ```
5. Agent heartbeats (`POST /execute/{id}/heartbeat`) to extend lease if slow.
6. Agent calls `POST /execute/{id}/deliver` → Forge validates.

**Validation chain:**
- `contract_validator.py` — 14+ checks: reasoning min_length, file references, must_contain_why, AC evidence per AC, composition (≥ 1 negative/edge_case PASS), copy-paste detection, operational contract presence, resubmit detection (2 warnings on identical reasoning hash).
- `test_runner.py` — Phase A: Forge runs `pytest` against paths referenced in AC; doesn't trust completion_claims.
- `coverage_analyzer.py` — source-term coverage of Knowledge SRC.

**Post Phase A (`VerdictEngine.commit`):** all rules evaluated together; one verdict; state transition through GateRegistry.

### Stage 4: Verify

**Automatic:**
- `POST /execute/{id}/challenge` → spawns Challenger agent (independent LLM instance) which asks 6 auto-generated questions about the delivery based on focus areas (ac_verification, impact_analysis, edge_cases).
- Challenger report with pass/fail per focus area.

**Manual:**
- Human PR review (mandatory per MANIFEST Principle 7).
- Business-outcome verification (observed in target environment).

**Accept:**
- If all green: `Execution.status = ACCEPTED`, `Task.status = DONE`, KR auto-updates (if task `completes_kr_ids` non-empty), `Change` rows persisted, ADRs exported to project `.ai/decisions/`, Handoff exported.

**Reject:**
- `Execution.status = REJECTED`; fix_report returned to agent; agent may resubmit (triggers resubmit detection).

**Fail:**
- `POST /execute/{id}/fail` → Task back to TODO (or → FAILED if unrecoverable).

## 4. MCP tools

From `platform/mcp_server/server.py` — 6 tools for Claude Code integration:

| Tool | Purpose | State side-effect |
|---|---|---|
| `forge_execute(project, agent, lean)` | Claim + assemble prompt | Task→IN_PROGRESS; Execution created |
| `forge_deliver(reasoning, ac_evidence, changes, decisions, findings, ...)` | Submit + validate | Execution→ACCEPTED/REJECTED; Task→DONE/TODO |
| `forge_challenge(execution_id, challenger_agent)` | Spawn challenger | Challenger report recorded |
| `forge_fail(execution_id, reason)` | Give up | Execution→FAILED; Task→FAILED or TODO |
| `forge_decision(type, issue, recommendation, ...)` | Record decision | Decision row |
| `forge_finding(type, severity, title, description, ...)` | Report finding | Finding row |

Phase A adds `idempotency_key` to mutating tools (P1 Idempotence).

## 5. State machines

### Task lifecycle

```
TODO ──────► CLAIMING ──────► IN_PROGRESS ──────► DONE
   ▲                              │   │
   │                              │   ▼
   │                              └─► FAILED
   │                                   │
   └─────────────── retry ◄────────────┘
   │
   │  ┌─► SKIPPED (explicit skip with reason)
   └──┘
```

### Execution lifecycle

```
PROMPT_ASSEMBLED ─► IN_PROGRESS ─► DELIVERED ─► VALIDATING ─► ACCEPTED
                        │             │             │
                        ▼             ▼             ▼
                     FAILED        REJECTED     REJECTED
                        ▲                          │
                   EXPIRED ◄─ lease expired        │
                                                   └─► (resubmit path)
```

Phase F adds `BLOCKED` state (P20 Uncertainty blocks execution).

### Decision lifecycle

```
OPEN ─► ANALYZING ─► CLOSED
  │                    │
  ▼                    ▼
DEFERRED          ACCEPTED | MITIGATED
```

OPEN decisions **block** plan approval for tasks that reference them via `blocked_by_decisions` (per root CLAUDE.md — implementation of this linkage is tracked in Phase A).

### Finding lifecycle

```
OPEN ─► APPROVED ─► (creates Task)
  │
  ├─► DEFERRED
  │
  ├─► REJECTED
  │
  └─► DISMISSED
```

## 6. Slash commands

Per `app/services/slash_commands.py`:

| Command | Purpose | Reference |
|---|---|---|
| `/plan <feature>` | Anti-shortcut planning | `.claude/skills/plan/` |
| `/ingest <src>` | Ingest source material | Stage 1 |
| `/analyze <src>` | Extract inconsistencies | Stage 1 |
| `/grill <topic>` | Force disambiguation | Stage 1 |
| `/objective <text>` | Create Objective + KRs | Stage 2 |
| `/decide <question>` | Open Decision (blocks until CLOSED) | Stage 2 |
| `/change-request <scope>` | Modify approved plan | Stage 2 |
| `/run` | Execute next available Task | Stage 3 |
| `/review` | Request reviewer action | Stage 4 |
| `/risk` | Deep-risk audit | cross-cutting |
| `/deep-verify <artifact>` | Verify self-reported evidence | cross-cutting |

Commands produce structured output with evidence tags (`[CONFIRMED]` / `[ASSUMED]` / `[UNKNOWN]`) per CONTRACT §B.

## 7. Per-mode work characteristics

Per [`../FORMAL_PROPERTIES_v2.md §P11`](../FORMAL_PROPERTIES_v2.md) diagonalizability, the 6 modes have distinct work characteristics:

| Mode | Input | Output | Typical latency | Concurrency |
|---|---|---|---|---|
| Planning | user intent + Knowledge | Objective, KR, Task, AC, Decision | minutes (LLM) | bounded per project |
| Evidence | raw material | Knowledge, Finding, EvidenceSet | seconds (extraction) | parallelizable |
| Execution | Task + prompt | Execution delivery | minutes-hours (LLM + test_runner) | per-Task parallel, per-project serialized |
| Validation | Delivery | Verdict + ContractViolation | seconds (deterministic) | parallelizable |
| Governance | Steward review, audit | AuditLog, steward_sign_off | human-scale | low |
| Autonomy | Q_n signals | AutonomyState, scope promotion | scheduled (daily/weekly) | 1 |

## 8. Per-role workflows

### Developer / Implementer

1. Create project (`/ui/signup` → project).
2. `/ingest` requirements.
3. `/plan <feature>` → get Objective + Tasks.
4. Approve plan in UI.
5. `/run` → agent executes tasks.
6. Accept deliveries one-by-one or bulk.
7. Monitor `/metrics` for run health.

### Reviewer

1. Review PR in GitHub.
2. Check against `AC.verification` evidence (test/command/manual).
3. If PR from Forge orchestrator: validate `Assisted-by: Forge` trailer + `[CONFIRMED]/[ASSUMED]/[UNKNOWN]` tags.
4. Approve / Request changes.

### Framework Steward (quarterly)

1. Read `DEEP_RISK_REGISTER.md` — status updates.
2. Audit CONTRACT §4.4 clauses 1–8 on `contract_validator.py` + `prompt_parser.py`.
3. Audit 11 CGAID artifacts presence.
4. Review Metric 4 (contract violations disclosed vs detected) trend.
5. Sign off on ADR-003 promoted documents.
6. Flag kill-criteria candidates.

### Auditor / external reviewer

1. Read [`../README.md`](../README.md) §Full reading path.
2. Re-verify evidence in [`../GAP_ANALYSIS_v2.md`](../GAP_ANALYSIS_v2.md) by own grep.
3. Audit `CausalEdge` graph for acyclicity + justification completeness.
4. Cross-reference `AuditLog` events with `Execution` state changes.
5. Produce review record in [`../reviews/`](../reviews/).

## 9. Cross-references

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — stack + middleware + lifespan.
- [`DATA_MODEL.md`](DATA_MODEL.md) — 30 entities + invariants.
- [`ONBOARDING.md`](ONBOARDING.md) — first-contribution tutorial using this workflow.
- [`../ROADMAP.md`](../ROADMAP.md) — phases that will implement missing pieces (VerdictEngine, CausalEdge, Stage 0, etc.).
