# /ac-template $ARGUMENTS

Manage acceptance criteria templates (AC-NNN) — reusable, parameterized AC patterns.

## Arguments

| Form | Meaning | Example |
|------|---------|---------|
| (none) | List all templates | `/ac-template` |
| `{id}` | Show template details | `/ac-template AC-001` |
| `add {title}` | Add new template interactively | `/ac-template add API endpoint performance` |
| `{id} instantiate` | Fill template with params | `/ac-template AC-001 instantiate` |
| `{id} update` | Update template | `/ac-template AC-001 update` |

## Procedure

1. Determine the active project:
```bash
ls forge_output/ 2>/dev/null
```

If no project exists, ask user to create one first with `/plan`.

### List (no arguments)

```bash
python -m core.ac_templates read {project}
```

### Show (template ID)

```bash
python -m core.ac_templates show {project} {template_id}
```

### Add (`add {title}`)

a. Check the contract:
```bash
python -m core.ac_templates contract add
```

b. Ask the user:
   - **Category**: performance, security, quality, functionality, accessibility, reliability, data-integrity, ux
   - **Template**: the AC text with `{placeholders}` for parameters
   - **Parameters**: for each placeholder — name, type, default, description
   - **Verification method**: how to verify this AC is met
   - **Scopes**: which areas this applies to

c. Create:
```bash
python -m core.ac_templates add {project} --data '[{
  "title": "{title}",
  "description": "{what this template checks}",
  "template": "{template text with {param} placeholders}",
  "category": "{category}",
  "parameters": [{"name": "{param}", "type": "string", "default": "", "description": "{what}"}],
  "verification_method": "{how to verify}",
  "scopes": ["{scopes}"],
  "tags": ["{tags}"]
}]'
```

### Instantiate (`{id} instantiate`)

a. Show the template:
```bash
python -m core.ac_templates show {project} {template_id}
```

b. Ask for parameter values (show defaults).

c. Instantiate:
```bash
python -m core.ac_templates instantiate {project} {template_id} --params '{"param1": "value1"}'
```

d. Show the resulting structured AC: `{text, from_template, params}`

This can be used as an `acceptance_criteria` entry on tasks (structured AC format).

### Update (`{id} update`)

```bash
python -m core.ac_templates update {project} --data '[{
  "id": "{template_id}",
  "template": "{updated template}",
  "parameters": [...]
}]'
```
