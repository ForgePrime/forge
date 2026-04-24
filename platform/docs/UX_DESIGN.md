# UX_DESIGN.md — L4 User Experience Specification

**Status:** DRAFT — pending distinct-actor review per ADR-003.
**Date:** 2026-04-25
**Depends on:** PLAN_LLM_ORCHESTRATION (L3 produces costs + routing audit consumed by dashboards), PLAN_GATE_ENGINE + PLAN_MEMORY_CONTEXT + PLAN_CONTRACT_DISCIPLINE + PLAN_GOVERNANCE (entity surfaces).
**Source spec:** MASTER_IMPLEMENTATION_PLAN §3 L4; MVP_SCOPE.md §L4 (developer-only at MVP); PRODUCT_VISION.md §3 ICP.
**Scope:** developer + tech-lead + compliance-officer + executive personas. MVP scope is **developer-only**; tech-lead onboarding wireframed but deferred to Phase 2; compliance + executive scaffolded but deferred to Phase 3.

> **Known unverified claim (CONTRACT §A.6):** UX correctness is empirical, not deterministic. This doc specifies *structure* (personas, flows, components, error messages), not pixel-level visual design. Pixel-level designs require Figma + design partner review (deferred to Phase 1 mid-sprint per MVP_SCOPE §validation plan). Onboarding-time SLA (<1h per MVP success criteria) is verified by 5 design-partner runs, not by this doc alone.

---

## 1. Personas (4 — MVP scope: persona 1 only)

### Persona 1: Developer (MVP — full coverage)

**Profile:** Backend engineer, 3-10 years experience, primary language Python (MVP) or TypeScript/Go (post-MVP). Works on a small-to-medium service (<10k LOC per MVP_SCOPE). Uses GitHub for PRs, has CLI muscle memory, prefers structured CLI output to GUIs for debug, wants GUI for review/audit.

**Job-to-be-done:** "I have an Issue describing a small behavior change. I want Forge to propose code, run tests, and open a PR. I review the diff + evidence trail and merge."

**Pain it removes (vs current Cursor/Copilot/Devin):**
- Evidence trail per Change → no manual copy-pasting commit context.
- Tests run pre-PR → no surprise CI failures.
- Ambiguity surfaced upfront → no halfway-implemented features needing rework.
- Compliance-grade audit log → no separate documentation pass.

**Surfaces consumed:**
- CLI: `forge init`, `forge objective show`, `forge execute`, `forge status`, `forge audit`.
- Web: `/`, `/projects/{slug}`, `/executions/{id}`.
- GitHub: PR description with evidence trail (auto-generated).

### Persona 2: Tech Lead (Phase 2 — wireframed, deferred)

**Profile:** Senior engineer or staff/principal level, 5-15 years. Reviews PRs from team, sets quality bar, owns technical debt budget, runs sprint planning.

**Job-to-be-done:** "I want to see what Forge is doing across the team, where it's struggling, where I need to override. I want to see autonomy levels, rule-prevention metrics, and override the routing for high-risk changes."

**MVP gap:** UI for autonomy dashboard, rule-retirement candidate review, Steward sign-off queue. Wireframed in §5 below; implementation deferred.

### Persona 3: Compliance Officer (Phase 3 — scaffolded, deferred)

**Profile:** Internal audit, security, or regulatory affairs. Non-engineer or limited-engineer.

**Job-to-be-done:** "Generate quarterly audit report showing all Decisions, EvidenceSets, BLOCKED Executions, Steward sign-offs, and CONTRACT violations. Show me what was changed, why, and who signed off."

**MVP gap:** Compliance dashboard + audit report generator. CLI `forge audit` returns JSON-only at MVP; full UI deferred.

### Persona 4: Executive (Phase 3 — scaffolded, deferred)

**Profile:** VP Engineering / CTO. Cares about cost, throughput, quality trends.

**Job-to-be-done:** "Show me cost per Task, throughput per week, quality trend (benchmark scores), and risk surface (open BLOCKED Executions, unresolved Findings)."

**MVP gap:** Executive dashboard. North-star metric ("compliance-ready Changes shipped per week per customer") tracked in `llm_calls` aggregations + `Changes` count, but UI deferred.

---

## 2. Information architecture

### MVP web pages (3)

```
/
└── /projects/{slug}
    └── /executions/{id}
```

Three pages, no login (single-user local deployment per MVP_SCOPE §L4). Auth scaffolding in place (cookie-based session) but disabled by default.

### Post-MVP web pages (Phase 2-3, scaffolded)

```
/
├── /projects                    [list — tech-lead persona]
├── /projects/{slug}
│   ├── /                        [overview — dev + tech-lead]
│   ├── /objectives              [list of Objectives]
│   ├── /objectives/{id}         [Objective detail + critical path SVG from D.6]
│   ├── /executions              [list, filterable by status]
│   ├── /executions/{id}         [detail — dev]
│   ├── /findings                [list — compliance + tech-lead]
│   ├── /decisions               [list — compliance]
│   ├── /audit                   [audit dashboard — compliance]
│   ├── /metrics                 [7 metrics — exec + tech-lead]
│   ├── /architecture            [E.9 hierarchical view — tech-lead]
│   ├── /critical-path           [D.6 Gantt — tech-lead]
│   ├── /rules/review            [G.4 retirement candidates — tech-lead]
│   └── /llm-costs/quarter       [L3.6 quarterly costs — exec]
└── /admin
    ├── /stewards                [G.5 — compliance]
    └── /data-classification     [G.1 — compliance]
```

### CLI surface (MVP — 5 commands; Phase 2-3 — 8 additional)

**MVP (5):**
- `forge init <repo-url>` — create Project, link GitHub repo, install webhook.
- `forge objective show [--id <uuid>]` — list / show Objectives.
- `forge execute <task-id>` — manually trigger an Execution (dev fallback when webhook fails).
- `forge status` — Project health snapshot (open Executions, BLOCKED count, recent Changes, cost-this-week).
- `forge audit <change-id>` — emit JSON evidence trail for a Change to stdout.

**Phase 2-3 (8 additional):**
- `forge resolve-uncertainty <execution-id> --accepted-by <role>` — F.4 endpoint backing.
- `forge contest-propagation <finding-id>` — G.11 contest endpoint backing.
- `forge rules retire <rule-id>` — G.4 archival.
- `forge metrics show` — G.3 metrics CLI view.
- `forge critical-path <objective-id>` — D.6 CritPath CLI view.
- `forge architecture <component-id>` — E.9 component view.
- `forge debt list` — F.12 unresolved technical-debt rows.
- `forge cost <execution-id>` — L3.6 per-Execution cost detail.

---

## 3. Developer flow (MVP — golden path)

### 3.1 Onboarding flow (target: < 1h per MVP_SCOPE success criteria)

```
T+0  : User clones repo, runs `docker-compose up`
T+2m : Healthcheck → /health returns Forge + DB + LLM provider all green
T+5m : User runs `forge init <repo-url>` → GitHub OAuth (or PAT) prompt → repo linked
T+10m: User adds `forge-task` label to an Issue
T+12m: Forge webhook fires → Execution created → user sees it in `forge status`
T+30m: First Execution completes → PR opened → user reviews diff
T+45m: User merges PR or files Finding to course-correct
T+55m: User reviews `forge audit <change-id>` to see evidence trail
T+60m: Onboarding done — user has shipped one PR via Forge end-to-end
```

**Onboarding gate (success criteria):**
- 1 user from scratch to first Execution in < 1h.
- 5 design-partner sessions averaging < 1h with ≥ 3 hitting target on first try.
- Documented friction points fed into `tests/onboarding/friction_log.md` for sprint refinement.

**Onboarding failure modes (mitigations):**

| Failure | Mitigation |
|---|---|
| Docker / Postgres setup error | `docker-compose up` health-checks each service before declaring ready; user sees `[FAIL] postgres: <error>` not generic startup failure |
| GitHub OAuth confusion | `forge init` provides PAT fallback path with clear explanation of permissions needed (read Issues + write PRs only) |
| First Execution stuck pending | `forge status` surfaces `BLOCKED` with reason; common reasons documented in error message itself, not in separate doc |
| LLM provider not configured | `/health` reports `[FAIL] llm_provider: missing ANTHROPIC_API_KEY` on first request; setup guide linked from error |
| First Issue not picked up | Webhook ping shown in `forge status`; manual `forge execute <task-id>` always available as fallback |

### 3.2 Issue → PR flow (golden path)

```
1. Developer creates GitHub Issue, adds `forge-task` label.
   — UI: GitHub Issue page (no Forge UI involvement).

2. Webhook fires → Forge ingests Issue as `Knowledge` entity.
   — UI: appears in `forge status` as `Execution(status=pending)` within ~5s.

3. Forge runs ingest → extracts goal, actor, process, requirement, risks.
   — UI: web `/executions/{id}` shows live progress: phases ticking through
        ingest → analyze → propose → execute → verify.
   — Latency budget: < 60s for ingest+analyze.

4. If ambiguity detected → BLOCKED state.
   — UI: `forge status` shows `BLOCKED — 1 ambiguity needs resolution`.
   — UI: web `/executions/{id}` shows ambiguity-resolution form with structured choices.
   — Resolution: developer picks option in UI OR runs CLI
              `forge resolve-uncertainty <execution-id> --accepted-by user`.

5. If no ambiguity → Objective activated → Tasks decomposed → execution starts.
   — UI: web `/executions/{id}` shows decomposed tasks + Decision (with 2+ alternatives
         per F.11).

6. Forge generates Change, runs tests locally.
   — UI: live test output streamed to web console (toggle in `/executions/{id}`).

7. PR opened with structured commit message + evidence trail in PR description.
   — UI: GitHub PR page (Forge backlinks but doesn't host UI).

8. Developer reviews PR diff in GitHub, sees evidence trail, merges.
   — UI: GitHub.

9. Forge captures merge → updates `Change.status=merged` → emits Finding if any
   post-merge Diff mismatch (G.10 BaselinePostVerification).
```

**Total latency target (MVP):** < 15 min P95 from Issue creation to PR open per MVP_SCOPE §1.

### 3.3 Audit flow (developer self-service)

```
forge audit <change-id>
```

Returns JSON with:
- Change metadata (file paths, lines added/deleted, reversibility_class).
- Linked Decision(s) with EvidenceSet(s).
- Linked Findings (if any).
- Linked Execution(s) with LLMCalls (cost, model, retry_count).
- ContextProjection ID + structural_categories (hidden details on demand via `--verbose`).
- Causal chain (10-link per G.9) summarized; full chain via `--full-chain`.

JSON schema versioned per ADR-013 (proposed) so downstream tooling (compliance reports) can rely on shape stability.

---

## 4. Error message specification

### 4.1 Error message rules (CONTRACT §B.5 inheritance)

Every error message follows the CONTRACT §B.5 template:
```
[STATUS] <what failed in concrete terms>
WHY: <root cause, one sentence>
EVIDENCE: <file:line OR query OR API response>
NEXT: <what user can do, ordered by likelihood>
```

**Banned patterns:**
- "Something went wrong" (no concrete what).
- "Please try again" without explaining when retry would help.
- Stack trace as primary content (stack trace allowed in --verbose, never as primary message).
- Error messages claiming verification when none was done (CONTRACT §B.6 false agreement).

### 4.2 Canonical error messages

| Error class | Template |
|---|---|
| BLOCKED — ambiguity | `[BLOCKED] Execution waiting on 1 ambiguity\nWHY: Issue describes "404 for missing user" but doesn't specify response shape\nEVIDENCE: ambiguity #abc123 in /executions/{id}\nNEXT:\n  1. Open /executions/{id} and select desired response shape\n  2. Run: forge resolve-uncertainty {id} --accepted-by user\n  3. View full ambiguity context: forge audit {id} --verbose` |
| BLOCKED — auth_failure | `[BLOCKED] LLM provider auth failed\nWHY: ANTHROPIC_API_KEY missing or invalid\nEVIDENCE: 401 from anthropic.com on tool_call_id={uuid}\nNEXT:\n  1. Verify key: echo $ANTHROPIC_API_KEY (should start with sk-ant-)\n  2. Set in .env: ANTHROPIC_API_KEY=sk-ant-...\n  3. Restart: docker-compose restart worker` |
| BLOCKED — projected_cost_exceeds_tau_cost | `[BLOCKED] Projected cost $2.30 exceeds budget $2.00\nWHY: Task complexity routes to Opus + 2 large file reads + 1 retry\nEVIDENCE: llm_calls cumulative $1.95 for execution {uuid}; current estimate $0.35\nNEXT:\n  1. Decompose task into smaller subtasks (recommended)\n  2. Override budget: forge execute --tau-cost-override 5.00 (requires Steward sign-off if > 2× default)\n  3. Review which calls are expensive: forge cost {execution-id}` |
| REJECTED — fewer_than_2_candidates | `[REJECTED] Architectural Decision needs ≥2 candidates\nWHY: F.11 CandidateSolutionEvaluation requires ≥2 structured candidates with 14-dim Score\nEVIDENCE: Decision {uuid} has 1 solution_candidate row\nNEXT:\n  1. Generate alternative candidate via /executions/{id}/regenerate-alternative\n  2. If 2nd alternative not feasible → mark Decision.type='trivial_change' and ensure change_size ≤ threshold (ADR-019)` |
| REJECTED — unaccepted_technical_debt | `[REJECTED] Change has unaccepted technical debt at app/foo.py:42\nWHY: F.12 detects 'TODO: handle Unicode' but no technical_debt row exists for this Change\nEVIDENCE: scripts/detect_debt_markers.py output; change_id={uuid}\nNEXT:\n  1. Either remove the TODO and re-run\n  2. Or create technical_debt row with accepted_by ∈ {steward, platform_engineer, tech_lead} (per ADR-020)` |
| REJECTED — projection_missing_required_category | `[REJECTED] StructuredTransfer rejected — projection missing 'requirements' category\nWHY: F.10 requires 6 structural categories; ContractSchema lists task as having requirement_refs but projection.requirements is empty\nEVIDENCE: ContextProjection {uuid}; task {uuid} has 3 requirement_refs\nNEXT:\n  1. Re-run ContextProjector with budget+10% (often a budget-truncation issue)\n  2. If MUST overflow → decompose task; minimum-viable projection cannot fit` |

All error messages are templated in `app/ui/error_messages.py` with a single source-of-truth table; tested via property test asserting every error_code in the codebase has a matching template entry (no ad-hoc strings).

### 4.3 Error message accessibility

- Color-coded severity (CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=blue) AND status icon (text-based: `[BLOCKED]`, `[REJECTED]`, `[WARN]`, `[INFO]`) — color-blind safe.
- All errors emitted to both stdout (CLI) and structured logs (JSON to stderr) — easy to grep, easy to ingest into Datadog/Loki later.
- Screen-reader: web error states use `role='alert'` + descriptive text (no icon-only conveyance).

---

## 5. Component library (MVP minimal)

### 5.1 Core components

| Component | Purpose | MVP / Phase |
|---|---|---|
| `<ExecutionTimeline>` | Visualizes phases of an Execution (ingest → analyze → propose → execute → verify) with per-phase status + duration | MVP |
| `<EvidenceList>` | Tabular display of EvidenceSet rows linked to a Decision/Change | MVP |
| `<DiffView>` | File-level diff with reversibility class badge + impact-closure list | MVP |
| `<CausalChain>` | Vertical SVG of the 10-link chain for a Change (from G.9) | Phase 2 |
| `<AmbiguityResolver>` | Form for F.4 resolve-uncertainty with structured choices | MVP |
| `<MetricsDashboard>` | 7-tile grid for G.3 metrics | Phase 3 |
| `<CriticalPathGantt>` | SVG Gantt-style chart for D.6 critical path | Phase 2 |
| `<ArchitectureGraph>` | Mermaid render of E.9 architecture_components hierarchy | Phase 2 |
| `<RuleRetirementQueue>` | Tabular list of G.4 retirement candidates with Steward action buttons | Phase 2 |
| `<CostBreakdown>` | L3.6 cost-per-call breakdown (model, tokens, retries) | MVP (basic), Phase 3 (analytical) |

### 5.2 Layout pattern

Single-column, max-width 1280px, dark-mode default (low-fatigue for engineers staring at this all day). All components ship with both light + dark themes. CSS framework: Tailwind (no opinion-forcing component library; matches codebase's existing patterns).

### 5.3 Live updates

- WebSocket connection from browser to Forge worker for live Execution-status streaming.
- Fallback: polling at 2s when WebSocket unavailable (corporate firewalls).
- Server pushes only diff (not full state); client reconciles.

---

## 6. Phase 1 MVP exit criteria (UX-specific)

- [ ] All 5 MVP CLI commands documented with `--help` text matching CONTRACT §B.5 template.
- [ ] All 3 MVP web pages render correctly on Chrome, Firefox, Safari (latest 2 versions each).
- [ ] Onboarding < 1h verified on 5 design-partner runs.
- [ ] Error message template coverage: every emitted error has a template entry (property test).
- [ ] `<ExecutionTimeline>` shows live updates within 2s of state change.
- [ ] `<DiffView>` displays diffs up to 1000 lines without UI lag.
- [ ] `forge audit <change-id>` JSON output matches versioned schema (ADR-013).
- [ ] No ad-hoc error strings in codebase: `grep -rE 'raise.*\b[A-Z][a-z]+Error\("[^"]+"\)' app/ | grep -v error_messages` returns 0 matches outside the template module.
- [ ] Accessibility audit: WCAG AA on the 3 MVP pages (axe-core CI gate).

---

## 7. Phase 2-3 deferred (scaffolded only)

The following are scaffolded but not implemented in MVP — wireframes + endpoint stubs only:

- Tech-lead persona dashboards (autonomy view, rule-retirement queue, Steward sign-off).
- Compliance audit report generator UI (CLI JSON output suffices for MVP).
- Executive cost-and-throughput dashboard (`<MetricsDashboard>` + `<CostBreakdown>` analytical view).
- IDE extensions (VS Code, JetBrains) — explicitly deferred per MVP_SCOPE §3.
- Mobile / tablet layouts — out of scope; desktop-only.
- Internationalization — English-only; i18n scaffolding via gettext extracted but no other locales.

---

## 8. Failure scenarios (ASPS Clause 11)

| # | Scenario | Status | Mechanism / Justification |
|---|---|---|---|
| 1 | null_or_empty_input | Handled | All form inputs typed via Pydantic; empty required fields blocked at submit; error messages explain (e.g. "Task ID required for forge execute"); UI never renders empty-state without explanation |
| 2 | timeout_or_dependency_failure | Handled | WebSocket fallback to polling; LLM provider timeout → BLOCKED state surfaced with auth/network/rate-limit specifics; healthcheck on `/health` shows component-level state |
| 3 | repeated_execution | Handled | CLI `forge execute <task-id>` checks for in-flight Execution; second call returns existing Execution ID (idempotent UI) rather than spawning duplicate |
| 4 | missing_permissions | Handled | GitHub OAuth scope explicit (`repo:read`, `pull_request:write`); insufficient scope → clear error pointing to re-auth flow; CLI uses PAT fallback when OAuth unavailable |
| 5 | migration_or_old_data_shape | Handled | Web pages tolerate optional schema fields (post-MVP additions); old Executions without `epistemic_snapshot_before` (E.7) render as "no snapshot" badge, not crash; JSON audit format versioned per ADR-013 |
| 6 | frontend_not_updated | Handled | This document IS the frontend spec — every entity surface check is enumerated in §2 and tracked in §6 exit criteria; new entity introduction requires PR updating this spec + UI |
| 7 | rollback_or_restore | Handled | UI rollbacks via PR revert (GitHub primary); CLI `forge audit` history allows reconstruction; web pages stateless (no in-memory state to lose) |
| 8 | monday_morning_user_state | Handled | All UI state is server-side (DB-backed); refresh / restart loses no work; cookie-based session optional and disabled by default in MVP |
| 9 | warsaw_missing_data | JustifiedNotApplicable | UX is browser/CLI level; no geographic data dimension. |

---

## 9. Open questions

| # | Question | Blocks |
|---|---|---|
| Q1 | Component library: ship Tailwind-only OR pick a component framework (shadcn/ui, Radix)? Trade-off: framework speeds development but adds dependency surface | Web page implementation |
| Q2 | WebSocket library: native vs Socket.IO vs SSE? Native is simpler but requires explicit reconnection logic | Live updates |
| Q3 | Error message i18n: ship English-only, or add gettext from day 1? Cost: gettext adds complexity for ~3 days | i18n scaffolding |
| Q4 | Onboarding video: record one before MVP-ship, or rely on text README? Video is higher-conversion but takes 2-3 days to produce | MVP-ship marketing |
| Q5 | Audit JSON schema versioning ADR (ADR-013) — must be CLOSED before `forge audit` ships to design partners | CLI ship |
| Q6 | Accessibility audit tool: axe-core (free, CI-integratable) vs commercial SaaS (Pa11y, etc.)? axe-core sufficient for MVP | CI gate |

---

## 10. Authorship + versioning

- v1 (2026-04-25) — initial L4 spec; 4 personas; 3 MVP web pages + 5 CLI commands; error message template; failure scenarios.
- Updates require explicit version bump + distinct-actor review per ADR-003.
