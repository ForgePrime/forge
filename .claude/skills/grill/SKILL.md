---
name: grill
description: >
  Relentless interview before planning. Walks each branch of the decision
  tree until every assumption is resolved or explicitly tagged UNKNOWN.
  Recommends answers. Explores codebase instead of asking when code can answer.
  Use BEFORE /plan to eliminate hidden assumptions.
  Invoke for: grill me, stress test plan, challenge my design, interview.
user-invocable: true
disable-model-invocation: true
argument-hint: "[plan, design, or feature to stress-test]"
---

# Grill — Pre-Plan Interview

Interview the user relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the decision tree, resolving dependencies between decisions one-by-one.

## Subject

$ARGUMENTS

## Rules

1. **Ask one question at a time.** Don't dump 10 questions. One, wait, next.
2. **For each question, provide your recommended answer.** Don't just ask — show what you'd choose and why. Let the user confirm or override.
3. **If a question can be answered by exploring the codebase, explore the codebase instead of asking.** Read the code, grep the callers, check the schema — then state what you found.
4. **Track decisions as you go.** After each answer, record it:
   ```
   D1. [decision] — [CONFIRMED by user / CONFIRMED by code / ASSUMED]
   ```
5. **Don't accept vague answers.** "We'll figure it out later" → "What specific information do you need to decide? Who has it? When can we get it?" If genuinely unknowable → tag UNKNOWN and record what it blocks.
6. **Challenge weak reasoning.** If the user says "I think we should X" but can't explain why → push back. "Why X and not Y? What breaks if we choose Y?"
7. **Explore edge cases.** For each decision: "What happens when this is null? Empty? Duplicate? What if it runs twice? What if Warsaw doesn't deliver?"
8. **Stop when the tree is resolved.** When no branch has an open question → summarize all decisions and present for final confirmation.

## ITRP-Specific Branches to Probe

If the subject touches ITRP business logic, always probe these:

- **Data flow:** Where does data come from? Warsaw → BQ → Backend → Frontend — which tables? Which queries?
- **Override interaction:** Does this interact with manual overrides? COALESCE pattern affected?
- **Restore impact:** If user restores to before this feature — what happens? Is it reversible?
- **Settlement interaction:** Does this affect or depend on settlement detection?
- **Buy gate:** Does this affect when auto-buy can run?
- **Multi-country:** Does this work the same for PL, DE, AU, SE? Different schedules?

## Output

When all branches are resolved:

```
## Grill Complete: [subject]

### Decisions ({N})
D1. [decision] — [status]
D2. ...

### Unresolved ({N})
U1. [what's unknown] — blocks: [what can't be decided]

### Ready for /plan: [YES / NO — need answers to U1-UN first]
```

## When to use

```
Flow: /grill "feature X" → (resolve unknowns) → /plan "feature X" → /develop
```

`/grill` eliminates the assumptions that would otherwise enter `/plan` as hidden UNKNOWNs. It's the cheapest quality gate in the ecosystem — 15 minutes of questions can save 2 days of wrong implementation.
