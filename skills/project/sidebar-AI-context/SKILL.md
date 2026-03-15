---
name: sidebar-ai-context
id: SKILL-SIDEBAR-AI-CONTEXT
version: "1.0"
description: "Entity-scoped AI sidebar with context binding, context extension, and auto-attached entity skills."
entity_types: [objective, idea, task, decision, guideline, knowledge, research]
scopes: [frontend, backend, ai, llm, skills]
---

# Sidebar AI Context

## Identity

| Field | Value |
|-------|-------|
| ID | SKILL-SIDEBAR-AI-CONTEXT |
| Version | 1.0 |
| Description | Implement entity-scoped AI conversations with context binding, user-driven context extension, and auto-attached entity skills. Covers O-009, O-012, O-013. |

## Objectives Covered

| Objective | Title | Appetite | Dependency |
|-----------|-------|----------|------------|
| O-009 | Entity-Scoped AI Conversations | medium | foundation — no blocker |
| O-012 | Chat Context Extension | small | depends on O-009 |
| O-013 | Entity Skill Config, Auto-Attach & Base Skills | medium | depends on O-009 |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (Next.js 14 + React 18 + Zustand)             │
│                                                          │
│  DAG Node ──┐                                            │
│  Detail Page ┼── onClick "AI Assistant" ──→ Sidebar      │
│  List Page ──┘                              │            │
│                                              ▼            │
│  ┌──────────────────────────────────────────────────┐    │
│  │ AI Sidebar                                       │    │
│  │  ┌─ EntityBadge {type, id, title}               │    │
│  │  ├─ SkillPicker (auto-attach or manual)         │    │
│  │  ├─ AddContextButton → EntitySearchDropdown     │    │
│  │  │    └─ ContextChips [max 5, removable]        │    │
│  │  ├─ ConversationsTab (filtered by entity)       │    │
│  │  ├─ TokenCounter (used / budget, color-coded)   │    │
│  │  └─ WorkflowProgress (if workflow session)      │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  sidebarStore (Zustand):                                 │
│    targetEntity: {type, id} | null                       │
│    additionalContexts: EntityRef[] (max 5)               │
│    activeSkill: SkillRef | null                          │
│    defaultScopes: Record<EntityType, string[]>           │
│    addedScopes / removedScopes                           │
└──────────────────┬───────────────────────────────────────┘
                   │ POST /llm/chat
                   │ { target_entity, additional_contexts, skill }
                   ▼
┌──────────────────────────────────────────────────────────┐
│  Backend (FastAPI + Python 3.11 + Redis Stack 7.4)       │
│                                                          │
│  ChatRequest                                             │
│    target_entity_type + target_entity_id (existing)      │
│    additional_contexts: [{type, id}] (new)               │
│    skill_id: str | null (new)                            │
│                                                          │
│  context_resolver.py                                     │
│    resolve(entity_type, entity_id) → context string      │
│    ~500 tokens per entity                                │
│    respects token_budget from ContextWindowManager       │
│                                                          │
│  SessionManager                                          │
│    Redis TTL: 7-30 days (extended from 24h)              │
│    Secondary index: entity_type + entity_id              │
│    GET /llm/sessions?entity_type=X&entity_id=Y           │
│                                                          │
│  ContextWindowManager (existing T-045)                   │
│    Pin last 5 tool results + summary every 10 msgs       │
│    Sliding window, 30k token budget (configurable)       │
│                                                          │
│  entity_skills config (project_config)                   │
│    {objective: [...], idea: [...], task: [...]}           │
│    Skill frontmatter: entity_types, contract_refs        │
└──────────────────────────────────────────────────────────┘
```

## ADRs (Architecture Decision Records)

These decisions are already recorded (D-026 through D-028). Follow them — do NOT redesign.

### ADR-1: Slash Command Router (frontend-side)

SlashCommandRouter lives in frontend. Maps `/command` to `{skill, session_type, initial_hint}`. Already implemented (T-043 DONE).

### ADR-2: Workflow State Machine (session-level, soft enforcement)

WorkflowStateMachine on backend ChatSession. Tracks steps, warns on deviation, does NOT hard-block. Already implemented (T-044 DONE).

### ADR-3: Context Window Manager (hybrid pinning)

Pin last 5 tool results + auto-generated session summary every 10 messages + sliding window. Budget 30k tokens. Already implemented (T-045 DONE).

### ADR-4: Entity Inline Cards (post-processing)

Regex detects `T-/D-/O-/I-/K-/G-/R-/L-/AC-` patterns in LLM responses. Renders clickable cards with status/summary. Already implemented (T-046 DONE).

### ADR-5: Archive/Remove vs Hard DELETE

Entities use archive/remove (soft delete), not hard DELETE. Already decided — follow this for all entity operations in the sidebar.

## Completed Foundation (reference only)

These tasks are DONE. Reference their patterns when implementing new work:

| Task | Name | What it built |
|------|------|---------------|
| T-043 | slash-command-router | `SlashCommandRouter` — maps commands to skills/session types |
| T-044 | workflow-state-machine | `WorkflowStateMachine` — multi-step workflow tracking |
| T-045 | context-window-manager | `ContextWindowManager` — token budget + hybrid pinning |
| T-046 | entity-inline-cards | `EntityInlineCard` — clickable entity refs in chat messages |
| T-047 | improve-tool-descriptions | `ENTITY:` prefix on all create/update tools |
| T-048 | session-type-behavior | `_SESSION_GUIDANCE` — per-session-type system prompt hints |
| T-049 | workflow-progress-ui | `WorkflowProgress` — step indicator in sidebar |
| T-050 | token-counter-ui | `TokenCounter` — used/budget display with color coding |

---

## Phase 1 — Entity-Scoped AI Conversations (O-009)

Foundation phase. Makes every entity in the system AI-conversable.

### 1.1 — Entity Context Binding

**Goal**: Clicking "AI Assistant" on a DAG node or entity detail page opens the sidebar with that entity's context auto-loaded.

**Frontend**:

a. Extend `sidebarStore` (Zustand) with:
```typescript
targetEntity: { type: EntityType; id: string } | null
```

b. When user clicks "AI Assistant":
- Set `targetEntity` in store
- Call `context_resolver` via the chat API (backend handles resolution)
- Display `EntityBadge` at top of sidebar showing entity type icon, ID, and title

c. Entry points — two trigger patterns:
- **DAG node**: Add "AI Assistant" option to `NodeContextMenu` (right-click menu on DAG nodes)
- **Detail page**: Add "AI Assistant" button/icon on entity detail page header (next to edit/delete)

d. Both triggers set `targetEntity` and open the sidebar. The sidebar does NOT need to know where the trigger came from.

**Backend**:

a. `ChatRequest` already has `target_entity_type` and `target_entity_id` fields. Verify they are passed through to `context_resolver.py` and injected into the system prompt.

b. `context_resolver.py` must handle all entity types:
- objective, idea, task, decision, guideline, knowledge, research, lesson, ac_template
- Each type resolves to a context string (~500 tokens) with key fields

c. Verify: `context_resolver` is called on first message in a session when `target_entity` is set.

**Acceptance criteria**:
- Clicking AI on DAG node opens sidebar with entity context auto-loaded
- Clicking AI on detail page opens sidebar with entity context auto-loaded
- EntityBadge displays entity type, ID, and title at the top of sidebar
- Context passed to LLM system prompt contains entity-specific data

### 1.2 — Session Persistence by Entity

**Goal**: AI conversations are persisted per entity with longer TTL. Users can resume or start new conversations per entity.

**Backend**:

a. Extend `SessionManager` in Redis:
- TTL: 7–30 days (configurable, up from 24h)
- Secondary index by `entity_type + entity_id` (for efficient lookup)

b. New query parameter on sessions endpoint:
```
GET /llm/sessions?entity_type=objective&entity_id=O-001
```
Returns sessions scoped to that entity, sorted by last activity.

**Frontend**:

a. `ConversationsTab` in sidebar:
- When `targetEntity` is set: show sessions filtered by that entity
- "Show all" toggle to see all sessions
- "New conversation" button creates a fresh session for the current entity
- Click on existing session resumes it (load messages from Redis)

**Acceptance criteria**:
- Sessions persist 7+ days (not 24h)
- Sessions filterable by entity_type + entity_id via API
- ConversationsTab shows entity-scoped sessions by default
- "Show all" toggle shows all sessions
- New conversation button works per entity
- Resume previous conversation per entity works

### 1.3 — Default Scopes per Entity Type

**Goal**: When opening AI for an entity, appropriate scopes are auto-applied based on entity type.

**Configuration** (in project config):
```json
{
  "entity_type_defaults": {
    "objective": { "scopes": ["*"] },
    "idea": { "scopes": ["inherit_from_objective"] },
    "task": { "scopes": ["task_specific"] },
    "decision": { "scopes": ["inherit_from_task"] },
    "guideline": { "scopes": ["guideline_scope"] },
    "knowledge": { "scopes": ["knowledge_scope"] }
  }
}
```

**Frontend** — extend `sidebarStore`:
- On `targetEntity` change: look up defaults from project config
- Apply default scopes (can be overridden via `addedScopes/removedScopes`)
- `"*"` means all scopes (for objectives — they see everything)
- `"task_specific"` means only the scopes from the task's own `scopes` field

**Acceptance criteria**:
- Objective opens AI with all scopes
- Task opens AI with task-specific scopes only
- Default scopes configurable in project config
- User can override defaults via addedScopes/removedScopes

---

## Phase 2 — Chat Context Extension (O-012)

Additive phase. Lets users enrich AI context with additional entities beyond the target.

### 2.1 — Add Context Button & Entity Search

**Goal**: "Add context" button in sidebar opens a searchable dropdown to find and add entities.

**Frontend**:

a. `AddContextButton` — positioned below EntityBadge:
- Opens a searchable dropdown on click
- Search input with debounce (300ms)
- Results grouped by entity type (objectives, ideas, tasks, decisions, etc.)
- Each result shows: type badge, ID, title/name, status

b. Search backend — reuse existing `searchEntities` endpoint:
- Query by ID or name substring
- Filter by entity type (optional)
- Return top 10 results per type

c. On selection:
- Add entity to `additionalContexts` array in `sidebarStore`
- Call `context_resolver` for the selected entity
- Inject resolved context into system prompt as `additional_contexts`
- Show as removable chip in sidebar

**Backend**:

a. Extend `ChatRequest` with:
```python
additional_contexts: list[dict] | None  # [{type: str, id: str}]
```

b. In chat handler, resolve each additional context via `context_resolver`:
- Respect token budget from `ContextWindowManager`
- ~500 tokens per entity, max 5 entities = ~2500 tokens additional
- If budget exceeded, warn user (do NOT silently drop context)

**Acceptance criteria**:
- Add context button opens searchable dropdown
- Search works by ID and name, results grouped by entity type
- Selected entity context loaded via context_resolver
- Token budget respected (warn if exceeded)
- Max 5 additional contexts

### 2.2 — Context Chips (display & removal)

**Goal**: Added contexts visible as removable chips. `@mention` stays display-only.

**Frontend**:

a. `ContextChips` component — renders below AddContextButton:
- Each chip shows: entity type icon + ID + short title
- "x" button to remove
- Max 5 chips (AddContextButton disabled when at limit)
- Chips persist for the session (stored in sidebarStore and on session in Redis)

b. `@mention` (EntityInlineCard in chat input) — NO CHANGES:
- Remains display-only
- Does NOT add to additionalContexts
- Keeps current behavior from T-046

**Acceptance criteria**:
- Added contexts shown as chips with type icon, ID, title
- Remove button on each chip works
- Max 5 enforced (button disabled at limit)
- @mention behavior unchanged (display-only)
- Chips persist within session

---

## Phase 3 — Entity Skills Config & Auto-Attach (O-013)

Skill system phase. Assigns domain skills to entity types with intelligent auto-attachment.

### 3.1 — Entity Skills Configuration

**Goal**: Map entity types to skills in project config. Skills know which entities they serve.

**Backend — project config extension**:
```json
{
  "entity_skills": {
    "objective": ["objective-definer"],
    "idea": ["idea-explorer"],
    "task": ["task-executor"],
    "decision": [],
    "guideline": [],
    "knowledge": []
  }
}
```

- Validate that referenced skills exist (SKILL.md files present)
- CRUD via project settings UI

**Skill frontmatter extension** — add to SKILL.md:
```yaml
entity_types: [objective]
contract_refs:
  - core.objectives.contract.add
  - core.objectives.contract.update
```

- `entity_types`: which entity types this skill serves
- `contract_refs`: which Forge contracts the skill uses (for tool guidance)

**Acceptance criteria**:
- entity_skills mapping in project config with validation
- Skill frontmatter supports entity_types and contract_refs
- Config CRUD via UI settings page
- Invalid skill references produce validation error

### 3.2 — Auto-Attach & Skill Picker

**Goal**: When opening AI for an entity, matching skills are auto-attached or offered via picker.

**Frontend logic** (in sidebar open flow):

```
On targetEntity change:
  skills = entity_skills[targetEntity.type]

  if skills.length === 0:
    → no skill attached (plain chat)
  if skills.length === 1:
    → auto-select that skill (inject SKILL.md into session)
  if skills.length > 1:
    → show SkillPicker with options:
      - Each skill: name + description from frontmatter
      - "AI choose" option: LLM reads skill descriptions and picks
```

**SkillPicker component**:
- Dropdown or radio group
- Shows skill name + 1-line description
- "AI choose" option sends all skill descriptions to LLM, LLM picks best match
- Selection stored on session (persists on resume)

**Backend — "AI choose" flow**:
- Receive candidate skill descriptions (~100 tokens each, max 10 skills = 1000 tokens)
- Prepend to first message: "Choose the most relevant skill for this entity and conversation"
- LLM responds with skill choice + reasoning (logged, not shown to user)
- Selected skill injected into session

**Acceptance criteria**:
- 0 skills → plain chat (no picker)
- 1 skill → auto-select, no picker
- 2+ skills → SkillPicker shown
- "AI choose" option works (LLM selects from descriptions)
- Selected skill persists on session resume

### 3.3 — Base Entity Skills (Starter Pack)

**Goal**: Minimum 3 working entity skills as starter pack.

**Skills to create** (in `skills/entity/` or project-specific location):

#### objective-definer
```yaml
name: objective-definer
entity_types: [objective]
contract_refs: [core.objectives.contract.add, core.objectives.contract.update]
```
- Guides defining objectives with measurable KRs
- Uses contracts to validate structured output
- Helps formulate SMART key results
- Suggests scopes and assumptions

#### idea-explorer
```yaml
name: idea-explorer
entity_types: [idea]
contract_refs: [core.ideas.contract.add, core.ideas.contract.update]
```
- Explores an idea's feasibility and implications
- Identifies relations (depends_on, related_to, supersedes)
- Suggests advances_key_results links to objectives
- Recommends parent/child hierarchy

#### task-executor
```yaml
name: task-executor
entity_types: [task]
contract_refs: [core.pipeline.contract.add-tasks, core.pipeline.contract.update-task]
```
- Assists with task execution within AI sidebar
- Loads task context (dependencies, guidelines, knowledge)
- Helps with implementation decisions
- Guides through acceptance criteria verification

**Acceptance criteria**:
- 3 skills created with correct frontmatter (entity_types, contract_refs)
- Each skill is a complete SKILL.md with steps
- Skills work end-to-end: entity → auto-attach → guided conversation
- Contract refs point to valid contracts

---

## Risk Mitigations

Follow these mitigations from the risk assessment (deep-risk analysis):

| Risk | Severity | Mitigation |
|------|----------|------------|
| LLM Tool Confusion (42+ tools) | HIGH (18) | `ENTITY:` prefix on tools (T-047 done). Keep tool descriptions explicit. |
| Data Loss from DELETE | HIGH (16) | Archive/remove semantics only (ADR-5). No hard delete via sidebar. |
| Context Window Exhaustion | HIGH (15) | ContextWindowManager (T-045 done). Max 5 additional contexts. Token counter (T-050 done). |
| Slash Command Ambiguity | MEDIUM (14) | SlashCommandRouter (T-043 done). Skill descriptions for disambiguation. |
| Workflow State Drift | MEDIUM (14) | WorkflowStateMachine soft enforcement (T-044 done). |

## Integration Points

### Existing Components to Extend (not replace)

| Component | Location | Extension |
|-----------|----------|-----------|
| `sidebarStore` | frontend Zustand store | Add `targetEntity`, `additionalContexts`, `activeSkill`, `defaultScopes` |
| `ChatRequest` | backend Pydantic model | Add `additional_contexts`, `skill_id` fields |
| `context_resolver.py` | backend | Verify all entity types covered |
| `SessionManager` | backend Redis | Extend TTL, add entity index |
| `NodeContextMenu` | frontend DAG component | Add "AI Assistant" option |
| `project_config` | backend/frontend | Add `entity_type_defaults`, `entity_skills` |

### DO NOT Modify

- `EntityInlineCard` behavior (display-only @mentions — T-046)
- `SlashCommandRouter` mapping (T-043 — already complete)
- `WorkflowStateMachine` logic (T-044 — already complete)
- `ContextWindowManager` algorithm (T-045 — already complete)
- `TokenCounter` UI (T-050 — already complete)

## Task Decomposition Guide

When planning tasks from this skill (via `/plan`), use this phasing:

```
Phase 1 (O-009) — Entity Binding:
  _1: backend-entity-session-persistence   (Redis TTL + entity index)
  _2: backend-additional-contexts          (ChatRequest extension)
  _3: frontend-sidebar-target-entity       (sidebarStore + EntityBadge)
  _4: frontend-dag-ai-trigger              (NodeContextMenu extension)
  _5: frontend-detail-page-ai-trigger      (detail page header button)
  _6: frontend-conversations-entity-filter (ConversationsTab filtering)
  _7: frontend-default-scopes              (entity_type_defaults in config)

Phase 2 (O-012) — Context Extension:
  _8: frontend-add-context-button          (searchable dropdown, depends _3)
  _9: backend-resolve-additional-contexts  (context_resolver + budget, depends _2)
  _10: frontend-context-chips              (display + removal, depends _8)

Phase 3 (O-013) — Entity Skills:
  _11: backend-entity-skills-config        (project config extension)
  _12: skill-frontmatter-extension         (entity_types + contract_refs)
  _13: frontend-skill-auto-attach          (auto-select or picker, depends _11)
  _14: frontend-ai-choose-skill            (LLM skill selection, depends _13)
  _15: create-base-entity-skills           (3 starter skills, depends _12)
```

Assign scopes per task: `_1–_2, _9, _11`: `[backend, ai]`; `_3–_8, _10, _13–_14`: `[frontend, ai]`; `_12, _15`: `[skills, ai]`.

## Success Criteria

- [ ] Every entity type accessible via AI sidebar (DAG node + detail page)
- [ ] Entity context auto-loaded via context_resolver on sidebar open
- [ ] Sessions persist 7+ days with entity-based filtering
- [ ] ConversationsTab filtered by active entity (with "show all" toggle)
- [ ] Default scopes per entity type configurable and applied
- [ ] "Add context" button with searchable entity dropdown
- [ ] Additional contexts resolved and injected (max 5, token budget respected)
- [ ] Context chips with removal (display-only @mention unchanged)
- [ ] entity_skills mapping in project config with validation
- [ ] Auto-attach (1 skill) and picker (2+ skills) work correctly
- [ ] "AI choose" option lets LLM select best skill
- [ ] 3 base entity skills functional end-to-end
- [ ] No hard DELETE — archive/remove only
- [ ] Token counter warns at 80% budget

## References

- `forge_output/forge-web/objectives.json` — O-009, O-012, O-013 definitions
- `forge_output/forge-web/research/deep-explore-entity-management-via-ai-sidebar---option-exploration.md`
- `forge_output/forge-web/research/deep-architect-entity-management-via-ai-sidebar---architecture-design.md`
- `forge_output/forge-web/research/deep-risk-entity-management-via-ai-sidebar---risk-assessment.md`
- `forge_output/forge-web/research/deep-feasibility-entity-management-via-ai-sidebar---feasibility-assessment.md`
- `forge_output/forge-web/decisions.json` — D-026 (slash router), D-027 (workflow SM), D-028 (context manager)
