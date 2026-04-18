# POLECENIE: Dekonstrukcja Forge UI/UX — kompletny audyt procesu pracy

**Adresat:** ja sam, w następnej sesji
**Reguła:** bez kodu. Tylko analiza i projekt. Implementacja w osobnej sesji po review.
**Output:** jeden dokument `forge_output/_global/FORGE_UX_DECONSTRUCTION.md` z 7 sekcjami opisanymi niżej.

---

## 0. Twardy kontrakt — czego mi NIE wolno

1. **Nie wolno** napisać "lepszy UX", "intuicyjny interfejs", "user-friendly", "seamless flow". Każdy taki ogólnik jest objawem że nie pomyślałem konkretnie. Zamiast — pisz "klikam X, oczekuję Y, dostaję Z".
2. **Nie wolno** opisać tylko "co jest" bez **dlaczego to nie działa** i **co konkretnie zmienić**.
3. **Nie wolno** skracać. Jeżeli krok ma 12 wymiarów do rozłożenia, rozłożyć wszystkie 12. Brak czasu/miejsca to wymówka.
4. **Nie wolno** komplementować swojej dotychczasowej pracy. Każdy element istniejący jest podejrzany dopóki nie udowodnię że ma sens.
5. **Nie wolno** zakładać że user wie co to ingest/analyze/plan/orchestrate. Jeśli funkcja istnieje a user nie wie kiedy jej użyć — to nie jest funkcja, to jest pułapka.
6. **Nie wolno** się chować za "to wymaga większego scope" — opisz problem nawet jeśli nie wiem jak go rozwiązać. Open question lepszy niż przemilczenie.

---

## 1. Kontekst który MUSZĘ wczytać przed zaczęciem

Czytam OBA plus istniejący kod:

1. `platform/app/templates/*.html` — wszystkie obecne ekrany
2. `platform/app/api/ui.py` — wszystkie obecne UI routes
3. `platform/app/api/pipeline.py` — endpointy ingest/analyze/plan/orchestrate
4. `forge_output/_global/FORGE_PRODUCTIZATION_PLAN.md` — co to ma być biznesowo
5. `forge_output/_global/UX_PERSONA_AND_JOURNEYS.md` — jeśli istnieje
6. `forge_output/_global/UX_MOCKUPS.md` — jeśli istnieje
7. `forge_output/_global/UX_IMPLEMENTATION_PLAN.md` — jeśli istnieje (te 5 deliverables UX agent stworzył 11 sesji temu i ZIGNOROWAŁEM — muszę je teraz uwzględnić, NIE pominąć)
8. `forge_output/warehouseflow/inputs/*` — przykładowe SOW żeby wiedzieć co user wrzuca
9. `forge_output/warehouseflow/workspace/*` — przykładowy output workspace żeby wiedzieć co Forge daje

**Bez tego kontekstu nie zaczynaj pisać.**

---

## 2. Sekcja A: Workflow per krok (chronologicznie)

Wymyśl 10-15 kroków pracy z Forge. Każdy krok rozłóż na 14 wymiarów:

### Per krok wymagane wymiary:

1. **Numer + nazwa kroku** (np. "3. Upload dokumentów źródłowych")
2. **Co user chce w tym kroku** — intencja, jednym zdaniem
3. **Skąd user wie że jest na tym kroku** — co go tu doprowadziło, co mu mówi że to teraz
4. **Co Forge robi pod spodem** — endpointy, DB writes, subprocess calls, koszt, czas
5. **Co user widzi w obecnym UI** — konkretne ekrany, buttony, labele. Cytuj template paths.
6. **Czego user nie widzi a powinien** — informacje brakujące w obecnym UI
7. **Cel istnienia tego kroku** — biznesowe uzasadnienie. Bez tego nie da się robić Y.
8. **Bez tego kroku — czy Forge nadal funkcjonuje?** — TAK/NIE i dlaczego
9. **Wady obecnej implementacji** — konkretne, nie ogólniki
10. **Ograniczenia interfejsu** — co user chce zrobić ale nie może
11. **Nieciągłości WCHODZĄCE** — z poprzedniego kroku przepływ się rwie, gdzie?
12. **Nieciągłości WYCHODZĄCE** — do następnego kroku przepływ się rwie, gdzie?
13. **Brakujące funkcje UI** — czego nie ma a musi być
14. **Brakujące funkcje BACKEND** — endpoint nie istnieje a powinien
15. **Sugerowana zmiana** — konkretnie co i jak. Mockup ASCII jeśli wizualne.
16. **Challenge** — kontrargumenty. Dlaczego ta zmiana może być zła. Dlaczego user może NIE chcieć tego co proponuję.

**Lista przykładowych kroków którą trzeba pełnie pokryć (nie ograniczać się do tych — uzupełnij):**

- 0. Pierwsze logowanie / signup
- 1. Otrzymanie maila/SOW od klienta — co user widzi natychmiast po loginie
- 2. Decyzja "potrzebuję nowy projekt" — gdzie kliknąć, czego się spodziewać
- 3. Upload dokumentów (jednego? wielu? jakie formaty? gdzie? widoczność po wgraniu? edycja? podgląd?)
- 4. Ingest (czy to faza odrębna od uploadu? czy wymaga osobnej akcji?)
- 5. Analyze — co to jest, kiedy uruchomić, ile trwa, ile kosztuje, co zrobi z dokumentami
- 6. Review wyekstrahowanych objectives — czy edytować, jak, na podstawie czego
- 7. Decyzja konfliktów (analyze wyekstrahował open_questions / conflicts)
- 8. Decyzja "który objective realizować pierwszy"
- 9. Plan — kiedy uruchomić, co zaplanuje, czy user widzi propozycję przed komitnem
- 10. Review tasków, edycja kolejności / treści, dodanie własnych
- 11. Konfiguracja przed orchestrate — Anthropic key, budget, infrastructure (Docker? Postgres?)
- 12. Orchestrate run — start, live monitoring, cancel, log strumień
- 13. Po DONE — co user widzi, jakie kolejne akcje, jak ocenić wynik
- 14. Findings triage — kiedy, dlaczego, co po decyzji
- 15. Iteracja — change request, retry failed task, dodanie zakresu
- 16. Wysłanie klientowi — git push, PDF, share link, raport
- 17. Audyt / compliance — kto chce zobaczyć llm_calls i po co

Dla każdego z tych ~17 kroków: 16 wymiarów = ~270 punktów minimum. Jeśli któryś krok masz "krótki" — nie znaczy że można pominąć, znaczy że pewne wymiary są N/A z **wyjaśnieniem dlaczego**.

---

## 3. Sekcja B: Audit per element UI (każdy widoczny widget)

Lista elementów do przepuszczenia przez audyt:

**Navbar:**
- Logo Forge
- Project context "project: X"
- User email
- Org slug
- ⚙ settings link
- Login/Wyloguj/Utwórz konto buttons

**`/ui/` (lista projektów):**
- Pusta lista vs lista z projektami
- "+ New project" button + form (slug + name + goal)
- Karty projektu — co pokazują (tasks/cost/findings/decisions) — czy te liczby coś znaczą dla usera?

**`/ui/projects/{slug}` góra:**
- 4 kafelki stats (tasks total / objectives count / cost / findings/decisions)
- Pasek 4 akcji (Ingest / Analyze / Plan / Orchestrate)
- 8 tabs (Objectives / Tasks / Files / LLM-calls / Findings / Decisions / Knowledge / Guidelines)

**Tab Objectives:** Lista objective cards + Edit + KR rows + Add objective form
**Tab Tasks:** Tabela z 7 kolumnami + Edit + Add task form
**Tab Files:** 2-kolumnowy layout (lista + viewer)
**Tab LLM-calls:** Tabela z purpose/model/cost/dur
**Tab Findings:** Karty z triage buttons (Approve/Defer/Reject)
**Tab Decisions:** Karty
**Tab Knowledge:** Karty (read-only)
**Tab Guidelines:** Karty + Add form

**Task report (`/ui/projects/{slug}/tasks/{ext}`):**
- Header z cost breakdown
- Sekcje: Requirements / Objective+KRs / Tests / Verification / Challenge / Findings / Decisions / Diff / AC / Comments / Not-executed claims

**Org settings (`/ui/org/settings`):**
- Anthropic key form
- Budget form
- Current month spend display

**Live orchestrate run (`/ui/orchestrate-runs/{id}`):**
- Status badge
- 4 kafelki (done/failed/cost/elapsed)
- Aktualny task + phase + cancel
- Final result list

**Login + Signup pages**

### Per element wymagane wymiary (10):

1. **Co reprezentuje** (1 zdanie)
2. **Skąd user ma wiedzieć kiedy z tego skorzystać** — z czego wynika kontekst kliknięcia
3. **Co się dzieje po interakcji** — natychmiast, w tle, długo
4. **Czy operacja jest **kompletnie** wspierana** — wszystkie potrzebne funkcje wokół
5. **Jakie funkcje brakują** wokół tego elementu (np. po Findings triage Approve nie ma "undo")
6. **Jakie ograniczenia interfejsu** (np. checkbox `skip_infra` — co to znaczy, dlaczego user ma to wiedzieć)
7. **Czy element istnieje sensownie samodzielnie** czy powinien być scalony z czymś / usunięty / przeniesiony
8. **Bez tego elementu** — czy workflow nadal działa? Co tracimy?
9. **Konkretne sugestie zmian** — usunąć / scalić / dodać / zmienić tekst / inny komponent
10. **Challenge** — kontrargumenty: dlaczego obecna implementacja może być właściwa pomimo zarzutów, dlaczego sugerowana zmiana może pogorszyć coś innego

---

## 4. Sekcja C: Nieciągłości w przepływie (krytyczne)

**Dla każdej nieciągłości:**
- Skąd user przychodzi (z którego ekranu / akcji)
- Gdzie powinien iść (jakie zadanie ma do wykonania)
- Co go blokuje (brak buttona / linka / oczekiwana akcja niedostępna)
- Co user obecnie robi gdy się gubi (rage-quit / przegląda losowe taby / pyta supportu)
- Naprawa: konkretny element interfejsu który połączy te dwa miejsca

**Lista podejrzewanych nieciągłości do potwierdzenia/obalenia:**

- 1. Po uploadzie dokumentów — gdzie idą? czy są widoczne? gdzie kliknąć żeby zobaczyć "co Forge wie"
- 2. Po Analyze — wiele rzeczy się stworzyło (objectives, KR, conflicts, open_questions) — gdzie user to wszystko zobaczy w spójnym widoku?
- 3. Conflicts/open_questions z analyze trafiają do tabeli `decisions` (type=conflict/open_question) — czy user wie co z tym zrobić? Brak buttona "Resolve" lub "Decide"?
- 4. Plan tworzy taski ale user nie widzi propozycji przed zatwierdzeniem — co jeśli nie chce 7 tasków?
- 5. Tab Tasks ma "+ Add task manually" ale jak user manualnie tworzy task pasujący do plan-istnejącej-fazy?
- 6. Tab Objectives nie pokazuje "który objective ma plan a który nie" — jak user wie co należy zaplanować dalej?
- 7. Orchestrate button — z jakim objective? Z jakim tasks? Cały projekt? Jeden objective? user nie wie
- 8. Po orchestrate run DONE — user wraca do listy tasków, ale brak "co teraz?" guidance
- 9. Findings tab pokazuje listę ale jak user się dowie że są nowe findings od Phase B/C extractora?
- 10. Workspace files — gdzie user pobierze cały kod? Brak "Download zip"
- 11. LLM-calls tab — kto i kiedy ma to przeglądać? Jaki triggers wejście tu?
- 12. Jak user ocenia czy task DONE jest **dobrze** zrobiony, nie tylko technically passed?

---

## 5. Sekcja D: Krytyczne braki funkcjonalne (UI i Backend)

### Per brak:
- **Co brakuje** (konkretnie)
- **Bez tego user nie może** (jakiego celu nie osiągnie)
- **Workaround obecny** (np. ręcznie SQL, ręcznie git, w terminalu)
- **Effort dodania** (S/M/L)
- **Priorytet do rozwiązania** (P0 blocker / P1 ograniczenie / P2 nice)

### Lista podejrzewanych braków (zweryfikować):

**UI (brak ekranu/elementu mimo że endpoint istnieje):**
- Brak wizard/onboarding nowego użytkownika
- Brak hero "co teraz" na dashboardzie
- Brak widoku "open conflicts/decisions" — nie wiadomo jak je decydować
- Brak komentarzy za pomocą @mentions / notification
- Brak download workspace jako zip
- Brak panel "ostatnia aktywność" / activity feed
- Brak edit Knowledge content
- Brak "Re-run task" po DONE
- Brak "Cancel orchestrate" widocznego z innych ekranów
- Brak diff viewer skoro tylko czasem renderowany
- Brak "Skills" UI (skoro micro_skills istnieją w DB)
- Brak Audit log UI (tabela jest)

**Backend (endpoint nie istnieje a powinien):**
- Brak workspace download zip
- Brak Decision UI resolve zwykłej decision (był tylko skill-based decisions)
- Brak Knowledge edit content
- Brak Project DELETE z UI
- Brak history zmian per encja (audit pokaże, ale brak diff/timeline)
- Brak "duplicate project" / template
- Brak export CSV/JSON projektu
- Brak retry single task
- Brak metrics aggregate (wszystkie projekty) — ile $ ile czasu

---

## 6. Sekcja E: Czego nie uwzględniono a musi być

To, co w obecnej architekturze Forge **nie istnieje** ale workflow tego wymaga:

- Onboarding new user (no flow exists)
- Templates / starter projects (no concept)
- Tutorial / inline help (no tooltips, no guides)
- Notifications (in-app, email) — task done, finding HIGH, budget alert
- Search / filter (lista projektów, taski, llm-calls — brak)
- Sort columns (tabela tasków/llm-calls)
- Bulk actions (np. zatwierdź wszystkie LOW findings)
- Keyboard shortcuts
- Mobile responsive (probably broken)
- Dark mode
- Print stylesheet (PDF export?)
- Empty states z CTA
- Loading states (orchestrate live ma, ale ingest/analyze/plan blokuje request bez spinnera)
- Error states z next actions (np. analyze failed → "Try again" / "Edit prompt")
- Offline handling
- Multi-org switcher (user może mieć membership w wielu)
- Profile edit (zmiana hasła, email, full name)

---

## 7. Sekcja F: Plan działania (output operacyjny)

Po analizie wyznacz:

1. **TOP 5 zmian z najwyższym impact** — czyli "naprawienie tych zmieni interfejs z bezsensownego na używalny"
2. **TOP 5 brakujących funkcji do dodania**
3. **TOP 5 nieciągłości do połączenia**
4. **Sekwencja implementacji** — co pierwsze, co potem, dlaczego (zależności)
5. **Mockupy ASCII** dla głównych nowych ekranów (minimum 4 — landing dashboard, upload+analyze flow, plan review, post-orchestrate summary)

---

## 8. Sekcja G: Open questions (rzeczy wymagające user input)

Pytania do user'a do rozstrzygnięcia przed implementacją. Przykłady (dopisać własne):

- Czy onboarding ma być wizard czy free-form?
- Czy Forge ma sugerować "co teraz?" agresywnie (notyfikacje) czy biernie (menu)?
- Czy templates projektów zaczynamy z Lingaro examples (warehouseflow) czy abstract?
- Czy zostają taby (8) czy nawigacja zorganizowana wokół workflow phases (4-5)?
- Czy "advanced mode" ukryty pod toggle dla power-userów (jak `skip_infra`)?
- Czy orchestrate ma być zawsze async czy opcja sync dla małych projektów?
- Czy llm_calls audit ma być zawsze widoczny czy tylko w "compliance mode"?

---

## 9. Sekcja H: Interaktywność, logowanie i bieżący dostęp do informacji

**Forge wykonuje operacje które trwają 2-30 minut** (analyze, plan, orchestrate, Phase A tests, Phase B extract, Phase C challenge). Każda z tych operacji wywala 5-50 sub-operations pod spodem (subprocess Claude CLI, pytest, git diff, KR measurement, encrypted API calls). User **musi** widzieć:

1. **Co się dzieje teraz** — nie "spinner", tylko konkretnie który krok, z jakim wejściem, ile trwa
2. **Ile to kosztuje do teraz** — w czasie rzeczywistym, nie po fakcie
3. **Co zostało zrobione** — od startu operacji, gdzie jesteśmy w multi-step flow
4. **Co zostanie zrobione** — estymacja pozostałego czasu/kosztu
5. **Co może pójść nie tak** — przed-uruchomieniem: jakie ryzyka, jakie scenariusze błędów
6. **Jak user może wpłynąć** — pauza, cancel, zmiana parametrów w locie

### Per mechanizm interaktywny do zbadania:

Dla każdego z poniższych **określić** (14 wymiarów):

1. Czy istnieje w obecnym UI? (gdzie, szczegółowo)
2. Czy jest **live** (refreshowany bez user action) czy **stale** (wymaga F5)?
3. Jaki opóźnienie wykrywania zmiany (0.5s? 2s? 10s? jak user się dowie o zmianie)?
4. Czy user widzi różnicę "było X, teraz Y" czy tylko aktualny stan?
5. Czy user może subskrybować powiadomienia (filtr po typie, po projekcie)?
6. Czy jest historia (kiedy co się zmieniło) czy tylko snapshot now?
7. Dostępność cross-screen — czy z task report widzę status orchestrate?
8. Mobile/tablet access — czy widać na mniejszym ekranie?
9. Accessibility (screen reader announcements na change?)
10. Wydajność — ile pollingu na minutę, czy serwer to udźwignie przy 50 users?
11. Retention — po jakim czasie log event znika?
12. Export — czy user może pobrać log jako CSV/JSON?
13. Cross-entity — czy log dla task łączy się z log dla objective/project?
14. Auto-link do źródła — z log event klikalny link do pełnego LLM call / diff / findings

### Lista interaktywnych mechanizmów do audytu:

**1. Live status operacji w toku:**
   - Orchestrate run (jest — polling 2s, ograniczony do jednego ekranu)
   - Analyze (nie ma — blokuje request)
   - Plan (nie ma — blokuje request)
   - Ingest (nie ma — blokuje request)

**2. Progress indicators:**
   - Orchestrate run (jest: current_task + phase + elapsed)
   - Phase A testing (nie widoczne — user nie wie że pytest jest uruchamiany)
   - Phase B extraction (nie widoczne)
   - Phase C challenge (nie widoczne)
   - Docker compose bootstrap (nie widoczne)

**3. Cost counter:**
   - Total run cost (jest, polling 2s)
   - Per-phase cost breakdown w czasie rzeczywistym (nie ma)
   - Cumulative org cost this month (jest w org settings, ale nie w main dashboard)
   - Per-project cost forecast przed uruchomieniem (nie ma)

**4. Log stream / output:**
   - Claude CLI stdout real-time (NIE MA — subprocess.run blokuje, user nie widzi co LLM pisze)
   - pytest output real-time (nie ma)
   - Git operations output (nie ma)
   - Docker compose logs (nie ma)
   - Last 50 events timeline per projekt (nie ma)

**5. Activity feed:**
   - Per-project (nie ma — audit_log tabela istnieje ale bez UI)
   - Per-org (nie ma)
   - Per-user ("co się działo od ostatniej wizyty") (nie ma)

**6. Notifications (in-app + email):**
   - Task DONE (nie ma)
   - Task FAILED after max retries (nie ma)
   - Finding HIGH wykryty (nie ma)
   - Budget 80% / 100% (nie ma — webhook tylko jeśli zewnętrznie skonfigurowany)
   - Challenge NEEDS_REWORK (nie ma)
   - Orchestrate run completed (nie ma)
   - Share link wygasa (nie ma)

**7. Cancel / pause controls:**
   - Orchestrate cancel (jest ale tylko w live view — nie można cancel z listy projektów)
   - Analyze/plan cancel (nie ma)
   - Task-level pause (nie ma)
   - Rollback po failed DONE task (nie ma)

**8. Real-time collab:**
   - Wiele users widzi ten sam projekt — jeden edytuje objective, drugi widzi zmianę? (NIE — optimistic locking nie ma, session cache)
   - Comment appears for all (nie — tylko po F5)

### Dla każdego z 8 mechanizmów — output wymaga:
- Stan obecny (jakiś URL, template, endpoint)
- Co user **powinien** widzieć / móc robić
- Gap analysis — konkretna luka
- Propozycja implementacji (SSE / WebSocket / polling / notification center)
- Trade-off (polling vs push, cost server, complexity)
- Priorytet (P0/P1/P2)

---

## 10. Sekcja I: Kompletność funkcjonalna — jak zbadać czy UI jest FUNKCJONALNY

**Ogólnik "funkcjonalny" to nic nie znaczy.** Trzeba operacjonalizować.

### 11 testów funkcjonalności do przejścia per feature:

1. **Critical path test** — czy user może wykonać zadanie end-to-end bez skakania do terminala / psql / IDE?
   - Przykład: "stworzyć projekt, załadować SOW, dostać plan 10 tasków, uruchomić 3, zobaczyć wynik, wysłać klientowi" — czy to się da **wyłącznie** przez UI?
2. **Form completeness** — czy wszystkie pola które user może chcieć ustawić są obecne? Jakie pola Forge accepts w API a nie są w UI?
3. **Reversibility** — czy każda akcja ma undo lub confirmation? Co jeśli user kliknie "Delete" przypadkiem?
4. **Discoverability** — czy user znajduje funkcję **bez** wiedzy URL? Czy jest dojście z innego ekranu?
5. **Feedback loop** — czy user dostaje potwierdzenie że akcja się stała? Gdzie to widać? Kiedy znika?
6. **Error recovery** — co user robi gdy rzecz nie wyszła? Czy UI pokazuje "spróbuj ponownie" / "edytuj parametry" / "skontaktuj się z adminem"?
7. **Role accessibility** — czy viewer/editor/owner każdy ma klarowny flow? Co viewer widzi gdy próbuje kliknąć Edit?
8. **Discoverable capabilities** — czy user wie że dana funkcja istnieje? (np. git push / PDF export — czy button jest widoczny?)
9. **Parameter guidance** — czy technical parametry są wyjaśnione? (np. `skip_infra` checkbox — tooltip co to znaczy?)
10. **Search / filter / sort** — czy user z 100 taskami może ogarnąć? 500 llm_calls? 50 findings?
11. **Progressive disclosure** — czy basic user widzi prosty formularz a power user może rozwinąć advanced?

### Per feature Forge przeprowadź test powyższych 11 punktów:

- Project creation
- Document upload + ingest
- Analyze operation
- Plan operation
- Task CRUD (add/edit/delete)
- Objective CRUD
- KR CRUD + measurement
- AC CRUD per task
- Guidelines CRUD
- Orchestrate start
- Orchestrate live monitoring
- Orchestrate cancel
- Task report view
- Task DONE report review
- Findings triage
- Decision resolution
- Comments add/view
- Share link generation
- Webhook config
- Budget management
- Anthropic key config
- Workspace file browser
- Git push (not implemented)
- PDF export (not implemented)

Każda funkcja × 11 testów = **minimum 24×11 = 264 rated punktów**. Wynik: Pass / Partial / Fail z konkretnym uzasadnieniem. Fail = priorytet naprawy.

---

## 11. Sekcja J: Symulacja Person — end-to-end przez interfejs

Wciel się (agent) w **5 konkretnych person**. Dla każdej:

### Format persony:

**Nazwa + rola (1 linia)**
**Background (1 paragraf):** kim jest, co wcześniej robił, jakie ma oczekiwania wobec Forge.
**Cel główny (1 zdanie):** co chce osiągnąć tą konkretną sesją użycia Forge.
**Kontekst biznesowy (2-3 zdania):** kto za tym stoi, kiedy ma deadline, komu raportuje.
**Level techniczny (skala):** może pisać Python? zna Git? używa terminala?
**Co wie o Forge przed sesją:** nic? podstawy? zaawansowane?

### Scenariusz E2E (20-30 kroków per persona):

Per każdy krok:

1. **Akcja user'a** — co dokładnie robi (click na X, wpisuje Y)
2. **Ekran / URL** — gdzie jest
3. **Co widzi** — konkretnie co pojawia się na ekranie (elementy, dane, buttony)
4. **Wewnętrzny dialog (cytat)** — co myśli ("gdzie jest X?", "wtf to ma znaczyć?", "ok rozumiem", "dlaczego musi tu być?")
5. **Effort rating (1-5)** — 1=oczywiste, 5=muszę zatrzymać, zgadywać, pytać
6. **Frustracja (yes/no + opis)** — jeśli tak: co konkretnie i dlaczego
7. **Czas** — ile zajęło (real world estimate)
8. **Co by pomogło** — co konkretnie zmienia ten krok z 5→1 effort

### Podsumowanie per persona (na końcu scenariusza):

- Czy persona osiągnęła cel? (TAK / NIE / CZĘŚCIOWO)
- TOP 3 frustracje (cytaty z wewnętrznego dialogu)
- TOP 3 rzeczy które działały dobrze
- Czy persona wróci do Forge? Dlaczego tak/nie?
- Jeden paragraph "co bym chciał jako ta persona" — z perspektywy persony, nie dewelopera

### 5 wymagana person:

**Persona 1 — Jakub, Tech Lead w software house, nowy user Forge**
- Dostał nowy SOW od klienta 2 dni temu. Szef powiedział "spróbuj Forge, ma być szybciej".
- Deadline pilot za 3 tygodnie.
- Python + JS dev z 8-letnim stażem. Używał Cursora.
- O Forge nie wie nic poza "ma być lepszy niż Cursor do audytu".
- Scenariusz: pierwsze logowanie → ładuje SOW + email od klienta (3 pliki razem) → próbuje uruchomić → próbuje zobaczyć wynik → chce pokazać klientowi.

**Persona 2 — Anna, Delivery Manager, wraca po tygodniu**
- Wie że zespół uruchomił Forge dla 2 projektów klienta X.
- Chce zrobić raport statusu dla klienta na piątek.
- Nie-techniczna (manager), używa Jira + Confluence.
- Scenariusz: login → chce zobaczyć "co było zrobione ostatnio" → chce porównać 2 projekty pod kątem kosztu/jakości → chce wyeksportować raport.

**Persona 3 — Maria, CFO Lingaro, compliance/budget perspective**
- Nie-techniczna finansistka. Słyszała że Forge kosztuje $X/mies. Chce zrozumieć.
- Cel: policzyć ROI Forge vs ręczne delivery.
- Ma prawo do org settings (rola owner).
- Scenariusz: login → gdzie zobaczyć koszty? → per projekt / per zespół → export CSV dla Excel → zrozumieć co drogie, co tanie → nastawić budgety.

**Persona 4 — Piotr, Client PMO** (u klienta Lingaro)
- Dostał share link do task report T-005.
- Cel: zweryfikować że deliverka od Lingaro rzeczywiście zrobiona.
- Zna podstawy Git (code review), nie zna Forge wcale.
- Scenariusz: klika link → widzi task report → chce sprawdzić faktyczny kod → chce zobaczyć testy → chce zrozumieć co to "Phase C challenge" → zastanawia się czy to wiarygodne źródło.

**Persona 5 — Marek, DevOps Lingaro, configuration + audit**
- Odpowiada za bezpieczeństwo i audit trails.
- Cel: skonfigurować webhooki do ich Slacka, ustawić retention policy, sprawdzić audit log.
- Ekspert techniczny, ceni konfigurację per YAML/env > klikanie.
- Scenariusz: login → gdzie webhooki? → konfiguracja secret rotation → gdzie audit log? → dlaczego brak export do SIEM?

### Dla WSZYSTKICH 5 person razem — meta-analiza:

1. **Top 10 wspólnych frustracji** (występują u 3+ person)
2. **Top 10 indywidualnych frustracji** (ważne mimo że dotyczą jednej roli)
3. **Top 5 "a-ha moments"** — gdzie którakolwiek persona dostała pozytywne wrażenie
4. **Najcięższe nieciągłości** — gdzie persona się poddaje / szuka pomocy
5. **Wspólne brakujące funkcje** (3+ personas wymagają tego samego)

---

## 12. Sekcja K: Zasady projektowania UI tied to Forge (nie generic UX)

Generic UX principles (consistency, feedback, clarity) nie wystarczają. Forge ma **specyficzne cechy** które wymagają specyficznych rozwiązań:

### Cechy Forge które wymuszają UX decyzje:

1. **Długie operacje (2-30 min)** — orchestrate, analyze, plan
   → Implikuje: async-first, live progress, cancel, background retry, save partial state
   → Nie: "klient w stylu Cursor" (instant response)

2. **Drogie operacje ($0.10 — $5 per LLM call, $50+ per pełny projekt)**
   → Implikuje: cost visible ZAWSZE, pre-confirmation przed $$$, budget guards, what-if
   → Nie: "klik i zapomnij"

3. **Audit-first, compliance target**
   → Implikuje: wszystko logowane, kto co zmienił widoczne, export na żądanie, immutable history
   → Nie: "ephemeral UX, reset often"

4. **Multi-user collab (Phase 2)**
   → Implikuje: komentarze, activity feed, notifications, lock indicators
   → Nie: solo-user assumptions

5. **Technical + business users w tej samej apce**
   → Implikuje: dwa mody (simple / advanced) lub progressive disclosure, tłumaczenie techniczne → biznesowe
   → Nie: "tylko dla programistów" albo "tylko dla managerów"

6. **Dane AI-generated wymagają human review** (nigdy nie ufaj)
   → Implikuje: review/approve/reject flow domyślny, confidence indicators, "Forge proponuje: ..." pattern
   → Nie: "Forge zrobił to, done"

7. **Workflow ma nieczytelne dependencies** (task zależy od objective który zależy od knowledge)
   → Implikuje: visualization dependency graph, prerequisites checklist, "zanim to → zrób to"
   → Nie: flat tabs z izolowanymi encjami

8. **Errors są drogie** (failed orchestrate $5+, rollback workspace brak)
   → Implikuje: pre-flight validation, dry run, rollback capability, incremental save
   → Nie: "klik OK zatwierdź" bez preview

9. **Klient = trzecia strona** (share links, PDF reports)
   → Implikuje: read-only public views, sanitization (brak secrets/tokens), branding
   → Nie: "internal tool only"

10. **Skalowanie: 1 → 50 → 500 projektów**
    → Implikuje: search / filter / sort wszędzie, bulk actions, archiving, aggregation dashboards
    → Nie: scroll przez listę projektów

### Per każda cecha — output wymaga:

- Obecny stan UI vs wymaganie
- Gap — konkretnie czego brak
- Implementation guideline — JAK to rozwiązać w kontekście Jinja+HTMX+Tailwind (stack Forge)
- Przykład zastosowania — konkretny ekran / komponent / interakcja
- Anti-pattern — czego NIE robić

### Workflow patterns — co kiedy:

- **Wizard** (kroki sekwencyjne z walidacją) — kiedy? (np. onboarding pierwszego projektu)
- **Dashboard** (overview z KPI) — kiedy? (landing dla returning user)
- **Kanban** (status-based flow) — kiedy? (taski per status)
- **Timeline** (chronological) — kiedy? (activity feed, audit log)
- **Tree / Graph** (hierarchical) — kiedy? (dependency graph, workspace files)
- **Table** (bulk data) — kiedy? (llm_calls, findings z filtrem)
- **Form** (input-heavy) — kiedy? (CRUD simple)

### Functionality patterns:

- Optimistic update vs pessimistic — kiedy co w Forge
- Inline edit vs modal vs full-page — kiedy co
- Toast vs modal vs banner — kiedy co
- Confirmation dialog — dla jakich akcji
- Bulk select UX — dla jakich tabel

### Empty state design tied to Forge:

Dla każdego ekranu — co user widzi gdy pusty:
- Lista projektów pusta → CTA "Start twój pierwszy projekt"
- Objective bez tasków → CTA "Zaplanuj ten cel (~4 min)"
- Task bez AC → CTA "Dodaj akceptację żeby Forge mógł zweryfikować"
- Findings pusty → "Świetnie! Nic do przeglądu" lub "Brak findings bo Phase B nie uruchomiony dla tego taska"
- LLM-calls pusty → "Ten projekt jeszcze nic nie kosztował"

### Loading / error states tied to Forge operations:

- Orchestrate trwa 20 min:
  - 0-5s: "Startowanie..."
  - 5-60s: "Claude pisze kod (T-001 attempt 1/3)..."
  - 60-120s: "Pytest weryfikuje..."
  - Per faza specyficzny text
- Analyze failed:
  - "Nie mogłem wyekstrachować objectives bo dokumenty są pełne [reason]. [Spróbuj ponownie] [Edytuj dokumenty]"

---

## 13. Sekcja L: Zalecenia UI/workflow/funkcjonalności tied to Forge code

Na podstawie znajomości **konkretnej architektury Forge** (z kontekstu sekcji 1), wyprowadź zalecenia:

### Architektura → UI patterns:

1. **Kontrakt operacyjny Forge** — użytkownik musi w UI widzieć że AI jest w checkach. Gdzie? Jak?
2. **Phase A/B/C multi-phase** — user powinien widzieć dla każdego task który phase przeszło. UI gdzie?
3. **llm_calls pełen audit** — dostępne, ale ukryte w tabie. Kiedy ujawnić?
4. **Docker compose per workspace** — user powinien widzieć że jest izolowany, nie "cloud nothing".
5. **External_id per encja (T-001, O-001, K-001)** — user widzi te kody. Czy mają sens? Czy lepiej nazwy?
6. **Org scoping** — user w wielu orgach musi mieć switcher. Gdzie?

### Per każde zalecenie:

- Obecny stan kodu (plik, linia jeśli istotne)
- Wpływ na UI — co konkretnie jest dotknięte
- Recommendation — JAK zmienić UI żeby pasował do architektury
- Trade-off — co tracimy dodając tę funkcję

---

## 14. Sekcja M: Gdybym był userem — co bym dodał do interfejsu (z samokrytyką)

Wciel się w perspektywę **frustrującego userа** który dostał 35 features ale dalej nie wie jak pracować. Zamiast listy generic UX principles, wypisz **obietnice** których user ode mnie oczekuje, pogrupowane według 5 kryteriów które user sam wskazał.

Per obietnica:
1. **Co chcę** (pierwsza osoba, głos usera)
2. **Dlaczego — jaką frustrację to rozwiązuje** (konkretnie z tego co miałem)
3. **Jak UI/backend ma to dostarczyć** (konkretnie, nie ogólnie)
4. **Czy ta propozycja jest dobra czy zła — self-challenge** (argumenty za / przeciw / kiedy pogorszy / trade-off / alternatywy)

### Kryterium 1: MODYFIKOWALNOŚĆ

Wymagane obietnice do rozpisania z 4 wymiarami każda:

- **Undo po destructive action** (delete task/objective/finding triage)
- **Version history per encja** (objective/task — kiedy kto co zmienił)
- **Rollback do poprzedniej wersji** (task instruction się popsuł, wracam)
- **Draft / preview przed commit** (plan tworzy 10 tasków — pokaż zanim zatwierdzę)
- **Inline edit wszędzie** (nie tylko w wybranych miejscach)
- **Batch edit** (zmień priorytet 5 objectives)
- **Nieniszczące operacje** (delete = soft archive, restore dostępne 30 dni)

Per ta obietnica — **czy to dobry pomysł dla Forge?** Challenge:
- Undo LLM call: **nie da się** (koszt już poniesiony)
- Rollback objective po użyciu w plan: skomplikowane (tasks odwołują się do starej wersji)
- Draft/preview: zwiększa złożoność flow, ale oszczędza $$$
- Batch na 5 objectives: potrzebne przy skali czy YAGNI?

### Kryterium 2: SPÓJNOŚĆ

Wymagane do rozpisania:

- **Design system** — kolory akcji, typografia, spacing, buttons (gdzie jest niespójność obecnie?)
- **Spójna nawigacja** — breadcrumbs, back button, URL patterns (gdzie obecnie chaotycznie?)
- **Spójny pattern modali vs inline edit vs full-page** — kiedy co
- **Spójny status vocabulary** — DONE vs ACCEPTED vs COMPLETED (Forge ma wszystkie!)
- **Spójna terminologia PL/EN** — user widzi "Orchestrate", "Objective" (EN) ale "Zaloguj", "Wyloguj" (PL) — mix? Ustalić.
- **Spójne skróty external_id** (T-001, O-001, K-001, D-001, F-001, G-001) — pokazywać czy ukrywać?
- **Spójne formatowanie dat/kosztów** (czasem "$0.08", czasem "0.076USD")
- **Spójne error messages** (czasem 422 JSON, czasem HTML, czasem redirect)

Self-challenge:
- Design system = inwestycja 1-2 dni pracy, ale **niezbędna** do wiarygodności komercyjnej
- PL/EN mix: czy warto unifikować? Koszt tłumaczenia vs wartość
- External_id: dev lubi, biznes nie rozumie — dwuwarstwowe: business name + technical id

### Kryterium 3: JAKOŚĆ działania

- **Performance guarantees** — lista 500 llm_calls nie zawiesza UI (virtualization / infinite scroll / pagination)
- **No page reload potrzebny** — wszystkie akcje HTMX partial update
- **State persistence** — F5 nie gubi scroll, filtery, expanded sections
- **Optimistic UI** — klikam Save, natychmiast widzę zmianę (rollback tylko przy błędzie)
- **Zero latency feedback** — button pressed state, spinner < 100ms
- **Offline handling** — wykrycie network loss, queue retry
- **Browser forward/back** działają jak należy (historia stack)
- **Deep linking** — każda rzecz ma stabilny URL (bookmark, share)
- **Accessibility (WCAG AA)** — keyboard nav, screen reader, contrast 4.5:1
- **Cross-browser** — Chrome/Firefox/Safari/Edge consistent

Self-challenge:
- Virtualization: premature jeśli 1-5 users, essential przy 50+ per org
- Optimistic UI dla LLM ops: nie działa (nie wiem wyniku do zwrotu CLI)
- WCAG AA: czas/wysiłek, ale EU legal requirement dla B2B
- Offline handling: Forge = server-heavy, offline ma ograniczony sens

### Kryterium 4: ELASTYCZNOŚĆ

- **Search + filter + sort wszędzie** (projekty, taski, findings, llm_calls)
- **Saved filters / views per user** ("moje HIGH findings w appointmentbooking")
- **Global search (Cmd+K)** — skacz do dowolnego taska/ekranu
- **Customizable dashboard widgets** — user decyduje co widzi
- **Keyboard shortcuts** — alt+n = new task, alt+s = save
- **Multiple simultaneous projects** — tab / window per projekt
- **Export wszędzie** — CSV, JSON, PDF
- **Bulk selection** — checkbox column + action toolbar
- **Pin / favorite** — przypnij używane projekty
- **Progressive disclosure** — simple mode dla nowych, advanced toggle
- **Per-user preferences** — theme, default tab, density

Self-challenge:
- Saved filters: nice-to-have, nie blocker
- Cmd+K global search: power feature, trudny implementacyjnie (indexing, fuzzy)
- Dashboard customization: support nightmare — każdy user inne UI
- Progressive disclosure: realny plus dla mix tech/business users

### Kryterium 5: WSPARCIE DZIAŁAŃ

- **"Co teraz?" guidance** — każdy ekran mówi co user powinien zrobić
- **Onboarding wizard** — first 5 min scripted
- **Sample project / template** — "zacznij od warehouseflow sample"
- **Contextual help** — ? icon obok każdego technical term
- **Empty states z CTA** — zamiast pustej listy, konkretny next step
- **Error recovery z next action** — "Orchestrate failed" → [Retry] [Edit params] [Contact support]
- **Pre-operation estimate** — "This will cost ~$4 and take ~15 min. Continue?"
- **Notifications center** — aggregated activity
- **Email digest** — daily summary
- **Activity feed per projekt** — timeline co się działo
- **Progress indicators na długich operacjach** — nie tylko "loading"
- **Tutorial replay** — bottom-right "Need help?" button
- **Celebratory moments** — "Project completed! 10 tasks done, $8.20 spent, below budget 🎉"
- **Warning przed drogim/nieodwracalnym** — "Orchestrate cały projekt = ~$50. Continue?"

Self-challenge:
- "Co teraz?" guidance: kluczowe ale niebezpiecznie paternalistyczne (power user zniesmaczony)
- Notifications: dobre dla async, ale overload ryzyko
- Pre-operation estimate: trudny (Forge nie wie dokładnie ile LLM calls), ale wartość wysoka — nawet szacunkowy pomoże
- Celebratory moments: może wydawać się infantylne dla enterprise — testować z personami

### Meta-challenge tych 5 kategorii

Każda z 5 kategorii konkuruje o budżet czasu. Nie wszystko da się w jednej sesji.

**Per kategoria wybierz TOP 3 obietnice z HIGHEST impact / LOWEST effort:**

- Modyfikowalność: 3 obietnice z priorytetem
- Spójność: 3 z priorytetem
- Jakość: 3 z priorytetem
- Elastyczność: 3 z priorytetem
- Wsparcie: 3 z priorytetem

Razem **15 MUST obietnic** — to krytyczne minimum dla "nie frustruje".

Reszta (~40 obietnic) = SHOULD (faza 2 UX) albo COULD (faza 3).

### Finalny challenge — czy to wszystko razem jest spójne?

Po wypisaniu 15 MUST obietnic — sprawdź:

1. Czy nie ma konfliktów? (np. "customization per user" vs "spójny design system")
2. Czy wszystkie są **mierzalne** (czy można za 2 tygodnie powiedzieć "tak zrobiono, nie"?)
3. Czy wszystkie mapują do istniejącego stacku (Jinja+HTMX+Tailwind) czy wymuszają React?
4. Czy razem tworzą narrację "Forge dla [target user] żeby [osiągnął X]"?
5. Czy któraś obietnica wyklucza inną?

---

## 15. Format dokumentu wynikowego

Plik: `forge_output/_global/FORGE_UX_DECONSTRUCTION.md`

Struktura:
```
# Forge UX Deconstruction — kompletny audyt

## 0. Executive summary (max 1 strona)
- Diagnoza w 5 zdaniach
- TOP 3 problemy
- TOP 3 propozycje
- Czego dotychczas nie zrobiono mimo że potrzebne

## 1. Workflow analysis — 17 kroków
### Krok 0: First login + onboarding
[16 wymiarów]
### Krok 1: ...
[etc.]

## 2. UI element audit — N elementów
### Navbar
### Dashboard "/"
### Project page top
### Tab Objectives
[etc.]

## 3. Nieciągłości — 12+
### Nieciągłość 1: Po uploadzie → ?
[5 wymiarów]
### ...

## 4. Krytyczne braki — UI
### ...
## 4b. Krytyczne braki — backend

## 5. Czego nie uwzględniono

## 6. Interaktywność i real-time feedback (Sekcja H)
- Per mechanizm: 14 wymiarów audytu
- 8 mechanizmów do sprawdzenia (live status, progress, cost, log stream, activity feed, notifications, cancel, real-time collab)

## 7. Kompletność funkcjonalna (Sekcja I)
- 24 features × 11 testów funkcjonalności
- Per feature: Pass / Partial / Fail + uzasadnienie + priorytet

## 8. Symulacja 5 person end-to-end (Sekcja J)
### Persona 1: Jakub, Tech Lead, nowy user
- Background + cel + scenariusz 20-30 kroków z dialogiem wewnętrznym
- Effort rating 1-5 per krok
- Podsumowanie: TOP 3 frustracje, TOP 3 pozytywy, wróci?
### Persona 2: Anna, Delivery Manager (returning)
### Persona 3: Maria, CFO (compliance/budget)
### Persona 4: Piotr, Client PMO (share link consumer)
### Persona 5: Marek, DevOps (audit + webhooks)
### Meta-analiza:
- TOP 10 wspólnych frustracji
- TOP 10 indywidualnych krytyczne
- Top 5 "a-ha moments"
- Najcięższe nieciągłości
- Wspólne brakujące funkcje

## 9. Zasady projektowania UI dla Forge (Sekcja K)
- 10 cech Forge które wymuszają specyficzne UX decyzje (długie operacje, drogie operacje, audit-first, etc.)
- Per cecha: gap + implementation guideline + przykład + anti-pattern
- Workflow patterns (wizard/dashboard/kanban/timeline/tree/table/form) — kiedy co w Forge
- Functionality patterns (optimistic/inline edit/toast/confirmation/bulk)
- Empty states per ekran
- Loading/error states per operacja

## 10. Zalecenia tied to Forge code (Sekcja L)
- Per architektoniczna cecha: obecny stan + impact UI + recommendation + trade-off

## 11. Obietnice usera w 5 kategoriach (Sekcja M)
### 11a. Modyfikowalność — 7 obietnic z self-challenge
### 11b. Spójność — 8 obietnic z self-challenge
### 11c. Jakość działania — 10 obietnic z self-challenge
### 11d. Elastyczność — 11 obietnic z self-challenge
### 11e. Wsparcie działań — 14 obietnic z self-challenge
### 11f. TOP 3 MUST per kategoria = 15 MUST obietnic
### 11g. Meta-challenge — czy razem spójne

## 12. Plan działania
- TOP 5 zmian
- TOP 5 brakujących funkcji
- TOP 5 nieciągłości
- Sekwencja implementacji (zależności)
- Mockupy ASCII dla minimum 6 nowych ekranów

## 13. Open questions (10+)
```

Długość docelowa: **80-120 stron markdown** (po rozszerzeniu o sekcje H-L). Nie skracać — każda sekcja ma konkretny zakres który był wskazany.

---

## 16. Red flags checklist — sprawdź PRZED zapisem dokumentu

- [ ] Czy każdy z 17 kroków workflow ma 16 wymiarów rozłożonych?
- [ ] Czy każdy element UI z mojej listy ma 10 wymiarów audytu?
- [ ] Czy każda nieciągłość ma 5 wymiarów + naprawę?
- [ ] Czy każdy z 8 mechanizmów interaktywności ma 14 wymiarów?
- [ ] Czy zrobiłem 264+ ratingów funkcjonalności (24 features × 11 testów)?
- [ ] Czy każda z 5 person ma scenariusz 20-30 kroków z dialogiem wewnętrznym + effort rating?
- [ ] Czy jest meta-analiza person (TOP 10 wspólnych frustracji)?
- [ ] Czy każda z 10 cech Forge ma konkretny guideline + przykład + anti-pattern?
- [ ] Czy wskazałem **konkretne** widgety / template paths / endpoint paths a nie ogólniki?
- [ ] Czy challenge'owałem każdą sugestię (kontrargumenty)?
- [ ] Czy NIE napisałem "intuicyjny", "user-friendly", "seamless"? (search dokumentu na te słowa, jeśli są — przepisz)
- [ ] Czy podałem mockupy ASCII dla minimum **6** nowych ekranów (landing, onboarding, upload+analyze, plan review, live operation, post-orchestrate)?
- [ ] Czy podzieliłem braki na UI / backend?
- [ ] Czy zaproponowałem priorytety (P0/P1/P2)?
- [ ] Czy uwzględniłem 5 deliverables UX agenta z poprzedniej sesji?
- [ ] Czy mam open questions (10+) wymagające user input?
- [ ] Czy persony są konkretne — mają imiona, background, dialogue, effort ratings — a nie abstract "user"?
- [ ] Czy dla każdej frustracji persony jest zaproponowany konkretny fix?
- [ ] Czy w Sekcji M każda z ~50 obietnic user ma **4 wymiary** (co chcę / dlaczego / jak dostarczyć / czy dobra czy zła)?
- [ ] Czy self-challenge w Sekcji M wskazuje **kiedy obietnica pogarsza** (nie tylko pluses)?
- [ ] Czy wybrałem TOP 3 per 5 kategorii = 15 MUST obietnic?
- [ ] Czy meta-challenge Sekcji M sprawdza konflikty między obietnicami?
- [ ] Czy wszystkie MUST obietnice są mierzalne (binarne tak/nie po 2 tygodniach)?

---

## 17. Tonalność

- Brutalnie szczery wobec **swojej własnej** dotychczasowej pracy. Każdy element istniejący jest podejrzany dopóki nie udowodnię że ma sens.
- Konkretne. Cytuj nazwy plików, ścieżki ekranów, nazwy buttonów. Nie "ten button" — `/ui/projects/{slug}/orchestrate POST`.
- Krytyka konstruktywna — każdy problem ma propozycję fix.
- Perspektywa nowego usera (NIE deweloperem Forge): "wchodzę pierwszy raz, widzę X, rozumiem Y/nie rozumiem Z".
- Bez sztucznego komplementowania ("dobra robota z auth"). Jeżeli auth UI jest niezrozumiałe — powiedz wprost.
- Polski, ale techniczne identifiery / nazwy plików / endpoints po angielsku.

---

## 18. Co MA NIE BYĆ w outputie

- Gotowy kod implementacyjny
- Lista technical debt niezwiązanego z UX (np. "Celery refactor")
- Marketing/sales arguments
- Porównanie z innymi narzędziami (Cursor itp.)
- Zachowawcze "może wartoby rozważyć" — albo proponuj albo nie
- Skróty / TL;DR dla sekcji rozłożenia (cała wartość jest w szczegółach)

---

## Zasada końcowa

Jeśli po napisaniu dokumentu czytam i nadal nie wiem co konkretnie zmienić — dokument jest do wyrzucenia. Każda sekcja musi pozostawić jasność: **co konkretnie**, **dlaczego**, **jak**.
