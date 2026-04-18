# Forge UX Deconstruction — kompletny audyt

**Autor:** self-analysis po 35 feature'ach z poprzednich sesji
**Data:** 2026-04-18
**Podstawa:** `FORGE_UI_DECONSTRUCTION_BRIEF.md` (17 sekcji, 18 red flags)
**Cel:** zdekonstruować obecny UI Forge, zdiagnozować dlaczego user mówi "bezsensu, nie wiem jak go używać", i zaprojektować konkretny plan naprawy — workflow-driven, nie data-driven.

---

## 0. Executive summary

**Diagnoza w 5 zdaniach:**

1. Obecny UI to **panel admina do bazy danych** — 8 tabs odzwierciedla 8 tabel API, zero odzwierciedlenia procesu pracy użytkownika.
2. User po zalogowaniu nie widzi żadnej narracji "co teraz, dlaczego, jak" — tylko puste listy i przyciski (`Ingest`, `Analyze`, `Plan`, `Orchestrate`) których znaczenia musi się domyślać lub zrozumieć z dokumentacji która **nie istnieje**.
3. Długie operacje (orchestrate 10-30 min, analyze 2-3 min, plan 3-4 min) są pod spodem realizowane dobrze, ale **UI skrywa co się dzieje** (brak progress, log stream tylko w jednym ekranie, brak pre-operation cost estimate, brak notifications).
4. Nieciągłości przepływu dominują: upload → "i co teraz?"; analyze → "gdzie wyniki?"; plan → "czy mogę to zmienić zanim ruszy?"; orchestrate DONE → "co oceniam?"; finding HIGH → "kto to ma naprawić?".
5. Forge ma unikalną wartość biznesową (cross-model verification + audit trail), ale UI **tego nie eksponuje** — user widzi techniczne encje (objectives, KRs, findings) zamiast odpowiedzi na pytania "czy kod jest gotowy do wysłania klientowi? co trzeba jeszcze zrobić? ile to kosztowało?".

**TOP 3 problemy (mechaniczne, widoczne po 30 sek używania):**

- **P1 — "Co mam robić?":** landing pokazuje listę projektów (lub pustkę) bez żadnego guidance. Nowy user ma 0 wiedzy jak zacząć.
- **P2 — "Co się właśnie dzieje?":** Claude CLI chodzi 20 minut w tle, user patrzy na spinner albo HTTP timeout (pre-async era) lub zgarnia notification po 20 minutach bez żadnego live feedback.
- **P3 — "Czy to jest gotowe?":** po orchestrate DONE user widzi `status=DONE` ale brak syntetycznej odpowiedzi "TAK, możesz wysłać klientowi / NIE, musisz jeszcze X". Raport jest szczegółowy ale **bez verdyktu**.

**TOP 3 propozycje (zwrotne w UX, wymagające redesignu):**

- **Landing = Dashboard zamiast listy projektów.** Activity feed "co się zmieniło od ostatniej wizyty", "co wymaga dzisiaj uwagi", pre-seeded CTA dla nowych.
- **Proces jako wizard**, nie tabs. Upload → Analyze → Review → Plan → Review → Orchestrate → DONE Report — z wyraźnymi checkpointami, możliwością backstep, i pre-operation cost+time estimates.
- **Raport DONE z verdyktem** (GOTOWE / BLOKERY / CZEKA NA REVIEW), nie tylko status dump. Każdy verdykt linkowany do konkretnej akcji.

**Czego dotychczas nie zrobiono mimo że potrzebne (już w poprzednim planie productization):**

- Onboarding wizard (był w Phase 1 plan, brak)
- Git push + PR (Phase 1 plan, brak — klient dostaje tylko kod w workspace na serwerze)
- PDF export raportu (Phase 1 plan, brak)
- Activity feed (nigdzie w planie, krytyczny brak)
- "Co teraz?" guidance per ekran (nigdzie w planie)
- Decision resolve UI (endpoint istnieje, brak buttonа — decisions conflicts od analyze są dead letter)
- Re-run failed task (brak)
- Workspace download ZIP (brak)
- Notifications / email digest (brak)
- Search / filter / sort na listach (brak)

---

## 1. Workflow analysis — 17 kroków chronologicznie

Każdy krok rozłożony na **16 wymiarów** zgodnie z poleceniem sekcji 2. Cel: przestać myśleć o UI jako o zbiorze CRUD na encjach, zacząć myśleć jako o procesie pracy użytkownika od otrzymania SOW do wysłania klientowi gotowego produktu.

### Krok 0 — First login + onboarding nowego usera

1. **Nazwa kroku:** pierwsze logowanie po signup.
2. **Co user chce:** zacząć używać Forge. Wie że to "ma mi pomóc zbudować coś z SOW".
3. **Skąd user wie że jest na tym kroku:** właśnie kliknął button "Zarejestruj" i został zalogowany. URL teraz `/ui/`.
4. **Co Forge robi pod spodem:** `AuthMiddleware.load_user` sprawdza JWT cookie, `request.state.user` i `request.state.org` są ustawione. `project_view` wywołane, query wszystkich projektów filtrowanych po `organization_id`.
5. **Co user widzi w obecnym UI:** template `index.html` — na górze nav z nazwą org i emailem, w środku tytuł "Projects", button "+ New project", poniżej — **pusta lista** (jeśli user świeżo zarejestrowany w własnej org). Pod button'em jest ukryty inline form (slug/name/goal). Brak empty state z CTA.
6. **Czego user nie widzi a powinien:** (a) czym jest Forge w 1 zdaniu, (b) 3-krokowy diagram "SOW → analiza → orchestrate", (c) template / sample project "WarehouseFlow" do przećwiczenia, (d) link do dokumentacji / tutoriala (nie istnieje), (e) "czego oczekujemy że zrobisz jako pierwsze".
7. **Cel istnienia tego kroku:** sprawić że user mówi "aha, wiem jak zacząć" w pierwsze 30 sekund.
8. **Bez tego kroku — czy Forge nadal funkcjonuje?** Technicznie TAK (można od razu stworzyć projekt), UX NIE — 80% nowych userów się zgubi i wróci do Cursora.
9. **Wady obecnej implementacji:** strona pusta, bez kontekstu, bez wizard'u. Sample slug "e.g. warehouseflow" jako placeholder w input to jedyna wskazówka.
10. **Ograniczenia interfejsu:** nie ma możliwości dodania projektu jednym klikiem "z template". Wymusza wymyślanie nazwy / slug / goal od zera.
11. **Nieciągłości wchodzące:** po signup user dostaje 303 redirect na `/ui/` — zero kontekstu "Właśnie utworzyłeś konto. Teraz...".
12. **Nieciągłości wychodzące:** po kliknięciu "+ New project" otwiera się inline form — potem redirect do `/ui/projects/{slug}` który jest **pusty** (brak tasków, brak dokumentów, brak objectives). User znowu zgubiony.
13. **Brakujące funkcje UI:** onboarding tour (choćby 3-slidowy), sample project import, "pokaż mi demo", dokumentacja inline.
14. **Brakujące funkcje backend:** endpoint `/api/v1/projects/{slug}/import-template` — skopiuj znaną konfigurację (warehouseflow demo z docs).
15. **Sugerowana zmiana:** empty state hero z 3 CTA — "Start z SOW (upload)" | "Pokaż mi sample (WarehouseFlow demo)" | "Dokumentacja". Plus 3-kroku ilustracja procesu.
16. **Challenge:** power user po 100 użyciach nie chce hero screen'u. Rozwiązanie: hero tylko gdy lista projektów pusta. Returning user dostaje activity feed.

### Krok 1 — Otrzymanie SOW / maila od klienta

1. **Nazwa kroku:** user ma dokumenty (SOW, emaile, specyfikacje) zapisane lokalnie i chce je wrzucić do Forge.
2. **Co user chce:** wgrać dokumenty jednym ruchem, zobaczyć że są w systemie, potwierdzić że każdy został poprawnie sparsowany.
3. **Skąd user wie że jest na tym kroku:** stworzył właśnie projekt, jest na `/ui/projects/{slug}`. Musi odnaleźć funkcję "upload".
4. **Co Forge robi pod spodem:** `POST /ui/projects/{slug}/ingest` multipart upload, `ingest_documents` w `pipeline.py`, każdy plik zapisywany jako `Knowledge` row z `category="source-document"`.
5. **Co user widzi w obecnym UI:** pasek 4 akcji "Ingest / Analyze / Plan / Orchestrate" — ingest ma input `<input type="file" multiple>` + button. Brak drag-and-drop, brak preview, brak listy już uploaded. Dokumenty pojawiają się potem w tab "Knowledge" (8. tab!) jako karty read-only.
6. **Czego user nie widzi a powinien:** (a) drag-and-drop zone, (b) progress per plik, (c) preview po parsowaniu (first 500 chars), (d) kategoryzacja (to SOW, to email od klienta, to spec techniczny), (e) możliwość edycji treści jeśli parser się gubi.
7. **Cel istnienia:** Forge nie zrobi nic bez dokumentów. To jest **krytyczny** krok — bez tego cały downstream pipeline stoi.
8. **Bez tego — czy Forge działa?** NIE. Ingest to entry point.
9. **Wady obecnej implementacji:** button "Ingest" w pasku 4 akcji — brak discovery że to **pierwszy** krok. User może pomyłkowo kliknąć "Orchestrate" jako pierwsze (kolejność alfabetyczna na ekranie, a proces idzie I→A→P→O).
10. **Ograniczenia interfejsu:** brak per-file kategoryzacji (wszystko `source-document`). Brak re-upload (zmieniony SOW? user usuwa w psql i wgrywa ponownie). Brak edycji treści.
11. **Nieciągłości wchodzące:** dopiero co utworzony projekt → pusta strona → gdzie kliknąć żeby wgrać? Button "Ingest" nie jest wyróżniony jako pierwszy krok.
12. **Nieciągłości wychodzące:** wgrałem pliki → **nie widzę potwierdzenia**. W tabie Knowledge są karty, ale tab "Knowledge" to 8. pozycja — user nie trafi tam intuicyjnie. Może sprawdzi "Files" tab (workspace) → nie znajdzie (tam są pliki kodu Claude, nie wgrane docs).
13. **Brakujące funkcje UI:** drag-and-drop, progress per plik, preview, kategoryzacja, edycja po uploadzie, delete, re-upload, tagowanie, pokazanie zbiorczej lister wgranych z rozmiarami.
14. **Brakujące funkcje backend:** `PATCH /knowledge/{id}` dla edycji treści, `DELETE /knowledge/{id}`, categoryzacja beyond `source-document`.
15. **Sugerowana zmiana:** **drop zone** na samej górze projektu (nie w pasku akcji). Wizualnie duży obszar "Upuść dokumenty (SOW, email, spec)". Po uploadzie lista kart per plik z nazwą / kategorią / rozmiarem / preview 200-znakowym / delete / edit. Dopiero **gdy user ma >= 1 plik** pojawia się zielony button "Analizuj dokumenty →".
16. **Challenge:** drag-and-drop wymaga JS (HTMX tego nie ma natywnie — potrzeba Alpine albo malutkiego vanilla script). Trade-off: trochę complexity, ale UX jump drastyczny.

### Krok 2 — Decyzja "uruchomić analyze"

1. **Nazwa kroku:** user ma dokumenty w Forge, teraz trzeba je zanalizować.
2. **Co user chce:** uruchomić analyze i zobaczyć co z tego wyjdzie.
3. **Skąd user wie że jest tu:** w obecnym UI — musi wiedzieć że po Ingest idzie Analyze. Brak wizualnej wskazówki. W sugerowanym — zielony button "Analizuj dokumenty →" pojawia się dopiero po uploadzie.
4. **Co Forge robi pod spodem:** `POST /ui/projects/{slug}/analyze` → `analyze_documents` → `invoke_claude(analyze_prompt)` → parsuje JSON z objectives/KRs/conflicts/open_questions → zapisuje jako Objective/KeyResult/Decision rows.
5. **Co user widzi w obecnym UI:** button "Analyze" w pasku akcji. Kliknięcie — **blokuje HTTP request 2-3 minuty**. Przeglądarka pokazuje spinner, brak progress, brak pre-operation estimate.
6. **Czego user nie widzi a powinien:** (a) pre-operation estimate "~3 min, ~$0.15, wyekstrahuje 5-10 objectives", (b) live log streaming "parsing SRC-001 chunk 1/3...", (c) progress bar 0-100%, (d) koszt narastający real-time.
7. **Cel istnienia:** bez analyze Forge nie ma objectives / KRs — nie da się zaplanować. Mandatory.
8. **Bez tego — czy Forge działa?** NIE. Downstream całkowicie zablokowany.
9. **Wady obecnej implementacji:** synchroniczne blokowanie + zero informacji + zero cost display. User może myśleć że się zawiesiło i zamknąć tab.
10. **Ograniczenia interfejsu:** brak możliwości wstrzymania, anulowania, zmiany parametrów w locie.
11. **Nieciągłości wchodzące:** po ingest → user musi wiedzieć że teraz kliknąć Analyze. Brak guidance.
12. **Nieciągłości wychodzące:** analyze kończy → user dostaje HTTP response (jeśli zdążył w timeout) — gdzie teraz? UI nie przełącza tabu na Objectives automatycznie. User musi odgadnąć.
13. **Brakujące funkcje UI:** pre-confirm modal ("Wykonać analyze? ~$0.15, ~3 min"), live progress view, auto-redirect do wyników.
14. **Brakujące funkcje backend:** async wariant (`orchestrate-async` pattern — jest dla orchestrate, brak dla analyze/plan), cancel endpoint, progress events.
15. **Sugerowana zmiana:** button zmienia się z "Analyze" na "Analizuj dokumenty →" tylko gdy dokumenty są. Kliknięcie → modal z estymacją + potwierdzenie → async run z live widokiem podobnym do orchestrate (current step, cost, elapsed). Po DONE auto-redirect do Objectives z banerem sukcesu "5 objectives wyekstrahowane (·$0.15)".
16. **Challenge:** modal dodaje jedno kliknięcie dla power usera. Rozwiązanie: checkbox "Nie pytaj więcej" w modalu zapisuje preferencję per-user.

### Krok 3 — Review wyekstrahowanych objectives

1. **Nazwa kroku:** user przegląda co AI wyekstrahowało i decyduje czy to ma sens.
2. **Co user chce:** zobaczyć każdy objective, ocenić czy trafny, poprawić jeśli błędny, rozdzielić jeśli zlepione, dodać brakujące.
3. **Skąd user wie że jest tu:** aktualnie tab Objectives. W sugerowanym flow: auto-redirect po analyze.
4. **Co Forge robi pod spodem:** query do `objectives` + `key_results` filtrowane przez `project_id`. Render template `project.html` z tab objectives + include `_objective_card.html` per objective.
5. **Co user widzi w obecnym UI:** listę kart objective z: external_id (O-001), tytuł, status badge (ACTIVE · P1), business_context (300 znaków), key_results pod spodem (pill status + text + target/current). Edit button obok każdego. Add Objective form na dole (collapsed).
6. **Czego user nie widzi a powinien:** (a) **który fragment SOW** dostarczył ten objective (wizualny link do `Knowledge.SRC-001 §X`), (b) conflicts/open_questions które analyze zauważył, (c) **sugestie** "może warto rozdzielić ten objective", (d) side-by-side view "source doc | extracted".
7. **Cel istnienia:** human-in-the-loop review — AI może się mylić, user musi móc skorygować zanim pójdzie dalej.
8. **Bez tego — czy Forge działa?** TAK ale kiepsko — błędne objectives → błędne taski → marnowanie LLM budget.
9. **Wady obecnej implementacji:** kart objective są dobrze designowane, ale kontekst (SKĄD to wzięte) niewidoczny. Tab "Decisions" gdzieś oddzielnie pokazuje konflikty ale user nie wie że ma tam iść.
10. **Ograniczenia interfejsu:** brak split view SOW | objective. Brak "merge two objectives" ani "split this objective into 2". Brak re-run analyze for this objective only.
11. **Nieciągłości wchodzące:** analyze skończony → w **którym** tabie user ląduje? Aktualnie — zostaje na tabie "objectives" (default). OK, ale brak banera "Oto wyniki analyze, review i kontynuuj".
12. **Nieciągłości wychodzące:** zreviewałem objectives → co teraz? Brak CTA "zaplanuj pierwszy objective". User musi odnaleźć button Plan w pasku 4 akcji.
13. **Brakujące funkcje UI:** link "z jakiego dokumentu" (wymagania z `requirement_refs` już są na task, brak na objective), sekcja "konflikty do rozwiązania" na samej górze taba, split/merge operations, "zaplanuj ten objective" button bezpośrednio na karcie.
14. **Brakujące funkcje backend:** `POST /objectives/{ext}/split` — tworzy 2 nowe z jednego, linkuje do source. `POST /objectives/{ext}/merge/{ext2}` — odwrotnie.
15. **Sugerowana zmiana:** dodać sekcję "Konflikty do rozwiązania" na górze taba (filtered z tabeli decisions, type=conflict lub open_question, status=OPEN). Każdy konflikt klikalny otwiera modal z 2 dokumentami side-by-side i wyborem "przyjmij A / przyjmij B / custom". Button "Zaplanuj" per każda karta objective. Link "Z dokumentu: SRC-001 §2.4" (jeśli analyze zachowa provenance).
16. **Challenge:** provenance wymaga żeby analyze zapisywał `source_knowledge_id` i `source_fragment` per wyekstrahowany objective. Aktualnie nie zapisuje. Wymaga zmiany w prompt analyze + schema change + plan prompt. Duży koszt — ale **niezbędny dla credibility** (user nie ufa bez dowodu).

### Krok 4 — Rozwiązywanie conflicts i open_questions

1. **Nazwa kroku:** analyze wygenerował konflikty między dokumentami (SOW mówi X, email mówi Y) i otwarte pytania (brak info o Z). User musi je rozstrzygnąć przed dalszym pracowaniem.
2. **Co user chce:** zobaczyć każdy konflikt, zrozumieć oba stanowiska, wybrać rozwiązanie, zapisać decyzję.
3. **Skąd user wie że jest tu:** nigdzie go tu nikt nie prowadzi. Tab "Decisions" jest 6. na liście, user nawet nie wie że tam są conflicts.
4. **Co Forge robi pod spodem:** analyze tworzy `Decision` rows z `type="conflict"` lub `"open_question"` i `status="OPEN"`. Endpoint `POST /decisions/{id}/resolve` istnieje.
5. **Co user widzi w obecnym UI:** w tab Decisions — kart z external_id, type, severity, issue text, recommendation. Status badge. **Brak przycisku Resolve**. Endpoint istnieje, UI brak.
6. **Czego user nie widzi:** (a) **widok źródeł** — który fragment SOW powiedział X, który email Y, (b) radio "Akceptuj wersję A / B / custom", (c) historia rozważań, (d) wpływ na downstream (który objective zależy od tej decyzji).
7. **Cel istnienia:** bez rozstrzygania, plan/orchestrate będzie zgadywał i może zrobić źle.
8. **Bez tego — czy Forge działa?** Tak, ale jakość wynikowa niska. Konflikty rezolwowane automatycznie przez Claude'a w plan — bez widoczności dla usera.
9. **Wady obecnej implementacji:** **brak UI do resolve**. User widzi listę konfliktów bez możliwości działania. Wymagane jest curl/psql.
10. **Ograniczenia interfejsu:** brak workflow zaakceptuj-odrzuć-odrocz dla conflicts. Brak linków do źródła (knowledge). Brak historii decyzji.
11. **Nieciągłości wchodzące:** po analyze user nie jest informowany "masz 3 konflikty do rozwiązania". Musi sam znaleźć tab Decisions.
12. **Nieciągłości wychodzące:** rozwiązałem konflikt (przez curl) → efekt? Plan i tak zrobi swoje. Decyzja gdzieś zapisana ale czy used? (Aktualnie: `resolution_notes` saved, nigdzie nie czytane przez plan prompt.)
13. **Brakujące funkcje UI:** Resolve modal z radio + side-by-side fragmenty źródłowe, button "Odrocz" (defer), button "To nie jest problem" (reject), historia rozważań.
14. **Brakujące funkcje backend:** plan prompt musi czytać `resolution_notes` i uwzględniać. Aktualnie ignoruje. Oznacza że nawet po rozwiązaniu konfliktu przez user'a, plan może go zignorować.
15. **Sugerowana zmiana:** na tabie Objectives sekcja "⚠ 3 konflikty wymagają Twojej decyzji zanim zaplanujesz" z linkami bezpośrednio do Resolve modal. Modal pokazuje 2 fragmenty side-by-side (wymaga Knowledge.excerpt provenance), radio buttons z opcjami, textarea na notkę. Po Resolve — decision status CLOSED, banner znika, user może kontynuować.
16. **Challenge:** wymusza sekwencję "resolve conflicts → plan". User może nie chcieć czekać i wolaliby dać plan zgadnąć. Rozwiązanie: zostawić jako SOFT block (banner z ostrzeżeniem, nie hard blokada).

### Krok 5 — Wybór objective do planowania

1. **Nazwa kroku:** user ma 5-7 objectives, decyduje który zaplanować pierwszy.
2. **Co user chce:** zobaczyć objectives posortowane sensownie, wybrać najważniejszy.
3. **Skąd user wie że jest tu:** po review objectives, chce zacząć budować.
4. **Co Forge robi pod spodem:** nic jeszcze — tylko user decyzja.
5. **Co user widzi w obecnym UI:** lista kart objective, brak sortowania per priority/dependency, brak "status plan" (czy ten objective ma już taski zaplanowane?).
6. **Czego user nie widzi:** (a) który objective jest "ready to plan" (wszystkie KR jasne, brak konfliktów), (b) dependency graph (O-002 zależy od O-001), (c) estymacja planowania (~8 tasków, ~$0.30, ~4 min).
7. **Cel istnienia:** wybór = commit do pracy. Źle wybrany = zmarnowany budget.
8. **Bez tego — czy Forge działa?** Częściowo — user może zaplanować wszystko po kolei. Ale 7 objectives × $0.30 = $2.10 na samo planowanie, plus orchestrate każdego to $20-50. Total $150+. Za dużo by robić wszystko.
9. **Wady obecnej implementacji:** dropdown "wybierz objective" przy button Plan — brak kontekstu który wybrać.
10. **Ograniczenia interfejsu:** brak dependency indicators, brak "planned / not planned" status na karcie objective.
11. **Nieciągłości wchodzące:** z review objectives → gdzie kliknąć "zaplanuj"? Button Plan jest w głównym pasku akcji, nie na karcie.
12. **Nieciągłości wychodzące:** wybrałem objective → plan dropdown → submit → hang na 3-4 min. Brak preview.
13. **Brakujące funkcje UI:** button "Zaplanuj" per karta objective, badge "📋 7 tasków zaplanowane" / "❓ nie zaplanowane", dependency chips.
14. **Brakujące funkcje backend:** `GET /objectives/{ext}/plan-status` — ile tasków ma, ile DONE/FAILED/TODO.
15. **Sugerowana zmiana:** karty objectives sortowane po priority, z wyraźnym statusem planowania i actions. Objective już zaplanowany ma button "Zobacz taski" zamiast "Zaplanuj".
16. **Challenge:** sortowanie po priority vs dependency vs data utworzenia — per-user preference? Domyślnie priority.

### Krok 6 — Plan objective (LLM decomposition)

1. **Nazwa kroku:** user kliknął "zaplanuj ten objective", Forge wywołuje Claude CLI do dekompozycji na taski.
2. **Co user chce:** zobaczyć proponowany plan zanim zaakceptuje, móc edytować przed commitem.
3. **Skąd user wie że jest tu:** kliknął button Plan. Aktualnie wymaga wyboru w dropdown + submit.
4. **Co Forge robi pod spodem:** `POST /ui/projects/{slug}/plan` → `plan_from_objective` → `invoke_claude(plan_prompt)` → parsuje JSON tasks → tworzy `Task` + `AcceptanceCriterion` rows.
5. **Co user widzi w obecnym UI:** button "Plan" w pasku — dropdown + Submit → **blokuje HTTP 3-4 min** → response JSON (w HTML wrapper). Potem user musi sam iść do tabu Tasks.
6. **Czego user nie widzi:** (a) pre-operation estimate "~3.5 min, ~$0.30, 7-12 tasków", (b) live progress, (c) **propozycja tasków PRZED zapisem** (draft mode).
7. **Cel istnienia:** Claude robi dekompozycję którą user manualnie by zrobił w Jirze przez pół dnia.
8. **Bez tego — czy Forge działa?** Tak ale tracimy główną wartość (szybka dekompozycja). User może manualnie tworzyć taski przez Add task form.
9. **Wady obecnej implementacji:** **brak draft mode** — Claude od razu commituje taski do DB. Jeśli plan zły, user musi usuwać po jednym (lub SQL).
10. **Ograniczenia interfejsu:** brak preview, brak "zmień max 10 tasków" guidance, brak "skip niektóre", brak "re-plan z hintem".
11. **Nieciągłości wchodzące:** kliknąłem Plan → blokada ekranu. Zamiast tego powinno być: spinner "generating plan...", live log.
12. **Nieciągłości wychodzące:** plan stworzony → user wraca do listy tasków, musi przejrzeć 10 tasków jeden po drugim przez Edit. Brak "zatwierdź cały plan" / "odrzuć i regeneruj".
13. **Brakujące funkcje UI:** draft review modal po plan — lista proponowanych tasków z checkboxem "accept" przy każdym, button "Accept all" / "Re-plan z innym hintem", dependency graph visualization, edit before commit.
14. **Brakujące funkcje backend:** plan z parametrem `dry_run=true` zwraca JSON bez commit. Następny call `commit_plan(draft_id)` zapisuje.
15. **Sugerowana zmiana:** plan operation = dwuetapowa. (1) Generate draft (~3 min, ~$0.30) → pokazuje listę proponowanych tasków. (2) User wybiera które keep, edytuje treści, ustawia kolejność. (3) Commit — taski trafiają do DB.
16. **Challenge:** dwuetapowość dodaje complexity. Alternative: plan commituje natychmiast ale z soft-delete (30 dni), user może odrzucić całość przez "Undo plan O-001".

### Krok 7 — Review zaplanowanych tasków i korekta

1. **Nazwa kroku:** user ma 7 tasków wygenerowanych przez plan, chce sprawdzić czy sensowne, edytować, zmienić kolejność.
2. **Co user chce:** każdy task czytelnie opisany, easy edit treści / AC / kolejności, dodanie własnych.
3. **Skąd user wie że jest tu:** po plan idzie do tab Tasks. Wymaga ręcznego przełączenia.
4. **Co Forge robi pod spodem:** query `tasks` + `acceptance_criteria` + `task_dependencies`. Render tabela.
5. **Co user widzi:** tabela z 7 kolumnami (ID, Name, Origin, Status, AC count, Req refs, KRs). Edit button na końcu — inline form expand. Add Task form na dole.
6. **Czego user nie widzi:** (a) **graf zależności** (T-003 depends_on T-001, T-002), (b) estymacja time/cost per task, (c) edit AC bezpośrednio (wymaga wejścia w Task report), (d) drag-drop reorder.
7. **Cel istnienia:** human review przed drogim orchestrate.
8. **Bez tego — Forge działa?** Tak ale user bardziej ślepo uruchamia orchestrate.
9. **Wady obecnej implementacji:** tabela OK dla flat list, ale brak dependency visualization. "Order" nie jest explicit — Forge robi topological sort ale user tego nie widzi.
10. **Ograniczenia interfejsu:** brak graf, brak batch edit (np. "dla wszystkich feature tasków zmień scope na backend"), brak "duplicate task", brak delete task bez idzie do DELETE endpoint który nie ma UI button.
11. **Nieciągłości wchodzące:** plan DONE → user sam ma iść do Tasks tab. Brak auto-redirect z banerem sukcesu.
12. **Nieciągłości wychodzące:** zreviewałem → chcę uruchomić → button Orchestrate w pasku 4 akcji. Ale parametry (max_tasks, skip_infra, enable_redis) są nieczytelne.
13. **Brakujące funkcje UI:** DAG visualization (SVG), inline AC edit w tabeli (nie w osobnym widoku), delete button, duplicate button, drag reorder (wymagał dependency checking).
14. **Brakujące funkcje backend:** bulk update tasks (batch scope change), `POST /tasks/{ext}/duplicate`.
15. **Sugerowana zmiana:** widok z 2 kolumnami — lewa: DAG graph (node per task, edges per dependency), prawa: tabela z filtered view. Klik na node → fokus prawej na ten task. Drag node przestawia kolejność (z walidacją dependency).
16. **Challenge:** DAG visualization w HTMX + Tailwind — wymaga SVG lib (Mermaid, Dagre). Trade-off: complexity vs readability. Dla 7 tasków tabela wystarczy. Dla 30+ DAG jest niezbędny.

### Krok 8 — Konfiguracja przed orchestrate (Anthropic key, budget, infra)

1. **Nazwa kroku:** user chce uruchomić orchestrate, ale musi zapewnić że ma Anthropic key, budget, i potencjalnie Docker infra.
2. **Co user chce:** zobaczyć że wszystko skonfigurowane, poprawić jeśli nie.
3. **Skąd user wie że jest tu:** nigdzie — aktualnie Forge startuje orchestrate i dopiero wtedy widzi "no Anthropic key" error.
4. **Co Forge robi pod spodem:** `_resolve_anthropic_key(proj)` → jeśli None → subprocess z system auth (działa w dev), jeśli set → decrypt i inject do env. Budget check `_enforce_budget` przed każdym LLM call.
5. **Co user widzi:** w obecnym UI — nic. Musi przejść do Org Settings (⚙ icon w navbar) żeby skonfigurować.
6. **Czego user nie widzi:** (a) pre-flight checklist "Anthropic key: ✓/✗, Budget: ✓/✗, Docker running: ✓/✗", (b) estymacja całego orchestrate "7 tasków, ~$8-15, ~45-90 min", (c) porównanie z obecnym spendem "$8 z $100 monthly budget".
7. **Cel istnienia:** zapobieganie "uruchomiłem, zabrakło budget, stracone $5 na halfway".
8. **Bez tego — Forge działa?** Częściowo — system auth Claude CLI fallback. Ale dla commercial deployment wymagane BYO key.
9. **Wady obecnej implementacji:** brak pre-flight. User dowiaduje się podczas orchestrate że coś nie działa.
10. **Ograniczenia interfejsu:** brak "skonfiguruj teraz" modal w kontekście uruchamiania, brak help text na Org Settings page ("dlaczego potrzebuję klucz", "jak go dostać").
11. **Nieciągłości wchodzące:** zreviewałem taski, chcę uruchomić → orchestrate button → no Anthropic key → 500 error.
12. **Nieciągłości wychodzące:** error → user musi odnaleźć Org Settings → skonfigurować → wrócić → uruchomić.
13. **Brakujące funkcje UI:** pre-flight checklist modal przed orchestrate (green/red checks), quick-fix buttons "ustaw klucz", "zwiększ budget".
14. **Brakujące funkcje backend:** `GET /projects/{slug}/pre-flight` zwraca status wszystkiego.
15. **Sugerowana zmiana:** button "Orchestrate" w pasku akcji po kliknięciu otwiera modal z pre-flight. Jeśli wszystko zielone — potwierdź i start. Jeśli coś czerwone — link bezpośrednio do setup.
16. **Challenge:** pre-flight modal dodaje friction. Rozwiązanie: skip gdy wszystko już skonfigurowane raz (cache w user prefs).

### Krok 9 — Start orchestrate run i live monitoring

1. **Nazwa kroku:** orchestrate ruszył, user patrzy jak Forge wykonuje taski.
2. **Co user chce:** widzieć co się dzieje teraz, ile trwa, ile kosztuje, móc zatrzymać.
3. **Skąd user wie że jest tu:** kliknął Orchestrate, dostał redirect do `/ui/orchestrate-runs/{id}`.
4. **Co Forge robi pod spodem:** `BackgroundTasks.add_task(_run_orchestrate_background, ...)` — task idzie w osobny wątek, UI polluje `/api/v1/orchestrate-runs/{id}` co 2s.
5. **Co user widzi:** strona z live-polling panelem — status badge (PENDING/RUNNING/DONE/FAILED), 4 kafelki (done/failed/cost/elapsed), current task + phase, progress_message, Cancel button jeśli RUNNING.
6. **Czego user nie widzi:** (a) **log stream** co Claude CLI pisze (stdout subprocess), (b) per-phase cost breakdown (execute Sonnet $0.40, extract Sonnet $0.05, challenge Opus $0.30), (c) ETA do końca, (d) lista tasków z ich statusami, (e) ostrzeżenie gdy koszt przekracza estymację.
7. **Cel istnienia:** human visibility w long-running ops. Forge USP — "nie ufaj blindly, Forge pokazuje co robi".
8. **Bez tego — Forge działa?** Tak ale user byłby ślepy — orchestrate trwa 30-60 min, user musi przyjść za godzinę i zobaczyć czy skończyło.
9. **Wady obecnej implementacji:** live view jest OK (jedyna dobrze zrobiona część UX), ale brak log stream subprocess Claude CLI, brak listy wszystkich tasków, tylko "current".
10. **Ograniczenia interfejsu:** cancel = zmienia `cancel_requested=true`, ale działa dopiero gdy pętla orchestrate sprawdzi między taskami. Aktualnie-wykonywany Claude CLI subprocess **nie jest zabity** — czeka do końca.
11. **Nieciągłości wchodzące:** kliknąłem Orchestrate → redirect 303 → live view ładuje się. Polling zaczyna się po load. OK.
12. **Nieciągłości wychodzące:** orchestrate DONE → user widzi final result z listą tasków + status. Ale brak "co teraz?" — klikalne linki do każdego taska DONE żeby przeglądać raport.
13. **Brakujące funkcje UI:** log stream (SSE albo heavy polling), per-phase cost, ETA calculation, lista wszystkich tasków w orchestrate z klikalnymi linkami, warning banner gdy koszt eskaluje.
14. **Brakujące funkcje backend:** endpoint `/orchestrate-runs/{id}/logs` zwracający stream stdout ostatniego CLI call. SSE endpoint dla live log.
15. **Sugerowana zmiana:** layout 3-kolumnowy: (lewy) lista tasków orchestrate z statusami, (środek) current task detail z live log, (prawy) cost tracker + ETA + cancel controls.
16. **Challenge:** SSE w FastAPI + Jinja + HTMX — możliwe ale trudne. Polling co 1s output stream jest prostsze ale obciąża serwer. Kompromis: polling co 3s z ostatnimi 100 lines log.

### Krok 10 — Review DONE taska i ocenia czy gotowe

1. **Nazwa kroku:** task status=DONE, user otwiera raport i decyduje czy akceptuje.
2. **Co user chce:** **verdykt** GOTOWE / WYMAGA POPRAWY + szczegóły jeśli trzeba.
3. **Skąd user wie że jest tu:** z orchestrate live view (jeśli klika link na task DONE) lub z tab Tasks.
4. **Co Forge robi pod spodem:** `GET /ui/projects/{slug}/tasks/{ext}` → `task_report()` agreguje wszystko — requirements, tests, challenge, decisions, findings, diff, AC, comments.
5. **Co user widzi:** strona z 10+ sekcjami w kolejności: header, requirements, objective+KRs, tests executed, challenge, findings, decisions, diff, AC, not-executed, comments.
6. **Czego user nie widzi:** (a) **syntetyczny verdykt** "🟢 GOTOWE DO WYSŁANIA / 🟡 MA WARNINGS / 🔴 BLOKERY", (b) "next actions" per finding HIGH ("napraw przed merge"), (c) comparison "expected vs delivered" (SOW wymagał X, Forge dostarczył Y — czy match?), (d) **button "Wyślij klientowi"** (git push / PDF / share link).
7. **Cel istnienia:** user musi szybko ocenić jakość Forge output żeby zdecydować: wysłać / retry / poprawić ręcznie.
8. **Bez tego — Forge działa?** Technicznie tak, biznesowo nie — user przegląda 10 sekcji szukając "czy to gotowe?" i nie znajduje jednoznacznej odpowiedzi.
9. **Wady obecnej implementacji:** raport jest **dokładny** (zaletą Forge) ale **bez wnioskowania** (user musi sam zinterpretować 10 sekcji).
10. **Ograniczenia interfejsu:** brak verdyktu, brak prioritized next actions, brak export, brak comparison view.
11. **Nieciągłości wchodzące:** z orchestrate live view → klik na T-001 DONE → strona raport. OK.
12. **Nieciągłości wychodzące:** zreviewałem → i co? Brak buttona "Wyślij klientowi", "Retry z poprawką", "Oznacz jako wymaga rework". User zostaje w ślepym zaułku.
13. **Brakujące funkcje UI:** **verdict banner** na górze (algorytm: jeśli any finding HIGH → 🔴, jeśli challenge NEEDS_REWORK → 🟡, jeśli wszystko pass → 🟢), action buttons "Wyślij klientowi" / "Retry" / "Export PDF" / "Share link", comparison z objective KRs (czy KR osiągnięty?).
14. **Brakujące funkcje backend:** git push (brak), PDF export (brak), retry endpoint (brak).
15. **Sugerowana zmiana:** header raportu to nie "T-001 Storage module: load/save JSON, status DONE, cost $0.36". To "🟢 T-001 GOTOWE DO WYSŁANIA · Pass: tests 3/3, challenge PASS · Cost: $0.36 · [Wyślij klientowi] [Export PDF] [Retry z poprawką]". Dalsze sekcje — szczegóły pod fold.
16. **Challenge:** algorytm verdyktu może się mylić. Soft approach: verdykt jako "sugestia Forge" plus override manual przez owner'a.

### Krok 11 — Findings triage (co zrobić z rzeczami które znaleźliśmy)

1. **Nazwa kroku:** task DONE, ale Phase B/C znalazły 3 findings (bugs, improvements, security concerns). User decyduje co z nimi.
2. **Co user chce:** przejrzeć każdy finding, zaakceptować jako task (auto-create) / defer / reject jako non-issue.
3. **Skąd user wie że jest tu:** tab Findings lub sekcja findings w raporcie taska.
4. **Co Forge robi pod spodem:** `POST /findings/{id}/triage` + action (approve→task / defer / reject).
5. **Co user widzi:** karty findings z 3 buttonami (✓ Approve→Task / ⏸ Defer / ✗ Reject). Jeśli approved — pojawia się text "Created task: T-010".
6. **Czego user nie widzi:** (a) **notifications** gdy nowe findings HIGH pojawiają się w orchestrate, (b) batch triage (zatwierdź wszystkie LOW), (c) filter per severity/type, (d) sort.
7. **Cel istnienia:** Forge findings to główny deliverable wartościowy — "AI znalazło bugi których inni nie zauważyli". Must-use feature.
8. **Bez tego — Forge działa?** Findings były by tylko listą. Cała wartość "quality" z Phase B/C wymaga user action na findings.
9. **Wady obecnej implementacji:** triage działa, ale discoverability słaba — findings tab to 5. z 8. User może nie zauważyć 3 HIGH finding się pojawiło.
10. **Ograniczenia interfejsu:** brak batch, brak filter, brak notification, brak activity feed.
11. **Nieciągłości wchodzące:** po orchestrate DONE user widzi final result, ale findings **nie są highlighted**. Nawet HIGH findings kryją się w liście tasków.
12. **Nieciągłości wychodzące:** approve findingu → tworzy task → gdzie go user znajdzie? W tabie Tasks, ale to inna kontekst niż findings.
13. **Brakujące funkcje UI:** pokazanie "⚠ 3 findings HIGH wymagają Twojej uwagi" na dashboardzie, filter dropdown, batch checkbox selection, link z finding do powiązanego taska.
14. **Brakujące funkcje backend:** `POST /findings/bulk-triage` (lista findings_ids + akcja).
15. **Sugerowana zmiana:** dashboard pokazuje "Do zrobienia" z findings HIGH na czerwono. Per-finding action jednym klikiem. Batch select dla masowego reject LOW.
16. **Challenge:** priorytet finding HIGH — czy user powinien być zablokowany w progressie dopóki nie triage'uje? Miękko — banner, nie hard block.

### Krok 12 — Iteracja: "zmień wymagania, re-plan, run again"

1. **Nazwa kroku:** klient przysłał korekty ("dodaj feature X, usuń Y"), user musi zaktualizować projekt.
2. **Co user chce:** dodać nowe requirementy, zaktualizować objective, dodać taski, uruchomić tylko zmienione.
3. **Skąd user wie że jest tu:** otrzymał email/sleep od klienta z listą zmian.
4. **Co Forge robi pod spodem:** pattern "change request" — analyze nowych dokumentów, diff z istniejącym planem, sugerowane zmiany.
5. **Co user widzi:** aktualnie — **nic**. Nie ma UI dla change request. User musi ręcznie: upload nowych docs → ponownie analyze (nie wiadomo czy tworzy duplikaty) → manual edit tasków.
6. **Czego user nie widzi:** (a) "upload delta" — nowe dokumenty bez kasowania starych, (b) "change impact" — które objectives/tasks dotknięte, (c) "re-plan tylko zmienione".
7. **Cel istnienia:** projekty nie są one-shot — iteracyjne.
8. **Bez tego — Forge działa?** Tak dla greenfield, nie dla iteracji. Masywny brak.
9. **Wady obecnej implementacji:** brak change request flow.
10. **Ograniczenia interfejsu:** brak.
11. **Nieciągłości wchodzące:** klient zmienił zakres → user nie wie jak wpleść w Forge bez powtórki całości.
12. **Nieciągłości wychodzące:** zmiana zrobiona manualnie → brak audit trail "co się zmieniło od wersji 1 SOW".
13. **Brakujące funkcje UI:** "Add change request" button, diff view before/after, selective re-plan, selective re-orchestrate.
14. **Brakujące funkcje backend:** `POST /projects/{slug}/change-request` — analyze delta, propose changes. Była skill "change-request" w starym Forge, brak w platform/.
15. **Sugerowana zmiana:** nowy tab "Changes" — lista wersji SOW, diff, change requests. Per change request: impact analysis + proposed tasks + user accept/modify.
16. **Challenge:** duże feature (2-3 wk effort). Alternative (short term): skip — user robi change request manualnie przez Edit objective + Add task. Długoterminowo: must-have.

### Krok 13 — Wysłanie klientowi (deliverable)

1. **Nazwa kroku:** user ma skończony projekt, chce wysłać klientowi: kod + raport.
2. **Co user chce:** jeden klik "Send to client" który: tworzy PR w jego GitHub, generuje PDF raport, wysyła email / Slack message klientowi z linkami.
3. **Skąd user wie że jest tu:** raport DONE, kliknął "Wyślij klientowi" (który nie istnieje).
4. **Co Forge robi pod spodem:** (planned) `git push` do remote + GitHub API PR + WeasyPrint PDF + webhook / email.
5. **Co user widzi:** **nic** — feature nie istnieje. User musi: manualnie sklonować workspace z serwera, git push do swojego repo, PDF zrobić print-to-PDF z raport page.
6. **Czego user nie widzi:** (a) share link do raportu, (b) PDF download, (c) git integration, (d) email compose.
7. **Cel istnienia:** **to jest deliverable**. Forge bez tego to "kod gdzieś na serwerze" — klient tego nie zobaczy.
8. **Bez tego — Forge działa?** Dla delivery: NIE. To główny krytyczny brak Phase 1.
9. **Wady obecnej implementacji:** brak feature.
10. **Ograniczenia interfejsu:** brak.
11. **Nieciągłości wchodzące:** skończyłem review → chcę wysłać → ślepa uliczka.
12. **Nieciągłości wychodzące:** nic nie wychodzi.
13. **Brakujące funkcje UI:** Send to client modal — checkboxy "co wysłać" (PR / PDF / share link), email recipient, custom message.
14. **Brakujące funkcje backend:** `POST /projects/{slug}/git-push` (branch + PR), `GET /tasks/{ext}/report.pdf`, `POST /share-links` (istnieje!) + email integration.
15. **Sugerowana zmiana:** pełen flow "Send to client" z modal, integracje z GitHub/Slack/email. Phase 1 MUST-have.
16. **Challenge:** wymaga OAuth app dla GitHub (complex) lub Personal Access Token (simpler). Plus provider integration dla email/Slack. Priority: PAT first.

### Krok 14 — Returning user: "co się zmieniło od ostatniej wizyty"

1. **Nazwa kroku:** user wraca po tygodniu przerwy, chce szybko ogarnąć status.
2. **Co user chce:** activity feed, "nowe rzeczy", "rzeczy wymagające uwagi", kontynuacja.
3. **Skąd user wie że jest tu:** zalogował się.
4. **Co Forge robi pod spodem:** nic specjalnego — per session.
5. **Co user widzi:** tę samą listę projektów co nowy user.
6. **Czego user nie widzi:** (a) "od ostatniej wizyty: 5 tasków DONE, 3 findings HIGH, $4.20 wydane", (b) lista zmian cross-project, (c) "co wymaga Twojej uwagi dziś" (pending findings, open decisions, failed tasks).
7. **Cel istnienia:** redukcja tarcia dla power users.
8. **Bez tego — Forge działa?** Tak ale returning user rzuca "za dużo rzeczy do ogarnięcia".
9. **Wady obecnej implementacji:** zero kontekstu czasowego.
10. **Ograniczenia interfejsu:** brak.
11. **Nieciągłości wchodzące:** zalogowałem się → muszę odgadnąć gdzie patrzeć.
12. **Nieciągłości wychodzące:** brak.
13. **Brakujące funkcje UI:** activity feed na landing, "since last visit" metrics, priority inbox z akcjami do zrobienia.
14. **Brakujące funkcje backend:** `users.last_login_at` jest (używane), ale brak `GET /activity?since=timestamp`.
15. **Sugerowana zmiana:** landing dashboard zamiast pustej listy. Sekcje: "Od ostatniej wizyty" / "Wymaga uwagi" / "Projekty aktywne" / "Quick actions".
16. **Challenge:** co dla nowego usera bez historii? Fallback: onboarding hero (krok 0).

### Krok 15 — Multi-project porównanie

1. **Nazwa kroku:** user ma 5 projektów, chce porównać które droższe, które mają więcej findings, które ship-ready.
2. **Co user chce:** dashboard metrics cross-project, sortowanie, filter.
3. **Skąd user wie że jest tu:** potrzeba managerska / CFO-owa.
4. **Co Forge robi pod spodem:** query aggregate wszystkich projektów.
5. **Co user widzi:** listę kart projektów z basic stats. Brak tabeli sortowalnej, brak charts, brak total.
6. **Czego user nie widzi:** (a) "total spend this month across projects", (b) "projects with findings HIGH", (c) "avg cost per DONE task per project" — comparison dla projektów.
7. **Cel istnienia:** CFO / manager potrzebuje big picture.
8. **Bez tego — Forge działa?** Tak dla single-project user, nie dla manager'a.
9. **Wady obecnej implementacji:** brak aggregate view.
10. **Ograniczenia interfejsu:** brak.
11. **Nieciągłości wchodzące:** wchodzę jako manager → nie widzę metrics → wychodzę do Excel.
12. **Nieciągłości wychodzące:** brak.
13. **Brakujące funkcje UI:** dashboard z KPI cards (org total cost month, # DONE tasks, avg cost/task), tabela projektów sortowalna.
14. **Brakujące funkcje backend:** `GET /organizations/{id}/metrics` — aggregate.
15. **Sugerowana zmiana:** osobny widok "Org overview" (kliknięcie w logo Forge w navbar).
16. **Challenge:** mniej ważne niż per-project workflow. Phase 2 feature.

### Krok 16 — Audit / compliance review

1. **Nazwa kroku:** user compliance/audit chce zweryfikować co Forge zrobił — jakie prompty, jakie odpowiedzi, kto kiedy zmienił.
2. **Co user chce:** pełen audit trail, export do SIEM, filter per user/action/date.
3. **Skąd user wie że jest tu:** regulated context (bank, healthcare).
4. **Co Forge robi pod spodem:** `audit_log` table istnieje ale brak UI. `llm_calls` table jest w UI (tab).
5. **Co user widzi:** tab LLM-calls (per projekt) pokazuje listę calls z cost/duration/model. Kliknięcie → full prompt+response. Brak per-user audit (kto edytował objective, kto triage'ował finding).
6. **Czego user nie widzi:** audit_log UI, export CSV, filter, full timeline z akcjami user'ów.
7. **Cel istnienia:** compliance mandate dla regulated industries. Forge USP.
8. **Bez tego — Forge działa?** Dla dev/startup tak, dla enterprise regulated NIE.
9. **Wady obecnej implementacji:** audit_log tabela jest, UI brak.
10. **Ograniczenia interfejsu:** brak filter, export, per-user view.
11. **Nieciągłości wchodzące:** compliance officer loguje się → nie widzi "audit view".
12. **Nieciągłości wychodzące:** brak.
13. **Brakujące funkcje UI:** tab "Audit" per project i global per org, filters, export CSV/SIEM.
14. **Brakujące funkcje backend:** `GET /audit?project=X&user=Y&date_from=Z&export=csv`.
15. **Sugerowana zmiana:** Phase 2 feature. Post-MVP.
16. **Challenge:** specific dla enterprise, mniej ważne dla Phase 1 pilot.

### Krok 17 — Retirement / archive projektu

1. **Nazwa kroku:** projekt skończony, user chce go zarchiwizować żeby nie zaśmiecał listy.
2. **Co user chce:** archive button, later restore.
3. **Skąd user wie że jest tu:** lista projektów się wydłuża.
4. **Co Forge robi pod spodem:** brak — `Project` nie ma `archived` column.
5. **Co user widzi:** brak opcji. User musi DELETE project (destructive, nie-odwracalne, trudne przez FK).
6. **Czego user nie widzi:** archive / unarchive, soft-delete.
7. **Cel istnienia:** housekeeping przy skalowaniu do 10+ projektów.
8. **Bez tego — Forge działa?** Tak dla 1-2 projektów, nie dla 20+.
9. **Wady obecnej implementacji:** brak feature.
10. **Ograniczenia interfejsu:** brak.
11. **Nieciągłości wchodzące:** projekt DONE → user chce go "odłożyć" → brak.
12. **Nieciągłości wychodzące:** brak.
13. **Brakujące funkcje UI:** button "Archive project" w project settings, filter "Show archived".
14. **Brakujące funkcje backend:** `PATCH /projects/{slug}` z `archived=true`, filter queries.
15. **Sugerowana zmiana:** Phase 2. Low priority.
16. **Challenge:** YAGNI dla early pilot. Odłożyć.

---

**Podsumowanie Sekcji 1:** 17 kroków. W każdym — konkretnie co user chce, co widzi, czego nie widzi, jakie braki UI/backend, co proponuję, jakie trade-offs. To jest **mapa workflow**. Design UI zbuduję wokół tego, nie wokół API entities.

---

# SEKCJA 2 — Audyt elementów UI (widget by widget)

Kryteria dla każdego elementu (10 wymiarów):
1. Co reprezentuje
2. Skąd user wie kiedy go użyć
3. Co się dzieje po interakcji
4. Czy operacja kompletnie wspierana
5. Brakujące funkcje wokół
6. Ograniczenia interfejsu
7. Sens samodzielny
8. Bez tego workflow działa?
9. Konkretne sugestie
10. Challenge / kontrargumenty

## 2.1 Navbar (top, `base.html`)

1. **Reprezentuje:** kontekst globalny (user, org, projekt) + dostęp do Org Settings + logout.
2. **Kiedy użyć:** zawsze widoczny; user klika, gdy chce zmienić projekt / org / wylogować się.
3. **Po interakcji:** link "Projects" → `/ui/projects`; "Org Settings" → `/ui/org/settings`; "Logout" → POST logout, redirect `/ui/login`.
4. **Kompletnie wspierane:** częściowo. Brak: org switcher (multi-org), project switcher (brak dropdown — trzeba wrócić do listy), user profile, notifications bell.
5. **Brakuje wokół:** breadcrumb (user w głębokim drzewie nie wie gdzie jest), search global (Ctrl+K), language switcher.
6. **Ograniczenia:** brak responsywności mobile (pilot = desktop, akceptowalne).
7. **Sens samodzielny:** TAK — stały punkt orientacyjny.
8. **Bez tego:** user nie ma jak się wylogować / zmienić context → krytyczne. Navbar MUST.
9. **Sugerowana zmiana:** dodać breadcrumb (project → objective → task), project switcher jako dropdown (top 5 ostatnich), dodać global search (Ctrl+K) w Phase 2.
10. **Challenge:** "za dużo w navbar → przeciążenie". Kontrargument: breadcrumb jest pasywny (tylko pokazuje), dropdown ukryty do click. OK.

## 2.2 Dashboard (`/ui/projects` — lista projektów)

1. **Reprezentuje:** wszystkie projekty usera w jego org.
2. **Kiedy użyć:** landing po loginie, przełączanie między projektami.
3. **Po interakcji:** kliknięcie karty → `/ui/projects/{slug}`. "New Project" → form.
4. **Kompletnie wspierane:** CRUD projekt — TAK. Ale brak metadanych: ile objectives? ile tasków DONE? last activity? budget used? Tylko slug + name + goal.
5. **Brakuje wokół:** filter/sort (po dacie, po status), statystyki (aktywne/archived/done), tiles z widget podsumowania.
6. **Ograniczenia:** scala do ~20 projektów max na liście. Brak paginacji.
7. **Sens samodzielny:** TAK.
8. **Bez tego:** brak entry point → krytyczne. MUST.
9. **Sugerowana zmiana:** kafelki zamiast listy. Każdy kafelek: nazwa, status objective (np. "2/3 ACHIEVED"), % tasków DONE (progress bar), last activity, budget used. Sort: last activity desc.
10. **Challenge:** "kafelki = więcej miejsca, mniej info na ekranie". Kontrargument: user pilotowy ma 1-5 projektów. Kafelki OK. Przy 20+ — przełącznik lista/grid.

## 2.3 Project page — top bar (nazwa, slug, 4 action buttons)

1. **Reprezentuje:** entry point do projektu + główne akcje pipeline.
2. **Kiedy użyć:** landing na projekcie.
3. **Po interakcji:** 4 buttony: "Ingest", "Analyze", "Plan", "Orchestrate" — każdy wywołuje swój endpoint.
4. **Kompletnie wspierane:** akcje są, ale **bez kontekstu** — user nie wie **w jakim stanie jest pipeline**. Buttony są zawsze klikalne, nawet jeśli nielogiczne (np. "Plan" bez objective).
5. **Brakuje wokół:** **wizualizacja stanu pipeline** (SOW registered? analyzed? planned? running?). Obecnie — tylko 4 buttony obok siebie, jak w kalkulatorze.
6. **Ograniczenia:** 4 buttony bez kontekstu = 4 pytania "czy muszę klikać? co się stanie?". Najgorszy punkt UI obecnie.
7. **Sens samodzielny:** NIE — user nie wie co robić.
8. **Bez tego:** workflow nie działa, ale obecna forma = 100% sensu negatywnego.
9. **Sugerowana zmiana:** **Pipeline stepper** — 4 kroki pionowe: `[1] Upload SOW` → `[2] Analyze` → `[3] Plan` → `[4] Orchestrate`. Każdy krok: status (empty / done / current / blocked), description ("SOW defines what we build"), action button widoczny TYLKO gdy krok aktywny, expand gdy DONE (pokazuje co dostał).
10. **Challenge:** "overhead vs 4 buttony w rzędzie". Kontrargument: obecnie 80% usera nie wie co zrobić. Stepper rozwiązuje 80%. Wart inwestycji.

## 2.4 Tab "Objectives"

1. **Reprezentuje:** listę celów biznesowych projektu (po /analyze).
2. **Kiedy użyć:** gdy user chce zobaczyć "co Forge wywnioskował z SOW", wybrać cel do /plan, edytować KR.
3. **Po interakcji:** lista kart; każda karta expand → KR list, conflicts badge, open_questions badge. Buttony: "Plan", "Edit title/description".
4. **Kompletnie wspierane:** tak — view/edit/add/delete. KR CRUD TAK.
5. **Brakuje wokół:** priorytetyzacja (drag-drop, owner na poziomie objective), grouping po epicu / tematyce, progress bar objective na podstawie % KR ACHIEVED.
6. **Ograniczenia:** przy 10+ objectives — ciężko znaleźć właściwy. Brak search.
7. **Sens samodzielny:** TAK dla review; NIE dla "planning flow" — user nie wie który wybrać do /plan.
8. **Bez tego:** workflow nie działa. MUST.
9. **Sugerowana zmiana:** sort po priority, collapse wszystko domyślnie (klik → expand), pokazać na karcie: "2/4 KR met", "0 conflicts", "Plan ready? YES/NO". Na górze — button "Plan all ready objectives" (bulk).
10. **Challenge:** "bulk plan = ryzyko błędnego planu". Kontrargument: user ma preview-approve po drafcie planu. Bulk = tylko szkielet.

## 2.5 Tab "Tasks"

1. **Reprezentuje:** listę tasków projektu + ich status + AC + wyniki.
2. **Kiedy użyć:** review planu, monitoring podczas orchestrate, debugging FAILED tasków.
3. **Po interakcji:** lista row; klik row → expand (AC list, instruction, result). Button "Begin" dla NEW/READY. Buttony "Edit", "Delete", "Skip".
4. **Kompletnie wspierane:** tak, ale **bez wizualizacji dependency**. Tasks są listą, nie grafem. User nie widzi "T-003 zależy od T-001".
5. **Brakuje wokół:** graf DAG (kto zależy od kogo), krytyczna ścieżka (najdłuższy łańcuch blokujący), filtruj (by status / objective / assignee).
6. **Ograniczenia:** przy 50+ tasków — lista staje się nieużywalna.
7. **Sens samodzielny:** TAK dla małych planów (5-10); słabe dla dużych (50+).
8. **Bez tego:** workflow nie działa (tasks = jądro).
9. **Sugerowana zmiana:** 2 widoki — (a) **List view** (obecny) dla kontroli, (b) **Kanban view** (Backlog / Ready / In-Progress / Review / Done) dla ogólnego obrazu, (c) **Graph view** (DAG strzałki) dla dependency debugging.
10. **Challenge:** "3 widoki = complexity". Kontrargument: user może wybrać co pasuje. Default: list (obecny). Advanced: kanban/graph.

## 2.6 Tab "AC" (Acceptance Criteria)

1. **Reprezentuje:** AC nie przypisane do tasków (standalone), albo przegląd wszystkich AC w projekcie.
2. **Kiedy użyć:** **niejasne** — AC są zwykle przy tasku; dlaczego osobna zakładka?
3. **Po interakcji:** lista AC z delete/edit.
4. **Kompletnie wspierane:** CRUD tak.
5. **Brakuje wokół:** filter (po statusie: met/not met), search. Ale **fundamentalnie — zakładka jest zła**.
6. **Ograniczenia:** duplikacja — AC widoczne przy tasku I w osobnej zakładce. User nie wie gdzie edytować.
7. **Sens samodzielny:** NIE. AC należą do task, nie do projektu.
8. **Bez tego:** workflow działa lepiej. **Usunąć zakładkę**.
9. **Sugerowana zmiana:** usunąć tab "AC". AC edytowalne TYLKO w kontekście taska (inline expand taska).
10. **Challenge:** "czasem AC są cross-task". Kontrargument: prawdziwie cross-task AC = KR (objective level). Tam jest miejsce. Osobny tab "AC" = redundancja.

## 2.7 Tab "KR" (Key Results)

1. **Reprezentuje:** Key Results — pomiary objectives.
2. **Kiedy użyć:** kontrola postępu objective.
3. **Po interakcji:** lista KR z current/target/status.
4. **Kompletnie wspierane:** CRUD tak.
5. **Brakuje wokół:** KR widoczne już w tabie "Objectives" (expand). **Duplikacja**.
6. **Ograniczenia:** ta sama co AC.
7. **Sens samodzielny:** NIE — KR należą do objective.
8. **Bez tego:** workflow lepszy. Usunąć zakładkę.
9. **Sugerowana zmiana:** usunąć. KR tylko w Objectives.
10. **Challenge:** "all KR view = przegląd statusu bez wchodzenia w objectives". Kontrargument: to można zrobić w Dashboard tab jako widget, nie osobna zakładka.

## 2.8 Tab "Findings"

1. **Reprezentuje:** problemy wykryte przez Claude podczas execute (Phase B delivery extraction) + Phase C challenge.
2. **Kiedy użyć:** po orchestrate run — user powinien przejrzeć findings.
3. **Po interakcji:** lista kart; każda: severity (critical/high/medium/low), category, title, description, recommendation. Triage: accept / reject / defer.
4. **Kompletnie wspierane:** częściowo. Triage status zapisywany ale **bez workflow follow-up**. Jeśli accept → co dalej? brak automatycznego task creation.
5. **Brakuje wokół:** "Accept → create task" (button). Filter po severity. Group by category. Export (MD/PDF).
6. **Ograniczenia:** findings są produktem, ale nikt ich nie używa (visual dead-end).
7. **Sens samodzielny:** TAK (wartościowe info).
8. **Bez tego:** workflow działa, ale user traci insight.
9. **Sugerowana zmiana:** "Accept & create task" → prefilled task form (title = finding.title, description = finding.description + recommendation). Alerty w dashboardzie: "3 critical findings not triaged". Export button.
10. **Challenge:** "auto-task = noise". Kontrargument: auto-task jest manualny (user klika "Accept → create"). Nie noise.

## 2.9 Tab "Guidelines"

1. **Reprezentuje:** zasady projektu (coding standards, must_not, domain rules).
2. **Kiedy użyć:** onboarding nowego projektu, ustalanie standardów.
3. **Po interakcji:** lista kart, CRUD.
4. **Kompletnie wspierane:** tak.
5. **Brakuje wokół:** scopes (backend/frontend/database), MUST vs SHOULD, templates ("load Python standards").
6. **Ograniczenia:** guidelines są statyczne, user musi pamiętać je tworzyć.
7. **Sens samodzielny:** TAK dla zaawansowanych.
8. **Bez tego:** default guidelines w kodzie; user nie customize. Workflow działa.
9. **Sugerowana zmiana:** template library (Python best, Node best, Django conventions). Button "Import from template". W forma dodać pole "scope" z dropdown.
10. **Challenge:** "user nie używa guidelines (0% obserwowane)". Kontrargument: bo nie ma template. Pozwól importować — wzrośnie użycie.

## 2.10 Tab "Decisions"

1. **Reprezentuje:** otwarte decyzje zidentyfikowane przez Claude podczas /analyze (wieloznaczności w SOW) + decisions zapisane podczas execute.
2. **Kiedy użyć:** resolve conflicts w analyze, audit historyczny.
3. **Po interakcji:** lista decisions, CRUD, status (OPEN / CLOSED / SUPERSEDED).
4. **Kompletnie wspierane:** CRUD tak, ale **brak linkage do objectives** (open decision → który objective blokuje?).
5. **Brakuje wokół:** "affected objectives" link, severity, kto resolve.
6. **Ograniczenia:** user nie wie, kiedy dodać decision manualnie vs Claude auto.
7. **Sens samodzielny:** TAK (audit).
8. **Bez tego:** workflow działa gorzej (conflicts niewidoczne).
9. **Sugerowana zmiana:** OPEN decisions na top dashboardu ("3 decisions need your resolution"). Inline przy objective badge "2 open decisions".
10. **Challenge:** "za dużo alertów". Kontrargument: 3 decisions przy 5 objectives to akceptowalny szum. MUST do resolve przed /plan.

## 2.11 Tab "Ideas"

1. **Reprezentuje:** staging area — pomysły, nie-objectives (jeszcze).
2. **Kiedy użyć:** brainstorm, zanim formalizuje się objective.
3. **Po interakcji:** CRUD idea.
4. **Kompletnie wspierane:** tak.
5. **Brakuje wokół:** "Promote idea → objective" (button).
6. **Ograniczenia:** staging area, której nikt nie używa (w CLAUDE.md: "opt-in").
7. **Sens samodzielny:** LIMITED.
8. **Bez tego:** workflow działa.
9. **Sugerowana zmiana:** ukryć w MVP; dodać jako "advanced mode". Albo merge z "Objectives (draft)".
10. **Challenge:** "niektóre teamy używają". Kontrargument: 0 obserwacji w pilot. Ukryć do Phase 2.

## 2.12 Tab "Discover" (exploration/research)

1. **Reprezentuje:** eksploracja opcji technicznych przed decyzją.
2. **Kiedy użyć:** complex architecture decision.
3. **Po interakcji:** Claude generuje exploration (options, risks, recommendation).
4. **Kompletnie wspierane:** tak (CLI `/discover`).
5. **Brakuje wokół:** UI do triggerowania `/discover` z webapp.
6. **Ograniczenia:** nie zintegrowane z UI (tylko CLI).
7. **Sens samodzielny:** TAK dla advanced users.
8. **Bez tego:** workflow podstawowy działa.
9. **Sugerowana zmiana:** Phase 2 — button "Discover option" przy decision.
10. **Challenge:** "feature nie-podstawowe". Zgoda. Odłożyć.

## 2.13 Tab "Knowledge" i "Research"

1. **Reprezentuje:** fakty wydobyte z SOW (Knowledge) + szersza wiedza domenowa (Research).
2. **Kiedy użyć:** audit — sprawdzić czy Claude dobrze zrozumiał SOW.
3. **Po interakcji:** lista faktów.
4. **Kompletnie wspierane:** tak, ale read-only (user nie może edytować, Claude'y generują).
5. **Brakuje wokół:** link "Knowledge K-012 → Objective O-002" (traceability).
6. **Ograniczenia:** listy są długie (100+ faktów), bez kategorii.
7. **Sens samodzielny:** MEDIUM.
8. **Bez tego:** workflow działa (fakty używane przez Claude w tle).
9. **Sugerowana zmiana:** scalić w jeden tab "Source Knowledge" z filter (knowledge | research). Group by objective.
10. **Challenge:** "audit musi widzieć surowe fakty". Zgoda; ale grouping + filter nie blokuje audit, polepsza UX.

## 2.14 Task row (obecna forma)

1. **Reprezentuje:** jeden task z ID, name, status, assigned objective.
2. **Kiedy użyć:** kliknąć → expand → zobaczyć detale, execute, triage.
3. **Po interakcji:** expand pokazuje AC, instruction, result (jeśli DONE).
4. **Kompletnie wspierane:** częściowo. Brak: estimated cost, estimated time, dependency preview.
5. **Brakuje wokół:** "View in workspace" (plik który task dotyczy), "View diff" (jeśli DONE).
6. **Ograniczenia:** status badge małe, łatwo przeoczyć różnicę READY vs IN_PROGRESS.
7. **Sens samodzielny:** TAK.
8. **Bez tego:** workflow nie działa.
9. **Sugerowana zmiana:** pokazać na rządku: [status] [T-NNN] [name] [objective] [depends_on count] [estimated_cost] [duration]. Expand: AC, instruction, depends, produces, result (jeśli DONE) z linkiem do diff.
10. **Challenge:** "za dużo info na rządku". Kontrargument: estymate + duration kluczowe dla decision "run or not". Trzymać.

## 2.15 Task detail / result panel (po DONE)

1. **Reprezentuje:** wynik wykonania taska — verdict (DONE/FAILED), logi, diff, cost, tests.
2. **Kiedy użyć:** review czy task został zrobiony dobrze.
3. **Po interakcji:** czyta logi, diff, tests.
4. **Kompletnie wspierane:** CZĘŚCIOWO. Phase A wyniki widać (tests passed/failed). Phase B findings widać (lista). Phase C challenge widać (verdict CONSISTENT/DIVERGENT).
5. **Brakuje wokół:** **jednolita narracja**: "Ten task dostarczył endpoint POST /users. Testy przeszły 8/8. Challenger zgodził się. 3 findings low-severity."
6. **Ograniczenia:** obecnie 4 sekcje (logs, tests, findings, challenge) obok siebie — user musi scrollować i łączyć sam.
7. **Sens samodzielny:** TAK (kluczowy output).
8. **Bez tego:** user nie może ocenić jakości.
9. **Sugerowana zmiana:** **Deliverable summary card** na górze: icons (tests ✓, challenger ✓, findings !), 3 linijki narracji, buttons "View code", "Approve", "Request revision". Szczegóły poniżej w accordions.
10. **Challenge:** "narracja = dodatkowy LLM call = koszt". Kontrargument: narracja może być deterministycznie złożona z już-posiadanych pól (tests count, challenger verdict, findings count). Zero-cost.

## 2.16 AC row (w expand task)

1. **Reprezentuje:** jeden warunek akceptacji.
2. **Kiedy użyć:** definicja AC przed execute, audit po DONE.
3. **Po interakcji:** expand pokazuje verification (test/command/manual), test_path/command, status (met/not met).
4. **Kompletnie wspierane:** CRUD tak.
5. **Brakuje wokół:** **widoczna executabilna verification** — kliknij "Run test" obok AC.
6. **Ograniczenia:** AC edit jest inline ale bez preview "co dokładnie sprawdzi test".
7. **Sens samodzielny:** TAK.
8. **Bez tego:** brak traceability SOW → test.
9. **Sugerowana zmiana:** obok AC — button "Run now" (pytest/bash). Status odświeża inline. Wyświetl test output inline.
10. **Challenge:** "run może trwać długo". Kontrargument: to jest user's choice klikać. Cache ostatni wynik + timestamp.

## 2.17 KR row

1. **Reprezentuje:** Key Result — measurable pomiar objective.
2. **Kiedy użyć:** edycja przy objective, review postępu.
3. **Po interakcji:** edit target, current, status.
4. **Kompletnie wspierane:** CRUD tak.
5. **Brakuje wokół:** measurement command (`pytest --co` counter, `curl /health` responder) — currently user wpisuje current manualnie.
6. **Ograniczenia:** "current" nie aktualizuje się automatycznie.
7. **Sens samodzielny:** TAK.
8. **Bez tego:** objective bez KR = vague.
9. **Sugerowana zmiana:** pole `measurement_cmd` + button "Re-measure". Claude automatycznie odpala cmd i wpisuje current.
10. **Challenge:** "command injection". Kontrargument: cmd jest w sandboxie (Docker per project). OK.

## 2.18 Finding card

1. **Reprezentuje:** jeden finding — severity, category, title, description, recommendation.
2. **Kiedy użyć:** triage po orchestrate.
3. **Po interakcji:** accept/reject/defer.
4. **Kompletnie wspierane:** triage TAK, follow-up NIE.
5. **Brakuje wokół:** "Create task from finding", "Export all".
6. **Ograniczenia:** finding nie ma link do task który go zgłosił.
7. **Sens samodzielny:** TAK.
8. **Bez tego:** user nie wie o problemach.
9. **Sugerowana zmiana:** button "→ Create task", link "From: T-005", severity badge z kolorem (red/orange/yellow/gray).
10. **Challenge:** "kolory = accessibility". Kontrargument: kolory + tekst ("CRITICAL"). OK.

## 2.19 Guideline card

1. **Reprezentuje:** jedna zasada.
2. **Kiedy użyć:** CRUD standardów.
3. **Po interakcji:** edit text + scope.
4. **Kompletnie wspierane:** tak.
5. **Brakuje wokół:** MUST/SHOULD toggle, scope dropdown.
6. **Ograniczenia:** user tworzy w próżni (bez inspiracji).
7. **Sens samodzielny:** MEDIUM.
8. **Bez tego:** defaults kod. OK dla MVP.
9. **Sugerowana zmiana:** template library.
10. **Challenge:** odłożyć. OK.

## 2.20 Comment thread

1. **Reprezentuje:** dyskusja przy taska/objective.
2. **Kiedy użyć:** team collaboration, audit dialogu.
3. **Po interakcji:** post, reply, resolve.
4. **Kompletnie wspierane:** podstawowe tak.
5. **Brakuje wokół:** @mentions, notifications, markdown preview.
6. **Ograniczenia:** linear thread (brak replies-to-reply).
7. **Sens samodzielny:** TAK dla team.
8. **Bez tego:** team bez comment → Slack side-channel → traci audit.
9. **Sugerowana zmiana:** @mention notyfikacja email, markdown preview, link do task/obj.
10. **Challenge:** "Slack wystarczy". Kontrargument: Slack nie zapisuje w projekcie → audit traci. Comment MUST.

## 2.21 Share link (capability URL)

1. **Reprezentuje:** publiczny link do zasobu bez loginu.
2. **Kiedy użyć:** pokaż klientowi deliverable bez tworzenia konta.
3. **Po interakcji:** tworzy URL z token, user wysyła klientowi.
4. **Kompletnie wspierane:** generate TAK, expire TAK, ograniczenie do typu resource (project/task/finding).
5. **Brakuje wokół:** password protect, view counter, revoke one-click.
6. **Ograniczenia:** link = anyone-with-link (jak Google Docs).
7. **Sens samodzielny:** TAK (klient bez konta).
8. **Bez tego:** klient musi się rejestrować → friction.
9. **Sugerowana zmiana:** TTL wybór (1d / 7d / 30d / no-expire), view counter, button "Revoke".
10. **Challenge:** "unauth link = risk". Kontrargument: token 128-bit + TTL. OK dla deliverable (nie tajny).

## 2.22 Org settings

1. **Reprezentuje:** organizacja: name, budget, members, API keys.
2. **Kiedy użyć:** admin — invite member, set budget, add API key.
3. **Po interakcji:** CRUD.
4. **Kompletnie wspierane:** podstawowe tak.
5. **Brakuje wokół:** audit log (kto co zrobił), billing history, usage charts.
6. **Ograniczenia:** role = owner/editor/viewer — brak custom roles.
7. **Sens samodzielny:** TAK.
8. **Bez tego:** multi-tenant bez admin → chaos.
9. **Sugerowana zmiana:** audit log tab (event, user, timestamp), usage chart (tokens / cost / run per month).
10. **Challenge:** "admin features można później". Zgoda dla pilot; MUST dla prod.

## 2.23 Orchestrate run — live panel

1. **Reprezentuje:** aktywny proces wykonywania tasków.
2. **Kiedy użyć:** po "Start orchestrate" — monitoring.
3. **Po interakcji:** polling co 3s, pokazuje: current task, phase (Phase A/B/C), elapsed, cost-to-date, done count, failed count.
4. **Kompletnie wspierane:** TAK (najnowsza ficzer).
5. **Brakuje wokół:** live console output (tail logów), "Pause", "Cancel run".
6. **Ograniczenia:** poll 3s nie realtime (brak WebSocket). User czeka 3s na update.
7. **Sens samodzielny:** TAK.
8. **Bez tego:** user patrzy w pustą stronę 5-15 min. KRYTYCZNE.
9. **Sugerowana zmiana:** dodać console tail (live logs), "Pause" (zatrzymuje między taskami), "Cancel" (zabija). SSE/WS zamiast polling.
10. **Challenge:** "live logs = spam". Kontrargument: user może collapse. Toggle "Show logs".

## 2.24 Login / signup form

1. **Reprezentuje:** entry point do platform.
2. **Kiedy użyć:** first time, logout.
3. **Po interakcji:** POST → token cookie + redirect.
4. **Kompletnie wspierane:** tak.
5. **Brakuje wokół:** "Forgot password", "SSO", email verification.
6. **Ograniczenia:** brak 2FA.
7. **Sens samodzielny:** TAK (must).
8. **Bez tego:** nie da się wejść.
9. **Sugerowana zmiana:** "Forgot password" flow (email reset), email confirm signup, 2FA opcjonalnie (Phase 2).
10. **Challenge:** "2FA = friction". Kontrargument: opcjonalne (user toggle w settings).

**Podsumowanie Sekcji 2:** 24 widgety. 4 z nich SZKODLIWE (tab AC, KR — duplikacja; Ideas — niby advanced ale nieużywane; "4 buttony pipeline" — bez kontekstu). 12 wymaga wyraźnych ulepszeń (dashboard kafelki, pipeline stepper, task graph, finding→task, live console, narracja wyniku). 8 działa poprawnie ale brakuje polishingu.

---

# SEKCJA 3 — Nieciągłości (Discontinuities)

Definicja: user wykonał krok A, naturalnie oczekuje B, ale system nie prowadzi (dead-end, flash, missing link).

Kryteria (5 wymiarów):
1. Gdzie występuje
2. Dlaczego user czeka B
3. Co obecnie dzieje się (lub nie)
4. Wpływ (P0/P1/P2/P3)
5. Fix

## 3.1 Po /ingest → pusty projekt

1. Upload SOW kończy się toastem "Uploaded". Potem user wraca do pustej strony projektu (4 buttony).
2. User oczekuje: "teraz coś się dzieje, np. analyze".
3. Obecnie: nie. User musi ręcznie kliknąć "Analyze". Brak prompt.
4. **P0** — 50% userów pilotowych nie wie co zrobić dalej (obserwowane).
5. Fix: toast "Uploaded. Ready to analyze?" z button "Analyze now →".

## 3.2 Po /analyze → lista objectives bez guide

1. Analyze zwraca toast "2 objectives created". User idzie do tab "Objectives" i widzi listę.
2. User oczekuje: "co teraz? Plan?".
3. Obecnie: lista objectives jest, ale bez CTA "Plan this". User musi domyślić się.
4. **P0** — 70% userów nie kliknie button Plan (jest na top bar, nie inline).
5. Fix: w objective card dodać button "Plan →" inline.

## 3.3 Po /plan → lista tasków bez orchestrate prompt

1. Plan kończy się: "7 tasks created". Tab "Tasks" pokazuje listę NEW.
2. User oczekuje: "teraz start".
3. Obecnie: user musi kliknąć top bar "Orchestrate".
4. **P1** — user sam się domyśla (podobnie jak 3.2).
5. Fix: po /plan toast "Plan ready. Start execution?" z button.

## 3.4 Po kliknięciu "Orchestrate" → brak natychmiastowego feedback

1. Click "Orchestrate".
2. User oczekuje: natychmiast widzi aktualny task, loading.
3. Obecnie: redirect 303 → `/ui/orchestrate-runs/{id}?project=slug`. Strona ładuje się po ~1s. User przez sekundę patrzy na loading.
4. **P2** — akceptowalne ale można usprawnić.
5. Fix: pre-render skeleton + poll od razu zaczyna.

## 3.5 W trakcie orchestrate → current task bez "peek code"

1. User widzi "current task: T-003 (in Phase B)".
2. User oczekuje: "co Claude teraz pisze? jaki plik?"
3. Obecnie: nic. Tylko phase name.
4. **P1** — user czuje się ślepy.
5. Fix: console tail (ostatnie 20 linii logu Claude'a) lub alternatywnie "currently editing: app/users.py".

## 3.6 Task DONE → brak "co dalej"

1. Task T-001 DONE, test 3/3 passed.
2. User oczekuje: "zobacz wynik w workspace, review, accept, przejdź do T-002".
3. Obecnie: strona odświeża, pokazuje T-001 jako DONE, brak CTA.
4. **P1** — user się dziwi "czy mam coś zrobić?".
5. Fix: na task row po DONE: buttony "View diff", "Re-run", "Approve".

## 3.7 Orchestrate run zakończony → brak deliverable summary

1. Run DONE. Wszystkie 7 tasks DONE.
2. User oczekuje: "OK, co dostałem jako całość? Zarchiwizuj to, wyślij klientowi".
3. Obecnie: panel pokazuje "DONE" i już. User musi kliknąć każdego taska osobno żeby coś sensownego zobaczyć.
4. **P0** — brak "run report".
5. Fix: auto-generate "Run Report" (md/pdf): summary, objectives status, tasks status, cost total, deliverables list, findings, decisions. Button "Download" + "Share link".

## 3.8 FAILED task → brak retry UX

1. Task FAILED (tests 2/5 passed).
2. User oczekuje: "widzę co nie przeszło, naprawić i retry".
3. Obecnie: w task detail widzi result log. Musi użyć CLI aby retry.
4. **P0** — KRYTYCZNE. Brak "Retry".
5. Fix: button "Retry" (re-execute taska) + "Edit instruction" (modify AC/desc) + "Mark as chore & force complete".

## 3.9 KR ACHIEVED ale task task niekompletny

1. System oznacza KR ACHIEVED (numeric: target met).
2. User oczekuje: "gdzie to jest widoczne?".
3. Obecnie: status zmienia się w Objectives tab, brak powiadomienia.
4. **P2** — akceptowalne.
5. Fix: toast "🎯 KR met: endpoint /users returns 201".

## 3.10 Comment posted → brak notify

1. User A pisze @UserB w komentarzu T-005.
2. User B oczekuje: email / in-app notif.
3. Obecnie: nic. Comment zostaje w DB, User B musi sam wejść.
4. **P1** — multi-user bez notyfikacji = nieużywalne.
5. Fix: email + in-app notification on @mention.

## 3.11 Budget exceeded → run zatrzymany bez recovery

1. Orchestrate run w toku, trafia na budget limit → status BUDGET_EXCEEDED.
2. User oczekuje: "OK, zwiększ budget i resume".
3. Obecnie: run zakończony, pozostałe tasks NEW. User musi kliknąć Orchestrate znowu.
4. **P1**.
5. Fix: "Resume run" button po zwiększeniu budget (kontynuuje od ostatniego nie-DONE task).

## 3.12 Share link utworzony → brak lista aktywnych linków

1. User klika "Create share link" dla T-005.
2. Obecnie: toast z URL, koniec. Jeśli user zapomni URL, musi utworzyć nowy.
3. User oczekuje: lista aktywnych shared links z revoke.
4. **P2**.
5. Fix: Settings → "Share links" tab z listą (resource, created, expires, view count, revoke).

## 3.13 Project delete → cascade unclear

1. User klika "Delete project".
2. User oczekuje: ostrzeżenie "7 tasks, 3 findings zostaną usunięte".
3. Obecnie: confirm dialog "Delete?" generic.
4. **P1**.
5. Fix: confirm z counter: "This will delete 7 tasks, 3 findings, 2 objectives, 1 orchestrate run. Type slug to confirm".

## 3.14 No-project new user → onboarding dead-end

1. Nowy user loguje się po signup.
2. Widzi pustą listę projektów.
3. Oczekuje: "stwórz pierwszy projekt" guide.
4. Obecnie: "New Project" button, brak step-by-step tutorial.
5. **P1**.
5. Fix: empty state z tutorial (3 kroki: create project → upload SOW → let Forge work). Opcjonalnie sample project demo.

## 3.15 Analyze zwraca conflicts → brak resolve UX

1. Analyze wykrył 2 open decisions (conflicts).
2. User oczekuje: "rozwiąż i wróć do analizy".
3. Obecnie: decisions są w tab "Decisions", user musi sam wejść, rozwiązać, potem wrócić.
4. **P0** — breakthrough moment.
5. Fix: **Modal** po /analyze: "2 decisions need resolution before planning. [Resolve now] [Later]". Inline resolve (choose A / B / manual).

**Podsumowanie Sekcji 3:** 15 nieciągłości. **P0 (3)**: po-ingest next step prompt, retry FAILED task, deliverable summary po run. **P1 (7)**: objective card "Plan" CTA, console tail during run, task DONE "next" CTA, comment notif, budget resume, project delete cascade, onboarding dead-end. **P2 (5)**: polishing.

---

# SEKCJA 4 — Krytyczne braki (UI + Backend osobno)

## 4.A Braki UI (co jest w backendzie, brak w UI)

| Feature | Backend | UI | Wpływ |
|---|---|---|---|
| AC run-now | ✓ test_runner | ✗ | P1 |
| KR measurement cmd | ✗ | ✗ | P1 (wymaga obu) |
| Task retry | ✓ (manual re-execute) | ✗ | P0 |
| Share link list/revoke | ✓ endpoint | ✗ list view | P1 |
| Budget resume | częściowo | ✗ | P1 |
| Audit log | ✗ | ✗ | P1 |
| Decisions resolve modal | ✓ endpoint | ✗ | P0 |
| Live console tail | ✗ | ✗ | P1 |
| Delete cascade warning | ✗ | ✗ | P1 |
| Onboarding tutorial | n/a | ✗ | P1 |
| Run report (deliverable) | ✗ | ✗ | P0 |
| Finding → task (create) | ✗ | ✗ | P1 |

## 4.B Braki Backend

| Feature | Why missing | Wpływ |
|---|---|---|
| KR measurement cmd executor | Nie zdefiniowany kontrakt | P1 |
| Run report generator (md/pdf) | Nie ma WeasyPrint; brak zbieracza danych | P0 |
| Budget resume orchestrate | Logic zatrzymuje, brak resume endpoint | P1 |
| Audit log middleware | Nie napisany | P1 |
| Email delivery (notifications, invites, reset password) | Brak SMTP client | P1 |
| WebSocket/SSE streaming | Tylko polling | P2 |
| Dep graph (cycle detection) | Brak validate_dag | P1 (tasks graph) |
| Task retry endpoint | Brak POST /tasks/{id}/retry | P0 |
| Incremental re-plan | Brak diff detector między plan-po-plan | P1 |

## 4.C Co jest, ale niewygodne

- CSRF: header-only (OK), ale form tagi w templates czasem forgotten (bug risk).
- Test runner: detect_language fallback na extension (dobry fix), ale nie wspiera mixed projects (Python+Node).
- Claude CLI subprocess: brak streaming (czeka pełną odpowiedź). Powoduje 30-120s "cisza".

**Podsumowanie Sekcji 4:** 12 braków UI (3 P0), 9 braków backend (3 P0). Najostrzejsze: Retry, Run report, Decisions resolve modal.

---

# SEKCJA 5 — Czego dotychczas nie rozważono

1. **Cost preview przed execute** — user nie wie "ile ten run mnie będzie kosztował?". Forge ma planner, Claude może estymować tokeny. Feature MUST: "Estimated cost: $3.50 ± 30%".

2. **Rollback taska** — jeśli DONE task okazał się błędny, user musi ręcznie revertować git. Brak "Rollback T-005" button.

3. **Template projektu** — user zaczyna nowy projekt często z podobnych guidelines. Brak "Clone settings from project X".

4. **Multi-language project** — Python backend + React frontend = jeden projekt. detect_language obecnie wybiera jeden. Brak per-task language.

5. **Test flakiness detection** — testy czasem przechodzą losowo. Brak retry-on-flaky.

6. **Contract verification between tasks** — task T-001 produces `POST /users`, task T-005 depends on nim. Czy T-005 rzeczywiście konsumuje ten kontrakt? Brak cross-task contract check.

7. **Human review gate** — orchestrate run czasem powinien się zatrzymać i czekać na manualny review (np. przed deploy). Obecnie: goes-to-end lub FAILED. Brak "Wait for human" task type.

8. **Budget per-objective** — zamiast globalnego budgetu org, per-objective ("ten goal = max $5"). Precyzyjniejsze enforcement.

9. **Integration tests cross-service** — testy E2E dotykające kilku serwisów. Test runner obecnie uruchamia unit. Brak e2e lane.

10. **Performance benchmarks** — Forge mierzy functional success, nie perf. Brak KR typu "latency p95 < 200ms" z automatyczną miarą.

11. **Security audit gate** — Phase D (brak obecnie): Claude/Semgrep skanuje kod pod secrets/SQLi/XSS. Forge promuje "trust" — audit MUST.

12. **User roles beyond owner/editor/viewer** — brak "reviewer" (tylko approve/reject), "cost-approver" (mieć право zwiększyć budget), "auditor" (read-only + audit log access).

13. **Learning from past runs** — Forge ma `lessons.json`. Ale nie ma pipeline "after run, extract lessons automatically". Jest CLI `/compound`, brak UI.

14. **Multi-model ensemble** — Phase C używa Opus jako challenger. Można użyć 3 różnych modeli (Opus, Sonnet, Haiku) + voting. Brak.

15. **Visual diff for non-code artifacts** — task może produce markdown docs, config YAML, migrations. Diff view obecnie dobry dla code, słabszy dla YAML/MD.

**Podsumowanie Sekcji 5:** 15 obszarów nie-rozważonych. Kluczowe dla trustworthiness: Human review gate (7), Security audit (11), Rollback (2), Cost preview (1).

---

# SEKCJA 6 — Audyt Interaktywności (real-time UI)

8 mechanizmów, 14 wymiarów każdy.

## Wymiary interaktywności (dla każdego mechanizmu):
1. Co komunikuje user → system
2. Co komunikuje system → user
3. Latency (ms)
4. Real-time? (WS / poll / static)
5. Feedback widoczny?
6. Cancellable?
7. Rollback-able?
8. Progress indicator?
9. Error handling?
10. Keyboard shortcut?
11. Accessibility (screen reader)?
12. Mobile responsive?
13. Undo?
14. Debounce/throttle?

## 6.1 Poll orchestrate-run status (`/api/v1/orchestrate-runs/{id}` co 3s)

1. GET request polling co 3s.
2. JSON z status, current_task, elapsed, cost.
3. ~50-200ms request latency + 3000ms interval = 1.5-3.2s efektywny.
4. Poll (not real-time).
5. Widoczny (UI odświeża).
6. No (request nie-cancellable).
7. No.
8. Tak (phase label, elapsed counter).
9. Minimal — jeśli 404 → "Run not found".
10. No.
11. No (cały panel nie ma ARIA labels).
12. No.
13. No.
14. 3s interval (throttle).
**Ocena:** wystarczający dla pilotu, ale 3s poll → user czuje "lag". WebSocket byłby lepszy. Dodać SSE = niski koszt.

## 6.2 Form submit (create project, add guideline, create task)

1. POST form (HTMX hx-post).
2. HTML fragment lub redirect 303.
3. ~100-300ms (DB insert).
4. Real-time response (no poll).
5. Tak (row dodany inline).
6. No.
7. No (trzeba delete).
8. No progress (fast).
9. HTMX pokazuje error toast.
10. Enter submit.
11. Częściowo (labels OK, errors bez ARIA).
12. No.
13. No.
14. Debounce na input? Nie. (OK, submit jednorazowy).
**Ocena:** OK dla podstawowych mutacji. Brak undo.

## 6.3 Inline edit (task title, objective desc, KR current)

1. Click → inline input → Enter / click-out commit.
2. Same row odświeżona.
3. ~100-200ms.
4. Real-time (HTMX PATCH + swap).
5. Tak.
6. Tak (Escape anuluje).
7. No (brak history).
8. No.
9. Error toast.
10. Enter commit, Escape cancel.
11. Częściowo.
12. No.
13. No.
14. Debounce 300ms na każdy keystroke? Nie. (OK — submit na Enter).
**Ocena:** dobry, brakuje history (kto co edytował).

## 6.4 Claude CLI subprocess (analyze, plan, execute)

1. Internal backend call (user nie wie że subprocess).
2. Result po 30-120s.
3. ~30-120 sekund.
4. Blocking (async w backend, user widzi "loading").
5. Częściowo — podczas orchestrate jest Phase label, podczas analyze — cisza.
6. Obecnie NIE (no SIGTERM do subprocess).
7. No.
8. Podczas orchestrate TAK (phase). Podczas /analyze NIE.
9. Jeśli timeout → error; jeśli Claude zwraca invalid JSON → fallback.
10. No.
11. No.
12. No.
13. No.
14. n/a.
**Ocena:** główna słabość — **30-120s cisza** podczas /analyze i /plan. MUST: spinner z phase ("Extracting facts... Analyzing objectives... Measuring KR...").

## 6.5 File upload (ingest SOW)

1. POST multipart/form-data z files.
2. Server response "X files registered".
3. ~500ms-2s (zależne od size).
4. Real-time response.
5. Tak (toast).
6. No.
7. Tak (unregister document).
8. Brak progress bar (jeśli plik duży).
9. Error toast (file too large).
10. No.
11. No.
12. No.
13. No.
14. n/a.
**Ocena:** brak progress bar dla dużych SOW (10MB PDF). Dodać.

## 6.6 Share link generation

1. POST /share-links.
2. URL w toast.
3. ~100ms.
4. Real-time.
5. Tak.
6. No.
7. Tak (revoke endpoint).
8. No.
9. Error toast.
10. No.
11. No.
12. No.
13. No.
14. n/a.
**Ocena:** OK ale user traci URL po zamknięciu toast. Dodać "Share links" list.

## 6.7 Signup / Login

1. POST /ui/signup, /ui/login.
2. Cookie set + redirect.
3. ~150-300ms (bcrypt hash slow by design).
4. Real-time.
5. Tak.
6. No.
7. No (user musi delete account).
8. No.
9. Error inline ("Email exists").
10. Tab between fields, Enter submit.
11. Labels OK.
12. No.
13. No.
14. n/a.
**Ocena:** OK. Brakuje forgot password.

## 6.8 HTMX swap (inline fragments — delete, add, edit)

1. HTTP request z hx-* headers.
2. Server zwraca HTML fragment.
3. ~100-200ms.
4. Real-time.
5. Tak.
6. Częściowo (hx-trigger).
7. No.
8. hx-indicator spinner (jeśli dodany — nie zawsze).
9. hx-target="#errors" (jeśli dodany).
10. No.
11. No.
12. No.
13. No.
14. hx-trigger="input changed delay:500ms" (jeśli dodany).
**Ocena:** HTMX jest bardzo dobry dla Forge. Brakuje: debounce na input changes, hx-indicator loading states wszędzie.

**Podsumowanie Sekcji 6:** 8 mechanizmów. Najsłabsze: Claude CLI subprocess (30-120s cisza podczas /analyze) i Poll 3s (WS byłby lepszy). Progress bars, undo, cancellation, keyboard shortcuts — brak systemowo.

---

# SEKCJA 7 — Kompletność Funkcjonalna (264 punkty oceny)

24 features × 11 testów per feature = 264 ocen. Legenda: ✓ = spełnione, ◐ = częściowo, ✗ = brak.

## Testy:
1. Happy path działa
2. Edge cases (pusta dane, 0 tasks, duże objects) obsłużone
3. Rollback/undo
4. Feedback (toast / inline msg)
5. Error handling
6. Cross-user concurrency (2 userów edytuje razem)
7. Audit trail
8. Search/filter
9. Sort
10. Export (MD/PDF/CSV)
11. Notifications

| # | Feature | 1 HP | 2 EC | 3 Und | 4 Fb | 5 Err | 6 CC | 7 Aud | 8 Sr | 9 Sort | 10 Ex | 11 Nt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Signup | ✓ | ◐ | ✗ | ✓ | ✓ | ◐ | ✗ | n/a | n/a | n/a | ✗ |
| 2 | Login | ✓ | ◐ | ✗ | ✓ | ✓ | ✓ | ✗ | n/a | n/a | n/a | ✗ |
| 3 | Create project | ✓ | ✓ | ✗ | ✓ | ✓ | ◐ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 4 | Ingest SOW | ✓ | ◐ | ✓ | ✓ | ◐ | n/a | ✗ | ✗ | ✗ | ✗ | ✗ |
| 5 | Analyze | ✓ | ◐ | ✗ | ◐ | ◐ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 6 | Create objective | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 7 | Edit objective | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | n/a | n/a | n/a | ✗ |
| 8 | Delete objective | ✓ | ◐ | ✗ | ✓ | ✓ | ✗ | ✗ | n/a | n/a | n/a | ✗ |
| 9 | Create KR | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 10 | Plan (draft) | ✓ | ◐ | ✗ | ◐ | ◐ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| 11 | Approve plan | ✓ | ◐ | ✗ | ✓ | ✓ | ✗ | ◐ | n/a | n/a | ✗ | ✗ |
| 12 | Create task | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 13 | Edit task | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | n/a | n/a | n/a | ✗ |
| 14 | Orchestrate start | ✓ | ◐ | ✗ | ✓ | ✓ | n/a | ◐ | n/a | n/a | ✗ | ✗ |
| 15 | Orchestrate live panel | ✓ | ✓ | n/a | ✓ | ◐ | n/a | ◐ | n/a | n/a | ✗ | ✗ |
| 16 | Task retry | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 17 | Finding triage | ✓ | ✓ | ◐ | ✓ | ✓ | ✗ | ◐ | ✗ | ✗ | ✗ | ✗ |
| 18 | Decision resolve | ✓ | ✓ | ◐ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| 19 | Guideline CRUD | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 20 | Comment post | ✓ | ✓ | ✗ | ✓ | ✓ | ◐ | ✓ | ✗ | ✗ | ✗ | ✗ |
| 21 | Share link | ✓ | ✓ | ✓ | ✓ | ✓ | n/a | ◐ | ✗ | ✗ | ✗ | ✗ |
| 22 | Org settings | ✓ | ✓ | ◐ | ✓ | ✓ | ✗ | ✗ | n/a | n/a | ✗ | ✗ |
| 23 | Invite member | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ◐ | n/a | n/a | n/a | ✗ |
| 24 | Logout | ✓ | ✓ | n/a | ✓ | ✓ | n/a | ✗ | n/a | n/a | n/a | n/a |

**Score:**
- ✓ (pełne): ~95 / 264 (36%)
- ◐ (częściowe): ~30 / 264 (11%)
- ✗ (brak): ~105 / 264 (40%)
- n/a: ~34 / 264 (13%)

**Największe dziury:**
- **Notifications (kolumna 11)**: 23/24 puste — cała platforma bez notyfikacji.
- **Audit trail (kolumna 7)**: 18/24 puste — brakuje event log.
- **Export (kolumna 10)**: 22/24 puste — brakuje PDF/MD/CSV exportów.
- **Sort/Search (kolumny 8,9)**: ~20/24 puste.
- **Task retry (wiersz 16)**: 11/11 pusty — całkowity brak feature.
- **Concurrency (kolumna 6)**: 15/24 złe lub puste — teamowa praca niesprawdzona.

**Podsumowanie Sekcji 7:** 36% features kompletnych, 40% z krytycznymi brakami. Najgorsze obszary: notifications, audit, export, retry.

---

# SEKCJA 8 — Symulacja 5 person E2E

Każda persona: 20-30 kroków z inner-dialogue + effort rating (1-5).

## 8.1 Jakub — Tech Lead pilotujący Forge (nowy klient)

**Cel:** uruchomić Forge dla 1 klienta, pokazać value w 2h.

1. [effort 2] Otwiera `http://localhost:8059` → `/ui/login`. Myśli: "OK, login. Account jest stworzone?"
2. [3] Signup form. Wpisuje email, password, org_slug. Myśli: "Org_slug? Co to dokładnie? Nie jestem pewny czy to wpływa na URL potem."
3. [1] Signup OK, redirect → `/ui/projects`. Pusta lista. Myśli: "OK, new project."
4. [2] Klik "New Project". Form: slug, name, goal. Wpisuje "webapp-pilot", "Webapp for TestClient", "Build a CRUD app". Myśli: "goal = co? czy to SOW? to hotfix, jakaś pierwsza linijka?"
5. [1] Project created. Landing page projektu. Myśli: "4 buttony. Co ja robię dalej?"
6. [4] **Zawieszenie na 45 sekund.** Myśli: "Ingest? Co to ingest?". Sprawdza dokumentację (gdzie jest? — nie ma linku w UI).
7. [3] Klik "Ingest". Form upload. Wrzuca SOW.pdf. "SOW registered".
8. [2] Klik "Analyze". Loading 45s. Myśli: "jest dobrze? coś się dzieje? może po prostu nic nie zrobił."
9. [1] Toast "2 objectives created". Przechodzi do tab "Objectives".
10. [3] 2 karty objectives. KR na każdej. Myśli: "OK tylko... co dalej? Jak plan? Button plan jest gdzie?"
11. [3] Klika top-bar "Plan". Form wybór objective. Wybiera O-001.
12. [2] "7 tasks created". Tab "Tasks". Myśli: "To wszystko? Teraz Orchestrate?"
13. [2] Top-bar "Orchestrate". Dialog: max_tasks, budget. Zostawia defaults. Start.
14. [1] Panel live. "T-001 — Phase B".
15. [4] Czeka 90s. Myśli: "Co się dzieje? Claude pisze? Czy skończy?"
16. [1] T-001 DONE, 3/3 tests. T-002 start.
17. [2] T-002 FAILED (1/3 tests). Myśli: "OK, co zrobić? Retry? Gdzie jest retry?"
18. [5] **Zawieszenie — 3 minut.** Szuka "Retry" w UI. Nie ma. Googluje dokumentację. Brak. Musi użyć CLI.
19. [4] Decyduje: skip this task. Manualnie. Wraca do UI — status nie odświeżony.
20. [3] T-003 leci... wolniej niż się spodziewa. Wraca do pracy nad czymś innym.
21. [2] Po 25 min run DONE (5/7 tasks DONE, 2 FAILED).
22. [4] Idzie po raport. Gdzie? Brak "Run report" button. Musi open każdego taska osobno.
23. [3] Kopiuje wyniki ręcznie do Notion.

**Total effort: 58.** Meta-obserwacja: **2 long-pauses (kroki 6, 18).** Obie dotyczą **retry + dokumentacja in-context**. Jakub nie wie, jak Forge myśli.

**Wniosek z persony:** Pipeline stepper (Krok 3.1), Retry button (Krok 3.8), Run report (Krok 3.7) — MUST.

## 8.2 Anna — Delivery Manager (coordinates 4 pilotów)

**Cel:** zobaczyć status 4 projektów na jednym ekranie.

1. [1] Login.
2. [2] `/ui/projects` — 4 kafelki (bez statystyk). Myśli: "Który pali się?"
3. [5] Klika każdy projekt osobno żeby zobaczyć progress. **15 minut na 4 projekty.**
4. [3] Chce powiedzieć klientowi C: "4/5 tasków DONE, $3 z $10 budget". Musi to wyliczyć ręcznie.
5. [4] Slack: "Jakub, co zrobisz z T-005 FAILED?" — nie dostaje odpowiedzi, brak notifications.
6. [3] W piątek 17:00 chce wysłać klientowi "weekly report". Generuje ręcznie (brak export).
7. [2] W Forge logowała się 3 razy dziennie, nic nowego nie widziała → przestała.

**Total effort: 20.** **Główny ból:** brak zbiorczego dashboard + brak notifications.

**Wniosek:** Multi-project dashboard widget (Sekcja 2.2), Notifications, Weekly report auto.

## 8.3 Maria — CFO (kontrolująca budget)

**Cel:** zrozumieć ile wydaje na Forge miesięcznie, jak to śledzić.

1. [2] Dostaje od Jakuba: "zaloguj się, zobacz Org Settings".
2. [1] Login.
3. [3] Nawigacja: Org Settings. Widzi: budget $1000, used $357.
4. [4] Myśli: "Ale za co? Jakie projekty zżerają najwięcej?" Brak breakdown.
5. [4] Wchodzi w projekty, patrzy orchestrate runs. Ręcznie sumuje koszty.
6. [5] Excel. 1.5h. Frustracja.
7. [3] Pyta Jakuba: "czy jest jakiś report? CSV?". Jakub: "nie, trzeba prosić developera."
8. [3] Maria decyduje: "cap budgetu na $500" — nie ma way ograniczyć per-projekt.

**Total effort: 25.** **Główny ból:** brak **financial dashboard + cost breakdown + CSV export**.

**Wniosek:** Cost dashboard (per project / per objective / per day), CSV/PDF export, budget per-objective.

## 8.4 Piotr — Client PMO (patrzy na shared link deliverable)

**Cel:** zobaczyć progress Forge bez konta.

1. [1] Klik link od Jakuba — share link do projektu.
2. [2] Widzi: nazwa, goal, tasks DONE 5/7. Myśli: "OK, ale co ma być zrobione, co jeszcze nie?"
3. [4] Klika T-001 DONE — widzi kod. Myśli: "Ja nie czytam kodu, ja chcę status biznesowy."
4. [5] Wraca do klient-managera: "Forge mi pokazał kod zamiast progress biznesowego." **NEGATIVE PERCEPTION.**
5. [4] Zamyka kartę.

**Total effort: 16.** **Główny ból:** share link pokazuje **technical view** zamiast **business view**.

**Wniosek:** Share link → business-level report (objectives status, KR met, timeline). Hide kod, findings detailed. Separate business view vs technical view.

## 8.5 Marek — DevOps (wdrażanie Forge na internal infra)

**Cel:** wdrożyć Forge, skonfigurować RBAC, backup.

1. [3] Clone repo, docker-compose up. OK.
2. [2] Login admin.
3. [4] Szuka RBAC advanced. Znajduje: owner/editor/viewer. Myśli: "brak custom roles, trudniej nadać dostep audytorowi."
4. [5] Chce enable audit log — szuka w settings, brak. Musi patrzeć w DB.
5. [5] Backup procedure — brak dokumentacji.
6. [4] Monitoring — brak Prometheus metrics, brak healthcheck beyond /health.
7. [3] Szybko decyduje: "pilot OK, prod dalej."

**Total effort: 26.** **Główny ból:** **observability + enterprise features** brak.

**Wniosek:** Prometheus /metrics, structured logs, custom roles, audit log UI, backup CLI.

**Meta-analiza 5 person:**
- **3 z 5** zatrzymały się przy braku "co dalej?" (pipeline stepper, retry, run report).
- **2 z 5** chciały zbiorczego widoku financial/status (dashboard multi-project, cost breakdown).
- **1 z 5** chciał business-level deliverable (share link business view).
- **1 z 5** chciał enterprise observability.

**Top 5 akcji z person:** Pipeline stepper, Retry button, Run report auto-generate, Multi-project dashboard, Cost breakdown + CSV export.

---

# SEKCJA 9 — Zasady UI dla Forge (10 cech)

Każda cecha: guideline + dobry przykład w obecnym kodzie + anti-pattern (do usunięcia).

## 9.1 Stan procesu zawsze widoczny

- **Guideline:** każda strona pokazuje "gdzie user jest w pipeline" (Ingest → Analyze → Plan → Run → Done).
- **Dobry przykład:** `orchestrate_run.html` — pokazuje phase, current task.
- **Anti-pattern:** `project.html` — top bar z 4 buttonami bez kontekstu.
- **Implementacja:** `templates/_pipeline_stepper.html` (nowy) — vertical stepper z `step.status`.

## 9.2 Dane > narracja, ale narracja > tabela

- **Guideline:** liczby najpierw (3/3 tests passed), potem human-readable summary ("All tests pass. Endpoint live."), na końcu raw data (logi, JSON).
- **Dobry przykład:** finding card — title + description.
- **Anti-pattern:** task result panel — 4 sekcje raw bez summary.
- **Implementacja:** "Deliverable summary card" — top of task result.

## 9.3 Akcja zawsze blisko obiektu

- **Guideline:** button "Plan" przy objective, button "Retry" przy task, button "Triage" przy finding. **NIE** w top-bar globalnie.
- **Dobry przykład:** task row → "Begin" inline.
- **Anti-pattern:** "Analyze", "Plan", "Orchestrate" buttony w top bar (oderwane od obiektu).
- **Implementacja:** każda karta/row ma swoje akcje inline; top-bar = nawigacja, nie akcje.

## 9.4 Niedostępne akcje są niedostępne

- **Guideline:** button disabled (greyed) z tooltipem "Why disabled" zamiast zawsze klikalnego "Plan" który zwraca error.
- **Dobry przykład:** żaden (anti-pattern wszędzie).
- **Anti-pattern:** klik "Plan" gdy 0 objectives → error toast.
- **Implementacja:** stepper `step.status: empty/done/current/blocked` + button visible only on `current`.

## 9.5 Każda zmiana ma feedback w 200ms

- **Guideline:** click → spinner / toast / inline change w max 200ms (subjective "instant"). Long ops (> 500ms) — explicit progress bar.
- **Dobry przykład:** HTMX inline edits (~150ms).
- **Anti-pattern:** /analyze 45-90s without spinner (cisza).
- **Implementacja:** dla LLM ops → faza spinnera z message ("Extracting facts... Analyzing objectives... Generating plan...").

## 9.6 Reversibility wszędzie gdzie to możliwe

- **Guideline:** delete → soft-delete + 30s undo toast. Edit → "Last edit (revert)". Run → cancel mid-run.
- **Dobry przykład:** żaden (brak undo systemowo).
- **Anti-pattern:** delete cascade bez confirmation z counter.
- **Implementacja:** `audit_log` z `before/after` JSON + "undo" endpoint.

## 9.7 Spójność słownictwa

- **Guideline:** "Objective" w UI i CLI i DB. Nie "Goal" w UI a "Objective" w CLI. Nie "Task" w UI a "Step" w CLI.
- **Dobry przykład:** mostly OK.
- **Anti-pattern:** "goal" jako pole w project (project.goal), "Objective" jako entity. **Mylące.**
- **Implementacja:** rename `Project.goal` → `Project.short_description`. "Goal" zarezerwowane dla "Objective".

## 9.8 Empty states aktywne

- **Guideline:** "No tasks yet. Plan first → click here" zamiast pustej listy.
- **Dobry przykład:** żaden.
- **Anti-pattern:** pusta lista tasków bez instrukcji.
- **Implementacja:** każdy `_*_list.html` ma fallback z CTA.

## 9.9 Audit + observability domyślnie

- **Guideline:** każda akcja zapisana w event log (kto, kiedy, co, before/after). User widzi audit per resource.
- **Dobry przykład:** orchestrate_run.events JSON.
- **Anti-pattern:** edit objective name — brak record kto/kiedy.
- **Implementacja:** `audit_log` table + middleware automated.

## 9.10 Performance widoczna (cost + time)

- **Guideline:** każda LLM-driven akcja pokazuje estimated cost + actual cost po. Każdy task pokazuje duration.
- **Dobry przykład:** orchestrate_run pokazuje total_cost.
- **Anti-pattern:** /analyze nie ma cost preview.
- **Implementacja:** estimated_cost field na każdy LLM action; banner "this will cost ~$0.15".

**Podsumowanie Sekcji 9:** 10 cech. Forge obecnie spełnia ~3/10 dobrze (HTMX inline, orchestrate live, finding card narration). Pozostałe — luki systemowe.

---

# SEKCJA 10 — Rekomendacje powiązane z kodem

Każda rekomendacja: plik / linia / zmiana / przykład.

## 10.1 Pipeline stepper komponent

- **Plik nowy:** `platform/app/templates/_pipeline_stepper.html`
- **Logika:** `platform/app/services/pipeline_state.py` (nowy) — funkcja `get_pipeline_state(project) → {ingest:done|empty, analyze:done|empty|blocked, plan:done|empty|blocked, run:none|in_progress|done}`.
- **Integracja:** `templates/project.html` — render `<{% include "_pipeline_stepper.html" %}>` na top.
- **Backend:** `platform/app/api/ui.py:project_view` — pobierz state.

## 10.2 Retry task

- **Endpoint nowy:** `POST /api/v1/projects/{slug}/tasks/{external_id}/retry` w `platform/app/api/pipeline.py`.
- **Logika:** reset task.status='READY', remove last_attempt result, re-execute via existing executor.
- **UI:** w `_task_row.html` po DONE/FAILED → button "Retry".
- **Test:** `tests/test_task_retry.py`.

## 10.3 Run report (markdown export)

- **Generator:** `platform/app/services/run_report.py` (nowy) — funkcja `generate_run_report(orchestrate_run_id) → str (markdown)`.
- **Endpoint:** `GET /api/v1/orchestrate-runs/{id}/report?format=md|pdf`.
- **UI:** w `orchestrate_run.html` po DONE → button "Download report".
- **PDF:** WeasyPrint `from weasyprint import HTML; HTML(string=md_to_html).write_pdf()`.

## 10.4 Decisions resolve modal

- **Template:** `_decision_resolve_modal.html` — radio: "Option A / Option B / Custom resolution".
- **Trigger:** po `/analyze` jeśli `decisions.OPEN > 0` → modal pop.
- **Endpoint:** `POST /decisions/{id}/resolve` istnieje (?). Sprawdzić; dodać jeśli brak.

## 10.5 Cost preview

- **Service:** `platform/app/services/cost_estimator.py` (nowy) — funkcja `estimate(action_type, context_size) → {min_usd, max_usd}`.
- **UI:** przed klick "Analyze" / "Plan" / "Orchestrate" → tooltip / inline "Estimated: $0.15 ± 50%".

## 10.6 Multi-project dashboard

- **Template:** zmodyfikować `projects_list.html` na grid kafelków zamiast tabeli.
- **Service:** `services/project_summary.py` — `get_summary(project) → {tasks_done, tasks_total, kr_met, kr_total, cost_used, cost_budget, last_activity}`.
- **Endpoint:** `GET /api/v1/projects?summary=true` z włączonym aggregation.

## 10.7 Audit log

- **Model:** `platform/app/models/audit_log.py` — `id, org_id, user_id, action, resource_type, resource_id, before_json, after_json, created_at`.
- **Middleware:** `audit_mw.py` — rejestruje wszystkie POST/PATCH/DELETE.
- **UI:** Settings → "Audit Log" tab z filter (action, user, date).

## 10.8 Notifications

- **Model:** `notification.py` — `user_id, type, payload, read_at, created_at`.
- **Service:** `notification_service.py` — `send(user, event)` → DB + email (jeśli SMTP configured).
- **Trigger:** comment @mention, task FAILED, run DONE, budget 80%.
- **UI:** navbar bell icon z dropdown.

## 10.9 Console tail (live logs)

- **Backend:** stream stdout subprocess Claude do orchestrate_run.events_log (append).
- **Endpoint:** `GET /orchestrate-runs/{id}/logs?since=offset` (paginated tail).
- **UI:** `orchestrate_run.html` accordion "Console output" — JS poll co 2s.

## 10.10 Empty states

- **Wszystkie list templates** (`_objectives_list.html` etc.) → dodać `{% if not items %} <div class="empty-state">...</div> {% endif %}`.
- **Komponent:** `_empty_state.html` z parametrami: `icon`, `title`, `description`, `cta_text`, `cta_href`.

**Podsumowanie Sekcji 10:** 10 konkretnych zmian z plikami i logiką. Każda możliwa do implementacji w 1-3h pracy.

---

# SEKCJA 11 — 50 obietnic dla użytkownika (5 kategorii × 10)

Każda obietnica: tekst, **dlaczego user tego potrzebuje**, **jak Forge dostarcza**, **self-challenge** (czy ta obietnica jest naprawdę dobra?). MUST oznaczone na końcu kategorii.

## 11.A Modyfikowalność (10 obietnic)

### A1. "Edytujesz każdy task w 2 kliknięciach"
- **Why:** plan rzadko jest perfekcyjny — user musi poprawiać.
- **How:** task row → expand → inline edit (HTMX) na fields name/description/instruction.
- **Challenge:** "edycja może łamać dependencies". Mitigate: validate przed save.
- **MUST:** TAK.

### A2. "Możesz dodać task ad-hoc bez full re-plan"
- **Why:** mid-flight discovery — user widzi missing task, dodaje ręcznie.
- **How:** "Add task" button na liście; form z auto-suggest depends_on.
- **Challenge:** "task ad-hoc bez objective traceability". Mitigate: wymagaj wyboru objective lub mark "outside-objective".
- **MUST:** TAK.

### A3. "Możesz edytować objective i KR po /analyze"
- **Why:** Claude czasem żle interpretuje SOW; user korekta.
- **How:** inline edit w Objectives tab.
- **Challenge:** "edycja po planie → tasks już oparte na starym objective". Mitigate: warning "edit will not re-plan; use Re-plan button".
- **MUST:** TAK.

### A4. "Re-plan objective bez tracenia historii"
- **Why:** SOW się zmienił, plan trzeba przebudować.
- **How:** button "Re-plan" → tworzy plan_v2; old plan zachowany jako archived.
- **Challenge:** "history bloat". Mitigate: limit do 5 versions, auto-prune.
- **MUST:** TAK.

### A5. "Edytujesz instructions taska przed retry"
- **Why:** task FAILED z powodu niejasnej instrukcji; user precyzuje.
- **How:** retry button → dialog z editable instruction.
- **Challenge:** "edit instruction = inny task semantycznie". Mitigate: log diff before-after instruction w audit.
- **MUST:** TAK.

### A6. "Edytujesz AC po DONE i re-evaluate"
- **Why:** AC były błędne; re-check.
- **How:** AC inline edit + button "Re-verify".
- **Challenge:** "re-evaluate ≠ re-execute". Clarify w UI: "this checks AC against existing code, doesn't re-run task".
- **MUST:** średnio.

### A7. "Skipujesz task z reason"
- **Why:** task przestał być potrzebny mid-execution.
- **How:** button "Skip" + textarea reason (min 50 chars).
- **Challenge:** "skip rozbija graph". Mitigate: tylko leaf tasks; non-leaf wymagają cascade-skip.
- **MUST:** TAK.

### A8. "Override budgetu mid-run"
- **Why:** run zatrzymany BUDGET_EXCEEDED; user zatwierdza więcej.
- **How:** dialog "Increase budget by $X and resume".
- **Challenge:** "user może puścić $1000 przez pomyłkę". Mitigate: 2-step confirm + cap per single increase ($50 default).
- **MUST:** TAK.

### A9. "Override gate failure z `--force`"
- **Why:** gate fałszywy alarm (np. test flaky).
- **How:** complete --force --reason w UI (button "Force complete" z modalem).
- **Challenge:** "user nadużyje force". Mitigate: audit log "X used force", monthly report.
- **MUST:** TAK (z audit).

### A10. "Replace Claude model per-task"
- **Why:** niektóre tasks lepiej Opus (planning), niektóre Sonnet (code).
- **How:** dropdown model w task config przed Begin.
- **Challenge:** "user nie wie który model wybrać". Mitigate: defaults inteligentne.
- **MUST:** średnio.

**TOP 3 MUST kategorii A:** A1 (edit task), A4 (re-plan), A8 (budget override).

## 11.B Spójność (10)

### B1. "Słownictwo jednolite (Objective/Task/KR/Finding)"
- **Why:** różne nazwy = mental load.
- **How:** glossary + linter na templates.
- **Challenge:** "rename Project.goal → short_description = breaking change". Mitigate: alias backward compat.
- **MUST:** TAK.

### B2. "Akcje są tam gdzie obiekt"
- **Why:** user szuka "co mogę z tym zrobić" — akcja inline.
- **How:** redesign — żadnych globalnych akcji.
- **Challenge:** "duplikacja kodu ('Edit' button na każdej karcie)". OK — komponent.
- **MUST:** TAK.

### B3. "Stan widoczny w 3 miejscach (badge, color, text)"
- **Why:** scan vs read.
- **How:** każdy entity ma `status_label`, `status_color`, `status_text`.
- **Challenge:** "kolor accessibility". Mitigate: tekst zawsze, kolor dodatkowy.
- **MUST:** TAK.

### B4. "Tych samych akcji = ten sam ikon + ten sam skrót"
- **Why:** muscle memory.
- **How:** design system z ikonami (✏ edit, 🗑 delete, ▶ run, ↻ retry).
- **Challenge:** ikon emoji w różnych OS różnie wygląda. Mitigate: HeroIcons lub custom SVG.
- **MUST:** średnio.

### B5. "Forms mają tę samą strukturę (label / input / hint / error)"
- **Why:** prediktabilność.
- **How:** komponent `_form_field.html`.
- **Challenge:** brak.
- **MUST:** TAK.

### B6. "Confirmation dialogs identyczne (title / body / [Cancel] [Confirm])"
- **Why:** brak surprise.
- **How:** komponent `_confirm_modal.html`.
- **Challenge:** dla destructive — wymaga type-to-confirm.
- **MUST:** TAK.

### B7. "Toasts: success green, error red, info blue, warning yellow"
- **Why:** color = meaning.
- **How:** uniform toast system.
- **Challenge:** accessibility — text icon + label.
- **MUST:** TAK.

### B8. "Tab order zawsze: lewo do prawo, gora do dolu"
- **Why:** keyboard nav.
- **How:** review tabindex w templates.
- **Challenge:** brak.
- **MUST:** TAK.

### B9. "Linki = niebieski + underline; buttons = solid bg"
- **Why:** affordance distinction.
- **How:** Tailwind utility classes consistent.
- **Challenge:** "design system ograniczenie". OK.
- **MUST:** TAK.

### B10. "Dates zawsze ISO + relative ('2026-04-17, 2 hours ago')"
- **Why:** ambig date format.
- **How:** komponent `_date.html`.
- **Challenge:** timezone confusion. Mitigate: zawsze UTC display + "your time" tooltip.
- **MUST:** średnio.

**TOP 3 MUST B:** B1 (vocabulary), B2 (akcje przy obiekcie), B3 (status widoczny 3 sposoby).

## 11.C Jakość (10)

### C1. "Phase A test runner mierzy real wyniki, nie self-claims Claude'a"
- **Why:** trust.
- **How:** test_runner.py uruchamia pytest/jest, zwraca real counts.
- **Challenge:** "test runner failure ≠ task failure (env problems)". Mitigate: distinguish env_error vs assertion_failure.
- **MUST:** TAK (już zrobione).

### C2. "Phase B Claude extracts decisions+findings post-execute"
- **Why:** capture insights.
- **How:** delivery_extractor.py.
- **Challenge:** koszt drugi LLM call. Mitigate: konfigurable on/off.
- **MUST:** TAK.

### C3. "Phase C cross-model challenge (Opus vs Sonnet)"
- **Why:** verification beyond self-validation.
- **How:** challenger.py uruchamia Opus z task.result, request "verdict".
- **Challenge:** "Opus i Sonnet często zgadzają (rodzina) — rare divergence". Mitigate: dodać external model (np. GPT-4 via API) jako 3rd opinion.
- **MUST:** średnio.

### C4. "git verify: diff jest realny, nie blank commit"
- **Why:** trust.
- **How:** git_verify.py — count files changed, total lines added/removed.
- **Challenge:** "duży diff ≠ dobry diff". OK — to mierzy aktywność, nie quality.
- **MUST:** TAK.

### C5. "KR auto-measure (numeric)"
- **Why:** progress tracking.
- **How:** kr_measurer.py — uruchamia measurement_cmd, parsuje wynik.
- **Challenge:** "cmd injection". Mitigate: sandboxed exec.
- **MUST:** TAK.

### C6. "Findings z severity + recommendation"
- **Why:** actionable.
- **How:** Phase B prompt enforce schema {severity, category, title, description, recommendation}.
- **Challenge:** "Claude generuje noise low-severity". Mitigate: filter + threshold.
- **MUST:** TAK.

### C7. "Coverage gate (knowledge → tasks → AC traceability)"
- **Why:** fidelity chain.
- **How:** core/pipeline.py validate_coverage.
- **Challenge:** "false negatives — synonym mismatch". Mitigate: semantic similarity check (embeddings).
- **MUST:** TAK.

### C8. "Audit log immutable"
- **Why:** compliance.
- **How:** model audit_log + insert-only constraint.
- **Challenge:** "delete user = orphan log". Mitigate: foreign key SET NULL.
- **MUST:** TAK.

### C9. "Cost cap per run"
- **Why:** prevent runaway.
- **How:** budget enforcement w orchestrator.
- **Challenge:** "cap przerwie ważny task". Mitigate: warning "run will stop at $X".
- **MUST:** TAK.

### C10. "Re-execute deterministic (same prompt → similar output)"
- **Why:** debugging.
- **How:** seed parameter w Claude (jeśli dostępne) + cache prompts.
- **Challenge:** "Claude nondeterministic". Mitigate: log prompts + raw responses for replay.
- **MUST:** średnio.

**TOP 3 MUST C:** C1 (real test runner), C2 (Phase B extract), C7 (coverage gate).

## 11.D Elastyczność (10)

### D1. "Skip /analyze dla simple plan (no SOW)"
- **Why:** small projects.
- **How:** /plan działa bez objectives (standalone mode).
- **Challenge:** "skip = brak traceability". Mitigate: warning.
- **MUST:** TAK.

### D2. "Multi-org per user"
- **Why:** consultancy patterns.
- **How:** memberships table z role.
- **Challenge:** "context switching confusing". Mitigate: org dropdown w navbar (clear current).
- **MUST:** TAK.

### D3. "Custom guidelines per project"
- **Why:** different clients = different rules.
- **How:** guidelines.json scoped per project.
- **Challenge:** "duplicate guidelines across projects". Mitigate: template library + import.
- **MUST:** TAK.

### D4. "Custom acceptance criteria per task"
- **Why:** varying needs.
- **How:** AC array per task; verification: test/command/manual.
- **Challenge:** "user lazy → manual everywhere → no real verification". Mitigate: warn "manual AC has no enforcement".
- **MUST:** TAK.

### D5. "Per-task model override"
- **Why:** cost vs quality tradeoff.
- **How:** task.model field.
- **Challenge:** "model not available". Mitigate: validate at save.
- **MUST:** średnio.

### D6. "Task type variation (feature/bug/chore/investigation)"
- **Why:** różne workflow.
- **How:** task.type enum + ceremony level auto-detect.
- **Challenge:** "user nie wie różnicy". Mitigate: inline help.
- **MUST:** TAK.

### D7. "Webhooks dla integracji (Jira / Slack / Linear)"
- **Why:** istniejące tooling.
- **How:** webhooks endpoints już dodane częściowo.
- **Challenge:** "webhook payload format zmienny". Mitigate: schema versioning.
- **MUST:** TAK.

### D8. "Export do MD / PDF / CSV / JSON"
- **Why:** różni odbiorcy.
- **How:** report_generator z format param.
- **Challenge:** "PDF ciężko do testować". Mitigate: snapshot tests.
- **MUST:** TAK.

### D9. "API + UI równoległe"
- **Why:** integracje + manual.
- **How:** /api/v1/* dla API, /ui/* dla UI; ten sam controller pod spodem.
- **Challenge:** "duplikacja routes". Mitigate: shared service layer.
- **MUST:** TAK.

### D10. "Browser-based or self-hosted"
- **Why:** enterprise on-prem.
- **How:** docker-compose deploy.
- **Challenge:** "on-prem ma upgrades problem". Mitigate: migration scripts.
- **MUST:** średnio.

**TOP 3 MUST D:** D2 (multi-org), D3 (custom guidelines), D7 (webhooks).

## 11.E Wsparcie (10)

### E1. "Inline help przy każdym fieldzie"
- **Why:** new user nie wie co wpisać.
- **How:** `?` icon → tooltip z explanation.
- **Challenge:** "tooltip noise dla power user". Mitigate: collapsible.
- **MUST:** TAK.

### E2. "Empty states z CTA + tutorial link"
- **Why:** unclear what to do.
- **How:** komponent `_empty_state.html`.
- **Challenge:** "empty states wzdrygnij user — czuje że jest błąd". Mitigate: friendly copy "no objectives yet — let Forge analyze your SOW".
- **MUST:** TAK.

### E3. "Error messages zawsze actionable"
- **Why:** "Error 500" useless.
- **How:** every exception caught → user-friendly + technical_details (collapsible) + suggested action.
- **Challenge:** "user-friendly messages dla każdego błędu — duża praca". Mitigate: top 20 errors mapped, rest generic.
- **MUST:** TAK.

### E4. "Sample project / demo on first login"
- **Why:** onboarding without SOW.
- **How:** auto-create "Sample Project" on signup.
- **Challenge:** "noise w listach projektów". Mitigate: clearly labeled "DEMO" + delete button.
- **MUST:** średnio.

### E5. "Search global (Ctrl+K)"
- **Why:** szybka nawigacja.
- **How:** dropdown search po nazwy projektów / tasków / objectives.
- **Challenge:** "search performance". Mitigate: indexed.
- **MUST:** TAK.

### E6. "Dokumentacja w kontekście (link do docs from each tab)"
- **Why:** user ma pytanie tu i teraz.
- **How:** każdy tab ma `?` link → `/docs/<slug>`.
- **Challenge:** "docs muszą być pisane". Yes — invest.
- **MUST:** TAK.

### E7. "Logs accessible per task"
- **Why:** debugging.
- **How:** task detail → "Logs" tab z stdout/stderr Claude.
- **Challenge:** "logs spam". Mitigate: filter level.
- **MUST:** TAK.

### E8. "Diff viewer side-by-side"
- **Why:** review code change.
- **How:** już jest częściowo — ulepszać.
- **Challenge:** "duże diffs slow". Mitigate: paginate.
- **MUST:** TAK.

### E9. "Activity feed per project"
- **Why:** "co się działo ostatnio?"
- **How:** audit_log filter per project, render w project page sidebar.
- **Challenge:** "feed spam". Mitigate: group by event type.
- **MUST:** TAK.

### E10. "Keyboard shortcuts (cheatsheet)"
- **Why:** power users.
- **How:** /? popup z list shortcuts.
- **Challenge:** "shortcuts conflicting w browser". Mitigate: only Ctrl+letter, not Cmd+letter.
- **MUST:** średnio.

**TOP 3 MUST E:** E1 (inline help), E2 (empty states CTA), E3 (actionable errors).

**Łączne MUST z kategorii (TOP 3 × 5 = 15):**
A1, A4, A8 — edit, re-plan, budget override.
B1, B2, B3 — vocabulary, action-near-object, status visible 3 ways.
C1, C2, C7 — real tests, Phase B extract, coverage gate.
D2, D3, D7 — multi-org, custom guidelines, webhooks.
E1, E2, E3 — inline help, empty states, actionable errors.

**Self-challenge na poziomie meta:**
- "50 obietnic = za dużo". Kontrargument: 15 MUST realistyczne na pilot. Reszta 35 = roadmap Phase 2-3.
- "Modyfikowalność vs Spójność = trade-off (mało rules = łatwo edyt; spójność wymaga reguł)". Yes — balansować w okresie.
- "Jakość = za dużo verification = wolno". Kontrargument: trust > speed. User pozwoli czekać 5min jeśli wynik wiarygodny.

---

# SEKCJA 12 — Plan działania (TOP 5 × 3 + sekwencja + mockupy)

## 12.A TOP 5 zmian UI (max wpływ)

1. **Pipeline stepper** zastępuje 4 buttony top-bar. Rozwiązuje Krok 0, 2, 3, 5, 9 z Sekcji 1 i Problem 3.1-3.3. (ROI najwyższy)
2. **Task result panel → Deliverable summary** (narrative card + accordions). Rozwiązuje Problem 3.7 i 2.15.
3. **Kafelki dashboard** z progress bars + statystyki. Rozwiązuje personę Anna (8.2) i Maria (8.3).
4. **Retry button + Run report** na task/run detail. Rozwiązuje Problem 3.6, 3.8, Jakub (8.1).
5. **Decisions resolve modal** po /analyze. Rozwiązuje Problem 3.15.

## 12.B TOP 5 nowych funkcji (backend + UI)

1. **Run report generator** (MD/PDF + download + share).
2. **Cost preview** przed /analyze, /plan, /orchestrate.
3. **Audit log** (table + UI tab + middleware).
4. **Notifications** (model + email + in-app bell).
5. **Task retry endpoint** + UI flow.

## 12.C TOP 5 nieciągłości (do zlikwidowania)

1. **Po ingest → prompt to analyze** (Problem 3.1).
2. **Po analyze → objective "Plan this" inline CTA** (3.2).
3. **Po task DONE → "View diff / Retry / Approve"** (3.6).
4. **FAILED → Retry UX** (3.8).
5. **Run DONE → Report** (3.7).

## 12.D Sekwencja implementacji (4 tygodnie)

**Tydzień 1 — Fundament UX:**
- Pipeline stepper komponent (dzień 1-2)
- Empty states wszędzie (dzień 2)
- Inline help (dzień 3)
- Vocabulary cleanup (Project.goal → short_description) (dzień 3)
- Dashboard kafelki (dzień 4-5)

**Tydzień 2 — Deliverable & Retry:**
- Deliverable summary card (dzień 1-2)
- Run report generator (MD) (dzień 2-3)
- Task retry endpoint + UI (dzień 3-4)
- FAILED task flow (dzień 4-5)

**Tydzień 3 — Verification & Notifications:**
- Cost preview (dzień 1)
- Decisions resolve modal (dzień 2)
- Audit log (dzień 3-4)
- Notifications (email + in-app) (dzień 4-5)

**Tydzień 4 — Polish & Flexibility:**
- Live console tail (dzień 1-2)
- Re-plan (versioned plans) (dzień 2-3)
- PDF export (WeasyPrint) (dzień 3)
- Search global Ctrl+K (dzień 4)
- QA + polishing (dzień 5)

## 12.E ASCII mockupy (6)

### Mockup 1 — Dashboard (list → kafelki)

```
┌────────────────────────────────────────────────────────────────┐
│ Forge   [Projects] [Org]              hergati@  ▼   [+ New]   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─ warehouseflow ─────┐  ┌─ appointmentbooking ─┐             │
│  │ Warehouse Ops       │  │ AppointmentBooking    │             │
│  │ 3/4 obj ACHIEVED    │  │ 1/3 obj ACHIEVED      │             │
│  │ 12/15 tasks DONE    │  │ 5/20 tasks DONE       │             │
│  │ ████████████░░ 80%  │  │ ██░░░░░░░░░░░░ 25%    │             │
│  │ $8.45 / $20         │  │ $12.00 / $15          │             │
│  │ active 2h ago       │  │ active 5m ago (▶)     │             │
│  └─────────────────────┘  └───────────────────────┘             │
│                                                                │
│  ┌─ todo-cli ──────────┐  ┌─ + New Project ──────┐              │
│  │ TodoCLI             │  │                      │              │
│  │ Pipeline: plan      │  │    (click to create) │              │
│  │ 2/7 tasks DONE      │  │                      │              │
│  └─────────────────────┘  └──────────────────────┘              │
└────────────────────────────────────────────────────────────────┘
```

### Mockup 2 — Project page z Pipeline Stepper

```
┌────────────────────────────────────────────────────────────────┐
│ Forge / warehouseflow                    [Settings] [Archive] │
├────────────────────────────────────────────────────────────────┤
│  Goal: Build warehouse ops system                             │
│                                                                │
│  ◉ 1. Upload SOW ........... ✓ DONE (3 documents)             │
│  │                                                             │
│  ◉ 2. Analyze .............. ✓ DONE (4 objectives, $0.07)     │
│  │                                                             │
│  ◉ 3. Plan .................. ✓ DONE (15 tasks, $0.12)        │
│  │                                                             │
│  ◉ 4. Orchestrate .......... ▶ RUNNING (T-009/15, phase B)    │
│      [View live panel →]                                       │
│                                                                │
│  [Tabs: Dashboard | Objectives | Tasks | Findings | Guidelines│
│   Decisions | Knowledge | Comments | Settings]                 │
└────────────────────────────────────────────────────────────────┘
```

### Mockup 3 — Objective card z inline CTA

```
┌────────────────────────────────────────────────────────────────┐
│  O-001 ▶ Build user authentication system      [Plan] [Edit] │
│  ├─ KR-1: POST /register returns 201 .............. ACHIEVED │
│  ├─ KR-2: JWT token in cookie ..................... ACHIEVED │
│  ├─ KR-3: Password hashed bcrypt .................. IN_PROG  │
│  ├─ 2 open decisions ............................. [Resolve] │
│  └─ 5 tasks | 3 DONE | 1 FAILED | 1 READY                    │
└────────────────────────────────────────────────────────────────┘
```

### Mockup 4 — Task result (deliverable summary)

```
┌────────────────────────────────────────────────────────────────┐
│ T-003  Implement POST /users endpoint          ✓ DONE in 86s │
├────────────────────────────────────────────────────────────────┤
│  📋 SUMMARY                                                    │
│  ✓ All 8 tests passed                                         │
│  ✓ Challenger (Opus) agrees with implementation              │
│  ⚠ 2 low-severity findings (review recommended)              │
│                                                                │
│  Cost: $0.36  |  Lines added: 124  |  Files: 3                │
│                                                                │
│  [View diff] [View logs] [Retry] [Approve]                    │
├────────────────────────────────────────────────────────────────┤
│  ▼ Acceptance criteria (3)                                    │
│  ▼ Tests output                                               │
│  ▼ Findings (2)                                               │
│  ▼ Challenger report                                          │
└────────────────────────────────────────────────────────────────┘
```

### Mockup 5 — Orchestrate live panel z console tail

```
┌────────────────────────────────────────────────────────────────┐
│  Orchestrate run #4                    [Pause] [Cancel] [×]  │
├────────────────────────────────────────────────────────────────┤
│  Current: T-009 "Add user profile edit"        elapsed: 4:23 │
│  Phase: B (extract decisions & findings)                      │
│                                                                │
│  Progress:  ▓▓▓▓▓▓▓▓░░░░░░░░░░░░  8/15 tasks DONE | 1 failed │
│  Cost used: $4.20 / $10.00  ───────────────────────────── 42%│
│                                                                │
│  ▼ Console output (tail 20 lines)                    [Copy]  │
│  $ pytest tests/users/ -v                                     │
│  ==================== 8 passed in 1.34s =====================│
│  Claude extracting findings...                                │
│  Found 2 potential issues: [low] missing index, [med] ...    │
│                                                                │
│  ▼ Recent tasks                                               │
│  ✓ T-008  Add user list           DONE   $0.45   1m42s       │
│  ✗ T-007  Migrate schema          FAILED $0.12   [Retry]     │
│  ✓ T-006  Create users table      DONE   $0.28   54s         │
└────────────────────────────────────────────────────────────────┘
```

### Mockup 6 — Decisions resolve modal (po /analyze)

```
┌────────────────────────────────────────────────────────────────┐
│  2 decisions need resolution before planning              [×] │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  D-001  Authentication method                                 │
│  SOW mentions both JWT and session cookies.                   │
│  Which to use?                                                │
│                                                                │
│   ( ) JWT in Authorization header                             │
│   (●) JWT in HttpOnly cookie + CSRF token                     │
│   ( ) Session cookie (Redis)                                  │
│   ( ) Other: [_____________________________________]          │
│                                                                │
│  D-002  Database                                              │
│  SOW doesn't specify DB engine.                               │
│                                                                │
│   (●) PostgreSQL (recommended — project default)              │
│   ( ) SQLite (prototype)                                      │
│   ( ) MySQL                                                    │
│                                                                │
│                          [Resolve later]  [Resolve and Plan →]│
└────────────────────────────────────────────────────────────────┘
```

**Podsumowanie Sekcji 12:** 4-tygodniowy plan. Tydzień 1 = największy ROI (pipeline stepper + kafelki + empty states). 6 mockupów pokazują docelowy vision.

---

# SEKCJA 13 — Open Questions (10+)

1. **Czy pipeline stepper ma być dominującym elementem (zajmuje 1/3 ekranu), czy tylko accent na top?** Rekomendacja: dominujący przy pierwszym entry, minify po setupie.

2. **Kto jest "ownerem" findingów — user projektu czy auditor?** Wpływa na triage flow. Rekomendacja: user + optional auditor.

3. **Czy re-plan usuwa old plan czy wersjonuje?** Wersjonowanie drożej (storage + query), ale audit. Rekomendacja: wersjonuj max 5.

4. **Czy kontrakt między tasks (T-001 produces → T-005 depends on) jest mechanicznie sprawdzany?** Obecnie: nie. Rekomendacja: dodać w Phase D (schema validation między produces i dependent task instructions).

5. **Jaka granica cost, przy której pytamy usera przed start?** $1? $5? $10? Rekomendacja: konfigurable, default $5.

6. **Multi-language projekt (backend Python + frontend TS) — jeden task hit oba czy split?** Rekomendacja: split — every task has single language.

7. **Co z SOW w innych językach (PL, DE)?** Claude radzi sobie, ale Forge messages po angielsku. Rekomendacja: i18n na Phase 3.

8. **Czy Phase C challenger ma być on-by-default?** Koszt +50%. Rekomendacja: konfigurable, default on dla production projektów, off dla prototyping.

9. **Czy user może wyłączyć audit log dla own org?** Compliance argumenty mieszane. Rekomendacja: nie — audit zawsze on.

10. **Czy trzeba budować mobile UI?** Pilot — desktop tylko. Rekomendacja: Phase 3 — read-only mobile dashboard.

11. **Jak traktować tasks DONE w projekcie 6 miesięcy temu — archive automatycznie?** Rekomendacja: manual archive + auto-suggest po 90d.

12. **Czy webhooks mają być per-org lub per-project?** Rekomendacja: per-project z org fallback.

13. **Czy cost preview jest shown w aggressive mode (pre-execute blokuje i czeka confirmation) czy passive (tooltip)?** Rekomendacja: pokazuj zawsze, blokuj gdy cost > $1 lub > 50% remaining budget.

14. **Czy user może exportować wszystko (cały projekt z historią) jako jednym zipem?** "Project backup". Rekomendacja: tak, Phase 2.

15. **Jak design system wygląda — czy Tailwind CDN wystarczy czy trzeba komponent library?** Rekomendacja: Tailwind + HTMX + custom komponenty Jinja. Unikać React (skomplikowałoby pipeline).

---

# PODSUMOWANIE DOKUMENTU

**Co zrobiłem:**
- 1 sekcja mapping workflow (17 kroków × 16 wymiarów).
- 1 sekcja audyt widgets (24 × 10 wymiarów).
- 1 sekcja nieciągłości (15 × 5 wymiarów).
- 1 sekcja braki (UI + Backend osobno, 21 pozycji).
- 1 sekcja czego nie rozważono (15).
- 1 sekcja interaktywność (8 × 14 wymiarów).
- 1 sekcja kompletność (264 ocen).
- 1 sekcja persony (5 × 20-30 kroków z inner-dialogue).
- 1 sekcja zasady UI (10 × 3 wymiary).
- 1 sekcja rekomendacji code (10 z plikami).
- 1 sekcja 50 obietnic (5 × 10 × 4 wymiary; 15 MUST).
- 1 sekcja plan (TOP 5 × 3 + sekwencja + 6 mockupów).
- 1 sekcja open questions (15).

**Top 3 rzeczy do zrobienia przed dalszym developmentem:**
1. Zastąp 4 buttony top-bar **Pipeline Stepper** (Tydzień 1).
2. Dodaj **Deliverable Summary + Retry + Run Report** (Tydzień 2).
3. Dodaj **Audit Log + Notifications + Cost Preview** (Tydzień 3).

**Top 3 fałszywe priorytety (które obecnie zabierają czas, ale mają low-ROI):**
1. Tab "AC" i "KR" jako osobne zakładki — USUŃ, są duplikaty.
2. Tab "Ideas" / "Discover" w podstawowym UI — ukryj (advanced mode).
3. Share link obecny format (kod pokazany klientom bez konta) — przekształć w business-view only.

**Top 3 rzeczy, które w ogóle nie istnieją, a są MUST:**
1. **Retry flow** (endpoint + UI + audit).
2. **Run Report** (MD + PDF + share link).
3. **Decisions Resolve Modal** po /analyze.

**Ocena obecnej platformy:**
- **Techniczne fundamenty:** solidne (Phase A test runner, Phase B findings, Phase C challenger, multi-tenant, budget).
- **UX:** poniżej progu użyteczności dla nowego usera (2+ long-pauses w typical flow).
- **Feature coverage:** ~36% pełne, 40% z krytycznymi brakami.

**Co byłoby po tych zmianach:**
- Pipeline clearly visible → user wie "gdzie jest".
- Retry/Run-Report → user kontroluje wynik.
- Dashboard kafelki → multi-project oversight.
- Cost preview + audit → trust.
- Empty states + inline help → onboarding.

**TL;DR:**
Forge ma dobry silnik (verification, multi-tenant, orchestrator). Brakuje **stan-widoczności, kontroli po-DONE, kontroli kosztu, i onboarding'u**. 4-tygodniowy plan kieruje te luki. Bez tego platforma działa technicznie, ale nie jest **używalna** dla nowych userów.
