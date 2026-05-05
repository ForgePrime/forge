# 8 Rules of Work — derived from experience

> Every rule comes from a real mistake. Not theory.

---

## 1. Data first, code second

Before writing the first line — answer the question:
> *"How do I know what the correct result should be?"*

If you don't have an answer → stop and build an evidence base.
A file with ground truth (data from the system, from business, from an external source) is the entry condition for planning — not its output.

**Without this:** every fix reveals the next one. Instead of one change — eight iterations.

---

## 2. Write test scenarios BEFORE code, not after

Writing a test scenario forces understanding of the system that planning does not.

A scenario "what if the resource is already held by another process?" requires checking how locking works, whether there is idempotency, what happens under concurrency. You discover this WHILE WRITING the scenario — not while planning.

Focus on **attacking** scenarios, not confirming ones:
- Empty dataset (0 records)
- Date range boundary (inclusive/exclusive?)
- "Already processed" state (no-op)
- Infrastructure failure mid-operation (what was saved?)
- Previous version still works (regression)

**Without this:** happy path works, edge case discovered in production.

---

## 3. Every stage ends with literal output — not a declaration

A stage closed without evidence is a declaration, not a fact.

| Wrong | Right |
|-------|-------|
| "Stage 1 done — works." | "Stage 1 COMPLETE. Output: `count=34052, skipped=142`. Invariant I1: 0 duplicates ✅" |

Literal output means: a concrete number, a concrete HTTP status, concrete rows from the database.
Not "seems to work" — only what you saw on the screen.

**Without this:** "works" means anything. Rollback after a week with no idea what changed.

---

## 4. Verify the plan with an independent method before implementation

The author of the plan cannot be its only verifier — same person with the same assumptions.

Before moving to code:
1. Run `/deep-verify` on the plan (scored findings + adversarial review)
2. If result is REJECT → fix the plan, don't implement

Independent verification does not mean lack of trust in the author. It means a second set of eyes has different blind spots.

**Without this:** a plan with a fundamental gap reaches implementation. Gap discovered at runtime.

---

## 5. Write documents for someone who doesn't know the context

Before delivering any document (plan, spec, instructions) ask:
> *"Can a new person, who has never seen any previous conversation, execute this task step by step without asking the author?"*

If the answer is "no" → the document is incomplete.

Checklist for every document:
- [ ] Who is the audience?
- [ ] What are the inputs (from where, in what format)?
- [ ] What decisions were made and why (min. 2 alternatives)?
- [ ] What does a correct result look like (concretely)?

**Without this:** the document works as a note for the author, not as instructions for anyone else.

---

## 6. A lesson goes into a blocking mechanism — not just a note

Markdown with lessons is a reference, not a safeguard.

A deterministic rule (e.g., "don't use `except Exception: pass`") has three levels:
1. **Note** — easy to ignore (70-90% compliance)
2. **Hook with exit 2** — blocks the operation before it reaches code (100% compliance)
3. **Automated test** — detects the violation in CI

If a rule is important and deterministic → it moves from level 1 to 2 or 3.
If it stays at level 1 → it's decoration.

**Without this:** the same mistakes return after a month, because the rule exists only in text.

---

## 7. On every change, check what else uses it

Changing a function, schema, API, data format — always has consumers.

Before modifying:
```
MODIFYING: [list of files]
IMPORTED BY / CONSUMED BY: [grep result]
NOT MODIFYING (out of scope): [list]
```

If you don't check — you'll find out from a production user.

"It compiled" is not verification. Verification means: all places that use the changed thing still work, confirmed by output.

**Without this:** a change in one place breaks another. Classic "fix A breaks B".

---

## 8. Challenge before fix (anti-loop)

Before applying a fix, especially the second or later one in the same area — write down:

```
IMPACT ESTIMATE: [blast radius — # files / # invoices / # rows / # users affected]
ROLLBACK PLAN:   [how to revert in <5 minutes]
ADVERSARIAL (≥3): [c1: counterargument | c2: hidden assumption | c3: regression class]
ALTERNATIVES (≥2): [2 different approaches with explicit pros/cons]
LOOP CHECK:      [is this defensive vs my last fix? if yes after 2 deep → STOP]
```

Empty `IMPACT ESTIMATE` or `ROLLBACK PLAN` = the fix is not understood deeply enough.

A **defensive fix** is one whose justification is "to undo a regression introduced by fix N−1". After **2 consecutive defensive fixes** without model re-evaluation → **STOP**. The next correct action is either:

- full revert + re-baseline
- escalate to user with the loop diagnosis
- step back and re-derive the model

Continuing to fix N+1 in the same direction extends the loop.

**Without this:** TD ladder. Five fixes deep, four reverted, ~5 hours wasted (incident 2026-04-25, see `LESSONS_LEARNED.md`).

Formal foundation: `theorems/Adaptive Contract-Governed Work Evolution Theorem.md`. Per-change disclosure format: `CONTRACT.md` §C.

---

## 8 questions before every task

1. How do I know what the correct result should be? *(evidence base)*
2. Do I have test scenarios that attack, not confirm? *(edge cases before code)*
3. How will I close each stage — what will the literal output be? *(evidence per stage)*
4. Will the plan pass independent verification before implementation? *(deep-verify)*
5. Will a new person understand this document without asking me? *(readability)*
6. Will this lesson reach a blocking mechanism? *(hook / test, not just markdown)*
7. Have I checked all consumers of this change? *(propagation)*
8. Is this a defensive fix vs my last one? Have I declared IMPACT + ROLLBACK + ALTERNATIVES? *(anti-loop, per Rule 8)*

If the answer to any is "no" → stop before code and fill the gap.
