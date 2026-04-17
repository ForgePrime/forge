# Forge Platform — Scenariusze testowe end-to-end

**Cel:** Przetestować CAŁY proces od wymagań biznesowych do kodu. Nie happy path — każdy scenariusz testuje co się dzieje gdy coś idzie nie tak, zmienia się, lub jest niekompletne.

---

## Jak czytać ten dokument

Każdy scenariusz ma:
- **GIVEN:** Stan początkowy
- **WHEN:** Co się dzieje (akcja, zmiana, problem)
- **THEN:** Co system POWINIEN zrobić
- **VERIFY:** Jak sprawdzić że zadziałało
- **FAIL IF:** Kiedy test jest niezdany

---

## FAZA 1: Ingestion — od dokumentu do wymagań

### TS-I-001: Dokument ze sprzecznościami

```
GIVEN: Specyfikacja mówi "PostgreSQL" na stronie 3, "Firestore" na stronie 7
WHEN:  AI ekstrakcja parsuje dokument
THEN:  System tworzy D-NNN (type=risk, status=OPEN) z obydwoma wersjami.
       NIE wybiera cicho jednej opcji.
       Notification do user: "Conflict found, decision needed."
VERIFY: decisions.json zawiera OPEN decision z issue zawierającym oba terminy.
        Żaden K-NNN requirement nie zakłada konkretnej bazy.
FAIL IF: AI wybrała jedną opcję bez OPEN decision.
         Lub: requirement K-NNN mówi "use PostgreSQL" bez OPEN decision.
```

### TS-I-002: Compound requirement (dwa wymagania w jednym)

```
GIVEN: Requirement "System obsługuje zamówienia z dostawą i płatnością online"
WHEN:  AI tworzy K-NNN
THEN:  System WARNS: "compound requirement detected (>100 chars + 'i'/'and')"
       AI rozbija na:
         K-001: "System tworzy zamówienie z listą produktów"
         K-002: "System oblicza koszt dostawy"
         K-003: "System obsługuje płatność online"
VERIFY: Każdy K-NNN ma ≤100 chars i jedno wymaganie.
FAIL IF: Jeden K-NNN zawiera compound (dwa niezależne wymagania).
```

### TS-I-003: Brakująca kategoria z 9 krytycznych

```
GIVEN: Dokument nie wspomina o error-handling
WHEN:  AI kończy ekstrakcję
THEN:  Gate C1 raportuje: "error-handling: UNKNOWN — create assumption or clarify"
       AI tworzy D-NNN (type=clarification_needed, status=OPEN):
       "Error handling approach not specified. Assumed: standard HTTP error codes."
VERIFY: Wszystkie 9 kategorii mają status KNOWN, ASSUMED, lub UNKNOWN.
        Żadna nie jest MISSING (ciche pominięcie).
FAIL IF: Gate C1 PASS z kategorią bez pokrycia.
```

### TS-I-004: Implicit assumption nie wykryte

```
GIVEN: Dokument mówi "użytkownicy logują się" ale nie mówi jakim mechanizmem
WHEN:  AI ekstrakcja
THEN:  AI tworzy D-NNN (type=architecture, status=OPEN):
       "Authentication mechanism not specified. Options: JWT, session, OAuth."
       Z if_wrong: "Wrong auth mechanism = security risk + rewrite."
VERIFY: Assumption jawne w decisions. Nie milczące.
FAIL IF: AI zakłada JWT bez decision. Lub: K-NNN mówi "JWT auth" bez OPEN decision.
```

### TS-I-005: Bardzo duży dokument (100+ stron)

```
GIVEN: Dokument 150 stron, 400 wymagań
WHEN:  AI ekstrakcja
THEN:  System obsługuje bez crash/timeout.
       Wymagania atomowe (≤200 chars każde).
       Extraction ratio ≥2 facts/page.
VERIFY: K-NNN count ≥ 300. Gate C1 PASS. Żaden K-NNN > 200 chars.
FAIL IF: Timeout. Lub: <100 K-NNN z 150 stron. Lub: compound requirements.
```

---

## FAZA 2: Analysis — od wymagań do objectives

### TS-A-001: OPEN decisions blokują planowanie

```
GIVEN: 3 OPEN decisions (1 clarification_needed, 1 risk HIGH, 1 architecture)
WHEN:  Użytkownik próbuje /plan
THEN:  Gate C2 BLOCKS: "3 OPEN decisions must be resolved before planning."
       System listuje jakie i dlaczego blokują.
VERIFY: draft-plan odmawia dopóki decisions nie CLOSED.
FAIL IF: Plan tworzony z OPEN decisions.
```

### TS-A-002: Objectives grupowane technicznie zamiast biznesowo

```
GIVEN: 20 requirements dotyczących orders, payments, delivery
WHEN:  AI tworzy objectives
THEN:  Objectives mają nazwy biznesowe:
       O-001: "Customers can place and track orders"
       NIE: "Implement backend API" (techniczna warstwa)
VERIFY: Objective titles zawierają actor + action (user-facing outcome).
FAIL IF: Objective title to techniczna warstwa ("Backend", "Database", "Frontend").
```

### TS-A-003: KR bez mierzalnego sposobu weryfikacji

```
GIVEN: Objective "Fast API responses"
WHEN:  AI tworzy KR: {description: "API is fast", measurement: "manual", check: "check"}
THEN:  Gate REJECTS: check field < 30 chars lub brak verb.
       AI poprawia: {metric: "p95_ms", baseline: 850, target: 200, 
                     measurement: "command", command: "python -m metrics p95"}
VERIFY: Każdy KR ma measurement z konkretną komendą/testem/instrukcją ≥30 chars.
FAIL IF: KR z check="check" lub check="verify" przechodzi gate.
```

### TS-A-004: Orphaned requirements (K bez O)

```
GIVEN: 25 requirements, AI tworzy 3 objectives linkując 22 requirements
WHEN:  Gate C2 sprawdza
THEN:  BLOCKS: "3 requirements not linked to any objective: K-023, K-024, K-025"
VERIFY: Każdy K-NNN z category=requirement linkowany do ≥1 O-NNN.
FAIL IF: Gate C2 PASS z orphaned requirements.
```

---

## FAZA 3: Planning — od objectives do task graph

### TS-P-001: AC only happy-path

```
GIVEN: Task type=feature, instruction "Add order endpoint"
WHEN:  AI tworzy AC: [
         {text: "Order created successfully", scenario_type: "positive", verification: "test"}
       ]
THEN:  fn_validate_ac_quality REJECTS:
       - count < 3 (need ≥3 for feature)
       - no negative scenario (need ≥1)
       AI musi dodać:
         {text: "Given empty cart, when checkout, then 400", scenario_type: "negative"}
         {text: "Given invalid product_id, when add to order, then 404", scenario_type: "edge_case"}
VERIFY: Approved plan ma ≥3 AC per feature task, ≥1 negative.
FAIL IF: Plan approved z only-positive AC.
```

### TS-P-002: Instruction zbyt ogólna (cold-start test fail)

```
GIVEN: Task instruction: "Implement caching"
WHEN:  Cold-start test: wklej instruction w blank context
THEN:  Agent NIE WIE jaki plik otworzyć pierwszy.
       Plan REJECTED: "Instruction too vague — no file paths, no patterns."
VERIFY: Instruction zawiera: exact files to create, files to modify, pattern to follow.
FAIL IF: Instruction bez file paths przechodzi planning gate.
```

### TS-P-003: Dependency produces mismatch

```
GIVEN: T-001 produces: {model: "Order(id, items, total)"}
       T-002 depends_on: [T-001], instruction: "Use User model from T-001"
WHEN:  Planning validation
THEN:  BLOCKS: "T-002 references 'User model from T-001' but T-001 produces 'Order model'"
VERIFY: uses_from_dependencies matches produces of dependencies.
FAIL IF: Broken contract between tasks undetected.
```

### TS-P-004: Coverage gap — requirement not in any task

```
GIVEN: 15 requirements, plan covers 13
WHEN:  draft-plan z coverage: [...13 COVERED...]
THEN:  BLOCKS: "2 requirements MISSING: K-014, K-015"
       AI musi: COVERED (add task) lub DEFERRED (z reason) lub OUT_OF_SCOPE (z reason).
VERIFY: coverage has status for EVERY requirement. No MISSING.
FAIL IF: Plan approved z requirements bez coverage status.
```

### TS-P-005: 5+ HIGH severity assumptions

```
GIVEN: Plan z 6 HIGH severity assumptions
WHEN:  draft-plan --assumptions [...]
THEN:  BLOCKS: "6 HIGH assumptions exceed limit (max 4). Resolve before planning."
VERIFY: Gate counts HIGH assumptions and blocks at ≥5.
FAIL IF: Plan approved z 5+ HIGH assumptions.
```

### TS-P-006: Feature registry conflict — duplicate endpoint

```
GIVEN: T-003 (DONE) registered: POST /api/orders
       New plan: T-010 creates POST /api/orders (same route)
WHEN:  draft-plan validation
THEN:  WARNING: "T-010 creates POST /api/orders which already exists (T-003).
       Duplicate or intentional override?"
VERIFY: Feature registry detects collision. Operator must acknowledge.
FAIL IF: Duplicate endpoint goes undetected.
```

---

## FAZA 4: Prompt Assembly — co AI dostaje

### TS-PA-001: MUST guideline zawsze w promptcie

```
GIVEN: G-001 [MUST, scope: backend]: "Firestore only"
       Task T-005 scopes: [backend]
WHEN:  GET /execute assembles prompt
THEN:  G-001 IN prompt.
       prompt_elements: {source: "G-001", included: true, reason: "scope_match:backend"}
VERIFY: Read prompt_elements WHERE execution_id=X AND source_external_id="G-001"
        → included=true.
FAIL IF: MUST guideline missing from prompt of matching-scope task.
```

### TS-PA-002: MUST guideline z innego scope NIE w promptcie

```
GIVEN: G-007 [MUST, scope: frontend]: "Use React hooks"
       Task T-005 scopes: [backend]
WHEN:  GET /execute
THEN:  G-007 NOT IN prompt.
       prompt_elements: {source: "G-007", included: false, 
                         exclusion_reason: "scope_mismatch:frontend∉[backend,general]"}
VERIFY: prompt_elements shows excluded with reason.
FAIL IF: Frontend guideline in backend task prompt. OR: exclusion not recorded.
```

### TS-PA-003: Budget overflow — SHOULD guidelines removed

```
GIVEN: 30KB of MUST guidelines + 15KB task content + 10KB knowledge = 55KB
       Budget: 50KB
WHEN:  GET /execute
THEN:  SHOULD guidelines EXCLUDED (60% > 50KB after P1-P3).
       prompt_elements: SHOULD entries with exclusion_reason: "budget_exceeded"
VERIFY: MUST and required knowledge PRESERVED. SHOULD removed. Total ≤ budget.
FAIL IF: MUST content truncated. OR: budget exceeded without SHOULD removal.
```

### TS-PA-004: P1 overflow — prompt cannot be assembled

```
GIVEN: 50 MUST guidelines totaling 80KB. Budget: 50KB.
WHEN:  GET /execute
THEN:  ERROR: "P1 sections (80KB) exceed 70% of budget (35KB). 
       Cannot assemble prompt. Reduce MUST guidelines or increase budget."
       Execution NOT created.
VERIFY: HTTP 422. No execution in DB. Clear error message.
FAIL IF: Prompt assembled with 80KB P1 (exceeds context window).
```

### TS-PA-005: Kontrakt operacyjny (global guidelines) ZAWSZE w promptcie

```
GIVEN: Kontrakt operacyjny = global guideline [MUST, scope: general]
WHEN:  GET /execute for ANY task (feature, bug, chore, investigation)
THEN:  Kontrakt operacyjny IN prompt.
       Sekcja: "OPERATIONAL CONTRACT — always applies"
VERIFY: EVERY execution has operational contract in prompt_elements.
        Nigdy excluded.
FAIL IF: Any execution without operational contract in prompt.
```

### TS-PA-006: Dependency context zawiera produces z ukończonego taska

```
GIVEN: T-003 (DONE) produces: {endpoint: "GET /api/pool/status"}
       T-005 depends_on: [T-003]
WHEN:  GET /execute for T-005
THEN:  Prompt sekcja "dependency_context" zawiera:
       "T-003 produces: GET /api/pool/status"
       + changes from T-003 (files modified, summaries)
VERIFY: prompt_elements z source_table="tasks", source_id=T-003.
FAIL IF: Dependency output missing from prompt.
```

### TS-PA-007: Unverified assumptions z poprzednich tasków w promptcie

```
GIVEN: T-003 delivery miała assumption: "Redis on localhost:6379, UNVERIFIED"
       T-005 modyfikuje pliki które assumption dotyczy
WHEN:  GET /execute for T-005
THEN:  Prompt zawiera sekcję: "⚠ Unverified assumptions from prior tasks:
       T-003 assumed Redis on localhost:6379 — NOT VERIFIED. Verify or refute."
VERIFY: Agent memory assumption propagated to prompt.
FAIL IF: AI starts T-005 without knowing about unverified assumption.
```

### TS-PA-008: Agent memory — mistakes propagated

```
GIVEN: Agent made mistake in T-003: "forgot to update .env.example after adding env var"
       T-005 instruction modifies config.py (adds REDIS_URL)
WHEN:  GET /execute for T-005
THEN:  Prompt contains: "⚠ Pattern from your prior work: In T-003 you forgot 
       to update .env.example after adding env var. Don't forget this time."
VERIFY: Agent memory mistake appears in prompt when relevant files overlap.
FAIL IF: AI repeats same mistake because system didn't warn.
```

---

## FAZA 5: Execution — AI pracuje

### TS-E-001: AI próbuje modyfikować plik z exclusion

```
GIVEN: Task T-005 exclusions: ["DO NOT modify db/pool.py"]
WHEN:  AI calls forge_check_ownership("db/pool.py")
THEN:  Response: {can_modify: false, reason: "exclusion in T-005"}
       Jeśli AI mimo to modyfikuje → delivery validation detects unplanned file.
VERIFY: forge_check_ownership returns correct ownership info.
        Delivery with unplanned files gets WARNING.
FAIL IF: AI modifies excluded file without any detection.
```

### TS-E-002: AI odkrywa bug w innym pliku (finding)

```
GIVEN: AI implementuje cache, czyta pool.py, widzi brak reconnect handling
WHEN:  AI calls forge_finding({type: "bug", severity: "HIGH", 
       title: "pool.py no reconnect", file_path: "db/pool.py:78", 
       evidence: "no try/except on connection acquisition"})
THEN:  Finding F-001 created w DB.
       Status: OPEN. Notification do user: "Finding HIGH severity."
       Finding NIE blokuje current task. AI kontynuuje.
VERIFY: Finding in DB. Notification delivered. Task continues.
FAIL IF: Finding lost. OR: Finding blocks current task execution.
```

### TS-E-003: Heartbeat expiry (AI crash)

```
GIVEN: Execution started, lease_expires_at = now + 30min
WHEN:  30 min passes without heartbeat (AI crashed)
THEN:  Cron job fn_expire_stale_executions:
       Execution → EXPIRED. Task → TODO. Available for next GET /execute.
VERIFY: Task status back to TODO. New agent can claim.
FAIL IF: Task stuck in IN_PROGRESS forever after AI crash.
```

### TS-E-004: Pre-flight check detects problem

```
GIVEN: Task T-005 instruction: "Add Redis caching"
WHEN:  AI calls forge_plan({
         files_to_modify: ["config.py"],
         questions: ["'Add caching' — read-only or read-write?"]
       })
THEN:  System: 
       - Impact check: "config.py imported by 4 files"
       - Question → creates OPEN decision D-NNN
       - Response: "Question recorded as D-014. Proceed with assumption or wait for answer?"
VERIFY: Decision created. AI informed about impact.
FAIL IF: Question silently ignored. OR: impact not reported.
```

### TS-E-005: Mid-execution decision

```
GIVEN: AI implementing cache, discovers aioredis vs redis-py choice
WHEN:  AI calls forge_decision({type: "implementation", 
       issue: "Redis client: redis-py vs aioredis",
       recommendation: "redis-py — aioredis deprecated",
       reasoning: "aioredis last release 2023, redis-py 5.x supports async"})
THEN:  Decision D-NNN created. Linked to current execution.
       Available in prompt for future tasks via forge_prior_decisions("cache").
VERIFY: Decision in DB. execution_id set. Retrievable via prior_decisions.
FAIL IF: Decision lost. OR: not linked to execution.
```

---

## FAZA 6: Delivery — AI oddaje wyniki

### TS-D-001: Filler reasoning rejected

```
GIVEN: Contract requires reasoning min_length: 100, must_reference_file: true
WHEN:  AI delivers reasoning: "Implemented the caching layer following best practices 
       and ensuring all requirements are met with proper testing and validation."
       (96 chars, no file reference)
THEN:  REJECTED: 
       - length: 96 < 100 → FAIL
       - must_reference_file: no file path found → FAIL
VERIFY: HTTP 422. Validation shows both failures. AI must resubmit.
FAIL IF: Filler reasoning accepted.
```

### TS-D-002: AC evidence z nieistniejącym testem

```
GIVEN: AC evidence: {ac_index: 0, verdict: "PASS", 
       evidence: "tests/test_cache.py::test_hit — 3ms avg"}
WHEN:  Mechanical AC verification runs
THEN:  System runs: pytest tests/test_cache.py::test_hit
       IF test exists and passes → PASS
       IF test doesn't exist → FAIL: "test file not found"
       IF test fails → FAIL: "test returned exit code 1"
VERIFY: Mechanical verification catches non-existent test.
FAIL IF: Evidence accepted for non-existent test.
```

### TS-D-003: Copy-paste evidence across ACs

```
GIVEN: 3 AC, evidence for all three is identical: "test passes and works correctly"
WHEN:  Anti-pattern check: copy_paste_evidence
THEN:  REJECTED: "AC evidence pairwise similarity > 0.8. 
       Each AC must have unique evidence."
VERIFY: difflib.SequenceMatcher detects similarity ≥ 0.8.
FAIL IF: Identical evidence for different ACs accepted.
```

### TS-D-004: Delivery without negative AC pass

```
GIVEN: 3 AC: 2 positive (PASS), 1 negative (FAIL)
WHEN:  Delivery validation
THEN:  REJECTED: "negative AC verdict is FAIL — must pass."
       ALSO rejected if: 3 AC all positive, none negative → composition check fails.
VERIFY: AC composition enforced: ≥1 negative must PASS.
FAIL IF: All-positive-only delivery accepted for feature task.
```

### TS-D-005: Kontrakt operacyjny — assumption ujawnione

```
GIVEN: Contract includes operational contract (always in prompt)
WHEN:  AI delivers with assumptions: [
         {statement: "Redis on localhost:6379", verified: false, 
          severity: "HIGH", if_wrong: "App crash at startup"}
       ]
THEN:  System:
       - Records assumption in task_assumptions / execution JSONB
       - Propagates to future tasks touching affected files
       - Notification: "Unverified HIGH assumption from T-005"
VERIFY: Assumption persisted. Shows up in next task's prompt (TS-PA-007).
FAIL IF: Assumption lost. OR: not propagated to future tasks.
```

### TS-D-006: Kontrakt operacyjny — partial implementation ujawnione

```
GIVEN: AI delivers with partial_implementation: {
         omitted_elements: [{
           element: "Cache invalidation on write",
           why_omitted: "Requires event bus (T-008)",
           risk_without: "Stale data up to TTL",
           completion_plan: "After T-008, add invalidate() in PUT handler"
         }],
         is_functional_without_omitted: true
       }
THEN:  ACCEPTED (functional without omitted).
       System auto-creates blocked task: 
       "Complete: cache invalidation" depends_on: [T-008]
       WARNING on objective KR tracking.
VERIFY: New task created from omitted element. Depends on T-008.
FAIL IF: Omitted element forgotten. No follow-up task.
```

### TS-D-007: Kontrakt operacyjny — partial implementation NONFUNCTIONAL

```
GIVEN: AI delivers with partial_implementation: {
         is_functional_without_omitted: false
       }
WHEN:  Delivery validation
THEN:  REJECTED: "Delivery is nonfunctional without omitted elements. 
       Cannot accept nonfunctional code."
VERIFY: HTTP 422. Nonfunctional partial delivery blocked.
FAIL IF: Nonfunctional code accepted as DONE.
```

### TS-D-008: Kontrakt operacyjny — scope interpretation z ambiguity

```
GIVEN: AI delivers with scope_interpretation: {
         chosen: "Read-through cache only",
         instruction_ambiguities: ["'Add caching' doesn't specify read vs write"]
       }
THEN:  System creates OPEN decision (type=clarification):
       "Instruction ambiguity: 'Add caching' — read or write? AI chose read-only."
       Notification to user.
       Jeśli user wybierze write-through → task wraca do TODO z updated instruction.
VERIFY: Ambiguity → OPEN decision → user resolves.
FAIL IF: Ambiguity silently resolved by AI without decision.
```

### TS-D-009: Kontrakt operacyjny — impact analysis z unchecked files

```
GIVEN: AI delivers with impact_analysis: {
         files_not_checked: [{
           path: "api/reports.py", 
           reason: "imports config.py but not in task scope",
           risk: "May break if REDIS_URL env var missing"
         }]
       }
THEN:  System creates finding (type=risk).
       Next task touching api/reports.py gets test scenario:
       "Verify no regression from T-005 config.py changes"
VERIFY: Finding created. Test scenario appears in future task prompt.
FAIL IF: Unchecked file risk forgotten.
```

### TS-D-010: Kontrakt operacyjny — confidence < 0.5

```
GIVEN: AI delivers with confidence: {overall: 0.3, unverified_claims: [...]}
WHEN:  Delivery validation
THEN:  ACCEPTED but task marked needs_review: true.
       Notification to operator: "T-005 delivery has LOW confidence (0.3). Review recommended."
       Unverified claims → OPEN decisions (type=verification_needed).
VERIFY: needs_review flag set. Operator notified. Claims tracked.
FAIL IF: Low confidence delivery passes without review flag.
```

### TS-D-011: Kontrakt operacyjny — propagation check z missed update

```
GIVEN: AI adds REDIS_URL to config.py. 
       propagation_check.should_also_update includes .env.example (updated: false)
WHEN:  Delivery validation
THEN:  System creates finding: ".env.example should be updated with REDIS_URL"
       System mechanically verifies: grep REDIS_URL .env.example → not found → confirms.
       Finding appears in next relevant task.
VERIFY: Finding created. Mechanical grep confirms missing.
FAIL IF: Missing update undetected. OR: finding not created.
```

### TS-D-012: Max attempts exceeded

```
GIVEN: Delivery REJECTED 5 times (max_attempts=5)
WHEN:  5th rejection
THEN:  Execution → FAILED. Task → FAILED.
       Notification: "T-005 failed after 5 delivery attempts. Operator must decide."
       Operator options: re-assign, rewrite instruction, skip.
VERIFY: Task FAILED. Not stuck in infinite rejection loop.
FAIL IF: 6th attempt allowed. OR: task stuck in IN_PROGRESS.
```

### TS-D-013: Resubmit with padding detected

```
GIVEN: Attempt 1 REJECTED: reasoning too short (80 chars).
       Attempt 2: AI adds " This ensures correctness." (now 105 chars).
       Same check (reasoning length) was the failure.
       Text diff between attempt 1 and 2 < 20%.
WHEN:  Resubmit detection
THEN:  WARNING: "Insufficient changes since last rejection. Same check failed."
       (Not auto-REJECT — AI might need to just add a sentence. But WARNING logged.)
VERIFY: Warning in validation result. Logged in execution_attempts.
FAIL IF: Padding not detected at all. OR: auto-rejected without nuance.
```

---

## FAZA 7: Test Scenarios auto-generated

### TS-TS-001: MUST guideline → test scenario created

```
GIVEN: G-001 [MUST, scope: backend]: "All data through StorageAdapter"
       Task T-005 scopes: [backend]
WHEN:  Plan approved → fn_generate_test_scenarios(T-005)
THEN:  TS-001 created: {
         source_type: "guideline_compliance", source_id: G-001,
         title: "Compliance: StorageAdapter Protocol",
         verification: "grep_check", verification_detail: "StorageAdapter"
       }
VERIFY: TS exists in DB linked to task. Shows in prompt.
FAIL IF: MUST guideline has no corresponding test scenario.
```

### TS-TS-002: HIGH risk → test scenario created

```
GIVEN: D-010 (type=risk, severity=HIGH): "Redis SPOF"
       Linked to idea I-001, T-005 origin=I-001
WHEN:  fn_generate_test_scenarios(T-005)
THEN:  TS-002 created: {
         source_type: "risk_mitigation", source_id: D-010,
         title: "Risk: Redis SPOF mitigation"
       }
VERIFY: HIGH risk → test scenario. AI must provide evidence of mitigation.
FAIL IF: HIGH risk without test scenario.
```

### TS-TS-003: Scenario cap (max 10 per task)

```
GIVEN: 15 MUST guidelines + 5 HIGH risks = 20 potential scenarios
WHEN:  fn_generate_test_scenarios
THEN:  Top 10 created (HIGH risks first, then MUST guidelines by relevance).
       Remaining 10 logged as excluded with reason.
VERIFY: ≤10 TS per task. Excluded list available in execution metadata.
FAIL IF: 20 scenarios created (overload). OR: HIGH risks excluded before guidelines.
```

### TS-TS-004: grep_check false positive — import without implementation

```
GIVEN: TS-001 verification: grep_check for "StorageAdapter"
       AI imports StorageAdapter but class doesn't implement it
WHEN:  Delivery validation runs grep on diff
THEN:  grep finds "StorageAdapter" → TS-001 PASS.
       BUT: this is false positive — import ≠ implementation.
VERIFY: Document that grep_check is heuristic, not verification.
        MUST guidelines should ALSO have AC with verification=test (not just grep).
FAIL IF: N/A — this is KNOWN LIMITATION, not a bug. grep_check is proxy.
```

---

## FAZA 8: Skills — wymienialność i stosowanie

### TS-SK-001: Skill załadowany do promptu we właściwym momencie

```
GIVEN: Task type=feature, skill "plan" registered in skills table
WHEN:  Planning phase (POST /plans/draft)
THEN:  Skill "plan" content in prompt assembly.
       Skill "ac-generation" content ALSO in prompt.
       prompt_elements: {source_table: "skills", source_id: skill_plan.id}
VERIFY: Correct skill loaded for correct phase. Recorded in prompt_elements.
FAIL IF: Wrong skill loaded. OR: no skill loaded. OR: skill not recorded.
```

### TS-SK-002: Skill wymiana — nowa wersja zastępuje starą

```
GIVEN: Skill "plan" version 1 in DB.
       Operator updates to version 2 (different AC rules).
WHEN:  Next plan uses skill
THEN:  Version 2 loaded. Prompt_elements: source_version=2.
       Previous plans' prompt_elements still show version=1 (historical record).
VERIFY: Latest version used. Historical versions preserved in snapshots.
FAIL IF: Old version used. OR: historical snapshots changed.
```

### TS-SK-003: Skill per task type

```
GIVEN: Task type=investigation
WHEN:  GET /execute
THEN:  Skill "execute" loaded (generic execution procedure).
       NOT skill "plan" (planning, not execution).
       Ceremony level = LIGHT (investigation).
       Contract = minimal (reasoning only, no AC evidence required).
VERIFY: Correct skill for task type. Correct ceremony. Correct contract.
FAIL IF: Feature skill loaded for investigation task.
```

### TS-SK-004: Missing skill — graceful fallback

```
GIVEN: Task references skill "deep-verify" but it's not in skills table
WHEN:  GET /execute
THEN:  System proceeds WITHOUT skill content. 
       WARNING: "Skill 'deep-verify' not found. Proceeding without skill guidance."
       prompt_elements: {source_table: "skills", included: false, 
                         exclusion_reason: "skill_not_found"}
VERIFY: No crash. Warning logged. Execution proceeds.
FAIL IF: Crash on missing skill. OR: silent missing (no warning).
```

---

## FAZA 9: Zmiany w trakcie projektu

### TS-CH-001: Nowy requirement w trakcie execution

```
GIVEN: 5 tasks planned, T-003 in progress
WHEN:  User: "Klient dodał wymaganie: eksport do PDF"
THEN:  AI/user creates K-NNN (new requirement).
       Impact assessment: "New requirement, not covered by existing tasks."
       Options: add task to current plan, create new objective.
       Coverage updated: K-NEW → COVERED by T-NEW or DEFERRED.
VERIFY: Requirement tracked. Task created or deferred with reason.
FAIL IF: Requirement mentioned but not tracked. OR: no impact assessment.
```

### TS-CH-002: Zmieniony requirement — task already DONE

```
GIVEN: T-001 (DONE) implemented K-001: "Orders have 3 statuses"
       Requirement changes to: "Orders have 5 statuses"
WHEN:  User: "Requirement K-001 changed"
THEN:  K-001 content updated (new version created).
       Impact: "T-001 (DONE) implemented old version of K-001."
       Decision: "T-001 needs rework. Reset to TODO?"
       Notification to user.
VERIFY: K version incremented. Impact assessed. User decides.
FAIL IF: Changed requirement not affecting completed task detected.
```

### TS-CH-003: Usunięty requirement

```
GIVEN: K-010 "CSV export" linked to T-004 (TODO)
WHEN:  User: "K-010 no longer needed"
THEN:  K-010 status → DEPRECATED.
       T-004: "Primary requirement deprecated. Skip task?"
       Coverage: K-010 → removed from coverage tracking.
VERIFY: Task identified for skip. Coverage updated.
FAIL IF: Task T-004 executed for deprecated requirement.
```

### TS-CH-004: Priorytetyzacja — zmiana kolejności

```
GIVEN: O-001 tasks: T-001..T-005. O-002 tasks: T-006..T-010.
       Current execution: T-003 (O-001) in progress.
WHEN:  User: "O-002 jest pilniejsze niż O-001"
THEN:  After T-003 completes → next task from O-002 (T-006), not O-001 (T-004).
       Dependencies respected (T-006 might depend on something from O-001).
       If dependency conflict → notification: "T-006 depends on T-004 (O-001). 
       Must complete T-004 first."
VERIFY: Task ordering reflects priority. Dependencies enforced.
FAIL IF: Priority change ignored. OR: dependency violation.
```

### TS-CH-005: Nowa guideline narzucona w trakcie projektu

```
GIVEN: Project in progress, 8/15 tasks DONE
WHEN:  User: "Nowa wytyczna: wszystkie endpointy muszą mieć rate limiting"
       → POST /guidelines [{title: "Rate limiting on all endpoints", 
                            weight: "must", scope: "api"}]
THEN:  New guideline G-NEW created.
       System checks: 8 DONE tasks — any affected? 
       "T-002, T-005 created endpoints WITHOUT rate limiting."
       Finding for each: "Existing endpoint may need rate limiting (new guideline G-NEW)"
       Future tasks in scope "api" → G-NEW in prompt.
       Test scenarios generated for remaining tasks.
VERIFY: New guideline propagated to future tasks.
        Existing DONE tasks flagged for potential rework.
FAIL IF: New guideline only applies to future tasks without checking past.
```

---

## FAZA 10: Kontrakt operacyjny — systematic testing

### TS-OC-001: AI ujawnia assumption vs AI milczy

```
GIVEN: Same task, same instruction. Two executions.
       Execution A: AI delivers assumptions: [{statement: "Redis on localhost"}]
       Execution B: AI delivers NO assumptions (empty)
WHEN:  Both delivered
THEN:  Execution A: assumption recorded, propagated.
       Execution B: NO explicit assumption.
       System cannot force AI to list assumptions — but CAN track:
       "Execution B had 0 assumptions. Pattern: 60% of this agent's deliveries have 0 assumptions. 
       Trust score impact."
VERIFY: System detects absence of operational contract fields over time.
FAIL IF: System has no mechanism to detect pattern of empty optional fields.
```

### TS-OC-002: Kontrakt operacyjny w KAŻDYM promptcie

```
GIVEN: 50 tasks in project, various types and ceremony levels
WHEN:  GET /execute for EACH task
THEN:  EVERY prompt contains operational contract section.
       Prompt_elements: {source_table: "guidelines", source_external_id: "G-OPERATIONAL",
                         included: true, selection_reason: "global_always"}
VERIFY: 50/50 executions have operational contract in prompt.
FAIL IF: Any execution missing operational contract.
```

### TS-OC-003: Zasada asymetrii — discovered assumption after 5 tasks

```
GIVEN: T-005 made silent assumption "single-tenant" (not declared).
       T-006, T-007, T-008, T-009, T-010 built on this assumption.
       T-011: AI discovers "wait, this might need multi-tenant support"
WHEN:  AI delivers T-011 with assumption: {statement: "single-tenant", verified: false,
       if_wrong: "T-006 through T-010 all assume single-tenant. Rework needed."}
THEN:  System flags: "Late-discovered assumption. 5 tasks potentially affected."
       Creates findings for T-006..T-010: "May need rework if multi-tenant."
       Notification to user: "Architectural assumption discovered late. Review needed."
VERIFY: System creates findings for affected tasks. User notified.
FAIL IF: Late assumption only noted for T-011, not propagated back to T-006-T-010.
```

---

## FAZA 11: Completeness — co JESZCZE powinno być testowane

### Nie przetestowane w powyższych scenariuszach:

**Multi-agent:**
- TS-MA-001: Dwa agenty claimują ten sam task → SELECT FOR UPDATE SKIP LOCKED
- TS-MA-002: Agent A's memory vs Agent B's memory — are they isolated?
- TS-MA-003: Agent A creates finding about Agent B's work — proper attribution?

**Web UI consistency:**
- TS-UI-001: Web UI shows same data as API (no cache staleness)
- TS-UI-002: Prompt inspector shows ALL elements (included + excluded) with reasons
- TS-UI-003: Finding triage in Web UI → creates task → task visible in pipeline
- TS-UI-004: Audit trail is complete and chronological

**Error handling:**
- TS-ERR-001: Database connection lost mid-delivery → transaction rollback, no partial state
- TS-ERR-002: MCP Server crash → Claude Code gets error → can retry
- TS-ERR-003: API restart during execution → stateless, execution continues
- TS-ERR-004: Malformed JSON in delivery → 400 Bad Request, not 500

**Performance:**
- TS-PERF-001: Prompt assembly < 2 seconds for task with 20 guidelines + 30 knowledge
- TS-PERF-002: Delivery validation < 3 seconds for delivery with 20 changes
- TS-PERF-003: File index generation < 5 seconds for 100-file project

**Data integrity:**
- TS-DI-001: Delete task → dependencies CASCADE, execution RESTRICT
- TS-DI-002: FK violation on bogus reference → 422, not 500
- TS-DI-003: Concurrent delivery for same execution → only one accepted

**Security / roles:**
- TS-SEC-001: Executor role calls POST /findings/{id}/triage → 403 Forbidden
- TS-SEC-002: Readonly role calls POST /deliver → 403 Forbidden
- TS-SEC-003: Expired API key → 401 Unauthorized

**End-to-end flow:**
- TS-E2E-001: Full pipeline: ingest doc → analyze → plan → execute 3 tasks → all DONE → objective ACHIEVED
- TS-E2E-002: Full pipeline with mid-flight change request: add requirement after 2 tasks done
- TS-E2E-003: Full pipeline with finding triage: AI finds bug → operator approves → new task → completed
- TS-E2E-004: Full pipeline with guideline added mid-project: retroactive impact check

**Edge cases not covered:**
- TS-EDGE-001: Empty project (no tasks) → status shows "no tasks, create plan"
- TS-EDGE-002: All tasks SKIPPED → objective status? (not ACHIEVED, not FAILED)
- TS-EDGE-003: Circular reference in knowledge dependencies (K-001 depends on K-002 depends on K-001)
- TS-EDGE-004: Task with 0 AC (chore type) → delivery requires only reasoning
- TS-EDGE-005: Same file modified by 3 sequential tasks → impact compounds
- TS-EDGE-006: Objective with all KRs ACHIEVED but tasks still TODO → inconsistency
- TS-EDGE-007: Finding triage creates task that conflicts with running task
- TS-EDGE-008: User modifies code outside Forge, commits directly → git diff includes non-AI changes
