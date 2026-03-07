# Assumptions & Deferred Decisions

This file tracks every assumption made during development and every decision deferred for later.
Updated as assumptions are validated or invalidated.

---

## Active Assumptions

### A-001: Single project at a time (for now)
- **Assumed**: Forge manages one project/goal at a time per working directory
- **Why**: Simplifies pipeline state. Multi-project needs orchestration layer.
- **Risk**: Low — can extend later without breaking core
- **Deferred to**: v2 (multi-agent support)

### A-002: ~~Git is always available~~ RESOLVED
- **Decision**: Git is recommended but optional. Forge works without git (with warnings).
- **Why resolved**: `core/git_ops.py` implements graceful degradation — all git operations are optional. `changes diff` requires git, but `changes record` works without it.
- **Resolved in**: v1.0, `core/git_ops.py`

### A-003: Python 3.8+ available
- **Assumed**: Target runtime is Python 3.8 or later
- **Why**: Using type hints, pathlib, f-strings. No match/case used anywhere.
- **Risk**: Low — Claude Code environments typically have modern Python

### A-004: Claude Code is the primary (but not only) consumer
- **Assumed**: SKILL.md files are read by Claude Code, but core/ tools work standalone
- **Why**: Core tools are plain CLI — any LLM or human can use them
- **Risk**: None — this is a feature, not a limitation

### A-005: Task graph is a DAG (no cycles)
- **Assumed**: Tasks can depend on other tasks, but no circular dependencies
- **Why**: Simplifies pipeline execution. Cycles would require iteration semantics.
- **Risk**: Low — real development workflows are naturally DAGs
- **Mitigation**: Validation at task creation time

### A-006: Skills are file-based, not package-based
- **Assumed**: A skill is a directory with SKILL.md + optional Python tools
- **Why**: Matches Skill_v1 pattern. Easy to read, copy, customize.
- **Risk**: Doesn't scale to hundreds of skills
- **Mitigation**: `core/plugins.py` provides a skill registry with auto-discovery for external skill packs

### A-007: Output format is JSON for machines, Markdown for LLM
- **Assumed**: Python CLI commands output Markdown (for LLM consumption), internal state is JSON
- **Why**: Proven in Skill_v1 — LLM reads Markdown better than raw JSON
- **Risk**: None — well-proven pattern

### A-008: Windows compatibility required
- **Assumed**: Must work on Windows (user's environment is Windows 11)
- **Why**: Current development environment
- **Impact**: UTF-8 workarounds, path handling, no Unix-specific features
- **Applied**: All Python files include the win32 UTF-8 reconfigure block

---

## Deferred Decisions

### DD-001: How to handle multi-file changes in a single task
- **Options**: (a) One change record per file, (b) One change record per logical change spanning files
- **Leaning toward**: (a) per-file, with a `group_id` linking related changes
- **Decide when**: When implementing the `implement` skill

### DD-002: How deep should reasoning traces go
- **Options**: (a) High-level only (1-3 steps), (b) Full chain-of-thought per decision
- **Leaning toward**: (b) full, but with a `detail_level` flag to control verbosity
- **Decide when**: When implementing the first real skill execution

### DD-003: ~~Should Forge manage git branches~~ RESOLVED
- **Decision**: Forge provides optional git integration (`core/git_ops.py`)
- **Approach**: Hybrid — Forge can create branches (`branch-create`) and commit with metadata (`commit`), but never force-pushes or deletes branches. User retains full control. All git ops are optional — Forge works without git.
- **Resolved in**: v1.0, `core/git_ops.py`

### DD-004: ~~How to handle failed gates~~ RESOLVED
- **Decision**: Gates report pass/fail, required gates block completion advisory (LLM decides)
- **Approach**: `core/gates.py` runs configured commands, stores results on task. Required gate failure prints warning but doesn't mechanically block `pipeline complete` — the skill procedure (`skills/next/SKILL.md`) instructs the LLM to fix before completing. This keeps Python as pure I/O, LLM as judge.
- **Resolved in**: v1.0, `core/gates.py`

### DD-005: ~~Skill discovery and registration~~ RESOLVED
- **Decision**: Auto-discovery from configured scan paths via `core/plugins.py`
- **Approach**: `plugins add-path` registers external skill pack directories. `plugins scan` discovers all `*/SKILL.md` subdirectories, parses YAML frontmatter, persists registry in `forge_plugins.json`. `/process {name}` executes discovered skills.
- **Resolved in**: v1.0, `core/plugins.py`

### DD-006: How to handle context window limits
- **Options**: (a) Rely on Claude Code's built-in compaction, (b) Forge-level context management
- **Leaning toward**: (a) for now, with (b) as future enhancement
- **Decide when**: When tasks start exceeding context limits in practice

### DD-007: Integration with existing project management tools
- **Options**: (a) Forge is standalone, (b) Two-way sync with Jira/GitHub Issues
- **Leaning toward**: (a) standalone first, with export capabilities
- **Decide when**: When user requirements are clearer

### DD-009: traces.py — per-task execution traces
- **Issue**: DESIGN.md mentions `core/traces.py` for aggregating execution traces, but it's not yet implemented
- **Current state**: Changes already have `reasoning_trace` per change record. The question is whether we need a separate trace aggregation module or if changes.py is sufficient.
- **Leaning toward**: Defer — changes.py covers the essential traceability. Add traces.py only if we need cross-task trace analysis.
- **Decide when**: After real-world usage reveals whether change-level traces are sufficient

### DD-010: ~~Skills directory — which skills to build first~~ RESOLVED
- **Decision**: Built plan, next (implement), and review skills
- **Skills built**: `skills/plan/SKILL.md` (goal decomposition), `skills/next/SKILL.md` (task execution with full traceability), `skills/review/SKILL.md` (structured code review)
- **Remaining**: test skill (can be added when needed, gates cover automated testing)
- **Resolved in**: v1.0

### DD-008: Change record granularity for non-code artifacts
- **Issue**: Should Forge track changes to configs, docs, tests the same as code?
- **Leaning toward**: Yes, same change records for all file types
- **Decide when**: When implementing the change tracking system

---

## Validated Assumptions (moved from Active)

(None yet — project just started)

---

## Invalidated Assumptions (moved from Active)

### ~~A-002: Git is always available~~
- **Was**: Assumed git is required
- **Reality**: Git is optional. `core/git_ops.py` provides graceful degradation.
- **Moved**: A-002 now marked RESOLVED in Active section above
