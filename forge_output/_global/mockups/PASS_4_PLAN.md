# Pass 4 plan — kierunek: redukcja + mechanical enforcement

**Data:** 2026-04-19 (przepisany)
**Bazuje na:** `MOCKUP_SYNTHESIS.md` + 4 katalogi (Part A/B/C/D, 45 mockupów) + `PASS_2_RISK_REPORT.md` + `PASS_3_RISK_REPORT.md`
**Zmiana kierunku:** zamiast dodawać 7 nowych mockupów (poprzednia wersja planu), **zredukować i wzmocnić mechanicznie**.

## Dlaczego nie dodajemy mockupów

Pass 2 zostawił 4 HIGH otwarte. Pass 3 nie zamknął żadnego, zmitygował H#4 w ~60%, otworzył 3 nowe. Cross-cutting wzorzec: **"Forge surfaces the gap, then lets the user proceed anyway."** Counterweight jest deklaratywny, nie blokujący — 13/38 mockupów ma informational counterweight który POWINIEN być blocking.

Trzy systemowe luki, których kolejne mockupy nie zamkną:
1. **Enforcement gap** — design contract zadeklarowany, nie wymuszony mechanicznie.
2. **Fidelity gap** — ~15% mockupów mapuje się do istniejącego kodu; 19 implied DB columns nie istnieje.
3. **Single-user assumption** — 0/38 mockupów adresuje concurrent edits, OOO escalation, findings dedup.

---

## Pass 4 — 8 obszarów, 5 faz

### Obszar (a) — Redukcja 38 → 12 core mockupów (state machines, nie happy-path strony)

Każdy mockup reprezentuje **pełen state machine**, nie jeden szczęśliwy ekran. Mapowanie:

| Nowy core mockup | Zastępuje (zachowując treść) | Stany do pokazania |
|---|---|---|
| 1. project-shell | `01-dashboard`, `02-project-empty`, `02v2-project-kb` | EMPTY / RUNNING / NEEDS_YOU / BLOCKED / DONE / ARCHIVED |
| 2. kb-source | 4× `02v2-add-source-*`, `02v2-source-preview` | DRAFT / INGESTING / EMBEDDED / CONFLICTED / STALE / EXCLUDED / ARCHIVED |
| 3. objective-shell | `03v2-create-objective`, `09-objective-detail`, `09-reopen` | DRAFT / ACTIVE / BLOCKED_AMBIGUITY / IN_ANALYSIS / IN_PLANNING / IN_DEVELOP / DONE_WITH_DEBT / ACHIEVED / REOPENED |
| 4. objective-dag | `03v2-objectives-dag`, `09-edit-dependencies` | view + edit + concurrent-edit conflict |
| 5. ambiguity | `09-answer-ambiguity`, `09-add-ac`, `09-add-scenario` | OPEN / IN_REVIEW / RESOLVED / DEFERRED / IGNORED + AC INVENTED variant (blocking) |
| 6. challenger-checks | `09-edit-challenger-checks` | edit + hit-rate decay alert |
| 7. task-create | `07-new-task`, `07-mode-selector`, `07-crafter-preview` | DRAFT / READY / RUNNING + mode comparison + cost-cap blocking |
| 8. orchestrate-live | `04-orchestrate-live`, `05v2-scenario-generate` | TODO / CLAIMING / IN_PROGRESS / PAUSED / CANCELLED / FAILED / DONE + per-phase timeout |
| 9. task-deliverable | 5× `05v2-*-deliverable` (jako body-variants), `05v2-create-followup-task` | DRAFT / DONE / DONE_WITH_CONCERNS / NEEDS_REVIEW / CLOSED + 4 task-type bodies |
| 10. close + audit | `05v2-close-task`, `05v2-assign-auditor`, `05v2-auditor-inbox`, `05v2-auditor-review` | OPEN / DEFERRED / CLOSED + assigning / awaiting / verdict + 4-verdict z TTL |
| 11. autonomy + governance | `12-project-config`, `12-skills-tab`, `12-hooks-tab`, `12-add-hook`, `12-phase-defaults-tab`, `11-skills-library`, `11-skill-edit` | L1 → L5 promotion criteria + watchlist + replay preview + veto |
| 12. ai-sidebar + modal | `16-ai-sidebar`, `16-preview-apply-modal` | demoted: tylko `witness` (stream) + `ask` (collapsed) |

**Co usuwamy:** wszystkie v1 superseded (`05-task-deliverable`, `02-project-empty` jeśli nie merge'owany do project-shell, `03-project-post-analyze`). `flow.html` zostaje jako reference.

**Wyjście Pass 4:** 12 core mockupów + 1 deprecation note. Nie ~52.

---

### Obszar (b) — Blocking enum na counterweight items (zamiast "skeptical UX" → "blocking UX")

Każdy counterweight item dostaje klasyfikację:

```ts
type CounterweightSeverity =
  | "informational"   // wyświetlane, można pominąć
  | "warning"         // amber banner, można pominąć z reason
  | "blocking"        // czerwony banner, akcja niemożliwa
  | "requires_override"  // czerwony, wymaga reason ≥50 chars + signed_by + audit log
```

**Konkretne reklasyfikacje (z risk reportów):**
- INVENTED AC → `blocking` (zamyka H5)
- Unsourced documentation paragraph → `blocking` (zamyka H5)
- Deferred HIGH finding gdy projekt ma >5 deferred HIGH >30d → `requires_override` (zamyka H3)
- KB folder ingest gdy regex znajdzie `.env|*.key|*.pem|*.aws/` → `blocking` (zamyka H1)
- Plan approve gdy `aggregate_cost_usd > project.plan_cost_cap_usd` → `requires_override` (zamyka MED z Pass 3)
- Scenario-gen phase wallclock > limit → `blocking` (zamyka H2)

**Mechanika:** każdy override pisze do nowej tabeli `final_actions_log`:
```sql
CREATE TABLE final_actions_log (
  id BIGSERIAL PRIMARY KEY,
  action_type VARCHAR(50) NOT NULL,         -- np. 'override_invented_ac'
  entity_table VARCHAR(50) NOT NULL,
  entity_id INTEGER NOT NULL,
  before_state_hash VARCHAR(64) NOT NULL,
  reason TEXT NOT NULL CHECK (length(reason) >= 50),
  actor_id VARCHAR(100) NOT NULL,
  signed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  client_ip INET,
  client_ua TEXT
);
```

To zastępuje 5 osobnych "audit log" rozproszeń — 1 tabela, jedno API.

---

### Obszar (c) — Verdict z TTL + evidence-hash-on-read (zamyka H4 + H6 jednym designem)

Zmiana w `manual_verification_task` (planowane od dawna jako nowa tabela — teraz z pełnym kontraktem):

```sql
CREATE TABLE manual_verification_task (
  id BIGSERIAL PRIMARY KEY,
  task_id INTEGER REFERENCES tasks(id),
  ac_id INTEGER REFERENCES acceptance_criteria(id),
  assignee_email VARCHAR(255) NOT NULL,
  scope_ac_ids INTEGER[] NOT NULL,            -- enforced przy file-preview API
  assigned_at TIMESTAMP WITH TIME ZONE NOT NULL,
  due_at TIMESTAMP WITH TIME ZONE NOT NULL,
  status VARCHAR(20) NOT NULL,                -- ASSIGNED / IN_REVIEW / SUBMITTED / EXPIRED
  verdict VARCHAR(30),                        -- PASSED_WITH_EVIDENCE / PASSED_ATTESTATION / REJECTED / NEEDS_CLARIFICATION
  -- Evidence chain
  evidence_files JSONB,                       -- [{filename, content_hash, immutable_storage_url, captured_at}]
  evidence_text TEXT,
  evidence_text_hash VARCHAR(64),
  code_commit_hash VARCHAR(64) NOT NULL,      -- snapshot kodu w momencie audytu
  -- TTL + revalidation
  revalidation_due_at TIMESTAMP WITH TIME ZONE,  -- NOT NULL gdy verdict='PASSED_ATTESTATION' + AC.tags ⊃ {hipaa,soc2,pci}
  revalidation_class VARCHAR(20),             -- PERMANENT / REQUIRES_REVALIDATION / PROVISIONAL
  -- Forensics
  signed_by VARCHAR(255),
  signed_at TIMESTAMP WITH TIME ZONE,
  client_ip INET,
  client_ua TEXT
);
```

**Re-verification on read:** każdy widok werdyktu w UI **najpierw** woła `GET /verdict/{id}/verify-hashes` który:
- pobiera plik z immutable storage
- liczy SHA256
- porównuje z `evidence_files[].content_hash`
- zwraca `HASH_MATCH | HASH_MISMATCH | FILE_GONE`
- jeśli mismatch → render verdict z czerwonym banerem "Evidence integrity broken — re-verify needed"

**TTL daemon:** scheduled job co 24h przegląda `revalidation_due_at < now()` → flip status na `EXPIRED`, spawn nowy `manual_verification_task` z linkiem do oryginalnego.

**S3 object-lock:** `evidence_files[].immutable_storage_url` musi wskazywać na bucket z `Object Lock = Compliance Mode`. Nie da się nadpisać ani usunąć przez TTL.

---

### Obszar (d) — Multi-user as first-class (cross-cutting invariant, nie nowy mockup)

Dodać do każdego mutable entity:
- `version` (INTEGER) — incrementowany przy każdym update
- `updated_by` (VARCHAR) — kto ostatnio edytował
- `updated_at` (TIMESTAMP) — kiedy

API kontrakt: każdy `PATCH/PUT` przyjmuje `If-Match: version=N` header. Jeśli stale → `409 Conflict` z payloadem `{current_version, current_state, your_version, conflict_fields}`.

**UI side:** reusable conflict-modal komponent (jeden mockup w obszarze 12 — `16-conflict-modal`):
- "Someone else edited this. Reload to see changes, or override (your changes will replace theirs — they will be notified)."
- Dwie akcje: `Reload` | `Override + notify`

**Findings-similarity matcher:** przy tworzeniu nowego finding, jeśli `cosine_similarity(new.text, existing.text) > 0.8` → modal "Looks similar to F-N. Merge / create separate / cancel."

**Auditor handoff:** `manual_verification_task` z `assignee.ooo_until > now() + 7d` → spawn `assignee_handoff_task` z reason. To jest **edycja** istniejącego `05v2-auditor-inbox`, nie nowy mockup.

---

### Obszar (e) — Cost cap jako hard gate (nie dashboard)

**Przed każdą drogą akcją:** modal "Ta akcja kosztuje ~$X.XX. Budżet projektu: $Y, pozostało $Z. [Continue] [Cancel]". Implementacja: middleware na FastAPI route który wycenia akcję przed wywołaniem service'u.

**Per-phase timeouts** (widoczne w UI, enforced w `scenario_generation_run`):
- Phase 1 (LLM draft): max 60s
- Phase 2 (workspace save): max 10s
- Phase 3 (test run): max 5 min — przekroczenie = `BLOCKING`, kill + raise finding
- Phase 4 (parse + report): max 2 min

**`plan_cost_cap_usd`** na poziomie projektu (`projects.plan_cost_cap_usd NUMERIC(10,2)`):
- `approve-plan` z `plan.aggregate_estimated_llm_cost > cap` → `requires_override`
- `requires_override` ścieżka pisze do `final_actions_log`

---

### Obszar (f) — Fidelity-check jako CI gate

Nowy linter: `tools/check_mockup_fidelity.py`:
- parsuje wszystkie mockupy w `forge_output/_global/mockups/*.html`
- wyciąga referencje do DB columns (np. annotations panel zawiera `task.estimated_llm_cost`)
- sprawdza czy kolumna istnieje w `app/models/*.py` LUB w `schema_migrations.PENDING_COLUMNS`
- **EXIT NON-ZERO** jeśli mockup referencuje nieistniejącą kolumnę → CI fail

Pre-commit hook + GitHub Actions check.

**Skutek:** mockup nie wchodzi do main bez backend-first. Odwraca trend ostatnich 3 passów.

**Side benefit:** automatycznie generowana lista `MOCKUP_TO_BACKEND_DELTA.md` pokazuje wszystkie braki — wkład do roadmapy backendu.

---

### Obszar (g) — Autonomy L1–L5 w jednym mockupie (state machine)

**Nowy mockup:** `13-autonomy-state.html` (część obszaru 11 z redukcji).

Pokazuje:
- Aktualny poziom projektu (L1 / L2 / L3 / L4 / L5) + wymagania awansu
- Promotion criteria (per-level checklist; np. L2→L3 wymaga "≥10 closed tasks bez deferred HIGH AND ≥3 successful PR merges")
- Watchlist: które kolumny / metryki są monitorowane przy promotion
- Replay preview: "ostatnie N tasków, gdyby były w L4 / L5, czy auto-merged?"
- Veto clauses: "L5 NIE auto-merguje gdy: HIPAA tag, finding HIGH unresolved, evidence hash mismatch w ostatnich 30d"
- Demotion triggers: warunki cofania poziomu (np. HIGH finding po auto-merge)

To ekspanduje ~20-słów wzmiankę w `12-project-config` do dedykowanego state-machinem.

**Backend:** już mamy `projects.autonomy_level` + `autonomy_promoted_at`. Dodać:
```sql
("projects", "autonomy_promotion_criteria_snapshot", "JSONB"),  -- snapshot kryteriów w momencie promote
("projects", "autonomy_demotion_triggers", "JSONB"),
("projects", "autonomy_replay_buffer", "JSONB"),                -- ostatnie N replay'ów dla preview
```

---

### Obszar (h) — AI sidebar demotion (5 ról → 2)

**Dzisiaj** sidebar: orientuje + sugeruje + wykonuje + świadczy + gwardzi (5 ról).

**Po:** 2 role:
- **`witness`** — tool-call stream zawsze widoczny (read-only); pokazuje co LLM aktualnie czyta / zapisuje / pyta
- **`ask`** — chat on-demand, **collapsed by default**; user otwiera kiedy chce, nie dostaje sugerujących pop-upów

Usunąć z sidebara: contextual suggestions / `/commands` palette / capability contract banner. Te przenieść do dedykowanego onboarding-toura, raz na projekt.

**Skutek:** sidebar przestaje być "kolejną aplikacją obok strony". Główna treść strony staje się main UX.

---

## Sequencing — 5 faz Pass 4

```
Phase 1 (1 sprint)  Backend-first: 19 implied columns + 3 nowe tabele
                    + final_actions_log + manual_verification_task
                    + autonomy snapshot fields. Wszystko w schema_migrations.

Phase 2 (1 sprint)  Fidelity CI gate live (check_mockup_fidelity.py).
                    Wszystkie istniejące mockupy które fail'ują → patche
                    annotations dopiero po Phase 1.

Phase 3 (2 sprinty) Blocking enum implementation:
                    - Backend: enforce blocking states w API
                    - Frontend: counterweight komponenty z severity prop
                    - Wszystkie 6 HIGH risks adresowane mechanicznie

Phase 4 (1 sprint)  Multi-user invariants:
                    - version columns + If-Match middleware
                    - 16-conflict-modal mockup
                    - findings-similarity matcher
                    - auditor handoff

Phase 5 (2 sprinty) Mockup redukcja 38 → 12:
                    - merge happy-path mockupów do state-machine variantów
                    - depreciacja v1 + duplicates
                    - autonomy state mockup (13-autonomy-state.html)
                    - sidebar demotion
                    - 1 audit pass (verify + risk) na końcu
```

---

## Acceptance criteria dla "Pass 4 done"

1. **Wszystkie 6 HIGH risks (H1–H6) CLOSED** w PASS_4_RISK_REPORT.md przez mechanical enforcement, nie przez "added a warning".
2. **Fidelity CI gate** zielony — żaden mockup nie referencuje nieistniejącej kolumny.
3. **`final_actions_log`** zawiera ≥1 wpis dla każdego `requires_override` typu (test integracyjny).
4. **`manual_verification_task` re-verification** zwraca `HASH_MATCH` na 100% świeżych verdyktów (test integracyjny).
5. **Multi-user 409 Conflict** jest zwracany na concurrent edit (test integracyjny: 2 PATCH-e, drugi dostaje 409).
6. **Plan cost cap** blokuje approve-plan przy aggregate > cap (test integracyjny).
7. **Mockup count: 12** (po redukcji), nie 38. v1 superseded usunięte z `index.html`.
8. **Skeptical-UX contract scoring**: wszystkie 12 nowych state-machine mockupów ≥8/9 (była średnia 6.8/9 w Pass 3).

---

## Co zmieniamy względem poprzedniej wersji planu

| Poprzednio (zarchiwizowane) | Teraz |
|---|---|
| Phase A: 3 ship-blocker edits | → Obszar (b) blocking enum, **wszystkie** counterweighty reklasyfikowane |
| Phase B: 5 nowych mockupów + 2 deep-edits | → **0 nowych mockupów typu add-feature**. Tylko 1 nowy: `13-autonomy-state` (obszar g) + `16-conflict-modal` (obszar d) |
| Phase C: 10 mockupów edycji + 2 nowe | → Wszystkie te edycje pochłaniają obszary (b)–(e) jako mechanical changes, nie jako copy edits |
| Phase D: 13 column adds + 3 nowe tabele | → Phase 1 + (c). Pozostaje, rozszerzone o `final_actions_log` + autonomy snapshot fields |
| Phase E: 5 LOW edits | → Pochłonięte przez Phase 5 redukcję (LOW#3 server-side signature → obszar c) |
| **Skupienie:** dodać UX | **Skupienie:** redukcja UX + mechanical enforcement + backend-first |

---

## Estymowany scope

- **1 nowy mockup** (`13-autonomy-state`) + **1 nowy reusable** (`16-conflict-modal`)
- **Redukcja 38 → 12** mockupów (merge variantów, deprecate v1)
- **~25 nowych kolumn DB + 4 nowe tabele** (manual_verification_task, scenario_generation_run, objective_reopen_event, final_actions_log)
- **1 nowy CI gate** (check_mockup_fidelity.py)
- **1 nowy daemon** (TTL revalidation)
- **2 audit reports** (PASS_4_VERIFY_REPORT.md + PASS_4_RISK_REPORT.md)

**Mniej niż poprzednia wersja Pass 4 ale głębsze.** 6 HIGH zamknięte mechanicznie, nie 0.
