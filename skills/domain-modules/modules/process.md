# Domain Module: Process / Workflow

## Triggers

Activated when entity scopes include: `workflow`, `process`, `state-machine`, `orchestration`, `automation`

## Prerequisites

Before running any phase, **read the codebase** and list what you found:
- Existing state machines or workflow engines
- Status/state fields on models — values, transitions
- Event/notification patterns for state changes
- Job/queue infrastructure: background processing, workers

**You MUST list files read and patterns found before proceeding.**
If you cannot list them, you have not read the codebase.

---

## Phase 1: Vision Extraction

**Used during**: objective definition, idea capture, initial alignment

### Input

- `user_goal` — what the user said they want
- `existing_states` — states found in codebase (from prerequisites)

### Questions to Ask

Pick 2-4 from below based on what you cannot answer from code:

**States** (always ask — this is the foundation):
- "I see [entity] has states [X, Y, Z]. What new states? Draw me the complete lifecycle start to finish."
- "Terminal state? Or can [entity] go back? Example: can COMPLETED be re-executed?"

**Transitions** (always ask — defines behavior):
- "For each state change — what triggers it? User action, system event, timer?"
- "Forbidden transitions? Example: RUNNING → DRAFT should never happen?"
- "Concurrent transitions? Two users cancel the same execution?"

**Side Effects** (ask proactively):
- "When entering state [X] — anything else happens? Notifications, cleanup, cascading updates?"
- "If transition fails halfway — rollback to previous? Move to ERROR?"

**Boundaries**:
- "Whole lifecycle or just one part? Building the engine or just state tracking?"
- "Who can trigger transitions? Any user? Admin? System only?"

**Never ask**: "Should we use a state machine library?", "What about error handling?", "Should states be persisted?"

### Output

Produce and store in **Research (R-NNN)**:

- **state_diagram** — complete state machine: all states, which are initial/terminal
  Example: PENDING (initial) → RUNNING → COMPLETED (terminal) | FAILED | CANCELLED (terminal)

- **state_transitions** — every allowed transition with trigger, condition, side effects
  Example: `{from: RUNNING, to: CANCELLED, trigger: user, condition: has permission, side_effects: [abort step, emit event]}`

- **forbidden_transitions** — explicitly prevented with reason
  Example: `{from: COMPLETED, to: RUNNING, reason: "Immutable. Create new execution."}`

- **failure_modes** — what happens when transitions fail
  Example: "System crash during PENDING → RUNNING: startup recovery finds stuck executions"

- **permissions** — who can trigger which transitions

- **open_questions** — unresolved, passed to Phase 2

---

## Phase 2: Research

**Used during**: discovery, exploration, feasibility assessment

### Input

- `state_diagram`, `state_transitions` — from Phase 1
- If missing: warn and ask user. Do NOT invent state diagrams.

### What to Research

1. **Existing state management**: How states stored (enum, string, table)? Existing patterns?
   "Workflow uses `status = Column(Enum('DRAFT', 'ACTIVE'))`. Execution follows same pattern."

2. **Transition enforcement**: Where validated (model, service)? Pattern?
   "Pattern: `WorkflowService.publish()` checks status before update."

3. **Side effect implementation**: Mechanism (direct call, event bus, queue)?
   "Events via `EventBus.emit()` in `services/event_bus.py`."

4. **Concurrency analysis**: Per transition, what if two processes try simultaneously?
   "RUNNING → CANCELLED and RUNNING → COMPLETED race: SELECT FOR UPDATE needed."

### Output

Store in **Research (R-NNN updated) + Knowledge (K-NNN)**:

- **state_implementation** — how to implement state machine in this codebase
- **transition_mapping** — each transition mapped to file, method, validation, concurrency
- **recovery_strategy** — how to handle incomplete transitions
- **resolved_questions**

---

## Phase 3: Planning

**Used during**: task decomposition, plan creation

### Input

- `state_diagram`, `state_transitions` — from Phase 1
- `state_implementation`, `transition_mapping` — from Phase 2

### Decomposition Strategy

Use **transition-centric decomposition**:

Good: `Create execution state model` / `Implement PENDING→RUNNING` / `Implement RUNNING→CANCELLED` / `Add retry (FAILED→RUNNING)`
Bad: `Implement state machine` / `Handle state transitions`

### Task Rules

**instruction** must reference: which transition(s), which file/method, validation, side effects.

**acceptance_criteria** — use `Given {current state} When {event} Then {new state + side effects}` format. One AC per valid transition, one per forbidden, one per side effect:
- "Given RUNNING execution, When cancel_execution(), Then status=CANCELLED"
- "Given COMPLETED execution, When cancel_execution(), Then raises InvalidTransition"
- "Given RUNNING execution, When cancel_execution() succeeds, Then EventBus.emit('execution.cancelled') called"

**exclusions** — which transitions NOT in this task, which side effects NOT in this task:
- "Do NOT implement retry (FAILED→RUNNING) — that's T-006"
- "Do NOT add UI for cancel — frontend task"

### Output

Store in **Task fields**: instruction, acceptance_criteria, exclusions, alignment.

---

## Phase 4: Execution

**Used during**: task implementation, verification

### Checklist

Before: Read state model, read existing transitions, read event handling.
During: Validate state BEFORE transition, use locking per strategy, fire ALL side effects.
After: Trace: API → validation → state change → side effects. Match spec?

### Micro-review (max 5 lines)

```
T-005 done: Implemented RUNNING → CANCELLED transition.
- Method: execution_service.cancel_execution(execution_id, user_id)
- Validates: status RUNNING, user has permission
- Side effects: step aborted, execution.cancelled event
- Forbidden: COMPLETED → CANCELLED raises InvalidTransition
Is this what you wanted?
```

---

## Cross-module Interface

### Provides to other modules

| To | Data | Purpose |
|----|------|---------|
| UX | `state_diagram` → states to render | UX knows which states exist |
| UX | `state_transitions` → triggers | UX knows which actions cause transitions |
| UX | `permissions` → who can do what | UX knows when to disable buttons |
| Backend | `state_transitions` → validation rules | Backend knows which transitions to allow/reject |
| Data | `state_diagram` → state values | Data knows enum values for schema |

### Needs from other modules

| From | Data | Purpose |
|------|------|---------|
| UX | `user_flows` → user-triggered transitions | Process knows which are user-initiated |
| Backend | `api_contracts` → endpoint per transition | Process knows API surface |
| Data | `entity_schema` → state storage | Process knows persistence mechanism |
