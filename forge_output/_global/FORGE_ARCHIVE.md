# Forge — Archiwum decyzji i wniosków

**Cel:** Historyczny reference. Zawiera dane, wnioski i polecenia z procesu projektowania Forge Platform. NIE jest dokumentem aktualnym — aktualny design jest w FORGE_ARCHITECTURE.md.

---

## 1. Twarde dane z ITRP (dowody na problemy)

- **AC evidence:** 7/77 tasków (9%) z dowodami weryfikacji
- **Changes reasoning:** 0/146 z reasoning_trace
- **Changes decision linkage:** 0/146 z decision_ids
- **Changes guidelines:** 0/146 z guidelines_checked
- **Copy-paste:** 75% zmian (109/146) identyczne opisy
- **Tool call baseline (t040):** 33-50% failure rate na create/update
- **Test coverage Forge:** 45% modułów bez testów, zero E2E
- **Changes C-001-C-005:** identyczne opisy dla 5 różnych plików
- **Reasoning traces:** `{"step": "auto-complete"}` — placeholder

---

## 2. Kaskady ryzyk

### Kaskada liniowa
```
Over-engineering → Solo dev overwhelm → Timeline explodes → Current system rots → Abandonment
```

### Kaskada kołowa (anti-gaming)
```
Gaming detected → Add rules → Complexity → More work → Rushed rules → False positives → Relax rules → Gaming returns
```

### Cobra Effects
1. Relaxing AC validation → easier gaming
2. Adding LLM reviewer → new dependency + its own gaming surface
3. CLI fallback for Claude Code → reduces pressure to fix HTTP API
4. Keeping JSON archive → two sources of truth confusion

---

## 3. Workflow gaps (V1 CLI → Platform)

| Workflow | Status w platformie |
|---|---|
| `/plan → /next → /complete` | COVERED |
| `/ingest` | PARTIAL — tabele OK, brak endpointu |
| `/analyze` | PARTIAL — tabele OK, brak endpointu |
| `/discover` | PARTIAL — decisions support, brak endpointu |
| `/change-request` | GAP |
| `/compound` | PARTIAL — tabela OK, brak workflow |
| `/onboard` | GAP |

### Fidelity Chain: 0/7 mechanizmów reimplementowanych
Mechanizmy ISTNIEJĄ w `pipeline_context.py` (Python) ale NIE SĄ reimplementowane w platformie.

### Pipeline Contracts C1-C7: 0 fully covered, 4 partial, 3 gaps

### Dane tracone przy migracji JSON → DB
- ac_templates (brak tabeli w v1 arch)
- draft_plan assumptions/coverage (brak storage)
- Decision exploration fields (options, open_questions, blockers)
- Knowledge tags, trust
- Task parallel flag, checkpoints

---

## 4. Challenge — TOP 5 problemów (z FORGE_CHALLENGE_RESULT)

1. **CRITICAL: Brak mechanizmu challenge/weryfikacji** → rozwiązane w sekcji 11 (meta-prompting, challenge commands)
2. **CRITICAL: Brak spec per feature** → do dodania (category: "feature-spec" w knowledge)
3. **HIGH: Monolityczne skills** → rozwiązane (micro_skills table)
4. **HIGH: 0/7 Fidelity Chain** → częściowo rozwiązane (do reimplementacji)
5. **HIGH: Operational contract optional** → rozwiązane (assumptions + impact_analysis REQUIRED)

---

## 5. Strategiczna decyzja: eksperyment przed architekturą

### 5 opcji z consequence tracing

| Opcja | Koszt | Ryzyko | Kiedy wybrać |
|---|---|---|---|
| A. Full Platform (37+ tabel) | 3-6 mies. | WYSOKIE | Gdy eksperyment (D) pokaże <30% poprawy |
| B. Incremental CLI | 1-2 tyg. | NISKIE | Gdy eksperyment (D) pokaże 60%+ poprawy |
| C. Hybrid (CLI + thin API) | 2-3 tyg. | ŚREDNIE | Gdy potrzebujesz widoczności bez full platform |
| D. Enforcement w promptach | 2-3 dni | MINIMALNE | ZAWSZE PIERWSZA — najtańszy test |
| E. SQLite zamiast JSON | 1 tyg. | ŚREDNIE | Gdy JSON jest bottleneck |

### Kluczowe pytanie (nadal aktualne)
> Dane ITRP (91% bez evidence) pochodzą z wersji systemu ZANIM dodano ceremony levels, AC validation, fidelity chain. Obecny system ma te mechanizmy ale NIKT NIE ZMIERZYŁ czy działają razem.

---

## 6. Essential objects (z Process Design)

```
KONIECZNE:
├── Requirement (K)        — bez nich nie wiadomo co budować
├── Task (T)               — bez nich nie wiadomo co robić
├── Acceptance Criteria     — bez nich nie wiadomo kiedy skończone
├── Instruction             — bez niej AI nie wie JAK
├── Guideline (G)          — bez nich każdy task robi po swojemu
├── Prompt (assembled)     — bez niego AI nie ma kontekstu
└── Change record (C)      — bez niego nie wiadomo co się zmieniło

WYSOCE WARTOŚCIOWE:
├── Objective (O) + KR, Decision (D), Finding (F)
├── Test Scenario (TS), Skill, Dependency/Produces
└── Spec per feature (DODANE po ITRP lessons)

OPCJONALNE:
├── Idea (I), Research (R), Lesson (L)
├── AC Template, Feature Registry
```

---

## 7. Wykonane polecenia (reference)

### FORGE_CHALLENGE_COMMAND (wykonane 2026-04-14)
6-częściowe polecenie challenge architektury. Wynik w sekcji 4 powyżej. Wnioski wchłonięte do architektury.

### FORGE_PROCESS_AND_UI_COMMAND (wykonane 2026-04-16)
Polecenie opisu pełnego procesu + design UI. Wynik w osobnych plikach (FORGE_PROCESS_FLOWS.md, FORGE_UI_DESIGN.md).

---

## 8. ITRP — co działa z AI (z LESSONS_LEARNED)

### Proces który działa:
```
User assigns → Agent plans → Agent implements → User verifies → User finds problem → Agent fixes → repeat
```

### Co poprawia jakość:
| Practice | Impact |
|----------|--------|
| Real data testing (BQ + Firestore) | High |
| Operational contract | High |
| User pushback ("stop pretending") | High |
| Spec per feature BEFORE code | High |
| Business acceptance criteria (Tuan's method) | High |
| Edge case tests (not happy path) | Medium |
| Project-specific skills | Medium |
| Rebuild + test BEFORE commit | Medium |

### Co pogarsza jakość:
| Anti-practice | Impact |
|---------------|--------|
| No spec for business logic | High |
| AI false completeness ("23/23 OK") | High |
| Over-planning low-risk tasks | Medium |
| Long conversations (context decay) | Medium |
| Generic skills without project context | Medium |
| Framework duplication | Low-Medium |

### Kluczowy wniosek:
> "The contract is necessary but not sufficient. The developer must still actively verify, challenge, and push back. The contract gives the developer specific things to check for. It does not replace the need to check."

W Forge rozwiązane przez: meta-prompting (Agent-A pisze challenge command → Agent-B weryfikuje → findings wracają do systemu). Challenge zastępuje manual pushback.
