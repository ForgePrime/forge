# Forge mockup synthesis — historia po przeczytaniu wszystkich

**Data:** 2026-04-19
**Autor:** synteza po Pass 1 + Pass 2 + Pass 3 + 4 katalogi (Part A/B/C/D, 45 mockupów)
**Wejście:** wszystkie pliki w `forge_output/_global/mockups/` + `walkthrough.md` + `index.html` + audyty

---

## 1. Co te 38 stron razem mówią (narracja)

To nie jest zestaw ekranów. To jest **hipoteza produktowa wyrażona w HTML**:

> "LLM tools przemieniają niepewność w pewność. Forge przemienia pewność w niepewność."

Każda strona odpowiada na trzy pytania zanim odpowie na cokolwiek innego: **czego nie zrobiono · czego nie sprawdzono · jakie założenie zrobiono cicho**. `walkthrough.md` (10 scenariuszy) i `index.html` ("design contract") wprost to deklarują: "If you see 'trustworthy' / 'looks good' / 'approve' framing, that is a contract violation".

Łuk narracyjny składa się z czterech warstw:

| Warstwa | Mockupy | Rola |
|---|---|---|
| KB jako ciągle rosnący zbiór | `02v2-project-kb` + 4 add-source + `source-preview` | Wiedza projektu to 4 typy źródeł (plik / URL / folder / notatka), z opisem i `focus_hint`, z wykrywaniem konfliktów. Nie SOW jako monolit. |
| Objective jako serce | `03v2-objectives-dag`, `09-objective-detail`, `09-reopen`, `09-edit-challenger-checks`, `09-edit-dependencies` | Objective ma DAG, KR, cross-objective conflicts, ambiguity loop, re-open z gap-note. "Heart of system" — słusznie. |
| Task jako 4 typy lifecycle'u | `07-new-task` (wizard), `07-mode-selector` (Direct / Crafted), `07-crafter-preview`, `05v2-*-deliverable × 4` (develop / analysis / planning / documentation) | 4 typy tasków z wspólnym "deliverable shell" ale rozbieżnym ciałem. Każdy kończy się challengerem i close-safety. |
| Human-in-the-loop + governance | `05v2-auditor-inbox`, `auditor-review`, `assign-auditor`, `11-skills-library`, `12-project-config`, `12-hooks-tab`, `16-ai-sidebar`, `16-preview-apply-modal` | Audytor z 4 typami werdyktu (PASSED_WITH_EVIDENCE / PASSED_ATTESTATION / REJECTED / NEEDS_CLARIFICATION), skills z ROI, operational contract, AI sidebar z capability contract. |

Scenariusze 1–10 (od greenfield po client audit, przez hallucination catch, cost overrun, L5 autonomy) pokazują że te 38 stron to **jeden spójny system, nie zbiór niezależnych ekranów**. Jest tu wizja.

---

## 2. Deep-verify — wynik

| Pass | Mockups | Defekty | Ostrzeżenia | Werdykt |
|---|---|---|---|---|
| Pass 1 foundation (9) | ✅ 9/9 PASS | 0 | 2 (taxonomy scenario kind vs type, DSL dla conditions niewalidowana) | PASS |
| Pass 2 (13) | ✅ 13/13 PASS | 0 | 2 (count mismatch 15→14 w reopen; schema assumption w edit-deps) | PASS |
| Pass 3 (5) | ✅ 5/5 PASS | 0 | 0 | PASS |
| v2 REVISED (12) | ⚠️ 11/12 + 1 broken link | 1 (`03v2-objectives-dag` → v1 `03-project-post-analyze` zamiast `09-answer-ambiguity`) | 3 | PASS z poprawką |
| v1 superseded (5) | ℹ️ słusznie zdeprecjonowane | — | — | NOTED |

**Implied data-model:** 19 nowych kolumn / tabel nieobecnych w obecnym schemacie (9 z Pass 3, 10 z Pass 2). W samym `05v2-planning-deliverable` — 5 z nich (`task.generated_by_task_id`, `task.covers_ac_ids[]`, `task.estimated_llm_cost`, `task.status='DRAFT'`, `plan.critical_path_task_ids[]`). **Żadna nie jest w kodzie.**

---

## 3. Deep-risk — 6 HIGH otwartych, nie 4

Pass 2 zostawił 4 HIGH otwarte. Pass 3 nie zamknął żadnego, zmitygował H#4 w ~60%, i otworzył 3 nowe. Skumulowany stan:

| # | Ryzyko | Mockup | Severity |
|---|---|---|---|
| H1 | KB folder ingest — 2418 plików bez pre-review globów; AWS keys mogą wejść w embedding | `02v2-add-source-folder` | HIGH |
| H2 | Scenario-gen bez gas-gauge — phase 3 może wisieć 5+ min; brak per-phase timeout | `05v2-scenario-generate` | HIGH |
| H3 | Close-task bez circuit-breaker na deferred findings — można zamknąć 2 HIGH + 1 MED bez alertu projektowego | `05v2-close-task` | HIGH |
| H4 | Manual AC: PASSED_ATTESTATION bez TTL + PASSED_WITH_EVIDENCE bez walidacji authenticity (content_hash nie re-verified na read, pliki nie immutable) | `05v2-auditor-review` | HIGH |
| H5 | INVENTED AC i unsourced paragraphs są flagged ale nie blokujące — "Approve all" puszcza downstream | `analysis-deliverable`, `planning-deliverable`, `documentation-deliverable` | HIGH |
| H6 | PASSED_ATTESTATION jest trwały i w KR roll-up równy PASSED_WITH_EVIDENCE — dla HIPAA/SOC2 to strukturalne. Zero revalidation | `05v2-auditor-review` | HIGH |

**Cross-cutting wzorzec (najgroźniejszy):** "Forge surfaces the gap, then lets the user proceed anyway." Counterweight jest wszędzie deklaratywnie, **nigdzie nie blokuje mechanicznie**. To jest wewnętrzna sprzeczność z design contractem — kontrakt mówi "skeptical, not reassuring", a UX daje "reassuring through visible-but-overridable warnings". Chybienie się skaluje: **13/38 mockupów ma informational counterweight który POWINIEN być blocking**.

---

## 4. Czy to poprawia czy pogarsza program

### Poprawia — w wymiarze wizji produktu

Forge różni się od Cursor / Cline / GitHub Copilot właśnie tym: **nie jest wrapperem na `/analyze`, nie jest scaffoldem który wydaje do IDE, jest skeptical auditor z pamięcią**. Ten kontrakt UX jest silną, obronną hipotezą biznesową — w świecie gdzie 90% AI tools zapewnia o jakości, jedno które systematycznie kwestionuje ma wartość zwłaszcza dla regulowanych branż (HIPAA, SOC2, finance).

### Pogarsza — w trzech wymiarach

1. **Scope creep.** 38 mockupów z planem na ~52 to projekt UX większy niż implementacja. Pilot warehouse'owy pokazał że trust gap nie jest w UX, jest w mechanical validation. Dodawanie 14 kolejnych mockupów nie zamknie H1–H6.
2. **Fidelity gap między mockupem a kodem.** Sprawdzono na `planning-deliverable`: ~15% mapuje się do istniejącego kodu. Jeśli ta proporcja trzyma się przez wszystkie mockupy, to ~32 z 38 mockupów wymaga znaczącej pracy DB + backend — to jest roadmapa na 6 miesięcy, nie na 3 sprinty.
3. **Jednoosobowy model założony wszędzie.** Wszystkie mockupy implicite. Real teams → real concurrent edits → stale graphs, podwójne findings, auditor vacation bez escalation. **0 z 38 mockupów to adresuje.**

### Netto

Kierunek słuszny, realizacja zbyt rozrosła się na froncie względem tego co backend utrzymuje. Design contract jest mocny ale **egzekucja go (enforcement) słaba**.

---

## 5. Jak ja bym to zaprojektował

Nie odrzucałbym kierunku. Ale **zredukowałbym i wzmocniłbym mechanicznie**:

### (a) Zredukować 38 → 12 core mockupów. Pre-production.

Każdy reprezentuje **pełen state machine** (7 stanów, nie jeden happy-path ekran). Np. zamiast 4 osobnych deliverable mockupów — jeden "task-deliverable" z 4 body-variantami w tej samej stronie + widocznymi stanami `TODO / CLAIMING / IN_PROGRESS / DRAFT / DONE_WITH_CONCERNS / FAILED / CLOSED`. **Mockup dostarcza widoków, nie stron.**

### (b) Zamiast "skeptical UX" → "blocking UX"

Wprowadziłbym enum na każdym counterweight item: `{ informational, warning, blocking, requires_override }`. INVENTED AC → `blocking`. Unresolved HIGH ambiguity → `blocking`. Deferred HIGH finding > threshold → `blocking`. Override zawsze pisze do **immutable `final_actions_log`** z reason + actor + before-state hash. To jest 1 tabela w schemacie, nie 5 kolumn.

### (c) Zamiast "4-verdict auditor" → "verdict z TTL i evidence-hash-on-read"

`PASSED_ATTESTATION` dostaje TTL (90d HIPAA / 180d SOC2). `PASSED_WITH_EVIDENCE` ma `content_hash` + `code_commit_hash`, **re-verified na każdym render**. S3 object-lock. To zamyka H4 + H6 jednym designem.

### (d) Multi-user jako first-class

Optimistic locking na każdym mutable entity (`depends_on_version`, `objective_version`, `task_version`). 409 Conflict + "reload prompt" modal. Findings-similarity matcher przy tworzeniu. Audytor-handoff UI gdy OOO >7d. To **nie jest 3 mockupy, to 1 cross-cutting invariant** dodany do istniejących.

### (e) Cost cap jako hard gate, nie dashboard

Przed uruchomieniem: "ta akcja kosztuje $2.14, budżet $10, pozostało $3.40. Continue / Cancel". Per-phase timeouts w UI (5min phase 3, 2min phase 4). `plan_cost_cap_usd` na poziomie projektu, **blokuje** approve-plan powyżej capu.

### (f) Fidelity-check jako CI gate

Linter który sprawdza: każdy mockup referencuje DB-kolumny które istnieją. Break na niematerialnych. **To wymusza backend-first, nie mockup-first.** Nie ma `task.estimated_llm_cost` w schemacie → mockup którego go używa nie wchodzi do merge.

### (g) Autonomy L1–L5 w ONE mockupie

Dzisiaj jest tylko wzmianka w project-config + autonomy-bar na `01-dashboard`. Cała koncepcja (promotion criteria, watchlist, replay preview, veto clauses) wymaga **dedykowanego ekranu z state machinem**. To jest scenariusz #3 z `walkthrough.md` — ale UI go nie wspiera.

### (h) "Demotion mode" dla AI sidebar

Dzisiaj sidebar **orientuje, sugeruje, wykonuje, świadczy, gwardzi**. 5 ról to zbyt wiele — sidebar staje się kolejną aplikacją obok strony. Zredukowałbym do 2: **witness** (tool-call stream, zawsze widoczny) + **ask** (chat on-demand, collapsed by default).

---

## Bottom line

Forge **nie potrzebuje więcej mockupów**. Potrzebuje:

1. **Egzekucji mechanicznej design contractu** który już zadeklarowano
2. **Backendu** który trzyma 19 implied columns z tych mockupów

Inaczej 6 miesięcy z rzędu będziemy dodawać pass-y które nie zamykają HIGH risks a multiplikują je.

---

## Podsumowanie w jednym akapicie

38 mockupów Forge wyrażają silną hipotezę produktową — **skeptical auditor, nie build-confidence tool**. Kierunek jest słuszny i obronny biznesowo (regulowane branże), ale egzekucja ma trzy systemowe luki: (1) counterweight jest deklaratywny, nie blokujący (6 HIGH risks otwartych, wzorzec "surface the gap then let user proceed"), (2) fidelity mockup→kod ~15% (19 implied DB columns nie istnieje), (3) jednoosobowy model założony wszędzie. Nie dodawać Pass 4. Zredukować do 12 core mockupów jako state-machines, wprowadzić enum `blocking` / `warning` / `informational` na counterweight items, `PASSED_ATTESTATION` z TTL + hash re-verified on read, multi-user as first-class, cost cap jako hard gate przed akcją, fidelity-check jako CI gate.
