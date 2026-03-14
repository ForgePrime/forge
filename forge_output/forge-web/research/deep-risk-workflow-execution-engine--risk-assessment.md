# Risk Assessment: Workflow Execution Engine
Scope: O-001 Workflow Execution Engine | Horizon: 3-6 months

## Risk Register
| # | Risk | P | I | V | D | R | Composite | Category |
|---|------|---|---|---|---|---|-----------|----------|
| 1 | Workflow state corruption on concurrent JSON writes | 2 | 4 | 3 | 3 | 2 | 16 | Technical |
| 2 | Workflow stuck forever (no timeout, silent failure) | 3 | 4 | 2 | 4 | 3 | 21 | Technical |
| 3 | Complexity creep making engine unmaintainable | 3 | 3 | 1 | 3 | 4 | 17 | Organizational |
| 4 | LLM context overflow on long workflows | 2 | 3 | 2 | 2 | 2 | 12 | Technical |
| 5 | Redis failure breaks events and sessions | 2 | 4 | 4 | 2 | 3 | 17 | Dependency |
| 6 | Server restart loses in-flight workflow state | 2 | 3 | 5 | 3 | 2 | 16 | Technical |

## Top 5 Risks

### 1. Workflow stuck forever — Composite: 21
Description: A workflow step fails silently (LLM timeout, tool error swallowed) and the workflow hangs indefinitely. No one notices because there's no timeout or health check.
Why it ranks high: High probability (LLM calls are inherently unreliable), high impact (user's objective blocked), and hard to detect (no monitoring built in by default).
Mitigation: Per-step configurable timeout (default 10 min). Workflow-level timeout (default 2 hr). Periodic health check that marks stale running steps as failed. Automatic notification on step failure.

### 2. Complexity creep — Composite: 17
Description: The workflow engine starts simple but accumulates features (conditional branching, parallel groups, retry policies, compensation logic) until it becomes a mini-Temporal that's harder to maintain than using Temporal.
Why it ranks high: Medium probability (scope creep is natural), and very hard to reverse (once complexity is in, refactoring is expensive).
Mitigation: Strict phase-based implementation. Phase 1: linear steps only. Phase 2: conditionals. Phase 3: parallel. NEVER add features preemptively. Each addition requires explicit decision record.

### 3. Redis failure — Composite: 17
Description: Redis is a hard dependency for EventBus (events) and SessionManager (sessions). If Redis goes down, workflows can't emit events or persist LLM sessions.
Why it ranks high: Redis is already a hard dep, so the risk exists regardless. High impact because both events and sessions break simultaneously.
Mitigation: Graceful degradation — workflow continues even if events fail to emit (log locally, retry later). Session persistence falls back to in-memory for short windows. Redis health check in workflow startup.

### 4. Workflow state corruption — Composite: 16
Description: Two concurrent workflows writing to workflows.json simultaneously corrupt each other's state.
Why it ranks high: forge-core already handles this pattern (tracker.json) but workflow state is new and might not get the same care.
Mitigation: Use forge-core's proven atomic write pattern (write .tmp, rename). Per-execution file locking via asyncio.Lock. Consider per-execution files instead of one workflows.json.

### 5. Server restart loses state — Composite: 16
Description: Server crashes mid-step. AgentLoop is async (in-memory), so the running step's progress is lost.
Why it ranks high: High velocity (instant loss) but medium probability (servers rarely crash). Medium reversibility (can retry the step).
Mitigation: Checkpoint after each completed step (already planned). On recovery, mark running steps as failed/retriable. LLM session history preserved in Redis (survives restart). Re-run failed step from clean state.

## Risk Interactions
| Risk A | Risk B | Interaction | Cascade? |
|--------|--------|-------------|----------|
| Redis failure | Server restart | Redis data also lost if restart is unclean | Yes |
| Stuck workflow | Complexity creep | More complex engine = more failure modes = more stuck workflows | Amplifies |
| State corruption | Concurrent workflows | More concurrent = higher corruption risk | Amplifies |

## Mitigations + Cobra Effect Check
| Mitigation | Fixes | Could Cause/Amplify | Cobra? |
|------------|-------|---------------------|--------|
| Per-step timeout | Stuck workflows | Could kill slow but valid LLM sessions | Minor — make timeout generous (10min) |
| Atomic JSON writes | State corruption | Adds I/O latency (~1ms) | No |
| Phase-based features | Complexity creep | Could delay needed features | Minor — prioritize based on user need |
| Redis health check | Redis failure | Adds startup latency | No |
| Per-execution files | State corruption | More files to manage | Minor — cleanup on workflow completion |

## Uncertainties
- How reliable are LLM providers under sustained multi-step workflow load? (No production data yet)
- Will users actually run 3+ concurrent workflows? (Requirement from objective, but actual usage unknown)
- How much context does each step actually need from previous steps? (Determines if per-step sessions are sufficient)

## Not Assessed
- Security risks (authentication, authorization) — assumed handled by existing forge-api middleware
- Cost risks (LLM API costs for long workflows) — out of scope for architecture risk
- Performance at scale beyond 10 concurrent workflows — not a current requirement
