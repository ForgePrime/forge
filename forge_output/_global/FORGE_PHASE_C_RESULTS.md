# Faza C — Cross-model challenge + Workspace infra

**Data:** 2026-04-17

## Co zbudowane

### C1 — Auto-challenge (Opus 4.7 vs Sonnet 4.6)
- `app/services/challenger.py` — po ACCEPTED delivery + Phase A + Phase B, odpala Opus z prompt "weryfikuj NIEZALEŻNIE claimsy"
- Prompt zawiera: delivery, Phase A test results, Phase B extraction (żeby nie duplikować findings)
- Returns `{per_claim_verdicts, new_findings, overall_verdict: PASS|NEEDS_REWORK|FAIL, summary}`
- Persists LLMCall purpose=challenge + nowe Finding rows z `evidence="challenger-surfaced"`
- Report endpoint rozróżnia findings by source (extractor vs challenger)

### C2 — Workspace docker-compose bootstrap
- `app/services/workspace_infra.py`
- Per-project postgres:16-alpine + optional redis:7-alpine
- Deterministic ports z hash projektu (smoketest: 56045/55991)
- `.env.forge` file w workspace z connection URLs
- Idempotent (compose up -d), health check wait 60s
- Cleanup: `stop_workspace_infra()` dla teardown
- Envs przekazywane do Phase A pytest runs + KR measurement

## Live test — T-004 SMS webhook delivery status

**Setup:**
- docker-compose up: postgres port 56045 + redis port 55991 ✓
- Task T-004 przeszedł całą pipeline Phase A → B → C w 1 attempt

**Koszt breakdown:**
```
execute (Sonnet 4.6):     $1.35  (~8 min)
extract (Sonnet 4.6):     $0.07  (~20s)
challenge (Opus 4.7):     $0.50  (~97s)
─────────────────────────
TOTAL:                    $1.92
```

**Findings breakdown:**
- Sonnet-executor napisał kod, testy lokalne PASS (3/3)
- Sonnet-extractor znalazł 4 decisions + 3 findings
- **Opus-challenger zweryfikował 9/9 claims, ALE znalazł 6 DODATKOWYCH findings**, verdict NEEDS_REWORK

**Opus-challenger wyłapał production-grade bugs których Sonnet-extractor nie widział:**

1. **F-013 [HIGH] Twilio signature validation łamie się za reverse-proxy**
   > str(request.url) zwraca wewnętrzny URL (http://internal:8000/...) ≠ URL podpisany przez Twilio (https://public.domain/...). Signature ZAWSZE failuje w prod.

   **To SHOW-STOPPER bug — cała integracja SMS nie zadziała w produkcji.**

2. **F-012 [HIGH] httpx.get() bez timeout**
   > Poll task co 15min, bez timeout na request. Jedna wolna odpowiedź od providera = zawieszony Celery worker.

3. **F-014 [MED] Infobip webhook payload format zły**
   > Kod oczekuje `{messageId, status}` (flat), rzeczywiście Infobip wysyła `{results: [{...}]}` (nested).
   > Żaden Infobip DLR nie zaktualizuje stanu reminder.

4. **F-015 [MED] Unknown MessageStatus silnie ignorowany**
5. **F-016 [MED] Poll query bez `.limit()` → memory risk przy nagromadzeniu stuck reminders**
6. **F-017 [LOW] Bare except swallows DB errors → Twilio nie retryuje mimo że update failował**

## Co to oznacza

**Bez Phase C**, delivery T-004 byłoby zamknięte jako DONE z czterema decisions + 3 findings. Rzeczywistość: 2 HIGH production bugs byłyby ukryte do pierwszego deployu.

**Z Phase C** (cross-model review):
- Verdict NEEDS_REWORK automatycznie flaguje task
- 6 nowych Finding rows w backlog, każdy z konkretnym file_path + fix suggestion
- User dostaje w report: "task ACCEPTED ale Phase C recommends rework before prod"

Różnica: Sonnet-executor testuje że `test_X PASSED`, Phase B patrzy na DECYZJE. **Phase C patrzy na PRODUKCYJNE KONSEKWENCJE** — proxy, timeouts, format compatibility, operational failure modes.

## Structure finalnego trustworthy DONE report

`GET /projects/{slug}/tasks/{ext}/report` zwraca:

```json
{
  "task": {
    "external_id": "T-004",
    "requirement_refs": ["SRC-002 punkt 9", "SRC-004 §Powiadomienia"],
    "completes_kr_ids": [],
    "produces": {...}
  },
  "requirements_covered": [{ref, source_title, source_known}],
  "objective": {external_id, title, key_results: [{..., completed_by_this_task}]},
  "acceptance_criteria": [{position, text, scenario_type, verification, test_path}],
  "tests_executed_by_forge": {
    "language": "python",
    "collected": 3, "passed": 3, "failed": 0,
    "per_ac": [{ac_index, passed, test_path, tests_matched}],
    "per_test": [{nodeid, outcome, duration_sec, longrepr}]
  },
  "verification_report": {git_diff, kr_measurements, tests, language},
  "auto_extracted_decisions": [{external_id, issue, recommendation, reasoning, severity}],
  "auto_extracted_findings": [{external_id, type, severity, title, description, file_path, suggested_action, source: "extractor|challenger"}],
  "challenge": {verdict, summary, claims_verified, claims_refuted, per_claim_verdicts},
  "not_executed_claims": [{action, reason, impact}],
  "cost_by_purpose": {"execute": 1.35, "extract": 0.07, "challenge": 0.50},
  "attempts": 1
}
```

**Każde pytanie usera ma odpowiedź:**
- "zrobione zgodnie z jakimi wymaganiami" → `requirement_refs` + `requirements_covered`
- "co zrobione" → `task.produces` + `changes` + `test_results.per_ac`
- "przetestowane i jak" → `tests_executed_by_forge` (Forge-executed, nie self-report)
- "jakie scenariusze, edge case" → AC z `scenario_type` + per-test mapping
- "gdzie testowane" → `test_path` per AC + `workspace_dir`
- "czego nie zrobiono" → `not_executed_claims`
- "co jeszcze zostało zauważone" → `auto_extracted_findings` (source: extractor + challenger)
- "dodane do backlog" → findings w tabeli Finding dostępne przez `/findings/{id}/triage` → auto-create Task

## Ekonomia Phase C

Narzut Phase C vs pre-C:
- Phase B extraction: +$0.07 per task (~10% narzut)
- Phase C challenge: +$0.50 per task (~40% narzut Opus 5× droższy)
- Phase A test runs: +~76s wall time (model changes + pytest)

Dla 10-task scenariusza: ~$20 vs ~$13 pre-C. **Wzrost 50% dla dużo większej pewności deliveri.**

ROI: jeden HIGH bug (typu F-013 signature validation) znaleziony w prod = koszt incident, dowodnie, pośpiechy, stracone zaufanie. Phase C kosztujący $0.50 per task jest absurdalnie tani w porównaniu.

## Status platformy

| Komponent | Status |
|-----------|--------|
| Ingest | ✓ |
| Analyze | ✓ |
| Plan (z requirement_refs + completes_kr_ids) | ✓ |
| Orchestrate | ✓ |
| **Phase A** (test_runner, git_verify, kr_measurer) | ✓ |
| **Phase B** (auto-extract Decision + Finding) | ✓ |
| **Phase C1** (cross-model challenge Opus) | ✓ |
| **Phase C2** (workspace docker-compose bootstrap) | ✓ |
| DONE report endpoint (trustworthy) | ✓ |
| Dashboard UI | **Nie zbudowane (Faza D)** |

## Następny krok — Faza D

Dashboard Jinja2+HTMX+Tailwind CDN:
- Lista projektów z summary
- Per-project view: objectives + tasks z live status + llm_calls
- Task detail = render "trustworthy DONE report" w HTML
- Forms: ingest upload, analyze, plan, orchestrate triggery
- Live polling `_htmx_` dla IN_PROGRESS

Bez Fazy D wszystko obsługujesz przez curl/psql/JSON. Jest funkcjonalnie, ale nie operationally friendly.
