---
name: onboard
id: SKILL-ONBOARD
version: "1.0"
description: "Discover and import existing project knowledge into Forge for brownfield projects."
---

# Onboard

## Identity

| Field | Value |
|-------|-------|
| ID | SKILL-ONBOARD |
| Version | 1.0 |
| Description | Discover project structure, extract decisions/conventions/constraints, import into Forge, configure gates. |

## Read Commands

| ID | Command | Returns | When |
|----|---------|---------|------|
| R1 | `python -m core.lessons read-all` | Lessons from past projects | Step 1 — prior knowledge |
| R2 | `python -m core.decisions contract add` | Contract for recording decisions | Step 4 — before import |
| R3 | `python -m core.lessons contract` | Contract for recording lessons | Step 4 — before import |
| R4 | `python -m core.pipeline status {project}` | Pipeline state after creation | Step 6 — verify |

## Write Commands

| ID | Command | Effect | When | Contract |
|----|---------|--------|------|----------|
| W1 | `python -m core.pipeline init {project} --goal "..."` | Creates Forge project | Step 4 — create project | |
| W2 | `python -m core.decisions add {project} --data '{json}'` | Records imported decisions | Step 4 — import decisions | `python -m core.decisions contract add` |
| W3 | `python -m core.lessons add {project} --data '{json}'` | Records imported lessons | Step 4 — import lessons | `python -m core.lessons contract` |
| W4 | `python -m core.pipeline config {project} --data '{json}'` | Sets test/lint commands | Step 5 — configure | `python -m core.pipeline contract config` |
| W5 | `python -m core.gates config {project} --data '[{json}]'` | Configures validation gates | Step 5 — configure | `python -m core.gates contract config` |

## Output

| File | Contains |
|------|----------|
| `forge_output/{project}/tracker.json` | Project with config and gates |
| `forge_output/{project}/decisions.json` | Imported decisions and conventions |
| `forge_output/{project}/lessons.json` | Imported lessons (if any) |

## Success Criteria

- All discoverable project sources have been scanned
- Key architectural decisions extracted and recorded with `decided_by: "imported"`
- Active conventions recorded as `type: "convention"` decisions
- Known constraints recorded as `type: "constraint"` decisions
- Test and lint commands auto-detected and configured as gates
- User has reviewed and confirmed the imported knowledge is correct
- No fabricated information — only extract what is explicitly stated in project files

## References

- `docs/STANDARDS.md` — Skill standards
- `docs/DESIGN.md` — Architecture overview

---

## Overview

Onboard a brownfield project into Forge by discovering its structure, extracting
existing knowledge (decisions, conventions, constraints, tech stack), and importing
it into Forge's tracking system. The skill adapts to whatever project structure it
finds — it does NOT assume any specific layout, framework, or language.

## Prerequisites

- A codebase exists in the working directory (or a specified path)
- The project is NOT yet tracked by Forge (no `forge_output/{project}/` exists)

---

### Step 1 — Discover Project Structure

Scan the project root for known file categories. Do NOT assume any files exist —
probe and report what is found.

**1A — Project identity** (what is this project?):
Scan for presence of:
- `README.md`, `README.rst`, `README`
- `package.json`, `pyproject.toml`, `setup.py`, `setup.cfg`
- `Cargo.toml`, `go.mod`, `pom.xml`, `build.gradle`
- `composer.json`, `Gemfile`, `mix.exs`

Read the first found to determine: project name, description, language, framework.

**1B — Documentation** (what has been written down?):
Scan for presence of:
- `docs/`, `doc/`, `documentation/`
- `ARCHITECTURE.md`, `DESIGN.md`, `CONTRIBUTING.md`
- `ADR/`, `adr/`, `docs/adr/`, `docs/decisions/`
- `CHANGELOG.md`, `HISTORY.md`
- `TODO.md`, `ROADMAP.md`

**1C — AI instructions** (existing LLM context?):
Scan for presence of:
- `.claude/CLAUDE.md`
- `.cursorrules`, `.cursorignore`
- `.github/copilot-instructions.md`
- `AGENTS.md`, `CLAUDE.md` (root level)
- `CONVENTIONS.md`, `CODING_STANDARDS.md`

**1D — Code standards configuration** (how is code formatted/linted?):
Scan for presence of:
- `.eslintrc*`, `.prettierrc*`, `biome.json`
- `ruff.toml`, `pyproject.toml` (check `[tool.ruff]`, `[tool.black]`, `[tool.mypy]`)
- `tsconfig.json`, `.editorconfig`
- `Makefile`, `justfile`
- `.pre-commit-config.yaml`

**1E — CI/CD** (what automated checks run?):
Scan for presence of:
- `.github/workflows/*.yml`
- `.gitlab-ci.yml`
- `Jenkinsfile`
- `.circleci/config.yml`
- `azure-pipelines.yml`

**1F — Infrastructure** (how is it deployed?):
Scan for presence of:
- `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml`
- `k8s/`, `kubernetes/`, `helm/`
- `terraform/`, `pulumi/`
- `serverless.yml`

**1G — Environment** (what configuration is needed?):
Scan for presence of:
- `.env.example`, `.env.template`, `.env.sample`
- `config/`, `settings/`

Present discovery results as a summary table:

```
## Discovery Results

| Category | Found | Files |
|----------|-------|-------|
| Project Identity | YES | package.json |
| Documentation | YES | docs/ARCHITECTURE.md, CONTRIBUTING.md |
| AI Instructions | YES | .claude/CLAUDE.md |
| Code Standards | YES | .eslintrc.json, .prettierrc |
| CI/CD | YES | .github/workflows/ci.yml |
| Infrastructure | YES | Dockerfile, docker-compose.yml |
| Environment | YES | .env.example |
```

Check lessons from past projects:
```bash
python -m core.lessons read-all
```

---

### Step 2 — Read and Classify Sources

Read each discovered file. For each file, classify the content into extractable
categories:

| Category | What to look for | Maps to |
|----------|------------------|---------|
| **Architecture decisions** | "We chose X because Y", "X is used for Y", framework/DB/API choices | `decisions add` with `type: "architecture"` |
| **Conventions** | "Always use X", "Never do Y", naming rules, code patterns, file structure rules | `decisions add` with `type: "convention"` |
| **Constraints** | "Must support X", "Cannot use Y", compliance requirements, browser support | `decisions add` with `type: "constraint"` |
| **Tech stack** | Languages, frameworks, databases, key libraries | `decisions add` with `type: "dependency"` |
| **Security rules** | Auth requirements, data handling rules, encryption requirements | `decisions add` with `type: "security"` |
| **Test/lint commands** | `npm test`, `pytest`, `ruff check`, CI pipeline commands | `pipeline config` + `gates config` |
| **Known tech debt** | "TODO: refactor X", "HACK:", documented limitations | `lessons add` with `category: "architecture-lesson"` |

**Critical rules for extraction:**

1. **Only extract what is explicitly stated** — do NOT infer or guess.
   If a file says "we use PostgreSQL", record that. If it doesn't mention a DB, don't guess.

2. **Preserve the original wording** in the `reasoning` field.
   Quote the source: `"Per README.md: 'We use PostgreSQL for...'"`

3. **Record the source file** in the `file` field of each decision.
   This creates a traceable link from decision back to its source.

4. **Distinguish confidence levels:**
   - `HIGH` — explicitly documented decision ("We chose X because Y")
   - `MEDIUM` — implied by configuration (e.g., `tsconfig.json` implies TypeScript)
   - `LOW` — inferred from code patterns (e.g., file naming suggests convention)

5. **AI instruction files are highest priority.**
   `.claude/CLAUDE.md` or `.cursorrules` contain curated, intentional instructions.
   Extract every rule, convention, and constraint from these files.

---

### Step 3 — Extract Gate Configuration

Determine test and lint commands from discovered sources. Check in priority order:

**For test commands:**
1. CI config — look for `npm test`, `pytest`, `cargo test`, `go test`, `mix test`, etc.
2. `package.json` `scripts.test` field
3. `pyproject.toml` `[tool.pytest]` section
4. `Makefile` — look for `test:` target
5. Presence of `jest.config.*`, `vitest.config.*`, `pytest.ini`, `conftest.py`

**For lint commands:**
1. CI config — look for `eslint`, `ruff`, `clippy`, `golangci-lint`, etc.
2. `package.json` `scripts.lint` field
3. `.pre-commit-config.yaml` hooks
4. `Makefile` — look for `lint:` target
5. Presence of `.eslintrc*`, `ruff.toml`, `biome.json`

**For type checking:**
1. CI config — `tsc --noEmit`, `mypy`, `pyright`
2. `tsconfig.json` existence
3. `pyproject.toml` `[tool.mypy]` section

Build a list of gate commands. If a command is found in CI config, mark it as
`required: true` (the project already enforces it). If inferred from config files
only, mark as `required: false` (advisory — needs user confirmation).

Present findings:

```
## Detected Gates

| Gate | Command | Source | Required |
|------|---------|--------|----------|
| test | npm test | .github/workflows/ci.yml | true |
| lint | npm run lint | package.json scripts | true |
| typecheck | npx tsc --noEmit | tsconfig.json (inferred) | false |
```

---

### Step 4 — Create Project and Import

Create the Forge project:

```bash
python -m core.pipeline init {project} --goal "Ongoing development of {project-name}"
```

Load contracts before importing (R2, R3):

```bash
python -m core.decisions contract add
python -m core.lessons contract
```

Import decisions in batches by type. Use `decided_by: "imported"` and
`status: "CLOSED"` for established facts, `status: "OPEN"` for things
that need user confirmation.

**Architecture and tech stack decisions:**
```bash
python -m core.decisions add {project} --data '[{
  "task_id": "ONBOARDING",
  "type": "architecture",
  "issue": "Primary framework",
  "recommendation": "FastAPI",
  "reasoning": "Per pyproject.toml: fastapi listed as dependency. Per README.md: \"Built with FastAPI\"",
  "alternatives": [],
  "confidence": "HIGH",
  "status": "CLOSED",
  "decided_by": "imported",
  "file": "README.md"
}]'
```

**Conventions:**
```bash
python -m core.decisions add {project} --data '[{
  "task_id": "ONBOARDING",
  "type": "convention",
  "issue": "Naming convention for API routes",
  "recommendation": "Use kebab-case for URL paths, snake_case for query params",
  "reasoning": "Per CLAUDE.md: \"All API routes use kebab-case\"",
  "alternatives": [],
  "confidence": "HIGH",
  "status": "CLOSED",
  "decided_by": "imported",
  "file": ".claude/CLAUDE.md"
}]'
```

**Constraints:**
```bash
python -m core.decisions add {project} --data '[{
  "task_id": "ONBOARDING",
  "type": "constraint",
  "issue": "Browser support requirement",
  "recommendation": "Must support Chrome, Firefox, Safari latest 2 versions",
  "reasoning": "Per CONTRIBUTING.md: \"We support the latest 2 versions of major browsers\"",
  "alternatives": [],
  "confidence": "HIGH",
  "status": "CLOSED",
  "decided_by": "imported",
  "file": "CONTRIBUTING.md"
}]'
```

**Known tech debt or lessons** (if found):
```bash
python -m core.lessons add {project} --data '[{
  "category": "architecture-lesson",
  "title": "Auth module needs refactoring",
  "detail": "Per TODO.md: auth module uses legacy session-based approach, planned migration to JWT. Any auth changes should consider this.",
  "severity": "important",
  "applies_to": "Any task touching authentication",
  "tags": ["auth", "tech-debt", "refactoring"]
}]'
```

**Rules for import quality:**

- Do NOT create more than 15-20 decisions. Focus on what matters for future work.
- Group related micro-conventions into a single decision (e.g., all naming conventions in one).
- If a convention is already enforced by a linter rule, note that — it's less critical to record.
- Every decision MUST have `file` set to the source file it was extracted from.
- Every `reasoning` field MUST quote or reference the source text.

---

### Step 5 — Configure Gates

Set project configuration with detected commands:

```bash
python -m core.pipeline config {project} --data '{"test_cmd": "npm test", "lint_cmd": "npm run lint"}'
```

Configure validation gates:

```bash
python -m core.gates config {project} --data '[
  {"name": "test", "command": "npm test", "required": true},
  {"name": "lint", "command": "npm run lint", "required": true}
]'
```

Only configure gates for commands that were actually found. Do NOT guess commands.
If no test/lint commands were detected, skip gate configuration and create an
OPEN decision asking the user:

```bash
python -m core.decisions add {project} --data '[{
  "task_id": "ONBOARDING",
  "type": "testing",
  "issue": "No test command detected — how to run tests?",
  "recommendation": "Please specify the test command for this project",
  "reasoning": "Scanned package.json, CI config, Makefile — no test command found",
  "confidence": "LOW",
  "status": "OPEN",
  "decided_by": "claude"
}]'
```

---

### Step 6 — Present and Verify

Show the imported state:

```bash
python -m core.pipeline status {project}
```

Present a summary for user review:

```
## Onboarding Complete: {project}

### Project Profile
- Language: {language}
- Framework: {framework}
- Key dependencies: {deps}

### Imported Knowledge
| Type | Count | Source Files |
|------|-------|-------------|
| Architecture decisions | N | README.md, docs/ARCHITECTURE.md |
| Conventions | N | .claude/CLAUDE.md |
| Constraints | N | CONTRIBUTING.md |
| Tech stack | N | package.json |
| Lessons (tech debt) | N | TODO.md |

### Configured Gates
| Gate | Command | Required |
|------|---------|----------|
| test | npm test | yes |
| lint | npm run lint | yes |

### Open Decisions (need your input)
- D-NNN: {issue} — please confirm or override

### What's Next
- Review imported decisions: `python -m core.decisions read {project}`
- Override anything incorrect: `python -m core.decisions update {project} --data '...'`
- Start planning work: `/plan {your next goal}`
```

**Wait for user confirmation.** The user should:
1. Review the imported decisions for accuracy
2. Override or close any OPEN decisions
3. Confirm that the gate commands are correct

---

## Error Handling

| Error | Action |
|-------|--------|
| No recognizable project files found | Ask user what kind of project this is, where docs are |
| Project already has forge_output/ | Show existing state, ask if user wants to re-onboard or continue |
| AI instruction file references external docs | Follow the references, read those files too |
| Conflicting information between sources | Record as OPEN decision with both sources cited |
| Very large documentation (>1000 lines) | Read in sections, focus on decisions/rules/conventions sections |
| No test or lint commands detected | Create OPEN decision asking user |
| Source file is not UTF-8 | Skip, note in summary |

## Resumability

- Project creation (W1) persists immediately — if interrupted, project exists
- Decisions (W2) are persisted per batch — partial import is saved
- Lessons (W3) are persisted immediately
- Gates (W5) can be re-configured idempotently
- Re-running onboard on existing project is safe — decisions dedup by (task_id, type, issue)
