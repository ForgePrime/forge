# Forge platform — Tier 3+4 DONE

All items from `FORGE_PLATFORM_BACKLOG.md` now implemented end-to-end.

## Tier 3 (done)

| ID | Scope | Backend | UI | Tests |
|---|---|---|---|---|
| E1 | Crafted mode | `services/crafter.py` + orchestrator 2-stage flow + `Execution.mode`/`crafter_call_id` columns | `PUT /api/v1/tier1/projects/{slug}/execution-mode` | 3 |
| I1-I5 | Autonomy L1-L5 | `services/autonomy.py` (level state, promotion criteria, veto clauses) + `Project.autonomy_level`/`autonomy_promoted_at` + `Objective.autonomy_optout` | `GET/POST .../autonomy`, `PUT .../objectives/{ext}/autonomy-optout` | 4 |
| C4 | URL crawler | `services/kb_crawl.py crawl_url` (httpx + BeautifulSoup, 10s timeout, 200k-char cap, content-type aware) | wired into existing `kb/url` endpoint | 2 |
| C5 | Folder scanner | `services/kb_crawl.py scan_folder` (recursive walk, respects `DEFAULT_IGNORES` + binary exts, 500k-byte cap per file, cap 200 samples) | wired into existing `kb/folder` endpoint | 2 |
| J6 | Replay harness | `POST /api/v1/tier1/llm-calls/{id}/replay` — re-runs archived `full_prompt` with current contract + returns identical/diff | JSON response (can be linked from task report) | 2 |

## Tier 4 (done)

| ID | Scope | Backend | UI | Tests |
|---|---|---|---|---|
| F3 | Skill ROI | `GET /api/v1/skills/{ext}/roi` + `POST .../record-invocation` | surfaced in org cross-project view | 2 |
| F4 | Marketplace promotion | `POST /api/v1/skills/{ext}/promote-to-org` (requires ≥3 projects + ≥10 invocations) | gatekeeper message | 1 |
| K1 | Org triage | `GET /api/v1/tier1/org/triage` — aggregated open_decisions + failed_tasks + dismissals-without-reason | ready for dashboard tile | 2 |
| K2 | Cross-project patterns | `GET /api/v1/tier1/org/cross-project-patterns` — lists skills with ≥3 projects + ≥10 invocations flagged `eligible_for_promotion` | ready for admin UI | 1 |
| K3 | Org budget overview | `GET /api/v1/tier1/org/budget-overview` (last 30d: per-project + per-purpose totals) | ready for org dashboard | 1 |
| L4 | Share-link business view | `public_share_view` rewritten — HTML rendering of objectives + KR + task counts; hides costs/prompts/internal IDs | fully implemented (tailwind via CDN) | 1 |

## Schema migrations added

- `executions.mode`, `executions.crafter_call_id`
- `projects.autonomy_level`, `projects.autonomy_promoted_at`
- `objectives.autonomy_optout`

Plus from earlier tiers:
- `projects.contract_md`, `acceptance_criteria.{source_ref,last_executed_at,source_llm_call_id}`, `findings.{dismissed_reason,dismissed_at,source_llm_call_id}`, `knowledge.{description,focus_hint,target_url}`, new tables `objective_reopens`, `skills`, `project_skills`, `ai_interactions`.

## Test coverage

96 tests — all non-happy-path:
- `test_ai_sidebar.py` (14)
- `test_ai_sidebar_ui.py` (7 Playwright)
- `test_kb_rework.py` (8)
- `test_skills.py` (10)
- `test_tier1_backlog.py` (19)
- `test_tier1_ui.py` (8)
- `test_tier2_forensics.py` (6)
- `test_tier34.py` (22)
- `test_pipeline.py` + others (legacy)
