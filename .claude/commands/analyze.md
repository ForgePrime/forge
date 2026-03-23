# /analyze $ARGUMENTS

Analyze extracted knowledge — resolve decisions, group requirements into objectives with measurable key results, prepare for planning.

## Arguments

| Form | Meaning | Example |
|------|---------|---------|
| (none) | Analyze current project | `/analyze` |
| `--resolve-only` | Only resolve OPEN decisions, skip objective creation | `/analyze --resolve-only` |

## Prerequisites

Ingestion must be completed first (`/ingest`). Expects:
- K-NNN (requirements, context, source-documents)
- D-NNN (decisions from ingestion)
- G-NNN (guidelines from docs)

## Instructions

Read and follow the procedure in `skills/analyze/SKILL.md`.

Key points:
- Resolve OPEN clarifications and assumptions before creating objectives
- Group requirements by business outcome (not technical area)
- Each objective: 3-15 requirements, 2-5 key results with measurement method
- Link every requirement K-NNN to an objective O-NNN
- After analysis, `draft-plan` should pass all gates

The arguments are: $ARGUMENTS
