# /ingest $ARGUMENTS

Document ingestion — register source documents, extract structured facts, detect conflicts and assumptions.

## Arguments

| Form | Meaning | Example |
|------|---------|---------|
| (none) | Scan project directory for docs and ingest all | `/ingest` |
| `{path}` | Ingest a specific file or directory | `/ingest docs/requirements.md` |
| `{path1} {path2}` | Ingest multiple specific files | `/ingest spec.md api-contract.yaml` |

## Instructions

Read and follow the procedure in `skills/ingest/SKILL.md`.

Key points:
- Register each document as K-NNN (category=source-document) with trust level (HIGH/MEDIUM/LOW)
- Extract every implementable fact — requirements, rules, decisions, guidelines
- Surface conflicts between documents as OPEN risk decisions (do NOT silently harmonize)
- Create OPEN decisions for implicit assumptions and unknowns
- Verify 9 critical categories (deployment, stack, users, data-in, data-out, persistence, error-handling, scale, definition-of-done)
- Create extraction record (R-NNN, category=ingestion) for each document

The target path is: $ARGUMENTS (if empty, scan project directory)
