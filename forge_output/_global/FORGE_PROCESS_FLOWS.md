# Forge — Pełny opis procesu

**Status:** Wygenerowany przez agenta na podstawie FORGE_PROCESS_AND_UI_COMMAND.md
**Źródła:** BUSINESS_SPEC, ARCHITECTURE, PROCESS_DESIGN, VS_ITRP_REALITY, LESSONS_LEARNED, CHALLENGE_RESULT, TEST_SCENARIOS

**Uwaga:** Ten dokument zawiera pełny opis procesu z diagramami, API calls, error flows. Jest obszerny (~2000 linii w surowej formie). Poniżej kluczowe elementy per krok. Pełny opis jest w FORGE_ARCHITECTURE.md sekcje 2, 7, 11.

---

## Podsumowanie kroków

| # | Krok | Aktorzy | Wejście | Wyjście | Gate |
|---|------|---------|---------|---------|------|
| 1 | Inicjacja | User | Dokumenty biznesowe | K-NNN (source-document) | — |
| 2 | Ekstrakcja | Agent-A→Parser→Agent-B | K-NNN source docs | K-NNN facts, D-NNN conflicts | C1 |
| 3 | Specyfikacja | Agent-A→Parser→Agent-B | K requirements | K-NNN feature-spec | Spec complete |
| 4 | Analiza | Agent-A→Parser→Agent-B | K requirements, specs | O-NNN + KR | C2 |
| 5 | Planowanie | Agent-A→Parser→Agent-B | O-NNN, specs, guidelines | T-NNN + AC + TS | C3-C4 |
| 6 | Implementacja | Agent-A→Parser→Agent-B | T-NNN + prompt | Delivery (code + evidence) | Contract |
| 7 | Challenge | Agent-A→Parser→Agent-B(INNY) | Delivery + spec | Challenge findings | — |
| 8 | Walidacja | Forge API | Delivery + challenge | ACCEPTED/REJECTED | Contract + gates |
| 9 | Zmiany | User + Agent | Changed requirements | Updated plan | Impact assessment |
| 10 | Learning | Agent + User | Project history | L-NNN → G-NNN | — |
| 11 | Ciągła pętla | System | Completed objectives | Next objective or done | C7 |

---

## Per-krok: flow + API + error

### Krok 1: INICJACJA

**Flow:** User dostarcza dokumenty → `POST /api/v1/projects/{slug}/knowledge` (category=source-document) → system rejestruje.

**API:** `POST /knowledge` z `{title, category: "source-document", content, scopes}`

**Error:** Dokument pusty → 422. Brak projektu → "Create project first." User od razu /plan bez /ingest → Gate C1 blocks.

---

### Krok 2: EKSTRAKCJA

**Flow:**
1. Agent-A pisze polecenie: "Wyekstrahuj atomowe fakty z K-001, rozbij compound, znajdź sprzeczności, pokryj 9 kategorii"
2. Prompt Parser dodaje: reputation "analyst", micro-skill "requirements precision", micro-skill "edge-case-explorer", kontrakt operacyjny
3. Agent-B ekstrakcja → K-002..K-025 (facts), D-001..D-003 (conflicts)
4. Gate C1: ≥2 facts/doc, 9 kategorii pokryte

**API:**
- `POST /knowledge` (batch facts)
- `POST /decisions` (conflicts, assumptions)
- `GET /status` (gate C1 check)

**Error:** <2 facts/doc → C1 FAIL. Placeholder "TBD" → content <30 chars → FAIL. Missing category → C1 FAIL.

---

### Krok 3: SPECYFIKACJA (spec per feature)

**Flow:**
1. Agent-A pisze polecenie: "Napisz spec dla feature X z input/output/formulas/edge_cases/acceptance"
2. Prompt Parser dodaje: reputation "analyst", requirements K-NNN, guidelines MUST
3. Agent-B → spec jako K-NNN (category: "feature-spec")

**API:** `POST /knowledge` z `{category: "feature-spec", content: structured JSON}`

**Error:** Spec bez edge_cases → WARNING. Spec z ogólnikową formułą → content <30 chars → FAIL.

**Ujawnione założenie:** Knowledge entity nie ma statusu DRAFT/REVIEWED/APPROVED. Feature-spec wymaga workflow approval — potrzebne rozszerzenie lub osobna encja.

---

### Krok 4: ANALIZA

**Flow:**
1. Resolve OPEN decisions (user/AI)
2. Agent-A pisze polecenie: "Pogrupuj requirements w objectives biznesowe z measurable KR"
3. Agent-B → O-001..O-003 z KR

**API:** `POST /objectives`, `POST /knowledge/link` (K→O)

**Gate C2:** ≥1 ACTIVE O, all KR measured, no orphaned K.

---

### Krok 5: PLANOWANIE

**Flow:**
1. Agent-A pisze polecenie: "Stwórz plan z AC derived FROM spec, cold-start test, dependency contracts"
2. Prompt Parser dodaje: reputation "architect", micro-skill "ac-from-spec", specs, guidelines
3. Agent-B → draft plan z tasks + AC + assumptions + coverage
4. fn_validate_ac_quality: ≥3 AC feature, ≥1 negative, ≥1 test
5. User approves → materializacja T-NNN + auto-generated TS-NNN

**API:** `POST /plans/draft`, `POST /plans/{id}/approve`

**Gates C3-C4:** AC quality, DAG acyclic, coverage complete, origin valid, <5 HIGH assumptions.

---

### Krok 6: IMPLEMENTACJA

**Flow:**
1. Agent-A pisze polecenie implementacji z kontekstem (spec, guidelines, agent memory mistakes, impact warnings)
2. Prompt Parser dodaje: reputation "developer", micro-skills, MUST guidelines, knowledge, deps, risks, agent memory, test scenarios, kontrakt operacyjny
3. MCP Server zarządza heartbeat (background, co 10 min)
4. Agent-B implementuje, nagrywa decisions/findings mid-execution
5. Agent-B oddaje delivery (13 sekcji + operational contract)

**API:** `GET /execute`, `POST /heartbeat`, `POST /decisions`, `POST /findings`, `POST /deliver`

**Error:** Lease expires → EXPIRED → task TODO. Max 5 attempts → FAILED. P1 overflow → 422.

---

### Krok 7: CHALLENGE

**Flow:**
1. Auto-trigger (FULL ceremony) lub manual (operator)
2. Agent-A pisze polecenie challenge: "Zweryfikuj KAŻDE twierdzenie delivery T-005" z konkretnymi claims do sprawdzenia
3. Prompt Parser dodaje: reputation "challenger", micro-skills "code-vs-declaration" + "assumption-destroyer", spec edge cases, agent memory mistakes
4. Agent-B (INNY niż implementer) challenge'uje — czyta KOD nie deklaracje
5. Findings → Forge API

**API:** `POST /executions/{id}/challenge`, `POST /commands/{id}/execute-result`

**Error:** Challenger pisze "all looks good" → contract rejects filler. Challenge timeout → EXPIRED.

**Ujawnione założenie:** Challenge endpoint NIE ISTNIEJE w MVP (12 tabel). To jest KRYTYCZNY brak — BUSINESS_SPEC wymaga 100% challenge coverage.

---

### Krok 8: WALIDACJA I COMPLETION

**Flow:** fn_validate_delivery: reasoning + AC evidence + scenarios + anti-patterns + operational contract sections. ACCEPTED → DONE + KR update + feature registry. REJECTED → attempt recorded, lease extended.

**API:** Internal (triggered by POST /deliver).

---

### Krok 9: ZMIANY W TRAKCIE

**Flow:** User sygnalizuje zmianę → impact assessment → adjust plan (minor/moderate/major/breaking).

**Ujawnione założenie:** Brak dedykowanego `/change-request` endpoint. System wymaga kilku sequential API calls.

---

### Krok 10: LEARNING

**Flow:** `/compound` → Agent analizuje historię → L-NNN lessons → promote critical → G-NNN guidelines.

---

### Krok 11: CIĄGŁA PĘTLA

```
/ingest → /analyze → /plan → /run → /complete
                       ^        |
                       |   /change-request
                       |   /finding → triage
                       +--------+
```

---

## Ujawnione założenia i pominięcia

1. **Feature-spec entity** — knowledge.category="feature-spec" ale brak DRAFT/APPROVED workflow
2. **Challenge endpoint** — opisany w architekturze ale NIE w MVP
3. **Change-request endpoint** — brak dedykowanego endpointu
4. **Agent memory** — Tier 2, nie MVP
5. **Micro-skills table** — Tier 2, nie MVP
6. **Reputation framing** — wymaga micro_skills, nie w MVP
7. **Trust calibration** — Tier 2/3
8. **Real data testing** — brak mechanizmu w gates
9. **Meta-prompting model** — nowy, obecny CLI nie wspiera
10. **Web UI primary vs Claude Code** — Claude Code = aktywny, Web UI = pasywny
