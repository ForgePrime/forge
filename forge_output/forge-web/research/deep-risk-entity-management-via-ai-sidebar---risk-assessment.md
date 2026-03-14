# Risk Assessment: Full Entity Management via AI Sidebar (O-003)

Scope: AI sidebar entity management, slash commands, real-time updates, multi-turn context
Horizon: medium appetite (2-4 weeks implementation)

## Risk Register

| # | Risk | P | I | V | D | R | Composite | Category |
|---|------|---|---|---|---|---|-----------|----------|
| 1 | LLM tool confusion (wrong tool selection with 42+ tools) | 3 | 3 | 4 | 3 | 2 | 18 | Technical |
| 2 | Data loss from DELETE operations via natural language | 2 | 5 | 4 | 3 | 2 | 16 | Technical |
| 3 | Context window exhaustion in multi-turn sessions | 3 | 3 | 2 | 4 | 3 | 18->15 | Technical |
| 4 | Slash command ambiguity (/plan = create or show?) | 3 | 2 | 3 | 3 | 1 | 13 | Knowledge |
| 5 | SWR revalidation race (stale cache after mutation) | 2 | 3 | 3 | 2 | 1 | 12 | Technical |
| 6 | Workflow state drift (LLM deviates from skill instructions) | 3 | 3 | 2 | 3 | 2 | 16->14 | Technical |
| 7 | Token cost explosion in multi-turn sessions | 3 | 2 | 1 | 2 | 1 | 10 | Economic |
| 8 | Skill injection context bloat (too many skills loaded) | 2 | 2 | 2 | 2 | 1 | 9 | Technical |

Composite = (P x I) + V + D + R

## Top 5 Risks

### 1. LLM Tool Confusion - Composite: 18
Description: With 42+ tools available, the LLM may select the wrong tool for a natural language request. Example: user says 'update the task status' and LLM calls updateObjective instead of updateTask.
Why it ranks high: Probability 3 (likely with many similar tools), velocity 4 (happens instantly, user sees wrong result), detectability 3 (may not be obvious the wrong entity was modified).
Mitigation: Scope-based filtering already limits visible tools to 8-12 per context. Improve tool descriptions to be more distinct. Add entity type hints in tool names. Consider grouping tools by workflow rather than entity.

### 2. Data Loss from DELETE Operations - Composite: 16
Description: If DELETE tools are added (per KR-1 gap analysis), users could accidentally delete entities via imprecise natural language. 'Remove that thing' could delete the wrong entity.
Why it ranks high: Impact 5 (data loss is permanent), velocity 4 (instant deletion), detectability 3 (user may not notice wrong entity deleted).
Mitigation: Use archive/status-change semantics instead of hard DELETE. Add two-step confirmation: LLM describes what it will delete, waits for user confirmation. Make all deletions soft-delete with recovery period.

### 3. Context Window Exhaustion - Composite: 15
Description: Multi-turn sessions accumulate messages. Tool calls add significant token overhead (tool schemas + results). After 10-15 turns with tool calls, context window may be exhausted.
Why it ranks high: Probability 3 (guaranteed in long sessions), detectability 4 (silent degradation - LLM starts forgetting earlier context), reversibility 3 (cannot recover lost context mid-session).
Mitigation: Implement hybrid context management (KR-4 Option C). Set max_total_tokens limit (currently 50k). Add session token counter visible to user. Offer 'new session with summary' when approaching limit.

### 4. Slash Command Ambiguity - Composite: 14
Description: Some slash commands have ambiguous intent. /plan could mean 'create a new plan' or 'show the existing plan'. /ideas could mean 'list ideas' or 'add a new idea'. This confuses the LLM.
Why it ranks high: Probability 3 (inherent ambiguity), velocity 3 (wrong interpretation visible immediately).
Mitigation: Skill SKILL.md for each command provides disambiguation. Frontend can pass additional metadata (e.g., 'this page has an existing plan'). LLM can ask for clarification when ambiguous.

### 5. Workflow State Drift - Composite: 14
Description: When a slash command triggers a multi-step workflow (e.g., /plan = draft -> review -> approve), the LLM may skip steps or call tools out of order, breaking the workflow.
Why it ranks high: Probability 3 (LLMs are not state machines), detectability 3 (wrong step may produce valid-looking but incorrect output).
Mitigation: Add workflow_state to session (current_step, expected_tools). Backend validates tool calls against expected workflow step. Warn user if LLM deviates.

## Risk Interactions

| Risk A | Risk B | Interaction | Cascade? |
|--------|--------|-------------|----------|
| 1 (Tool confusion) | 2 (Data loss) | Tool confusion + DELETE = wrong entity deleted | YES - amplifies |
| 3 (Context exhaustion) | 6 (Workflow drift) | Lost context causes LLM to lose workflow state | YES - cascade |
| 1 (Tool confusion) | 4 (Command ambiguity) | Ambiguous command + wrong tool = compounded error | YES - amplifies |
| 7 (Token cost) | 3 (Context exhaustion) | Trying to stay in budget causes context loss | Shared root cause |

## Mitigations + Cobra Effect Check

| Mitigation | Fixes | Could Cause/Amplify | Cobra? |
|------------|-------|---------------------|--------|
| Scope-based tool filtering | Risk 1 (confusion) | May hide needed tools, causing 'tool not found' errors | Minor - [suggest-scope:X] handles this |
| Soft-delete with confirmation | Risk 2 (data loss) | Adds friction to legitimate deletions, slower workflow | Minor - acceptable tradeoff |
| Hybrid context management | Risk 3 (exhaustion) | Pinning wrong messages wastes context budget | Minor - simple pinning rules mitigate |
| Skill injection for commands | Risk 4 (ambiguity) | Skill content adds to context size (Risk 8) | Minor - budget already enforced |
| Workflow state tracking | Risk 6 (drift) | Rigid state machine may block valid LLM creativity | Medium - needs escape hatch for user override |
| Token budget per session | Risk 7 (cost) | Hard cutoff may interrupt important workflows | Medium - warn before cutoff, offer continuation |

## Uncertainties
- LLM tool-calling accuracy distribution (we know tools exist but not success rate)
- User behavior patterns (how often do users chain multiple entity operations?)
- Whether skill instructions are sufficient to guide multi-step workflows
- Impact of concurrent AI sessions on Redis performance

## Not Assessed
- Security risks (prompt injection via entity content displayed in chat)
- Availability risks (Redis/LLM provider downtime)
- Compliance risks (data stored in LLM context)
- Multi-user collaboration risks