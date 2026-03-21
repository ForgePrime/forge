# Forge — Kompletny Diagram Procesu

## 1. Przepływ Główny (High-Level)

```mermaid
flowchart TB
    subgraph PLANNING["FAZA 1: PLANOWANIE"]
        USER_GOAL["Użytkownik podaje CEL\n(/plan {goal})"]
        LLM_READS["LLM czyta specyfikację,\nkod źródłowy, dokumentację"]
        LLM_PRODUCES_TASKS["LLM generuje TASK GRAPH\n(JSON array z zadaniami)"]
        DRAFT["draft-plan\nwaliduje + bramki"]
        REVIEW["LLM/Użytkownik\nprzegląda DRAFT"]
        APPROVE["approve-plan\nmaterializuje zadania"]
    end

    subgraph EXECUTION["FAZA 2: WYKONANIE (pętla)"]
        NEXT["next / begin\nprzydziela zadanie"]
        CONTEXT["Budowanie KONTEKSTU\n(ContextAssembler)"]
        LLM_IMPL["LLM IMPLEMENTUJE\nkod, testy, zmiany"]
        COMPLETE["complete\nwalidacja + zamknięcie"]
    end

    subgraph PERSISTENCE["FAZA 3: PERSYSTENCJA"]
        TRACKER["tracker.json"]
        DECISIONS_F["decisions.json"]
        CHANGES_F["changes.json"]
        GUIDELINES_F["guidelines.json"]
        OBJECTIVES_F["objectives.json"]
        KNOWLEDGE_F["knowledge.json"]
    end

    USER_GOAL --> LLM_READS --> LLM_PRODUCES_TASKS --> DRAFT
    DRAFT -->|"PASS"| REVIEW --> APPROVE
    DRAFT -->|"FAIL: >=5 HIGH assumptions\nlub MISSING coverage"| LLM_READS
    APPROVE --> NEXT
    NEXT --> CONTEXT --> LLM_IMPL --> COMPLETE
    COMPLETE -->|"Następne zadanie"| NEXT
    COMPLETE -->|"Wszystko DONE"| DONE["Projekt zakończony"]

    APPROVE --> TRACKER
    COMPLETE --> TRACKER
    COMPLETE --> DECISIONS_F
    COMPLETE --> CHANGES_F
    COMPLETE --> OBJECTIVES_F
    CONTEXT -.->|"czyta"| TRACKER
    CONTEXT -.->|"czyta"| DECISIONS_F
    CONTEXT -.->|"czyta"| GUIDELINES_F
    CONTEXT -.->|"czyta"| KNOWLEDGE_F
    CONTEXT -.->|"czyta"| OBJECTIVES_F
    CONTEXT -.->|"czyta"| CHANGES_F
```

---

## 2. Co LLM Otrzymuje i Musi Dostarczyć na Każdym Etapie

```mermaid
flowchart LR
    subgraph INPUT_PLAN["CO LLM OTRZYMUJE\n(Planowanie)"]
        I1["Cel użytkownika (tekst)"]
        I2["Kod źródłowy projektu"]
        I3["Istniejące objectives/KR"]
        I4["Guidelines (ogólne)"]
        I5["Knowledge base"]
        I6["Ideas (pomysły)"]
    end

    subgraph OUTPUT_PLAN["CO LLM MUSI DOSTARCZYĆ\n(Planowanie)"]
        O1["JSON array zadań:\n- id, name, description\n- instruction\n- acceptance_criteria\n- depends_on\n- produces (kontrakt)\n- type (feature/bug/chore)\n- scopes"]
        O2["Assumptions:\n[{assumption, severity,\nbasis}]"]
        O3["Coverage:\n[{requirement, status,\nreason}]"]
    end

    INPUT_PLAN --> LLM_P["LLM\n(Planowanie)"]
    LLM_P --> OUTPUT_PLAN
```

```mermaid
flowchart LR
    subgraph INPUT_EXEC["CO LLM OTRZYMUJE\n(Wykonanie zadania)"]
        E1["Task detail:\nname, description,\ninstruction, AC, produces"]
        E2["Alignment contract:\ngoal, must/must_not"]
        E3["Exclusions (DO NOTs)"]
        E4["Guidelines MUST\n(zawsze, priorytet 1)"]
        E5["Guidelines SHOULD\n(jeśli mieści się w oknie)"]
        E6["Knowledge\n(explicit + scope-matched)"]
        E7["Dependency context:\nproduces + changes\nz ukończonych tasków"]
        E8["Decisions\n(OPEN, affecting)"]
        E9["Business context:\nObjective + KR progress"]
        E10["Active Risks"]
        E11["Plan staleness warnings"]
    end

    subgraph OUTPUT_EXEC["CO LLM MUSI DOSTARCZYĆ\n(Wykonanie)"]
        X1["Implementacja kodu"]
        X2["--reasoning\n(dlaczego tak zrobiono)"]
        X3["--ac-reasoning\n'AC 1: [kryterium] —\nPASS: [dowód]'"]
        X4["--deferred\n[{requirement, reason}]\n(opcjonalnie)"]
        X5["Przejście bramek\n(testy, lint)"]
    end

    INPUT_EXEC --> LLM_E["LLM\n(Wykonanie)"]
    LLM_E --> OUTPUT_EXEC
```

---

## 3. Szczegółowy Przepływ Danych: draft-plan

```mermaid
flowchart TB
    subgraph WEJŚCIE
        GOAL["Cel projektu"]
        TASKS_JSON["JSON z zadaniami\n(LLM wygenerował)"]
        ASSUMPTIONS["--assumptions\n[{assumption, severity, basis}]"]
        COVERAGE["--coverage\n[{requirement, status, reason}]"]
    end

    TASKS_JSON --> VALIDATE_CONTRACT["Walidacja kontraktu\n(wymagane pola, typy, enumy)"]
    VALIDATE_CONTRACT -->|"OK"| ASSUMPTIONS_GATE

    ASSUMPTIONS --> ASSUMPTIONS_GATE{"Bramka Assumptions\n>=5 HIGH?"}
    ASSUMPTIONS_GATE -->|">=5 HIGH\nFAIL"| REJECT["ODRZUCENIE\nLLM musi poprawić"]
    ASSUMPTIONS_GATE -->|"<5 HIGH\nPASS"| COVERAGE_GATE

    COVERAGE --> COVERAGE_GATE{"Bramka Coverage\njakieś MISSING?"}
    COVERAGE_GATE -->|"MISSING\nFAIL"| REJECT
    COVERAGE_GATE -->|"Wszystko COVERED/\nDEFERRED/OUT_OF_SCOPE"| SAVE_DRAFT

    SAVE_DRAFT["Zapis do tracker.json\ndraft_plan: {\n  tasks: [...],\n  assumptions: [...],\n  coverage: [...]\n}"]

    SAVE_DRAFT --> SHOW_LLM["Wyświetl LLM:\n- Tabela zadań (ID, name, deps)\n- Podsumowanie assumptions\n- Podsumowanie coverage\n- Ostrzeżenia referencji"]
```

---

## 4. Szczegółowy Przepływ: approve-plan

```mermaid
flowchart TB
    DRAFT_PLAN["tracker.json\ndraft_plan.tasks"] --> REMAP["Remap temp IDs\n_1,_2 → T-001,T-002"]
    REMAP --> DAG_CHECK{"Walidacja DAG\n(cykle?)"}
    DAG_CHECK -->|"Cykl znaleziony"| FAIL_DAG["FAIL: Circular dependency"]
    DAG_CHECK -->|"OK"| AC_CHECK{"Hard gate:\nfeature/bug\nma AC?"}
    AC_CHECK -->|"Brak AC"| FAIL_AC["FAIL: AC wymagane\ndla feature/bug"]
    AC_CHECK -->|"OK"| MATERIALIZE["Materializacja:\n- tasks → tracker.json['tasks']\n- draft_plan → null\n- plan_approved_at → timestamp\n- idea status → COMMITTED"]

    MATERIALIZE --> SHOW["Wyświetl LLM:\n- Mapowanie ID (_1→T-001)\n- Lista zmaterializowanych tasków\n- Potwierdzenie"]
```

---

## 5. Szczegółowy Przepływ: begin / next (Context Assembly)

```mermaid
flowchart TB
    NEXT_CMD["next {project}"] --> FIND_TASK{"Znajdź TODO task:\n1. Deps spełnione?\n2. Brak konfliktów?\n3. Brak blocking decisions?"}
    FIND_TASK -->|"Znaleziono"| CLAIM["Claim task\n(2-phase dla multi-agent)"]
    FIND_TASK -->|"Brak"| NO_TASK["Brak dostępnych tasków"]

    CLAIM --> SET_STATUS["status → IN_PROGRESS\nagent → {name}\nstarted_at → timestamp\nstarted_at_commit → git SHA"]

    SET_STATUS --> GIT_BRANCH["Git: utwórz branch\n(opcjonalnie worktree)"]

    GIT_BRANCH --> BUILD_CONTEXT["ContextAssembler\nbuduje kontekst"]

    subgraph CONTEXT_SECTIONS["Sekcje kontekstu (priorytet)"]
        direction TB
        P1_TASK["P1: Task content\n(name, desc, instruction, AC,\nscopes, produces, alignment,\nexclusions)\nNIGDY nie obcinane"]
        P1_MUST["P1: Guidelines MUST\nmax 10% okna\nNIGDY nie obcinane"]
        P2_KNOW_REQ["P2: Knowledge required\n(explicit knowledge_ids)\nmax 15%"]
        P3_KNOW_CTX["P3: Knowledge context\n(scope-matched, max 10)\nmax 10%, obcinalne"]
        P4_SHOULD["P4: Guidelines SHOULD\nmax 10%, obcinalne\nPominięte jeśli total > 80%"]
        P5_DEPS["P5: Dependency context\n(produces + changes z deps)\nmax 10%, obcinalne"]
        P6_RISKS["P6: Active risks\nmax 5%, obcinalne"]
        P7_BIZ["P7: Business context\n(Objective + KR progress)\nmax 5%, obcinalne"]
        P8_TESTS["P8: Test context\n(test/lint commands, gates)\nmax 5%, obcinalne"]

        P1_TASK --> P1_MUST --> P2_KNOW_REQ --> P3_KNOW_CTX
        P3_KNOW_CTX --> P4_SHOULD --> P5_DEPS --> P6_RISKS --> P7_BIZ --> P8_TESTS
    end

    BUILD_CONTEXT --> CONTEXT_SECTIONS

    CONTEXT_SECTIONS --> TOKEN_BUDGET["Token Budget:\n- 25% zarezerwowane na output\n- Per-section max_pct caps\n- Overflow: usuń najniższy priorytet"]

    TOKEN_BUDGET --> DELIVER["Dostarcz do LLM:\nMarkdown z wszystkimi sekcjami"]
```

---

## 6. Skąd Pochodzą Dane Kontekstu

```mermaid
flowchart LR
    subgraph ŹRÓDŁA["PLIKI ŹRÓDŁOWE"]
        TR["tracker.json\n(tasks, deps, produces,\nAC, scopes, alignment)"]
        DE["decisions.json\n(OPEN decisions,\naffects, blocked_by)"]
        GU["guidelines.json\n(scope, weight,\ncontent, rationale)"]
        KN["knowledge.json\n(domain knowledge,\nscope-matched)"]
        OB["objectives.json\n(KR progress,\nbusiness goals)"]
        CH["changes.json\n(file changes\nz dependency tasków)"]
        RE["research.json\n(exploration findings)"]
        LE["lessons.json\n(post-mortems)"]
        GL["_global/guidelines.json\n(cross-project standards)"]
    end

    subgraph FILTROWANIE["FILTROWANIE"]
        SCOPE_F["Filtr SCOPE\n(task.scopes +\n'general' always)"]
        WEIGHT_F["Filtr WEIGHT\nmust vs should vs may"]
        PRIORITY_F["Filtr PRIORITY\n1=critical → 8=nice-to-have"]
        DEP_F["Filtr DEPENDENCIES\n(tylko completed deps)"]
        STATUS_F["Filtr STATUS\n(ACTIVE guidelines,\nOPEN decisions,\nactive risks)"]
    end

    subgraph ODBIORCA["ODBIORCA: LLM"]
        CTX["Sformatowany\nMarkdown kontekst\nz sekcjami priorytetowymi"]
    end

    TR --> DEP_F --> CTX
    DE --> STATUS_F --> CTX
    GU --> SCOPE_F --> WEIGHT_F --> CTX
    GL --> SCOPE_F
    KN --> SCOPE_F --> PRIORITY_F --> CTX
    OB --> CTX
    CH --> DEP_F --> CTX
    RE --> CTX
    LE --> CTX
```

---

## 7. Przepływ complete — Walidacja i Zamknięcie

```mermaid
flowchart TB
    COMPLETE_CMD["complete {project} {task_id}\n--reasoning '...'\n--ac-reasoning '...'\n--deferred '[...]'"]

    COMPLETE_CMD --> CEREMONY["Określ CEREMONY LEVEL"]

    subgraph CEREMONY_RULES["Ceremony Level"]
        MINIMAL["MINIMAL\nchore/investigation\nBrak wymagań"]
        LIGHT["LIGHT\nbug, <=3 pliki\nWymagane: reasoning"]
        STANDARD["STANDARD\nfeature, <=3 AC\nWymagane: reasoning +\nAC reasoning"]
        FULL["FULL\nwszystko inne\nWymagane: reasoning +\nAC reasoning +\nchanges"]
    end

    CEREMONY --> CEREMONY_RULES

    CEREMONY_RULES --> VALIDATE

    subgraph VALIDATE["WALIDACJA (blokująca)"]
        V1["1. Blocking decisions\n(OPEN → FAIL)"]
        V2["2. Reasoning\n(wymagane jeśli !=MINIMAL)"]
        V3["3. Changes recorded\n(wymagane dla STANDARD/FULL)"]
        V4["4. Gates enforcement\n(required gates muszą PASS)"]
        V5["5. Mechanical AC\n(pytest / command → ZAWSZE blokuje)"]
        V6["6. Manual AC reasoning\n(>=50 znaków, format:\n'AC N: [kryterium] — PASS: [dowód]')"]
        V1 --> V2 --> V3 --> V4 --> V5 --> V6
    end

    VALIDATE -->|"Wszystko PASS"| FINALIZE

    subgraph FINALIZE["FINALIZACJA"]
        F1["status → DONE\ncompleted_at → timestamp\nceremony_level → X"]
        F2["Auto-record changes\n(git diff → changes.json)"]
        F3["Auto-update KR\n(descriptive: NOT_STARTED →\nIN_PROGRESS → ACHIEVED)"]
        F4["Deferred → OPEN decisions\n(decisions.json)"]
        F5["Git: push, PR, clean worktree"]
    end

    FINALIZE --> F1 & F2 & F3 & F4 & F5
```

---

## 8. Przepływ AC (Acceptance Criteria)

```mermaid
flowchart TB
    subgraph DEFINIOWANIE["DEFINIOWANIE AC (Planning)"]
        PLAIN["Plain string\n'API returns 200'\n→ manual verification"]
        STRUCTURED["Structured:\n{text, verification: 'test',\ntest_path: 'tests/auth.test.ts'}"]
        TEMPLATE["AC Template\n(ac_templates.json)\n→ pre-built AC sets"]

        TEMPLATE -->|"from_template"| STRUCTURED
    end

    subgraph TRANSPORT["TRANSPORT"]
        DRAFT_T["draft-plan\n→ walidacja: feature/bug\nMUSI mieć AC"]
        APPROVE_T["approve-plan\n→ hard gate: brak AC = FAIL"]
        BEGIN_T["begin/context\n→ AC wyświetlone LLM\nz [test] [command] [manual]"]
    end

    subgraph WERYFIKACJA["WERYFIKACJA (complete)"]
        MECH["Mechanical AC\n(verification: test/command)"]
        MECH_RUN["Uruchom pytest/command\nZbierz stdout/stderr"]
        MECH_RESULT{"Wynik?"}
        MECH_PASS["PASS\n→ zapisz w ac_verification_results"]
        MECH_FAIL["FAIL\n→ BLOKUJE complete\n(zawsze, niezależnie od ceremony)"]

        MANUAL["Manual AC\n(verification: manual / plain string)"]
        MANUAL_CHECK["Sprawdź --ac-reasoning:\n- >= 50 znaków\n- Format: AC N: ... — PASS: ..."]
        MANUAL_RESULT{"Wynik?"}
        MANUAL_PASS["PASS"]
        MANUAL_FAIL["FAIL\n→ BLOKUJE (STANDARD/FULL)"]
    end

    PLAIN --> DRAFT_T
    STRUCTURED --> DRAFT_T
    DRAFT_T --> APPROVE_T --> BEGIN_T

    BEGIN_T --> MECH & MANUAL
    MECH --> MECH_RUN --> MECH_RESULT
    MECH_RESULT -->|"OK"| MECH_PASS
    MECH_RESULT -->|"FAIL"| MECH_FAIL

    MANUAL --> MANUAL_CHECK --> MANUAL_RESULT
    MANUAL_RESULT -->|"OK"| MANUAL_PASS
    MANUAL_RESULT -->|"FAIL"| MANUAL_FAIL
```

---

## 9. Przepływ Guidelines

```mermaid
flowchart TB
    subgraph ŹRÓDŁA_G["ŹRÓDŁA GUIDELINES"]
        PROJ_G["guidelines.json\n(projektowe)"]
        GLOBAL_G["_global/guidelines.json\n(cross-project)"]
        OBJ_G["objectives.json\n→ derived_guidelines\n(wygenerowane z objective)"]
    end

    subgraph FILTR["FILTROWANIE"]
        SCOPE["1. Filtr SCOPE\ntask.scopes + 'general'\n+ inherited z objective/idea"]
        STATUS["2. Filtr STATUS\ntylko ACTIVE"]
        WEIGHT["3. Podział WEIGHT"]
    end

    subgraph DOSTARCZENIE["DOSTARCZENIE DO LLM"]
        MUST_G["MUST weight\nPriorytet 1\nmax 10% okna\nNIGDY nie obcinane\nZAWSZE widoczne"]
        SHOULD_G["SHOULD weight\nPriorytet 4\nmax 10% okna\nObcinalne\nPominięte jeśli total > 80%"]
        MAY_G["MAY weight\nNie ładowane domyślnie\nTylko na żądanie"]
    end

    PROJ_G & GLOBAL_G & OBJ_G --> SCOPE --> STATUS --> WEIGHT
    WEIGHT --> MUST_G & SHOULD_G & MAY_G
```

---

## 10. Przepływ Objectives / KR → Tasks

```mermaid
flowchart TB
    OBJ["Objective (O-001)\ntitle, status: ACTIVE\nscopes: [backend, perf]"]
    KR_NUM["KR numeryczny\nmetric: 'p95 ms'\nbaseline: 850, target: 200\ncurrent: 500"]
    KR_DESC["KR opisowy\ndescription: 'All endpoints documented'\nstatus: NOT_STARTED"]

    OBJ --> KR_NUM & KR_DESC

    subgraph FLOW_TO_TASKS["Przepływ do zadań"]
        IDEA["Idea (I-001)\n→ origin: O-001\n→ dziedziczy scopes"]
        TASK["Task (T-001)\n→ origin: I-001 / O-001\n→ dziedziczy scopes\n→ dziedziczy knowledge_ids"]
    end

    OBJ -->|"derived_guidelines"| GUIDELINES_GEN["Guidelines\nwygenerowane z objective"]
    OBJ --> IDEA --> TASK

    subgraph AUTO_UPDATE["AUTO-UPDATE przy complete"]
        FIRST_DONE["Pierwszy task DONE\n→ KR opisowy:\nNOT_STARTED → IN_PROGRESS"]
        ALL_DONE["Wszystkie taski DONE\n→ KR opisowy:\nIN_PROGRESS → ACHIEVED"]
        NUMERIC_MANUAL["KR numeryczny:\nwymaga ręcznej aktualizacji\n(current value)"]
    end

    TASK -->|"complete"| AUTO_UPDATE

    subgraph BIZ_CONTEXT["Business Context → LLM"]
        CTX_OBJ["Objective title + status"]
        CTX_KR["KR progress\n(% dla numerycznych,\nstatus dla opisowych)"]
    end

    OBJ --> CTX_OBJ
    KR_NUM & KR_DESC --> CTX_KR
    CTX_OBJ & CTX_KR -->|"Priorytet 7\nmax 5% okna"| LLM_BIZ["LLM widzi\nbusiness context"]
```

---

## 11. Przepływ Decisions

```mermaid
flowchart TB
    subgraph TWORZENIE["TWORZENIE DECISIONS"]
        MANUAL_D["Ręcznie przez LLM\n(decisions add)\nGdy: konflikt, wybór,\nniepewność"]
        DEFERRED_D["Auto z --deferred\n(complete --deferred)\nGdy: wymaganie odroczone\ndo przyszłego tasku"]
        CONFLICT_D["Gdy LLM znajduje konflikt\n→ OPEN decision\nz oboma stronami"]
    end

    subgraph STATUS_D["STATUSY"]
        OPEN_D["OPEN\n→ blokuje taski\njeśli w blocked_by_decisions"]
        CLOSED_D["CLOSED\n→ rozwiązane"]
        DEFERRED_S["DEFERRED\n→ przyszła decyzja"]
        ANALYZING_D["ANALYZING\n→ w trakcie badania"]
    end

    subgraph WPŁYW["WPŁYW NA PIPELINE"]
        BLOCK["blocked_by_decisions:\ntask NIE MOŻE ruszyć\ndopóki OPEN"]
        AFFECTS["affects: [T-003, T-005]\n→ wyświetlone w kontekście\ntych tasków"]
        CONTEXT_D["Sekcja 'Decisions'\nw kontekście LLM\n→ LLM wie o otwartych\ndecyzjach"]
    end

    MANUAL_D & DEFERRED_D & CONFLICT_D --> OPEN_D
    OPEN_D --> BLOCK & AFFECTS & CONTEXT_D
    OPEN_D -->|"resolve"| CLOSED_D
```

---

## 12. Przepływ Gates

```mermaid
flowchart TB
    subgraph CONFIG_G["KONFIGURACJA"]
        GATE_DEF["gates config:\n{name: 'test',\ncommand: 'pytest',\nrequired: true}"]
        GATE_STORE["tracker.json['gates']"]
    end

    GATE_DEF --> GATE_STORE

    subgraph EXECUTION_G["WYKONANIE (przy complete)"]
        AUTO_RUN["Auto-run gates\njeśli brak gate_results\nna tasku"]
        RUN_CMD["Uruchom shell command\n(pytest, eslint, etc.)"]
        CAPTURE["Zbierz stdout/stderr\n(max 500 znaków)"]
    end

    GATE_STORE --> AUTO_RUN --> RUN_CMD --> CAPTURE

    subgraph ENFORCEMENT["ENFORCEMENT"]
        REQ_GATE{"Required gate?"}
        REQ_PASS["PASS → kontynuuj"]
        REQ_FAIL["FAIL → BLOKUJE complete\n(exit 1)"]
        ADV_GATE["Advisory gate\nFAIL → warning only"]
        FORCE{"--force?"}
        FORCE_CHECK{"Task type?"}
        FORCE_OK["chore/investigation\n→ force dozwolone"]
        FORCE_NO["feature/bug\n→ force ZABRONIONE"]
    end

    CAPTURE --> REQ_GATE
    REQ_GATE -->|"required=true"| REQ_PASS & REQ_FAIL
    REQ_GATE -->|"required=false"| ADV_GATE
    REQ_FAIL --> FORCE --> FORCE_CHECK
    FORCE_CHECK --> FORCE_OK & FORCE_NO
```

---

## 13. Pełna Mapa: Co Skąd Trafia Do LLM

```mermaid
flowchart TB
    subgraph USER["UŻYTKOWNIK"]
        U_GOAL["Cel / specyfikacja"]
        U_FEEDBACK["Feedback / korekty"]
        U_APPROVE["Approve / reject"]
    end

    subgraph FILES["PLIKI FORGE (forge_output/)"]
        F_TRACKER["tracker.json"]
        F_DECISIONS["decisions.json"]
        F_CHANGES["changes.json"]
        F_GUIDELINES["guidelines.json"]
        F_OBJECTIVES["objectives.json"]
        F_KNOWLEDGE["knowledge.json"]
        F_RESEARCH["research.json"]
        F_LESSONS["lessons.json"]
        F_AC_TEMPL["ac_templates.json"]
        F_GLOBAL["_global/guidelines.json"]
    end

    subgraph GIT["GIT"]
        G_DIFF["git diff\n(changed files)"]
        G_SHA["git rev-parse HEAD\n(commit SHA)"]
        G_BRANCH["branch management"]
    end

    subgraph PIPELINE["PIPELINE (core/pipeline.py)"]
        CMD_DRAFT["draft-plan"]
        CMD_APPROVE["approve-plan"]
        CMD_NEXT["next"]
        CMD_BEGIN["begin"]
        CMD_CONTEXT["context\n(ContextAssembler)"]
        CMD_COMPLETE["complete"]
    end

    subgraph LLM["LLM (Claude)"]
        LLM_PLAN["Planuje:\n→ Task JSON + deps\n→ Assumptions\n→ Coverage"]
        LLM_EXEC["Wykonuje:\n→ Kod źródłowy\n→ Testy\n→ Reasoning\n→ AC reasoning\n→ Deferred items"]
        LLM_DECIDE["Decyduje:\n→ Decisions (konflikty)\n→ Changes (opis zmian)\n→ Korekty planu"]
    end

    %% User → Pipeline
    U_GOAL -->|"/plan"| CMD_DRAFT
    U_FEEDBACK -->|"iteracja"| CMD_DRAFT
    U_APPROVE -->|"/approve"| CMD_APPROVE

    %% Files → Context
    F_TRACKER -->|"tasks, deps,\nproduces, AC"| CMD_CONTEXT
    F_DECISIONS -->|"OPEN decisions,\naffects"| CMD_CONTEXT
    F_GUIDELINES -->|"scope-filtered,\nMUST/SHOULD"| CMD_CONTEXT
    F_GLOBAL -->|"cross-project\nstandards"| CMD_CONTEXT
    F_KNOWLEDGE -->|"explicit +\nscope-matched"| CMD_CONTEXT
    F_OBJECTIVES -->|"KR progress,\nbusiness goals"| CMD_CONTEXT
    F_CHANGES -->|"dependency\nchanges"| CMD_CONTEXT
    F_RESEARCH -->|"exploration\nfindings"| CMD_CONTEXT
    F_LESSONS -->|"past lessons"| CMD_CONTEXT
    F_AC_TEMPL -->|"AC templates"| CMD_DRAFT

    %% Pipeline → LLM
    CMD_DRAFT -->|"draft summary,\ntask table,\nassumptions,\ncoverage"| LLM_PLAN
    CMD_CONTEXT -->|"priorytetowy\nMarkdown kontekst"| LLM_EXEC
    CMD_COMPLETE -->|"gate results,\nAC verification,\nceremony level"| LLM_EXEC

    %% LLM → Pipeline
    LLM_PLAN -->|"task JSON"| CMD_DRAFT
    LLM_EXEC -->|"--reasoning\n--ac-reasoning\n--deferred"| CMD_COMPLETE
    LLM_DECIDE -->|"decisions add"| F_DECISIONS
    LLM_DECIDE -->|"changes record"| F_CHANGES

    %% Pipeline → Files
    CMD_APPROVE -->|"materialize tasks"| F_TRACKER
    CMD_COMPLETE -->|"status=DONE"| F_TRACKER
    CMD_COMPLETE -->|"auto-record"| F_CHANGES
    CMD_COMPLETE -->|"deferred→OPEN"| F_DECISIONS
    CMD_COMPLETE -->|"KR auto-update"| F_OBJECTIVES

    %% Git
    G_DIFF -->|"changed files"| CMD_COMPLETE
    G_SHA -->|"started_at_commit"| CMD_NEXT
    CMD_NEXT -->|"create branch"| G_BRANCH
    CMD_COMPLETE -->|"push, PR"| G_BRANCH
```

---

## 14. Token Budget — Jak ContextAssembler Zarządza Oknem

```
┌──────────────────────────────────────────────────────────┐
│                    CONTEXT WINDOW (100%)                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │         AVAILABLE FOR INPUT (75%)                │     │
│  │                                                  │     │
│  │  P1: Task content          [max 30%] PROTECTED  │     │
│  │  P1: MUST guidelines       [max 10%] PROTECTED  │     │
│  │  P2: Required knowledge    [max 15%]            │     │
│  │  P3: Context knowledge     [max 10%] obcinalne  │     │
│  │  P4: SHOULD guidelines     [max 10%] obcinalne  │     │
│  │  P5: Dependency context    [max 10%] obcinalne  │     │
│  │  P6: Active risks          [max  5%] obcinalne  │     │
│  │  P7: Business context      [max  5%] obcinalne  │     │
│  │  P8: Test context          [max  5%] obcinalne  │     │
│  │                                                  │     │
│  │  Overflow → usuń od P8 w górę                   │     │
│  │  SHOULD pominięte jeśli total > 80%             │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
│  ┌─────────────────────────────────────────────────┐     │
│  │         RESERVED FOR OUTPUT (25%)                │     │
│  │         (LLM response space)                     │     │
│  └─────────────────────────────────────────────────┘     │
│                                                          │
└──────────────────────────────────────────────────────────┘

Estymacja tokenów: chars / 4 (heurystyka bez tokenizera)
```

---

## 15. Tabela Podsumowująca: Etap → Wejście → LLM Action → Wyjście

| Etap | Co LLM otrzymuje | Co LLM musi zrobić | Co LLM musi dostarczyć | Gdzie trafia wynik |
|------|---|---|---|---|
| **`/plan`** | Cel użytkownika, kod, objectives, knowledge | Zaprojektować graf zadań | JSON array: tasks z AC, deps, produces, scopes + assumptions + coverage | `draft-plan` → `tracker.json[draft_plan]` |
| **`draft-plan` review** | Tabela tasków, podsumowanie assumptions/coverage, ostrzeżenia | Przejrzeć, skorygować | Poprawiony JSON lub potwierdzenie | `approve-plan` → `tracker.json[tasks]` |
| **`begin`** | Task detail + pełny kontekst (guidelines, knowledge, deps, risks, business) | Zrozumieć zadanie, ograniczenia, kontrakty | — (przejście do implementacji) | — |
| **Implementacja** | Kontekst z begin + kod źródłowy | Napisać kod, testy, spełnić AC | Pliki kodu, testy | Git (working tree) |
| **`complete`** | Ceremony level, gate results, AC verification | Podsumować pracę, udowodnić AC | `--reasoning`, `--ac-reasoning`, `--deferred` | `tracker.json`, `changes.json`, `decisions.json`, `objectives.json` |
| **Decisions** | Konflikt lub niepewność | Opisać obie strony, zaproponować | Decision JSON (type, options, recommendation) | `decisions.json` |
| **Changes** | Git diff | Opisać co i dlaczego zmieniono | Change records (auto z git) | `changes.json` |

---

## Legenda

- **P1–P8** — priorytety sekcji kontekstu (1 = najwyższy, nigdy nie obcinany)
- **MUST/SHOULD/MAY** — wagi guidelines (MUST = obowiązkowe, SHOULD = zalecane, MAY = opcjonalne)
- **Ceremony** — poziom formalności completion (MINIMAL < LIGHT < STANDARD < FULL)
- **Gate** — mechaniczny test (command) uruchamiany przy complete
- **AC** — Acceptance Criteria (kryteria akceptacji zadania)
- **KR** — Key Result (mierzalny wynik powiązany z Objective)
- **Produces** — kontrakt semantyczny: co task dostarcza downstream tasków
