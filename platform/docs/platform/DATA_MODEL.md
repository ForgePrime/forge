# Forge Platform — Data Model

> **Status:** DRAFT per [`../decisions/ADR-003`](../decisions/ADR-003-human-reviewer-normative-transition.md). Point-in-time snapshot 2026-04-23. For current truth read `app/models/*.py`.

**Purpose:** enumerate 30 entities, their relationships, and DB-level invariants. Grouped by CGAID Layer (per [`../FRAMEWORK_MAPPING.md §4`](../FRAMEWORK_MAPPING.md)).

**Source of truth:** [`platform/app/models/*.py`](../../app/models/) — this document mirrors at point-in-time.

## 1. Entity overview

```
Layer 2 (Tooling)          Layer 3 (Delivery)              Layer 4 (Control)
─────────────────          ──────────────────              ────────────────
MicroSkill                 Project                          Decision
Guideline                  Objective                        OutputContract
Knowledge                  ├── KeyResult                    ContractRevision
AIInteraction              └── ObjectiveReopen              ProjectHook
LLMCall                    Task                             HookRun
                           ├── AcceptanceCriterion          AuditLog
Meta                       ├── task_dependencies
────                       Execution
Organization               ├── ExecutionAttempt
├── Membership             ├── PromptSection
User                       └── PromptElement
Lessons                    OrchestrateRun
Comment                    Change
Webhook                    Finding
                           TestRun
```

Total: **30 tables.**

Phase A–G add: `evidence_sets`, `idempotent_calls`, `verdict_divergences`, `causal_edges`, `context_projections`, `invariants`, `autonomy_states`, `failure_modes`, `data_classifications`, `contract_violations`, `rules` — 11 new (total would be 41 post-Phase G).

## 2. Layer 3 (Delivery) — core

### Project

Table: `projects`. Central entity; owns all work.

| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| organization_id | FK → organizations.id | multi-tenant isolation |
| slug | str unique | URL-friendly id |
| name | str | display name |
| description | text | |
| contract_md | text | per-project operational contract addition |
| autonomy_level | str `∈ {L1..L5}` | per `autonomy.py` |
| autonomy_promoted_at | timestamp | last promotion |
| config | JSONB | veto_paths, budget_task_usd, budget_run_usd, warn_at_pct |

Children: Objectives, Tasks, Decisions, Findings, Knowledge, MicroSkills, Guidelines.

### Objective + KeyResult

Tables: `objectives`, `key_results`, `objective_dependencies`, `objective_reopens`.

**Objective** ([`app/models/objective.py`](../../app/models/objective.py)):
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| project_id | FK | |
| external_id | str | O-NNN |
| title | str | |
| description | text | |
| status | str `∈ {DRAFT, ACTIVE, ACHIEVED, ABANDONED}` | |
| priority | int | default 3 |
| autonomy_optout | bool | watchlist opt-out |
| test_scenarios | JSONB list | `{id, label, kind ∈ {edge_case, failure_mode, security, regression}, description}` — parallel taxonomy to AC scenario_type |
| challenger_checks | JSONB list | per develop task |
| kb_focus_ids | int[] | narrowed Knowledge scope |

**KeyResult** (same file):
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| objective_id | FK | |
| position | int | ordered |
| kr_type | str `∈ {numeric, descriptive}` | CHECK |
| description | str | |
| target_value | float or null | for numeric |
| current_value | float or null | |
| status | str `∈ {NOT_STARTED, IN_PROGRESS, ACHIEVED, BLOCKED}` | |
| measurement_command | str or null | Phase A kr_measurer.py |

Invariant: `kr_type='numeric'` ⇒ `target_value NOT NULL`.

**ObjectiveReopen**: audit trail for objectives re-opened post-achievement (stability signal in autonomy).

### Task + AcceptanceCriterion

Tables: `tasks`, `task_dependencies`, `acceptance_criteria` ([`app/models/task.py`](../../app/models/task.py)).

**Task** columns:
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| project_id | FK | |
| external_id | str | T-NNN |
| name | str | |
| description | text nullable | |
| instruction | text nullable | |
| type | str `∈ {feature, bug, chore, investigation, analysis, planning, develop, documentation}` | CHECK |
| status | str `∈ {TODO, CLAIMING, IN_PROGRESS, DONE, FAILED, SKIPPED}` | CHECK |
| scopes | str[] | for scope-filtered guidelines |
| origin | str nullable | |
| produces | JSONB | **contract shape** — Phase E.1 makes this typed `ContractSchema` |
| alignment | JSONB | |
| exclusions | str[] nullable | |
| ceremony_level | str `∈ {LIGHT, STANDARD, FULL}` | auto-detected per `execute.py:53-60` |
| agent | str nullable | |
| started_at / completed_at | timestamp | |
| started_at_commit | str | git rev at start |
| skip_reason / fail_reason | text | |
| requirement_refs | str[] | SRC-NNN tokens per `plan_gate.py` |
| completes_kr_ids | str[] | for auto KR update |
| origin_finding_id | FK nullable | Finding → Task causal edge |
| risks | JSONB list | `{risk, mitigation, severity, owner}` |

Invariants:
- `task_has_content`: `instruction IS NOT NULL OR description IS NOT NULL`.
- `no_self_dep` on `task_dependencies`: `task_id != depends_on_id`.
- `type IN ...` CHECK.
- `status IN ...` CHECK.

**task_dependencies** association table: `(task_id, depends_on_id)` PK.

**AcceptanceCriterion** columns:
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| task_id | FK | cascade delete |
| position | int | ordered |
| text | text | min length 20 (CHECK) |
| scenario_type | str `∈ {positive, negative, edge_case, regression}` | CHECK — Phase F extends to 9 per ADR-001 |
| verification | str `∈ {test, command, manual}` | CHECK |
| test_path | str nullable | e.g. `tests/test_x.py::test_y` |
| command | str nullable | shell command |
| source_ref | str nullable | SRC-NNN or objective ref; NULL → "INVENTED BY LLM" badge |
| last_executed_at | timestamp nullable | B1 trust-debt counter |
| source_llm_call_id | FK nullable | reasoning trace |

### Execution + ExecutionAttempt + Prompt*

Tables: `executions`, `execution_attempts`, `prompt_sections`, `prompt_elements` ([`app/models/execution.py`](../../app/models/execution.py), [`app/models/execution_attempt.py`](../../app/models/execution_attempt.py)).

**Execution** columns:
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| task_id | FK | |
| agent | str | |
| status | str `∈ {PROMPT_ASSEMBLED, IN_PROGRESS, DELIVERED, VALIDATING, ACCEPTED, REJECTED, EXPIRED, FAILED}` | CHECK; Phase F adds `BLOCKED` |
| attempt_number | int | 1-based |
| mode | str nullable `∈ {direct, crafted}` | E1 |
| crafter_call_id | FK nullable | for crafted mode |
| prompt_text | text | what AI received |
| prompt_hash | str | SHA256 |
| prompt_meta | JSONB | section stats |
| contract | JSONB | required output shape |
| contract_version | int | |
| delivery | JSONB | what AI returned |
| delivered_at | timestamp | |
| validation_result | JSONB | |
| validated_at | timestamp | |
| lease_expires_at | timestamp | |
| lease_renewals | int | |
| completed_at | timestamp | |

Relations: Task (belongs to), PromptSection[], PromptElement[].

**ExecutionAttempt** — per-resubmit tracking (per IMPLEMENTATION_TRACKER.md:28):
- `reasoning_hash` — SHA256 of reasoning for resubmit detection.
- Same hash across attempts → `resubmit.identical_reasoning` WARNING.

**PromptSection** (prompt assembly audit):
| Column | Notes |
|---|---|
| execution_id | FK cascade |
| section_name | P0..P7, reminder, operational_contract |
| priority | for truncation ordering |
| included | bool |
| exclusion_reason | why excluded |
| rendered_text | text |
| char_count | |
| position | in final prompt |
| element_count | |

**PromptElement** (per-item in a section):
| Column | Notes |
|---|---|
| execution_id | FK cascade |
| section_id | FK to PromptSection |
| source_table | what model row it came from |
| source_id | |
| source_external_id | |
| source_version | |
| content_snapshot | text — the literal content |
| included | bool |
| selection_reason / exclusion_reason | |
| scope_details / budget_details | JSONB |
| position | |
| char_count | |

Together: Execution + PromptSection + PromptElement form a **complete audit trail of what the agent saw**.

### Change, Finding, TestRun, OrchestrateRun

**Change** ([`app/models/change.py`](../../app/models/change.py)):
| Column | Notes |
|---|---|
| id | PK |
| project_id | FK |
| execution_id | FK nullable |
| external_id | C-NNN |
| task_id | FK |
| file_path | |
| action | `∈ {create, edit, delete, rename, move}` CHECK |
| summary / reasoning | |
| lines_added / lines_removed | |

Phase C adds: `reversibility_class`, `rollback_ref`.

**Finding** ([`app/models/finding.py`](../../app/models/finding.py)):
| Column | Notes |
|---|---|
| id | PK |
| project_id | FK |
| execution_id | FK nullable |
| external_id | F-NNN |
| type | `∈ {bug, improvement, risk, dependency, question, smell, opportunity, gap, lint}` |
| severity | `∈ {HIGH, MEDIUM, LOW, critical, CRITICAL}` |
| title / description | |
| file_path / line_number | nullable |
| evidence | text nullable |
| suggested_action | |
| status | `∈ {OPEN, APPROVED, DEFERRED, REJECTED, DISMISSED, ACCEPTED}` |
| triage_reason / triage_by | |
| created_task_id | FK nullable — Task created from this Finding |
| dismissed_reason / dismissed_at | B1 dismissal audit |
| source_llm_call_id | FK nullable — reasoning trace |

Phase D ties `failure_mode_id` (when G4 FailureMode entity exists).

**TestRun**: per-Execution pytest runs (for Phase A test_runner).

**OrchestrateRun**: multi-task pipeline runs:
- `tasks_attempted`, `tasks_done`, `tasks_failed`, `tasks_skipped`.
- `status ∈ {RUNNING, DONE, INTERRUPTED, FAILED}`.

### Decision

Table: `decisions` ([`app/models/decision.py`](../../app/models/decision.py)):
| Column | Notes |
|---|---|
| id | PK |
| project_id | FK |
| execution_id / task_id | FK nullable |
| external_id | D-NNN |
| type | str (e.g. `root_cause`, `adr`, `trade_off`, `risk`) |
| issue / recommendation / reasoning | text |
| status | `∈ {OPEN, CLOSED, DEFERRED, ANALYZING, MITIGATED, ACCEPTED}` |
| severity / confidence | str nullable |
| alternatives_considered | JSONB — Phase F P21 requires ≥ 2 for type=root_cause |
| resolution_notes | |

## 3. Layer 3 — support entities

### Knowledge

Table: `knowledge` ([`app/models/knowledge.py`](../../app/models/knowledge.py)):
| Column | Notes |
|---|---|
| id | PK |
| project_id | FK |
| external_id | SRC-NNN |
| category | e.g. `source-document`, `feature-spec`, `requirement` |
| title | |
| content | text |
| source_ref | text — tokenizable SRC-NNN reference |
| scope_tags | str[] |
| version | int |

## 4. Layer 4 (Control)

### OutputContract + ContractRevision

Defines per `(task_type, ceremony_level)` what delivery must contain.

**OutputContract**:
| Column | Notes |
|---|---|
| task_type | e.g. "feature", "*" wildcard |
| ceremony_level | `∈ {LIGHT, STANDARD, FULL, *}` |
| version | int |
| active | bool |
| definition | JSONB — required fields, min_length, reject_patterns, etc. |

Seed: 4 rows `(*,*), (feature,STANDARD), (feature,FULL), (bug,LIGHT)`.

Lookup fallback chain (`execute.py:42`): `(exact, exact)` → `(*, exact)` → `(exact, *)` → `(*, *)`.

**ContractRevision**: versioning of OutputContract changes.

### ProjectHook + HookRun

Automation trigger model (not Claude Code hooks — application-level).

**ProjectHook**:
| Column | Notes |
|---|---|
| project_id | FK |
| trigger | event name (e.g. "execution.accepted") |
| condition | str optional filter |
| action | what to execute (URL, command) |

**HookRun**: execution log per hook firing.

### AuditLog

Cross-cutting audit trail.
| Column | Notes |
|---|---|
| project_id | FK nullable (for cross-project events) |
| entity_type / entity_id | what was touched |
| action | what happened |
| actor | who |
| kwargs | JSONB details |

Phase G5 adds `reviewed_by_steward_id`.

## 5. Layer 2 (Tooling)

### MicroSkill

Table: `micro_skills`. 10 seeded.
| Column | Notes |
|---|---|
| code | unique id (e.g. `impact_aware`) |
| category | `reputation | technique | verification` |
| name / description | |
| body | text — prompt fragment injected per scope tags |
| version | int |
| active | bool |

### Guideline

Must-follow rules, scope-filtered.
| Column | Notes |
|---|---|
| external_id | G-NNN |
| severity | MUST / SHOULD |
| scope_tags | str[] |
| content | text |
| applies_to | JSONB |

### AIInteraction + LLMCall

**AIInteraction**: outer-level "chat turn" or "tool invocation".
**LLMCall**: actual HTTP call to LLM provider.
| LLMCall column | Notes |
|---|---|
| provider | e.g. "anthropic" |
| model | e.g. "claude-opus-4.7" |
| prompt_hash | |
| input_tokens / output_tokens / cost_usd | |
| latency_ms | |
| status | SUCCESS / FAILED |
| error | text nullable |

Foundation for Metric 5 (skill change outcome) and CONTRACT §4.2 subagent tracking.

### Lessons

Anti-pattern catalog. Self-seed from `lessons.py:seed_self_anti_patterns` at startup.
| Column | Notes |
|---|---|
| title / description | |
| pattern | identifier |
| remediation | |
| seeded_from | source |

## 6. Meta

### Organization + User + Membership

Multi-tenant.
| Organization | User | Membership |
|---|---|---|
| id, slug, name | id, email, password_hash, api_key | org_id, user_id, role |

Role ∈ `{viewer, editor, owner}`.

### Comment

Threaded comments on entities (Objective, Task, Finding).

### Webhook

Outbound webhook configuration per project.

## 7. Relationship map (high level)

```
Organization
  └── Membership ─► User
  └── Project
       ├── Knowledge                              (Layer 2)
       ├── MicroSkill, Guideline                  (Layer 2)
       ├── Objective ── KeyResult                 (Layer 3: planning)
       │     └── ObjectiveReopen
       ├── Task                                   (Layer 3: work unit)
       │     ├── AcceptanceCriterion
       │     ├── task_dependencies  (self)
       │     ├── Executions                       (Layer 3: run)
       │     │     ├── ExecutionAttempt
       │     │     ├── PromptSection ── PromptElement
       │     │     ├── Changes
       │     │     ├── Findings
       │     │     ├── Decisions
       │     │     └── TestRuns
       │     └── origin_finding_id ─► Finding
       ├── OrchestrateRun                         (Layer 3: batch)
       ├── OutputContract ── ContractRevision     (Layer 4)
       ├── ProjectHook ── HookRun                 (Layer 4)
       ├── Decision                               (Layer 4)
       ├── Finding                                (Layer 3: audit)
       ├── AuditLog                               (Layer 4)
       ├── AIInteraction ── LLMCall               (Layer 2: audit)
       └── Webhook
```

## 8. Cross-cutting invariants (current state — DB-level)

| Invariant | Evidence |
|---|---|
| Every Task has instruction OR description | `task.py:22-25` `task_has_content` CHECK |
| Task cannot depend on itself | `task.py:15` `no_self_dep` CHECK |
| AC text ≥ 20 chars | `task.py:84` `ac_min_length` CHECK |
| AC scenario_type ∈ 4 values | `task.py:86-88` CHECK — Phase F extends to 9 |
| AC verification ∈ 3 values | `task.py:89-92` CHECK |
| Task type in enumerated set | `task.py:26-32` CHECK |
| Task status in enumerated set | `task.py:33-36` CHECK |
| Execution status in enumerated set | `execution.py:14-19` CHECK |
| Decision status in enumerated set | `decision.py:11-15` CHECK |
| Finding type / severity / status in enumerated sets | `finding.py:13-18` CHECK |
| KeyResult kr_type ∈ 2 values | `objective.py:62` CHECK |

Phase E.2 [`../ROADMAP.md §8`](../ROADMAP.md) makes these first-class `Invariant` entities registered per state transition.

## 9. Key invariants NOT yet DB-enforced (Phase A–F deliverables)

| Invariant | Introduced by | When enforced |
|---|---|---|
| Every Decision has ≥ 1 EvidenceSet link | Phase A P16 | Phase A.1 exit |
| Every state transition passes through VerdictEngine | Phase A P7 | Phase A.4 exit |
| EvidenceSet.kind ∈ allowed enum | Phase A, ADR-001-ish for evidence | Phase A.1 |
| Every new Decision/Change/Finding has ≥ 1 CausalEdge | Phase B P14 | Phase B.1 trigger |
| CausalEdge acyclic | Phase B P14 | Phase B.1 trigger + clock constraint |
| Every ACTIVE Objective has reachability_evidence | Phase E.4 P9 | Phase E.4 gate |
| Every HIGH/CRITICAL Decision has steward_sign_off_by | Phase G.5 | Phase G.5 |
| Every Confidential+ Knowledge has DataClassification | Phase G.1 | Phase G.1 |

## 10. Migration path (Phase A–G summary)

Migrations introducing new tables:

| Phase | Tables added |
|---|---|
| A | `evidence_sets`, `idempotent_calls`, `verdict_divergences` |
| B | `causal_edges`, `context_projections` |
| C | (Change column additions: `reversibility_class`, `rollback_ref`) |
| D | `failure_modes` |
| E | `invariants`, `autonomy_states`, (ContractSchema field refactor) |
| F | (Execution column additions: `uncertainty_state`; enum extension on `status` to add `BLOCKED`); (reasoning-structured sub-fields on Execution.delivery) |
| G | `data_classifications`, `contract_violations`, `rules`, (User column: `steward_role`), (Objective column: `business_dod`, `reachability_evidence`) |

Every migration must have idempotent up + reversible down per general [`../ROADMAP.md`](../ROADMAP.md) constraint.

## 11. External references

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — system-level overview.
- [`WORKFLOW.md`](WORKFLOW.md) — how these entities are written/read.
- [`../FORMAL_PROPERTIES_v2.md`](../FORMAL_PROPERTIES_v2.md) — 25 atomic properties, many binding to entities here.
- [`../GAP_ANALYSIS_v2.md`](../GAP_ANALYSIS_v2.md) — which properties this data model satisfies or fails.
- [`../ROADMAP.md`](../ROADMAP.md) — which migration adds which table.
- [`../decisions/`](../decisions/) — ADRs affecting schema (ADR-001 enum extension, future ADRs).
- `app/models/*.py` — source of truth. If this doc diverges, code wins; file a Finding.
