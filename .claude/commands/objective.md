# /objective $ARGUMENTS

Define a business objective with measurable key results — the "north star" for work.

## Arguments

| Form | Meaning | Example |
|------|---------|---------|
| `{title}` | Define objective interactively | `/objective Reduce API response time` |
| `{title} --quick` | Skip alignment, add directly | `/objective Fix auth perf --quick` |

## Procedure

1. Determine the active project:
```bash
ls forge_output/ 2>/dev/null
```

If no project exists, create one:
```bash
python -m core.pipeline init {slug} --goal "Project workspace"
```

2. **Align** (medium alignment per `skills/deep-align/SKILL.md`):

   a. **Restate** the user's objective: "You want to achieve X because Y."
      Get confirmation before proceeding.

   b. **Ask 2-4 targeted questions** to define measurable key results:
      - "How will you know this is achieved? What metric(s) change?"
      - "Where are you now on that metric? Where do you want to be?"
      - "How much effort are you willing to invest? (days/weeks/months)"
      - "What assumptions must hold for this to make sense?"

      Only ask what you genuinely don't know. If the user gave metrics
      in the title/description, don't re-ask.

   c. **Constraint-frame the description** — add 1-3 short constraints: what sources to use, what NOT to do, what to do when blocked. Keep it tight — one sentence per constraint, not a paragraph.

      **Push back on bad ideas.** If the objective is vague, unrealistic, or poorly scoped — say so directly. Don't just ask polite questions. Express your opinion: "This is too broad because X", "I'd cut Y because Z", "This will fail without W". Influence the user toward a better objective before locking it in.

      Skip framing for objectives that are already specific.

   d. If `--quick` — skip alignment, infer reasonable defaults, flag assumptions.

3. Check the contract:
```bash
python -m core.objectives contract add
```

4. Create the objective from confirmed understanding:

```bash
python -m core.objectives add {project} --data '[{
  "title": "{confirmed title}",
  "description": "{why this matters, business context}",
  "key_results": [
    {"metric": "{what we measure}", "baseline": N, "target": N},
    {"metric": "{second metric}", "baseline": N, "target": N}
  ],
  "appetite": "{small|medium|large}",
  "scope": "{project|cross-project}",
  "assumptions": ["{assumption 1}", "{assumption 2}"],
  "tags": ["{relevant tags}"],
  "scopes": ["{guideline scopes this objective relates to}"]
}]'
```

5. **Optionally create derived guidelines** — if the objective implies coding standards:
   - e.g., KR "p95 < 200ms" → guideline "Every endpoint must have latency benchmark"
   - Create the guideline with `derived_from: "O-001"` for traceability:
   ```bash
   python -m core.guidelines add {project} --data '[{
     "title": "{standard implied by objective}",
     "scope": "{from objective scopes}",
     "content": "{what to do}",
     "rationale": "Derived from objective O-001: {objective title}",
     "weight": "must",
     "derived_from": "O-001"
   }]'
   ```
   Then link back: update the objective's `derived_guidelines` with the new guideline ID.
   Only create guidelines when a KR clearly implies an enforceable standard. Do NOT auto-generate.

6. Present the created objective and suggest next steps:
   - `/idea {title}` — propose Ideas that advance specific Key Results
   - `/research O-001` —  structured analysis summaries linked to objectives
   - `/objectives` — see all objectives
   - `/objectives O-001` — see details + coverage
   - `/guideline {text}` — create standards derived from this objective
   - Remind: when creating Ideas, link them with `advances_key_results: ["O-001/KR-1"]`

## Key Results Guidelines

Good KRs are:
- **Measurable**: has a number (not "improve performance" but "p95 < 200ms")
- **Bounded**: has baseline AND target (not just target)
- **Outcome-focused**: measures result, not output ("retention up 20%" not "ship 5 features")
- **2-5 per objective**: fewer = too vague, more = unfocused
