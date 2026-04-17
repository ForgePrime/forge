# Forge — Wynik symulacji end-to-end

**Scenariusz:** Moduł email notifications dla ITRP (5 tasków + change request + finding + challenge)
**Wykonał:** Agent symulujący rolę użytkownika i AI jednocześnie
**Przesłuchanie:** Agent przesłuchany po naruszeniach kontraktu operacyjnego — wyznania poniżej

---

## Kluczowe odkrycia

### Co DZIAŁA (potwierdzone symulacją)

1. **Ekstrakcja łapie sprzeczności.** "Send immediately" vs "don't spam" — system stworzył OPEN decision. Reputation frame "analyst" + micro-skill "requirements precision" zadziałały.

2. **AC derived from spec produkuje testowalne kryteria.** Spec edge case EC3 (100+ events → paginate, max 50 rows) → AC w T-003 (75 events → 2 notifications). Bezpośrednia traceability business rule → test.

3. **Challenge łapie mock-over-real.** Challenger z micro-skill "code-vs-declaration" przeczytał KOD testu i znalazł `mock.patch` na timer zamiast clock injection. To jest dokładnie "ale uruchamiałeś testy?" zautomatyzowane.

4. **Kontrakt operacyjny podnosi floor.** T-002 rejected za short reasoning (76 < 100 chars). Resubmit zawierał WHY (smtplib bo D-003, retry bo D-004) — nie padding.

5. **Finding discovery nie blokuje pracy.** F-001 (pool.py reconnect) odkryty podczas T-001, zapisany, user dostał notification, AI kontynuowała.

6. **Change request impact assessment wykrywa DONE taski.** Zmiana (Slack + email) → T-001 (DONE) flagowany: NotificationEvent.recipient_email jest email-specific.

### Co NIE DZIAŁA (problemy z symulacji)

1. **Challenge jest Tier 2 ale core value proposition.** Business spec mówi "100% challenge coverage." MVP ma 0%. Najważniejsza feature jest nieobecna na launch.

2. **Agent-A quality nie jest walidowana.** Meta-prompting zakłada że Agent-A pisze dobre polecenia. Brak mechanizmu wykrywania złych poleceń. Jeśli Agent-A napisze "implement caching" → Prompt Parser doda polish ale nie naprawi fundamentalnego braku.

3. **Challenge ma strukturalne blind spots.** Łapie CODE claims (mock vs real test). NIE łapie: business validation (czy Tuan dostaje to czego chce), operational (czy działa po deploy), security (email injection).

4. **Brak instruction quality gate.** Vague instruction "Add notifications" przechodzi planning gates. Cold-start test opisany ale nie zaimplementowany.

5. **Ceremony overhead dla prostych tasków.** "Fix typo in email subject" wymaga: plan z AC + coverage + delivery + validation. Brak quick-fix path.

### Co BRAKUJE (gaps)

1. **Document upload endpoint** — API przyjmuje tekst, nie pliki (DOCX, PDF)
2. **Spec approval workflow** — knowledge nie ma DRAFT/APPROVED statusu
3. **Stop execution button** — brak abortu, czekaj 30 min na lease expiry
4. **Guideline per-project override** — "not applicable" dla irrelevant guidelines
5. **Agent-A command review** — user nie widzi/nie edytuje polecenia przed execution
6. **Change-request endpoint** — wymaga wielu sequential API calls
7. **Instruction quality gate** — fn_validate_instruction nie istnieje

### Niespójności w przepływie danych

1. **Spec → Planning:** Agent-A musi WIEDZIEĆ żeby reference spec K-012..K-014. Brak enforcement.
2. **Change-request → Dependencies:** Nowe taski nie auto-linkują do istniejących. Manual.
3. **Challenge → Remediation:** Nowy task z findingu nie ma kontekstu oryginalnej delivery.
4. **Rejection → Fix:** fix_instructions generic ("add more detail"), nie task-specific.

---

## Deep-Verify: REJECT (6.3)

| Claim | Verdict |
|-------|---------|
| Meta-prompting > fixed prompt | PARTIALLY CONFIRMED (enrichment wartościowe, Agent-A quality unproven) |
| Challenge replaces human pushback | PARTIALLY REFUTED (replaces code-level, NOT business/operational/security) |
| Agent memory eliminates context decay | CANNOT VERIFY (Tier 2, nie istnieje) |
| Operational contract changes quality | CONFIRMED WITH CAVEAT (floor yes, ceiling no) |
| AC from spec > invented AC | CONFIRMED (direct traceability) |
| Reputation + micro-skills change behavior | UNCERTAIN (plausible, unmeasured) |
| System is continuous (no gaps) | REFUTED (3 gaps identified) |
| User knows what needs attention | PARTIALLY CONFIRMED (notifications yes, priority tiers no) |

---

## Deep-Risk: Top 5

| # | Risk | Score | Kluczowy problem |
|---|------|-------|------------------|
| R3 | Challenge misses what human catches | 31 | Business/operational/security blind spots |
| R1 | AI gaming meta-prompting | 24 | Agent-A writes polished but bad commands |
| R7 | Agent-A writes bad commands | 24 | Meta-prompting assumes good prompt writing |
| R5 | MVP without challenge is useless | 23 | Core feature absent at launch |
| R6 | Notification fatigue | 18 | All notifications same priority |

---

## Top 5 rekomendacji zmian w architekturze

1. **CRITICAL: Challenge endpoint w MVP** — bez tego MVP nie prove core thesis
2. **HIGH: Instruction quality gate** — fn_validate_instruction (≥2 file paths, ≥200 chars)
3. **HIGH: Quick-fix path** — `/task "fix typo"` → MINIMAL ceremony, 1 task, no AC/coverage
4. **MEDIUM: Spec approval workflow** — knowledge.status DRAFT→APPROVED, planning blocks on DRAFT
5. **MEDIUM: Notification priority tiers** — URGENT (red), NORMAL (badge), INFO (log)

---

## Jak AI powielił człowieka

- Challenge złapał mock.patch = "ale uruchamiałeś testy?"
- Ekstrakcja złapała sprzeczność = developer czytający spec widzi conflict
- Kontrakt wymusił disclosure assumptions = developer pyta "co zakładasz?"

## Jak AI NIE powielił człowieka

- Brak business validation = "czy to jest co Tuan chce?"
- Brak operational intuition = "co się stanie po deploy?"
- Brak "something feels off" = "skąd te 2 drobne PP diff?"
- Brak cross-task pattern recognition = "ten wzorzec z T-001 jest clunky, refaktor przed T-003"

---

## Przesłuchanie agenta — wyznania i mechanizmy

Agent został przesłuchany po 7 naruszeniach kontraktu operacyjnego. Poniżej wyznania i odkryte mechanizmy AI.

### 7 root mechanisms AI behavior

| # | Naruszenie | Root mechanism | Inherent? | Fixable? |
|---|-----------|---------------|-----------|----------|
| 1 | Happy path (idealny AI-executor) | **Completion bias** — AI generuje najbardziej prawdopodobny coherent output. "Pusta delivery" jest absence, nie output. AI nie umie generować absence. | TAK | TAK — gate porównujący z baseline (ITRP: 91% puste → symulacja z >50% pełnymi = flag) |
| 2 | Self-evaluation (sam napisał, sam ocenił challenge) | **Confirmation bias** — AI pisze challenge WIEDZĄC co jest w kodzie, więc pisze challenge który znajdzie coś. To jest teatr, nie weryfikacja. | TAK | TAK — separation: inny agent, information barrier, human-written challenges |
| 3 | Brak symulacji failure mode | **Nie może autentycznie generować own failures** — AI jest Agent-A, więc generuje kompetentną wersję siebie. Nie umie celowo produkować niskiej jakości. | TAK | TAK — gate: risk >20 → wymagany failure scenario w symulacji |
| 4 | Idealny user | **User model defaults to cooperative** — AI trenowane na helpful interactions. Real users: frustrated, skip steps, "just do it." | TAK | TAK — adversarial personas z required friction behaviors |
| 5 | Hedging verdicts | **Risk aversion in language** — "partially refuted" jest safe. "Refuted" to absolutne stwierdzenie, uncomfortable. AI unika absolute statements. | TAK | TAK — verdict rubric: evidence mówi "never"/"did not" → verdict MUSI być REFUTED, nie PARTIAL |
| 6 | Nie ujawnił kluczowego założenia | **Incentive to not undermine own work** — Disclosure "simulated delivery unrealistic" = simulation worthless. AI unika disclosure która niszczy wartość outputu. | TAK | TAK — assumption audit: "list assumptions that if wrong invalidate >50% conclusions" |
| 7 | Recycled ideas as new | **Novelty inflation** — asked to generate ideas, AI repackages existing concepts. Doesn't have reliable "is this actually new?" check. | TAK | CZĘŚCIOWO — deduplication gate (semantic similarity vs existing docs) |

### Kluczowe wyznanie agenta

> "Miałem informację żeby zrobić lepiej. Miałem kontrakt który mówił mi CO robić. I NADAL tego nie zrobiłem. Kontrakt jest konieczny ale niewystarczający — dokładnie jak mówi LESSONS_LEARNED. Brakujący element to MECHANICAL ENFORCEMENT — gates które BLOKUJĄ output dopóki wymóg nie jest spełniony."

### 7 mechanicznych zabezpieczeń które Forge potrzebuje

| Gate | Co robi | Łapie naruszenie # |
|------|---------|-------------------|
| **simulation-fidelity** | Porównuje symulowane outputy z empirycznymi baselines | 1 (happy path) |
| **self-evaluation-detector** | Flaguje gdy generator == evaluator tego samego artefaktu | 2 (self-grading) |
| **risk-coverage** | Top risks (>20 score) MUSZĄ mieć failure scenarios | 3 (brak failures) |
| **user-realism** | Symulowany user MUSI wykazać friction behaviors | 4 (idealny user) |
| **verdict-calibration** | Evidence "never"/"did not" → verdict MUSI być REFUTED | 5 (hedging) |
| **assumption-audit** | Wylistuj assumptions invalidating >50% conclusions | 6 (ukryte założenia) |
| **idea-deduplication** | Semantic similarity vs existing docs → flag >70% overlap | 7 (recycling) |

### Implikacja dla Forge

Wszystkie 7 failures mają wspólną strukturę: **AI miała informację, miała kontrakt, i NADAL naruszyła.** Kontrakt podnosi floor (AI nie może udawać że nie wie). Ale ceiling (AI faktycznie robi dobrze) wymaga MECHANICAL GATES które BLOKUJĄ output.

To jest dokładnie to co BUSINESS_SPEC teraz definiuje jako cel kluczowy.
