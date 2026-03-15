---
name: domain-modules
id: SKILL-DOMAIN-MODULES
version: "1.0"
description: "Orchestrator for domain-specific modules that guide vision extraction, research, planning, and execution across different technical domains."
---

# Domain Modules — Orchestrator

## Purpose

Generic alignment, planning, and execution skills produce generic output.
Domain modules produce **domain-specific** output — the right questions,
the right AC format, the right edge cases for each technical area.

This orchestrator selects and combines modules based on the objective/idea/task scopes.

## Available Modules

| Module | File | Scopes that trigger it |
|--------|------|----------------------|
| UX/UI | `modules/ux.md` | `frontend`, `ui`, `ux`, `design`, `components` |
| Backend | `modules/backend.md` | `backend`, `api`, `server`, `services` |
| Process/Workflow | `modules/process.md` | `workflow`, `process`, `state-machine`, `orchestration`, `automation` |
| Data | `modules/data.md` | `database`, `data`, `schema`, `migration`, `storage`, `etl` |

## When to Use

This skill is invoked **by other skills**, not directly by the user.
Skills that should invoke domain modules:

- `skills/deep-align/SKILL.md` — during vision extraction (objective, idea)
- `skills/plan/SKILL.md` — during task decomposition
- `skills/next/SKILL.md` — during task execution
- `skills/discover/SKILL.md` — during research/exploration
## How to Use (for calling skills)

### Step 1 — Determine active scopes

Read scopes from the current entity (objective, idea, or task):

```
entity.scopes = ["frontend", "backend", "workflow"]
```

### Step 2 — Load matching modules via Python server

The Python server handles scope matching, phase extraction, and multi-module merging:

```bash
# Load all matching modules for given scopes and phase:
python -m core.domain_modules for-scopes --scopes "{scopes}" --phase {phase}

# Or load a specific module + phase:
python -m core.domain_modules get {module} --phase {phase}

# Check cross-module dependencies:
python -m core.domain_modules deps {module1} {module2}
```

The `for-scopes` command automatically:
- Maps scopes to modules (multiple can match)
- Extracts only the requested phase (~35 lines per module, not 175)
- Shows cross-module dependencies when 2+ modules are active
- Skips bug/chore tasks via `--task-type` complexity gate

| Your current activity | Phase to request |
|----------------------|-----------------|
| Defining objective / extracting vision | `--phase vision` |
| Research / discovery / exploration | `--phase research` |
| Planning / task decomposition | `--phase planning` |
| Executing a task | `--phase execution` |

### Step 3 — Merge outputs from multiple modules

When multiple modules are active, their outputs are **merged, not concatenated**.
Rules:

1. **Questions**: Combine questions from all active modules. Remove duplicates. Group by module for clarity. Cap at 6-8 questions total — prioritize by impact.

2. **Output artifacts**: Each module produces its own section in the output. Example for objective with scopes `[frontend, backend]`:
   ```
   ## UX Vision
   user_flows: [...]
   ui_states: [...]
   
   ## Backend Vision  
   api_contracts: [...]
   error_scenarios: [...]
   ```

3. **Cross-module dependencies**: When module A's output affects module B, note it explicitly:
   ```
   ## Cross-domain Dependencies
   - UX flow "user clicks Execute" requires Backend endpoint POST /api/workflows/{id}/execute
   - Backend state change "workflow → RUNNING" must trigger UX state update (polling or WebSocket)
   ```

4. **Conflicts**: If modules suggest conflicting approaches, surface them as decisions for the user — do NOT resolve silently.

### Step 4 — Validate chain continuity

Before producing output, check:

- **Does this phase's output contain everything the NEXT phase expects as input?**
  Each module defines `input_contract` and `output_contract` per phase.
  If current phase output is missing a field that next phase input requires → ask the user for it NOW.

- **Does this phase's input contain everything it expected from the PREVIOUS phase?**
  If missing → warn and either ask user or derive from context.

## Anti-patterns

| Anti-pattern | Why it's bad | What to do instead |
|-------------|-------------|-------------------|
| Skipping modules because "it's obvious" | Hidden assumptions = drift | Always run matching modules, even if output seems predictable |
| Asking 15 questions across 3 modules | User overload | Prioritize: max 6-8 questions total, grouped by impact |
| Module produces generic output | Defeats the purpose | Output must reference SPECIFIC files, components, endpoints from the actual codebase |
| Ignoring cross-module dependencies | Integration breaks at execution | Always produce cross-domain dependency list when 2+ modules active |
| Running module without reading codebase first | Questions are theoretical, not grounded | Read relevant code BEFORE generating module questions |

## Scope Discovery

If the entity doesn't have scopes yet (e.g., user just said "I want to add workflow execution"),
determine scopes from the description:

1. Does it mention UI/display/buttons/pages? → add `frontend`
2. Does it mention API/endpoints/services? → add `backend`  
3. Does it mention states/transitions/flows? → add `workflow`
4. Does it mention tables/schemas/queries? → add `database`
5. If unclear → ask user: "This seems to touch [X] and [Y]. Does it also involve [Z]?"

## Adding New Modules

To add a domain module:

1. Create `skills/domain-modules/modules/{name}.md` following the 4-phase structure
2. Define input/output per phase with `## Phase N:` markers
3. Add scope mappings to `MODULES` registry in `core/domain_modules.py`
4. Add to the Available Modules table above
5. Ensure output of Phase N matches input expectations of Phase N+1
