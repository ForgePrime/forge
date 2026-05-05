# INTEGRATIONS.md — L5 External-System Integration Specification

**Status:** DRAFT — pending distinct-actor review per ADR-003.
**Date:** 2026-04-25
**Depends on:** PLAN_GATE_ENGINE (A.5 idempotency for retryable webhooks); PLAN_LLM_ORCHESTRATION (cost tracking flows through to integration calls).
**Source spec:** MASTER_IMPLEMENTATION_PLAN §3 L5; MVP_SCOPE.md §L5 (GitHub only at MVP); FORMAL_PROPERTIES_v2.md P17 (provenance for external-source evidence) + P22 (disclosure of external-call failures).
**Scope:** integration adapters with external systems. **MVP scope is GitHub only.** Other integrations scaffolded with adapter pattern; deferred.

> **Known unverified claim (CONTRACT §A.6):** External systems are non-deterministic from Forge's perspective (rate limits, schema drift, downtime, account suspensions). This doc specifies the *adapter contract* (how Forge presents external-system calls to L1+L2), not the external systems themselves. External-system reliability is empirical and out of scope of G_L5. Same scope split as L3.

---

## 1. Adapter pattern (universal)

Every external-system integration follows the same adapter pattern:

```
+----------------+     +-------------------+     +----------------+
| Forge L1+L2    | --> | IntegrationAdapter | --> | External       |
| (governance)   |     | (this layer)       |     | system         |
+----------------+     +-------------------+     +----------------+
                              |
                              v
                       +-------------------+
                       | EvidenceSet       |
                       | (provenance + chk)|
                       +-------------------+
```

**Adapter contract (every adapter implements):**

```python
class IntegrationAdapter(Protocol):
    name: str                                    # e.g. "github"
    version: str                                 # adapter version, not external API version
    authority_level: AuthorityEnum              # max authority this adapter can grant tools
    requires_idempotency_key: bool

    def health() -> HealthResult: ...           # for /health endpoint
    def authenticate(credentials) -> AuthResult: ...
    def call(operation, args, idempotency_key) -> CallResult: ...
    def capture_evidence(call_result) -> EvidenceSet: ...    # P17 + P18 binding
    def classify_failure(error) -> Literal['transient', 'permanent']: ...   # L3.5 reuse
```

Every external call:
1. Goes through `IntegrationAdapter.call()` — single dispatch point.
2. Records `EvidenceSet(kind='command_output' | 'file_citation', provenance=<adapter>:<operation>, reproducer_ref=<args>, checksum=<sha256(response)>)` per P17 + P18.
3. Routes failures through `IntegrationAdapter.classify_failure()` matching L3.5 semantics.
4. Threads `idempotency_key` from A.5 to external API where supported (GitHub Webhooks, Slack message-id).

Adapters are registered in `app/integrations/registry.py` — one entry per external system; `health()` aggregated into `/health`.

---

## 2. GitHub adapter (MVP — full coverage)

**Operations exposed (8):**

| Operation | Read/Write | Authority | Idempotency |
|---|---|---|---|
| `read_issue(issue_id)` | R | read_only | not required |
| `read_repo_tree(ref)` | R | read_only | not required |
| `read_file(path, ref)` | R | read_only | not required |
| `clone_repo(url, dest)` | R | read_only | not required |
| `create_branch(name, base)` | W | idempotent_write | required (`branch_name` is key) |
| `commit_changes(branch, files, message)` | W | side_effecting_write | required |
| `open_pr(branch, title, body)` | W | side_effecting_write | required (`branch_name+title_hash`) |
| `comment_on_issue(issue_id, body)` | W | side_effecting_write | required |

**Webhook listener:**
- Endpoint: `POST /webhooks/github`
- Signature verification: HMAC-SHA256 with `GITHUB_WEBHOOK_SECRET`; mismatch → 401, no processing.
- Idempotency: `(delivery_id, event_type)` unique constraint in `github_webhook_events` table; replay safely returns prior result.
- Events handled (MVP): `issues.opened`, `issues.labeled`, `pull_request.closed`, `pull_request.merged`.
- Events ignored (MVP): everything else; logged at INFO, not WARN (intentional ignore is not a problem).

**Forge-task label trigger:**
- Issue with `forge-task` label → ingest as Knowledge → create Execution → run pipeline.
- Label removed → Execution.status=BLOCKED with `reason='forge_task_label_removed'`; no auto-cancel (developer can re-add label or run `forge cancel`).

**Auth flow:**
- **Primary:** GitHub App installation (preferred — higher rate limits, finer permissions, no user OAuth dance for service-to-service).
- **Fallback:** Personal Access Token (`GITHUB_PAT`) for single-user local dev.
- Permissions required: `repo:read`, `pull_requests:write`, `issues:read`, `issues:write`. Webhooks: `installation_repositories`, `issues`, `pull_request`.

**Rate-limit handling:**
- Adapter respects `X-RateLimit-Remaining` header.
- < 100 remaining → emit Finding(severity=MEDIUM, kind='github_rate_limit_low'); Forge backs off non-urgent operations (read_repo_tree polling).
- 0 remaining → BLOCKED with `reason='github_rate_limit_exhausted'`; resumes automatically when reset window passes (clock from `X-RateLimit-Reset`).

**Failure classification (rule-based per L3.5 reuse):**

| GitHub response | Classification | Recovery |
|---|---|---|
| 401, 403 | permanent | BLOCKED; auth issue |
| 404 (resource) | permanent | BLOCKED; resource missing — not retryable |
| 409 (conflict) | permanent | BLOCKED; conflict surfaced to user |
| 422 (validation) | permanent | BLOCKED; payload issue, no retry |
| 429 | transient | retry after `Retry-After` header (capped at 60s); after 3 retries → BLOCKED |
| 5xx | transient | exponential backoff, max 3 retries → BLOCKED if persists |
| network timeout | transient | same as 5xx |

**Local git mirror:**
- Forge maintains local clones in `var/repos/<project_slug>/` for read operations.
- Pull on Execution start (within last 5 min cached); fresh clone if cache expired.
- Worktree per Execution to avoid conflicts: `var/worktrees/<execution_id>/`.
- Cleanup: worktrees removed 24h after Execution terminal state (DONE / BLOCKED / FAILED).

**Test coverage (MVP exit gate):**

```bash
# T1: webhook signature verification
pytest tests/integrations/test_github_webhook.py::test_invalid_signature_rejected -x

# T2: webhook idempotency
pytest tests/integrations/test_github_webhook.py::test_replay_idempotent -x
# PASS: same delivery_id received twice → second is no-op

# T3: forge-task label trigger
pytest tests/integrations/test_github_webhook.py::test_forge_task_label_creates_execution -x

# T4: 8 operations EvidenceSet capture
pytest tests/integrations/test_github_adapter.py::test_evidence_capture -x
# PASS: each of 8 operations on success records EvidenceSet with correct kind + provenance + checksum

# T5: rate-limit backoff
pytest tests/integrations/test_github_adapter.py::test_rate_limit_backoff -x

# T6: failure classification matrix
pytest tests/integrations/test_github_adapter.py::test_failure_classification -x
# PASS: each of 7 GitHub-error categories classified per matrix above

# T7: idempotency_key propagation on writes
pytest tests/integrations/test_github_adapter.py::test_idempotency_key_passed -x

# T8: local git mirror cleanup
pytest tests/integrations/test_github_adapter.py::test_worktree_cleanup -x
# PASS: terminal Execution → 24h later, worktree removed; non-terminal → preserved
```

**Gate:** T1–T8 pass + GitHub App credentials in test fixtures + signature secret in test env → PASS.

---

## 3. CI integration (Phase 2 — scaffolded, deferred)

**Operations to expose (when shipped):**
- `read_run_status(run_id)` — current state.
- `trigger_run(workflow, ref)` — kick off CI.
- `read_logs(run_id)` — fetch test output for evidence.

**Providers planned:**
- GitHub Actions (free, default for GitHub-hosted repos).
- CircleCI (common alternative).
- Buildkite (enterprise common).

**MVP gap:** CI runs locally via `pytest` in subprocess from worker, not via CI provider. Test output captured directly into EvidenceSet.

**Failure scenarios already mapped via subprocess:**
- subprocess timeout → `pytest -x` fast-fail; configurable via `FORGE_TEST_TIMEOUT_SEC` env (default 600).
- pytest absent → `/health` reports `[FAIL] pytest_runner: pytest not installed`.
- test collection error → BLOCKED with `reason='test_collection_error: <pytest stderr>'`; full stderr in EvidenceSet.

**Adapter scaffold:**
- `app/integrations/ci/base.py` — Protocol per §1.
- `app/integrations/ci/local_pytest.py` — MVP implementation (subprocess wrapper).
- Phase 2 additions: `github_actions.py`, `circleci.py`, `buildkite.py`.

---

## 4. Issue tracker integration (Phase 2-3 — scaffolded, deferred)

**MVP:** GitHub Issues only (covered by §2 GitHub adapter).

**Phase 2-3 providers planned:**
- Linear (common in tech startups).
- Jira (enterprise).
- Notion databases (lightweight teams).

**Adapter contract additions:**
- `read_ticket(ticket_id)`, `comment_on_ticket(ticket_id, body)`.
- Issue-tracker-specific concept mappings: Linear "Cycle" → Forge Objective; Jira "Epic" → Objective; Jira "Story" → Task.

**Cross-tracker DAG concern:**
- If a Project has multiple trackers (e.g. Linear for product, GitHub for engineering tasks) → cross-reference via `Knowledge.source_ref` polymorphic field.
- B.7 SourceConflictDetector catches cross-tracker contradictions (e.g. Linear says "feature X is P0", Jira says "feature X is deferred").

---

## 5. Deployment integration (Phase 3 — scaffolded, deferred)

**Out of MVP scope.** Forge produces PRs; deployment is a separate concern.

**Phase 3 providers planned:**
- Render.com (where Forge itself is deployed at MVP).
- Vercel.
- Fly.io.
- AWS / GCP / Azure (enterprise).

**Operations envisioned:**
- `read_deploy_state(env)` — for Findings on prod regression.
- `trigger_rollback(env, version)` — only via Steward sign-off (G.5 gating).
- `read_deploy_logs(deploy_id)` — for incident-response evidence.

**MVP gap:** none — deployment is outside Forge's responsibility. Forge's only "deploy" concern at MVP is its own deployment (Docker Compose locally, Render.com hosted).

---

## 6. Observability integration (Phase 2 — scaffolded, deferred)

**MVP:** structured JSON logs to stdout per OPERATIONS.md §3. No external observability yet.

**Phase 2 providers planned:**
- Logfire (Pydantic-aligned, low integration cost — first choice).
- Datadog APM (enterprise common).
- Honeycomb (event-driven model fits Execution lifecycle well).
- OpenTelemetry (vendor-neutral; partial seed already present per recent commit `e9f6ad3 feat(otel): OpenTelemetry tracing starter`).

**Telemetry events emitted (already structured at MVP):**
- `Execution.started`, `Execution.completed`, `Execution.failed`, `Execution.blocked`.
- `LLMCall.started`, `LLMCall.completed`, `LLMCall.failed`.
- `Verdict.computed`, `Gate.passed`, `Gate.rejected`.
- `Finding.created`, `Decision.created`, `Change.created`.

**Trace IDs:**
- Already present per OTel starter: `execution_id` propagates as trace ID.
- Phase 2 additions: span hierarchy, attribute taxonomy, sampling strategy ADR.

**Metrics already collectable (Phase 1, surfacing via `/metrics`):**
- Per MASTER §3 L7 5 outcomes: Quality, Cost, Latency, UX, Reliability — each maps to specific aggregations of the events above.
- 7 CGAID metrics (G.3) — backend ready, dashboard UI deferred per UX_DESIGN.md §5.1.

---

## 7. Notification integration (Phase 2 — scaffolded, deferred)

**MVP:** GitHub PR descriptions are the only outbound notification. Webhook → execution → PR. The PR description IS the notification to the developer.

**Phase 2 providers planned:**
- Slack (most common for team notifications).
- Microsoft Teams (enterprise common).
- Email (SES, SendGrid, Postmark).
- Discord (common for OSS / smaller teams).

**Events to notify:**
- BLOCKED Execution requiring action (Steward, ambiguity-resolver, distinct-actor reviewer).
- HIGH/CRITICAL Finding (immediate alert).
- Quarterly metrics summary (digest).
- Cost overrun (HIGH severity per L3.6).

**Adapter scaffold:**
- `app/integrations/notifications/base.py` — Protocol.
- `app/integrations/notifications/null.py` — MVP no-op (events logged but not sent externally).

---

## 8. Adapter health aggregation (`/health` endpoint)

```json
{
  "forge": "ok",
  "db": "ok",
  "llm_provider": "ok",
  "integrations": {
    "github": {"status": "ok", "rate_limit_remaining": 4123, "version": "v1"},
    "ci": {"status": "ok", "type": "local_pytest", "version": "v1"},
    "issue_tracker": {"status": "n/a", "reason": "github_issues_handled_via_github_adapter"},
    "deployment": {"status": "n/a", "reason": "out_of_mvp_scope"},
    "observability": {"status": "ok", "type": "stdout_structured_logs", "version": "v1"},
    "notifications": {"status": "n/a", "reason": "out_of_mvp_scope"}
  }
}
```

`/health` returns 200 iff `forge`, `db`, `llm_provider`, and all integrations with status != "n/a" are "ok". Non-blocking integrations (Phase 2 deferred) report "n/a" with reason. Blocking ones report concrete status.

---

## 9. Failure scenarios (ASPS Clause 11)

| # | Scenario | Status | Mechanism / Justification |
|---|---|---|---|
| 1 | null_or_empty_input | Handled | Adapter typed inputs (Pydantic models per Operation); empty webhook payload rejected with 400; empty file path on `read_file` → ValueError with clear message |
| 2 | timeout_or_dependency_failure | Handled | Per-operation timeout; rate-limit backoff for GitHub; subprocess timeout for local_pytest with `FORGE_TEST_TIMEOUT_SEC`; failure classification (§2 matrix) routes to retry or BLOCKED |
| 3 | repeated_execution | Handled | Webhook idempotency via `(delivery_id, event_type)` unique constraint; `idempotency_key` propagated to GitHub writes (branch_name, title_hash); A.5 MCP idempotency layered on top for tool-call dedup |
| 4 | missing_permissions | Handled | GitHub OAuth/PAT scope checked at adapter init; insufficient → /health reports `[FAIL] github: missing scopes <list>`; signature mismatch on webhook → 401 |
| 5 | migration_or_old_data_shape | Handled | Adapter `version` field; payload schema versioning per `Knowledge.source_ref_version`; old webhook events parseable via versioned handler dispatch |
| 6 | frontend_not_updated | Handled | Adapter changes surface in /health JSON shape; UX_DESIGN.md §10 versioned audit JSON includes adapter versions per Change |
| 7 | rollback_or_restore | Handled | Adapter env flags reversible (e.g. `GITHUB_ADAPTER_MODE=read_only` for safe-mode); local git worktrees clean up on terminal state but preserve on BLOCKED for forensics |
| 8 | monday_morning_user_state | Handled | Adapter state is per-call (no in-memory accumulation); GitHub rate-limit info refreshes per response header; subprocess test runner stateless |
| 9 | warsaw_missing_data | JustifiedNotApplicable | Adapters integrate with code-management systems; no geographic data dimension |

---

## 10. Open questions

| # | Question | Blocks |
|---|---|---|
| Q1 | GitHub App vs PAT default: ship App as primary (requires public key registration) or PAT (simpler local-dev story)? Trade-off: App is preferred for production, PAT is faster onboarding | MVP onboarding |
| Q2 | Webhook secret rotation policy — manual ADR or automated? At MVP scale, manual; document as residual risk in AUTONOMOUS_AGENT_FAILURE_MODES.md if not addressed | Phase 2 |
| Q3 | OTel sampling strategy — sample all or 10% with full trace on errors? ADR for Phase 2 | Phase 2 observability |
| Q4 | Retry-After cap — 60s in MVP draft; should it be configurable per ADR? | Phase 2 calibration |
| Q5 | Adapter circuit breaker — at what failure rate does adapter declare itself unhealthy? Currently per-call retry; circuit-breaker pattern for sustained failures is Phase 2 | Phase 2 reliability |

---

## 11. Authorship + versioning

- v1 (2026-04-25) — initial L5 spec; GitHub adapter MVP-complete; 5 other adapter classes scaffolded.
- Updates require explicit version bump + distinct-actor review per ADR-003.
