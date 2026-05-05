---
name: forge
description: >
  Reference Procedure router. Given a task description, identifies the right
  Procedural Card from .ai/framework/REFERENCE_PROCEDURE.md and walks through
  ordered steps with evidence_obligation enforcement. Invokes sub-skills
  (/plan, /develop, /deep-verify, /deep-risk, /grill) per step's action_type.
  Blocks on UNKNOWN per CONTRACT.md §B.2. Invoke for ANY task as the entry point.
user-invocable: true
disable-model-invocation: true
argument-hint: "[task description]"
---

# /forge — Reference Procedure Router

## Cel

Każde zadanie zaczyna się tutaj. /forge identyfikuje który Procedural Card z `.ai/framework/REFERENCE_PROCEDURE.md` pasuje do zadania, prowadzi przez ordered steps, egzekwuje `evidence_obligation` per step, dispatchuje do sub-skilli.

Bez /forge wykonanie zadania nie ma deklarowanej procedury — typ akcji każdego kroku zostaje na intuicji wykonawcy, łamiąc E8 (deterministic justification) z CONTRACT.md §E.

## Kiedy /forge a kiedy bezpośrednio sub-skill

- **`/forge`** — pełne zadanie (feature, bug, analysis), trzeba przejść przez wszystkie 4 stage'e CGAID.
- **`/plan`, `/develop`, `/grill`, `/deep-verify`** bezpośrednio — pojedynczy stage, gdy karta już zidentyfikowana lub gdy robisz cząstkową pracę w ramach większej karty.

## TASK
$ARGUMENTS

---

## KROK 1 — Identify card

Wypełnij sloty. Pusty slot = wracaj.

```
1.1 task_type ∈ {feature, bug, analysis, refactor, hotfix, classification}: ___
1.2 ceremony_level ∈ {LIGHT, STANDARD, FULL}: ___
    Justification (który trigger z REFERENCE_PROCEDURE §6 pasuje): ___
1.3 prereq check (per card.prereq):
    - Stage 0 classification done? [YES — tier ___ | NO — STOP, run classification card first]
    - other prereqs from card: ___
1.4 selected card_id: ___
```

Jeśli **brak karty pasującej** → STOP. Karta nie istnieje = backlog item w REFERENCE_PROCEDURE §8 B2 + ADR. **NIE improwizacja.**

---

## KROK 2 — Walk steps S1 → SN

Dla każdego step z karty wypełnij blok:

```
2.x.0 step_id (z karty): ___
2.x.1 cgaid_stage: ___
2.x.2 action_type: ___
2.x.3 action_payload (verbatim z karty lub adaptowane do zadania): ___

2.x.4 dispatch:
       direct_skill   → invoke skill (np. /plan, /develop, /grill)
       meta_prompt    → spawn Agent z prompt-amplification (subagent_type=Explore)
       opinion_prime  → spawn Agent z persona priming
       theorem_check  → /deep-verify vs theorems/<stage>/<file>.md
       rubric_check   → apply rubric (DATA_CLASSIFICATION.md lub inna)
       risk_probe     → /deep-risk lub /grill (adversarial)

2.x.5 evidence_obligation populated:
       artifact:    ___ (konkretny plik / record id)
       claims:      [statement / epistemic / tier / acceptance per claim]
       min_tier:    ___ (T1/T2/T3 — per stage, R3/R4 z REFERENCE_PROCEDURE §4)
       unknowns:    ___ (jeśli niepuste → STOP per CONTRACT §B.2; escalate lub explicit-accept)
       trace_link:  ___ (gdzie archiwizujemy)

2.x.6 gate predicates passed: ___
       Jeśli nie → BLOCK, return to action lub re-investigate.

2.x.7 manual_fallback used? [YES/NO]
       (jeśli YES — czy wykonanie ręczne wciąż produkuje ten sam evidence_obligation?)
```

---

## KROK 3 — Exit gate

```
3.1 wszystkie steps complete: ___
3.2 wszystkie evidence_obligation populated (R1–R2 pass): ___
3.3 wszystkie gates passed: ___
3.4 unknowns [] across all steps (R5 pass): ___
3.5 trace_links archived (R6 pass): ___
3.6 build steps min_tier ≥ T2 (R3 pass): ___
3.7 verify steps min_tier == T3 (R4 pass): ___
3.8 mechanical R1–R6 check: ___
```

Każdy slot CONFIRMED → karta closed.

---

## Reguły blokujące (HARD)

- **R1/R2 violation** — pusty `artifact` lub pusty `claims` w jakimkolwiek kroku → step nie zaliczony.
- **R5 violation** — niepuste `unknowns` na exit_gate → karta wchodzi w BLOCKED state (P20). NIE wolno close.
- **Solo-verifier** w S4 (Stage 4) → P22 §B.8 violation; wymagany distinct actor.
- **Brak APPROVE** od distinct actor po S2 (Stage 2) dla STANDARD/FULL → blok przed S3.
- **Improwizacja karty** gdy żadna nie pasuje → STOP, backlog item, nie kontynuuj.

---

## Failure modes — co NIE robić

1. **Improwizować kartę** gdy żadna nie pasuje. Backlog item w REFERENCE_PROCEDURE §8 + ADR.
2. **Pomijać evidence_obligation** "bo to oczywiste". Oczywiste = T1 citation, koszt <30s.
3. **Markować step jako complete** bez populacji wszystkich pól evidence_obligation.
4. **Skip manual_fallback documentation** — bez tego procedura przestaje być wykonywalna ręcznie, łamie założenie tool-agnostic.
5. **Składać action_type od siebie** — `opinion_prime` nie jest substytutem dla `theorem_check`. Każdy ma osobne acceptance criteria.
6. **Solo-verify w S4** — to literal P22 §B.8 violation.

---

## Reference

- Karty + grammar + invariant rules: `.ai/framework/REFERENCE_PROCEDURE.md`
- Action type acceptance criteria: REFERENCE_PROCEDURE §2
- evidence_obligation schema: REFERENCE_PROCEDURE §3
- Tier system T1/T2/T3: REFERENCE_PROCEDURE §3
- Theorem index per stage: REFERENCE_PROCEDURE §5
- Sub-skills: `.claude/skills/{plan,develop,grill,deep-verify,deep-risk,test,guard}/SKILL.md`
- Operational contract: `.ai/CONTRACT.md`
