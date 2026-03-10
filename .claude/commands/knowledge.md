# /knowledge $ARGUMENTS

Manage knowledge objects (K-NNN) — domain rules, architecture docs, technical context, code patterns.

## Arguments

| Form | Meaning | Example |
|------|---------|---------|
| (none) | List all knowledge | `/knowledge` |
| `{id}` | Show knowledge details | `/knowledge K-001` |
| `{id} impact` | Show impact analysis | `/knowledge K-001 impact` |
| `add {title}` | Add new knowledge interactively | `/knowledge add Redis caching patterns` |
| `{id} update` | Update knowledge content (creates new version) | `/knowledge K-001 update` |
| `{id} link {entity}` | Link knowledge to entity | `/knowledge K-001 link T-005` |
| `{id} deprecate` | Mark knowledge as deprecated | `/knowledge K-001 deprecate` |

## Procedure

1. Determine the active project:
```bash
ls forge_output/ 2>/dev/null
```

If no project exists, ask user to create one first with `/plan`.

### List (no arguments)

```bash
python -m core.knowledge read {project}
```

### Show (knowledge ID)

```bash
python -m core.knowledge show {project} {knowledge_id}
```

### Impact analysis (`{id} impact`)

```bash
python -m core.knowledge impact {project} {knowledge_id}
```

### Add (`add {title}`)

a. Check the contract:
```bash
python -m core.knowledge contract add
```

b. Ask the user:
   - **Category**: domain-rules, api-reference, architecture, business-context, technical-context, code-patterns, integration, infrastructure
   - **Content**: the knowledge content (document, rules, patterns, etc.)
   - **Scopes**: which areas this applies to

c. Create:
```bash
python -m core.knowledge add {project} --data '[{
  "title": "{title}",
  "category": "{category}",
  "content": "{content}",
  "scopes": ["{scopes}"],
  "tags": ["{tags}"]
}]'
```

### Update (`{id} update`)

a. Show current content:
```bash
python -m core.knowledge show {project} {knowledge_id}
```

b. Ask what changed and why (change_reason is required for versioning).

c. Update:
```bash
python -m core.knowledge update {project} --data '[{
  "id": "{knowledge_id}",
  "content": "{new content}",
  "change_reason": "{why it changed}"
}]'
```

### Link (`{id} link {entity}`)

```bash
python -m core.knowledge link {project} --data '{
  "knowledge_id": "{knowledge_id}",
  "entity_type": "{task|idea|objective|guideline}",
  "entity_id": "{entity_id}",
  "relation": "reference"
}'
```

### Deprecate (`{id} deprecate`)

```bash
python -m core.knowledge update {project} --data '[{
  "id": "{knowledge_id}",
  "status": "DEPRECATED"
}]'
```
