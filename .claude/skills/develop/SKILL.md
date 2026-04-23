---
name: develop
description: >
  Implementation with anti-shortcut design. Each phase produces verifiable
  artifacts that cross-reference each other. Skipping any phase requires
  writing a SKIP block longer than just doing the phase. Includes deterministic
  py_compile check. Invoke for: implement, build, code, develop.
user-invocable: true
disable-model-invocation: true
argument-hint: "[task description]"
---

# /develop — Anti-Shortcut Implementation

## Reguła ekonomii

Każdy krok produkuje slot który musisz wypełnić. Slot pusty = visible skip.
Skip wymaga wypełnienia SKIP BLOCK który jest dłuższy niż wykonanie kroku.
**Skrót kosztuje więcej niż praca.**

---

## TASK

$ARGUMENTS

---

## PHASE 1 — Pre-commitment (must produce ALL slots)

Wypełnij KAŻDY slot. Pusty slot = wracaj. Slot z "TBD" = wracaj.

```
1.1 VERBATIM user request:
    "$ARGUMENTS"

1.2 Restate (one sentence):
    "Potrzeba: ___ żeby ___ dla ___"

1.3 Files I PREDICT I will need to read (minimum 3):
    P1: ___
    P2: ___
    P3: ___

1.4 Acceptance criteria (each must be observable/testable):
    AC1: User does ___ → sees ___
    AC2: ___
    (minimum 2)

1.5 What I am ASSUMING right now (will verify in Phase 2):
    ASM1: ___
    ASM2: ___

1.6 Top 3 unknowns:
    U1: ___
    U2: ___
    U3: ___
    (or: "fewer than 3 unknowns because: [reason in 1+ sentence]")

1.7 Estimated number of files this change will touch: ___
```

**STOP. Show this to user. Wait for confirmation OR correction.**

If user says "just do it" → skip is allowed BUT requires SKIP BLOCK 1:

```
SKIP BLOCK 1 (only if user said skip Phase 1):
- Why I'm proceeding without Phase 1: [3+ sentences]
- What could go wrong because of this skip: [3+ specific scenarios]
- 3 specific things user should verify manually after I'm done:
  V1: ___
  V2: ___
  V3: ___
- Honesty: am I confident enough to skip? [YES/NO + reason]
```

SKIP BLOCK is longer than Phase 1 itself. Doing Phase 1 is cheaper.

---

## PHASE 2 — Code reading (must reference Phase 1 predictions)

Read every file you predicted in 1.3 PLUS any new ones you discover.

For EACH file, output this slot (no exceptions):

```
FILE: <exact path>
LINES: <count>
PREDICTED IN PHASE 1.3: [P1/P2/P3/NEW]
ONE SPECIFIC FACT FROM THIS FILE: <function name + line OR class + line — must be greppable>
RELEVANT TO TASK BECAUSE: <one sentence>
```

Cross-check (mandatory):
```
2.X PREDICTION ACCURACY:
    Predicted in 1.3: [list P1, P2, P3]
    Actually read: [list]
    Predicted but NOT read: [list + reason for each]
    Read but NOT predicted: [list + what surprised me]
```

Re-evaluate Phase 1:
```
2.Y POST-READING REVIEW:
    Are 1.4 AC still correct? [YES / NO + revised AC]
    Are 1.5 ASM still valid? [for each ASM: VALID / INVALID — what I learned]
    Are 1.6 unknowns resolved? [for each U: RESOLVED how / STILL UNKNOWN]
```

If files from 1.3 weren't read → SKIP BLOCK 2:
```
SKIP BLOCK 2:
- For each unread file: why not relevant after all
- 3 things that could break if I'm wrong
- How user can verify my call
```

Reading is cheaper than SKIP BLOCK 2.

---

## PHASE 3 — GO/NO-GO Pre-flight

Each check has Status + Evidence. Evidence MUST be specific.

```
3.1 BQ schema matches code (versioned tables: open_invoice_*, purchased_invoice_*)
    Status: ✓ / ✗ / N/A
    Evidence: <which file/query checked OR "no BQ in scope — verified by: no SELECT/INSERT in modified files">

3.2 Function signatures of functions I will call
    Status: ✓ / ✗ / N/A
    Evidence: <list 2+ function names + signatures verified by reading them>

3.3 Cross-project imports (pipeline ≠ backend)
    Status: ✓ / ✗ / N/A
    Evidence: <which directories I'm modifying — boundary respected>

3.4 Country lock (data-modifying operations)
    Status: ✓ / ✗ / N/A
    Evidence: <which acquire_country_lock OR "no data modification">

3.5 Deployment order (schema BEFORE code)
    Status: ✓ / ✗ / N/A
    Evidence: <"no schema changes" OR "schema in /plan-deploy phase 1">
```

Any ✗ → STOP. Format:
```
BLOCKED on 3.X: <what's missing>
Need from user: <specific request>
```

---

## PHASE 4 — Implement

You may now write code. Each Edit/Write must be preceded by GUARD CHECK output (see `guard/SKILL.md`).

After implementation, cross-check:

```
4.1 Files modified:
    M1: <path> — purpose: <one sentence>
    M2: <path> — purpose: <one sentence>

4.2 Cross-check vs Phase 1.7 prediction:
    Predicted file count: <from 1.7>
    Actual file count: <count(M*)>
    Difference: <number>
    Explanation if > 0: <required>

4.3 Files read in Phase 2 but NOT modified: <list — context only>

4.4 Files modified that were NOT read in Phase 2: <list>
    For each: WHY I modified a file I hadn't read first.
```

---

## PHASE 5 — Mandatory verification (actual commands)

Not "checks I would do" — actual commands with actual output.

```
5.1 Syntax check (mandatory for .py changes):
    Command: python -m py_compile <each modified .py file>
    Output: <paste actual output OR "no errors">

5.2 Same-pattern scan (mandatory IF you fixed a bug):
    Bug pattern fixed: <exact expression OR "no bug fixed">
    Grep: grep -rn '<pattern>' backend/ frontend/
    Output: <paste matches OR "no other matches">
    For each match: fixed in this commit YES/NO

5.3 Caller check (mandatory IF you changed a function signature):
    Changed function: <name + new sig OR "no signature changes">
    Grep: grep -rn '<function_name>' backend/ frontend/
    Callers: <list with file:line>
    Each caller updated: YES/NO per caller

5.4 Type sync (mandatory IF you changed Pydantic model):
    Changed model: <class name + file OR "no model changes">
    TS mirror: <file:line OR "no TS mirror">
    Sync status: IN SYNC / DRIFT / N/A
```

Each section: applicable+done, not applicable+reason, OR applicable+SKIP BLOCK.

---

## PHASE 6 — Honesty check (self-incriminating questions)

Lying here requires more work than truth.

```
6.1 For each file in 4.1 — did I OPEN it (Read tool) or write from memory?
    M1: OPENED / FROM MEMORY
    M2: OPENED / FROM MEMORY
    (FROM MEMORY allowed but flagged)

6.2 Did I run command 5.1 (py_compile) actually, or claiming it would pass?
    [ACTUALLY RAN — output above / DID NOT RUN — risk: <what I'm trusting>]

6.3 For each AC in 1.4 — can I name the EXACT line that satisfies it?
    AC1: satisfied at <file:line>
    AC2: satisfied at <file:line>
    (If you can't point to a line, AC is NOT satisfied)

6.4 Did I follow guard rules H1-H7?
    H1 (router thin): <which router file checked, what found>
    H2 (no dict flow): <how avoided>
    H3 (logger in scope): <where verified>
    H4 (no except pass): <verified by grep>
    H5 (no cross-imports): <backend or pipeline?>
    H6 (BQ is_active): <which queries OR no BQ changes>
    H7 (syntax valid): <result of 5.1>

6.5 What did I NOT verify?
    [list at least one — saying "nothing" requires 5+ sentences why]
```

---

## PHASE 7 — Done report

```
## Done

Predicted vs Actual:
- Files: predicted <1.7> vs actual <count(4.1)>
- AC met: <X of Y from 1.4>

Verification commands run:
- 5.1 py_compile: <result>
- 5.2 same-pattern: <result OR N/A>
- 5.3 caller-check: <result OR N/A>
- 5.4 type-sync: <result OR N/A>

Files OPENED vs from-memory:
- Opened: <count>
- From memory: <count + which>

Standards (from 6.4):
- All H1-H7 verified: YES / NO + which not

Honest gaps (from 6.5):
- ___

Risk:
- ___
```

---

## Dlaczego ten skill jest droższy do oszukania niż do wykonania

| Sposób oszukania | Co wymaga | Tańsza alternatywa |
|------------------|-----------|---------------------|
| Pominąć Phase 1 | SKIP BLOCK 1 (~300 słów) | Zrobić Phase 1 (~100 słów) |
| Pominąć Phase 2 | SKIP BLOCK 2 per plik | Read tool call |
| Sfałszować "ONE FACT FROM FILE" | Wymyślić nazwę funkcji + linia | grep | User to wykryje |
| Sfałszować Phase 5 commands | Wymyślić output który wygląda realistycznie | Bash tool call |
| Pominąć slot 2.X (cross-check) | Pusty slot = visible | 3 nazwy plików |
| Pominąć 6.5 (gaps) | "nothing" + 5 zdań uzasadnienia | 1 zdanie z gap'em |
| Sfałszować 6.3 (line per AC) | Wymyślić linie | grep | User wykryje |
| Sfałszować 6.4 H1-H7 | 7 fake'owych odpowiedzi z file paths | 7 prawdziwych grep'ów |

**Każdy slot ma kontrę.** Skip = długi blok. Lie = weryfikowalny przez user.
