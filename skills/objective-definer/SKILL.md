---
name: objective-definer
description: "Guides definition and refinement of objectives with measurable key results"
version: "1.0.0"
entity-types: [objective]
contract-refs: [objectives/add, objectives/update]
---

# Objective Definer

Help the user define, refine, and structure business objectives with measurable key results.

## When to Use

- User is creating a new objective
- User wants to refine an existing objective's KRs
- User needs help making KRs measurable and specific

## Procedure

1. **Understand the goal**: Ask clarifying questions about the business outcome.
2. **Draft the objective**: Create a clear, concise title and description.
3. **Define Key Results**: For each KR, determine:
   - Numeric KR: `{metric, baseline, target, current}` for quantifiable outcomes
   - Descriptive KR: `{description}` for milestone-based outcomes
   - Mixed: both metric + description for context
4. **Set appetite**: small (days), medium (weeks), large (months)
5. **Identify scopes**: which guideline scopes relate to this objective
6. **State assumptions**: explicit hypotheses that must hold

## Output Format

Use the `objectives/add` contract for field specifications. Fetch the contract via:
```
GET /api/v1/contracts/objectives/add
```

## Quality Checklist

- Title is concise and action-oriented (e.g., "Reduce API response time")
- Description explains WHY this matters and WHO benefits
- Each KR is independently verifiable
- Numeric KRs have realistic baseline and target values
- Appetite reflects actual effort budget, not aspiration
- Assumptions are falsifiable

## Tips

- Prefer 2-4 KRs per objective (more is unfocused)
- At least one KR should be numeric when possible
- Use `advances_key_results` on ideas to link back to this objective's KRs
- Derived guidelines can be created from objective scopes
