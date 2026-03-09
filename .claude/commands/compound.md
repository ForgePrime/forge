# /compound

Extract lessons learned from project execution. This is the "Compound" phase —
turning experience into reusable knowledge for future projects.

Inspired by: "Each unit of engineering work should make subsequent units easier."

## Procedure

1. Find the active project and load full context:
```bash
python -m core.pipeline status {project}
python -m core.decisions read {project}
python -m core.changes read {project}
```

2. Review the project execution and identify lessons in these categories:
   - **pattern-discovered**: Reusable patterns found during implementation
   - **mistake-avoided**: Things that went wrong and how they were fixed
   - **decision-validated**: Decisions that proved correct
   - **decision-reversed**: Decisions that proved wrong
   - **tool-insight**: Better ways to use tools or libraries
   - **architecture-lesson**: Structural insights
   - **process-improvement**: Better workflow approaches

### Guidelines effectiveness

Analyze which guidelines were actually checked during execution:
```bash
python -m core.changes read {project}
python -m core.guidelines read {project} --status ACTIVE
```

Cross-reference `guidelines_checked` in change records against active guidelines:
- Which guidelines were checked most/least?
- Were any must-guidelines never checked? (potential gap)
- Include findings in lessons.

3. For each lesson, load the contract first:
```bash
python -m core.lessons contract
```

4. Record lessons:
```bash
python -m core.lessons add {project} --data '[
  {
    "category": "pattern-discovered",
    "title": "Concise, actionable title",
    "detail": "Explain WHY this matters, not just what happened",
    "task_id": "T-XXX",
    "decision_ids": ["D-XXX"],
    "severity": "critical|important|minor",
    "applies_to": "When is this lesson relevant?",
    "tags": ["searchable", "keywords"]
  }
]'
```

5. Show the recorded lessons:
```bash
python -m core.lessons read {project}
```

## Guidelines

- Focus on REUSABLE insights, not project-specific details
- Every lesson should be actionable — "always do X" or "never do Y"
- Link to specific decisions and tasks that generated the lesson
- Severity: critical = caused or would cause production issues, important = significant time/quality impact, minor = nice to know
- Ask the user if they have additional lessons to add
- Check past lessons to avoid duplicates: `python -m core.lessons read-all`
