---
name: idea-explorer
description: "Guides exploration, refinement, and structuring of ideas with relations and KR links"
version: "1.0.0"
entity-types: [idea]
contract-refs: [ideas/add, ideas/update]
---

# Idea Explorer

Help the user explore, refine, and structure ideas within the Forge planning hierarchy.

## When to Use

- User is capturing a new idea
- User wants to break an idea into sub-ideas
- User needs to link ideas to objective KRs
- User wants to explore feasibility before committing

## Procedure

1. **Capture the idea**: Get a clear title and description.
2. **Classify**: Assign category (feature, improvement, experiment, research, other) and priority.
3. **Link to objectives**: Identify which KRs this idea advances via `advances_key_results` (e.g., `["O-001/KR-1"]`).
4. **Define relations**: Set up `depends_on`, `related_to`, `supersedes`, or `duplicates` links.
5. **Hierarchy**: Determine if this is a top-level idea or a child (set `parent_id`).
6. **Scope inheritance**: Ideas inherit scopes from their linked objective.

## Output Format

Use the `ideas/add` contract for field specifications. Fetch the contract via:
```
GET /api/v1/contracts/ideas/add
```

## Status Lifecycle

```
DRAFT -> EXPLORING -> APPROVED -> COMMITTED -> (REJECTED | DEFERRED)
```

- DRAFT: Initial capture
- EXPLORING: Under active investigation (use `/discover` for deep analysis)
- APPROVED: Validated, ready for planning
- COMMITTED: Tasks have been created from this idea
- REJECTED/DEFERRED: Not pursuing (now or ever)

## Quality Checklist

- Title is descriptive and specific
- Description includes the "what" and "why"
- At least one KR link if an objective exists
- Category and priority are set
- Relations to other ideas are identified
- Scopes are set (inherited from objective or explicit)

## Tips

- Use sub-ideas for complex features: parent = epic, children = specific aspects
- Before APPROVED, consider running `/discover {idea_id}` for risk assessment
- Ideas with `depends_on` won't be plannable until dependencies are COMMITTED
- The `commit` action on an idea validates all its `depends_on` are resolved
