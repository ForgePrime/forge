# Domain Module: UX/UI

## Triggers

Activated when entity scopes include: `frontend`, `ui`, `ux`, `design`, `components`

## Prerequisites

Before running any phase, **read the codebase** and list what you found:
- Component directory structure (e.g., `components/`, `app/`, `pages/`)
- Existing UI patterns: component library, styling approach, state management
- Similar components (modals, forms, tables, buttons) — patterns to reuse

**You MUST list files read and patterns found before proceeding.**
If you cannot list them, you have not read the codebase.

---

## Phase 1: Vision Extraction

**Used during**: objective definition, idea capture, initial alignment

### Input

- `user_goal` — what the user said they want
- `existing_components` — components found in codebase (from prerequisites)

### Questions to Ask

Pick 2-4 from below based on what you cannot answer from code:

**Layout & Placement** (when goal involves new UI elements):
- "I see [ComponentX] has buttons [A, B, C] in the header. Where does the new [element] go — next to these? In a different section?"
- "New page/route, section within [existing page], or overlay/modal?"

**User Flow** (always ask for interactive features):
- "Walk me through click-by-click: user sees [X], clicks [Y], then what? What do they see next?"
- "When user is done — where do they end up? Back to list? Stay? Redirect?"

**States & Edge Cases** (ask proactively):
- "What does the user see when [data is empty / list has 0 items]?"
- "If [action] fails — error message? Retry option?"
- "If [action] already in progress — disabled button? Status indicator?"

**Never ask**: "What is the scope of UI changes?", "Any design preferences?", "Should it be responsive?"

### Output

Produce and store in **Research (R-NNN)**:

- **user_flows** — step-by-step user interactions, click by click
  Example: "User opens Workflow page → sees 'Execute' in header → clicks → modal with step list → confirms → status Running"

- **ui_placement** — where each element goes, referencing existing components
  Example: `{element: "Execute button", location: "WorkflowHeader.tsx after Edit button", type: "ButtonPrimary with Play icon"}`

- **ui_states** — every state including edge cases
  Example: default (button enabled), empty (disabled + tooltip), running (disabled + spinner), error (enabled + warning)

- **ui_decisions** — explicit decisions: "modal not drawer", "polling not WebSocket"

- **open_questions** — unresolved, passed to Phase 2

---

## Phase 2: Research

**Used during**: discovery, exploration, feasibility assessment

### Input

- `user_flows`, `ui_states`, `ui_placement` — from Phase 1
- If missing: warn and ask user. Do NOT invent user flows.

### What to Research

1. **Existing patterns**: Find similar components, document file path + props + styling.
   "Found `DeleteConfirmModal.tsx` using `DialogPrimitive`. New modal follows same pattern."

2. **Component mapping**: For each element from `ui_placement`, identify exact file, exact insertion point.
   "WorkflowHeader.tsx renders `<div className='flex gap-2'>`. Execute button goes inside this div."

3. **Resolve open questions**: Answer from codebase or ask user.

4. **Edge case analysis**: For each `ui_state`, verify existing handling patterns.

### Output

Store in **Research (R-NNN updated) + Knowledge (K-NNN)** for durable artifacts:

- **component_mapping** — exact files to create/modify with locations
- **existing_patterns** — patterns that MUST be followed, with source file
- **resolved_questions** — answers to Phase 1 open questions
- **edge_cases** — with decided handling

---

## Phase 3: Planning

**Used during**: task decomposition, plan creation

### Input

- `component_mapping`, `existing_patterns` — from Phase 2
- `user_flows`, `ui_states` — from Phase 1

### Decomposition Strategy

Use **component-centric decomposition**:

Good: `Create ExecuteWorkflowModal` / `Add Execute button to WorkflowHeader` / `Connect modal to API`
Bad: `Implement workflow execution UI` / `Handle edge cases`

### Task Rules

**instruction** must reference: exact file, exact pattern source, exact location within file.

**acceptance_criteria** — use `Given {component state} When {user interaction} Then {visual + data change}` format. One AC per `ui_state` minimum:
- "Given workflow has steps, When user opens modal, Then modal shows numbered step list"
- "Given 0 steps, When user opens modal, Then modal shows 'No steps defined' AND Confirm disabled"
- "Given execution running, When user views header, Then Execute button disabled, shows 'Running...'"

**exclusions** — what NOT to modify, NOT to implement:
- "Do NOT modify WorkflowList.tsx"
- "Do NOT add step editing in execute modal"

### Output

Store in **Task fields**: instruction, acceptance_criteria, exclusions, alignment.

---

## Phase 4: Execution

**Used during**: task implementation, verification

### Checklist

Before: Read pattern source file, read target file, check imports.
During: Follow pattern exactly, handle ALL states from AC, do NOT add unlisted behavior.
After: For each AC — is state in code? For each exclusion — did I touch forbidden files?

### Micro-review (max 5 lines)

```
T-003 done: Created ExecuteWorkflowModal.
- New file: components/workflow/ExecuteWorkflowModal.tsx
- Pattern: follows DeleteConfirmModal (DialogPrimitive)
- States: default (step list), empty (no steps msg), loading (spinner)
- Excluded: execution history, step editing
Is this what you wanted?
```

---

## Cross-module Interface

### Provides to other modules

| To | Data | Purpose |
|----|------|---------|
| Backend | `user_flows` → required API calls | Backend knows what endpoints UX needs |
| Backend | `ui_states` → error states | Backend knows what errors to return distinctly |
| Process | `user_flows` → trigger points | Process knows which UI actions trigger state changes |

### Needs from other modules

| From | Data | Purpose |
|------|------|---------|
| Backend | `api_contracts` → response shapes | UX knows what data to display |
| Backend | `error_codes` → distinct errors | UX knows which error messages to show |
| Process | `state_transitions` → valid states | UX knows which states to render |
| Data | `entity_schema` → field names/types | UX knows what fields to show in forms/tables |
