# Exploration: Full Entity Management via AI Sidebar (O-003)

## Knowledge Audit

### Known Facts
1. **42 tools** registered in tool_registry.py covering 12 entity types
2. **Generic tools**: searchEntities, getEntity, listEntities work for ALL entity types
3. **Entity-specific tools**: createTask, updateTask, completeTask, createObjective, updateObjective, createIdea, updateIdea, createDecision, updateDecision, createKnowledge, updateKnowledge, createGuideline, updateGuideline, createLesson, promoteLesson, createResearch, updateResearch, recordChange
4. **Planning tools**: draftPlan, showDraft, approvePlan, getTaskContext
5. **Verification tools**: runGates, getProjectStatus, getProject
6. **Skill tools**: 9 tools for skill management
7. **Meta tools**: listAvailableTools, getToolContract
8. **WebSocket streaming**: chat.token, chat.tool_call, chat.tool_result, chat.complete, chat.error events
9. **SWR revalidation**: wsDispatcher has TOOL_TO_ENTITY mapping, debounced mutate (300ms), toast (500ms)
10. **MutationTracker**: 5s TTL dedup window prevents echo
11. **20 slash commands** defined in SlashCommandDropdown
12. **Session types**: chat, plan, execute, verify, compound - stored in session but informational only
13. **App context builder**: 4-layer system prompt (identity, modules, tool discovery, workflows)
14. **Scope negotiation**: active/inactive scope tracking with [suggest-scope:X] UI hints
15. **File uploads**: drag-drop, 1MB/file, 10/session, stored in Redis

### Assumptions (from O-003)
1. Existing tool registry covers most entities - CONFIRMED: 42 tools, 12 entity types
2. LLM correctly interprets natural language to tool calls - PARTIALLY CONFIRMED: tools exist, success rate unknown
3. SWR revalidation sufficient without dedicated WebSocket per entity - CONFIRMED: debounced SWR revalidation already works via wsDispatcher

### Unknown Gaps
1. Tool call success rate - no metrics
2. Token budget for long conversations - no explicit management
3. Workflow session behavior - session_type does not affect tool availability
4. Entity card rendering - no inline entity cards in chat messages
5. Backend entity-specific WS events unclear if emitted after LLM tool execution

---

## Options

### KR-1: All 12 Entity Types CRUD via Natural Language (>95% success)

| Option | Requirements | Risks | Benefits | Key Unknown |
|--------|-------------|-------|----------|-------------|
| A: Enhance tool descriptions + add few-shot examples | Update 42 tool descriptions, add examples to app context | Low risk | Quick wins, measurable | Baseline success rate |
| B: Add entity routing layer (classifier before LLM) | New middleware, intent -> entity -> tool | Over-engineering, latency | Guaranteed selection | Whether LLM already handles this |
| C: Fill CRUD gaps + improve descriptions | Add ~15 new tools, update descriptions | Medium effort | Complete coverage | Whether DELETE needed vs archival |

**Recommended: Option C** - Fill gaps first, then improve descriptions. Measure success rate.

### KR-2: Slash Commands Triggering Workflow Sessions

| Option | Requirements | Risks | Benefits | Key Unknown |
|--------|-------------|-------|----------|-------------|
| A: Frontend-driven session_type + backend behavior switch | FE sets session_type, BE adjusts prompt + tools | Tight coupling | Clean separation | How many distinct behaviors needed |
| B: Backend command parser | BE detects /command, overrides params | Duplicates FE parsing | Single source of truth | Message cleaning before LLM |
| C: Skill injection approach | /command maps to SKILL.md, loaded via existing skill system | Already partially built | Reuses existing system, flexible | Whether instructions sufficient |

**Recommended: Option C** - Leverage existing skill injection. Map slash commands to skills. No new backend infrastructure.

### KR-3: Real-time Updates <1s

| Option | Requirements | Risks | Benefits | Key Unknown |
|--------|-------------|-------|----------|-------------|
| A: Verify existing pipeline + fix gaps | Ensure all tools in TOOL_TO_ENTITY, verify WS events | Low risk | Minimal effort | Whether BE emits entity events from tool handlers |
| B: Add dedicated entity mutation events | BE emits entity.created from tool handlers | Medium effort | Explicit triggers | Whether chat.tool_result sufficient |
| C: Optimistic UI from tool results | Parse chat.tool_result to update Zustand | Parsing complexity | Instant (0ms vs 300ms) | Whether payloads have enough data |

**Recommended: Option A** - Verify and fix. Pipeline already works.

### KR-4: Multi-turn Context

| Option | Requirements | Risks | Benefits | Key Unknown |
|--------|-------------|-------|----------|-------------|
| A: Sliding window (keep N recent messages) | Backend truncates old messages | Loses early context | Simple, predictable | Optimal window size |
| B: Summarization (LLM summarizes old messages) | New pre-processing step | Extra LLM call, latency | Preserves key context | Summary quality |
| C: Hybrid (pin important + sliding window) | Mark tool results as pinned, window for rest | More complex state | Best of both | What counts as important |

**Recommended: Option C** - Pin tool results and workflow milestones, sliding window for conversation.

---

## Consequence Trace

### Option C (KR-1: Fill CRUD gaps + improve descriptions)
- **1st order**: ~15 new tools added, all entity types have complete CRUD
- **2nd order**: More tools = slightly higher LLM confusion risk, but better descriptions offset this
- **3rd order**: Users trust AI sidebar for ALL operations, sidebar becomes primary interface

### Option C (KR-2: Skill injection for slash commands)
- **1st order**: Each /command loads SKILL.md guiding LLM through workflow
- **2nd order**: Skills updateable without code changes, new workflows = new SKILL.md files
- **3rd order**: Community-contributable workflow skills, extensible workflow engine

### Option C (KR-4: Hybrid context management)
- **1st order**: Long conversations stay within token budget, key tool results preserved
- **2nd order**: Extended workflow sessions without losing critical context
- **3rd order**: Complex multi-step workflows (/plan -> /next -> /review -> /compound) in single session

---

## Challenge Round

### KR-1 Option C: Fill CRUD gaps
- **Strongest counter**: DELETE intentionally absent. Forge = append-only audit trail. Adding DELETE tools risks data loss.
- **Failure condition**: Users expect SQL-like DELETE but Forge uses status archival.
- **Rebuttal**: Offer archive/remove tools matching Forge semantics, not hard DELETE.

### KR-2 Option C: Skill injection
- **Strongest counter**: Skills are static text. Cannot enforce tool ordering or state machines. LLM may deviate.
- **Failure condition**: LLM ignores skill instructions and calls random tools.
- **Rebuttal**: Add workflow state tracking on session (current_step, expected_next_tool). Backend validates.

### KR-4 Option C: Hybrid context
- **Strongest counter**: Deciding what to pin is hard. Wrong pinning = wasted context.
- **Failure condition**: If all tool results pinned, no savings. If none, just a sliding window.
- **Rebuttal**: Simple rule: pin last N tool results + session summary. Not AI-based scoring.

---

## Recommended Path

**Incremental enhancement** - infrastructure is 80% built.

1. **KR-1**: Fill CRUD tool gaps (archive/remove ops, AC template CRUD) + improve tool descriptions. Measure success rate.
2. **KR-2**: Map slash commands to skill injection. Each /command auto-attaches its skill. Add workflow state tracking.
3. **KR-3**: Verify existing revalidation pipeline. Fix TOOL_TO_ENTITY gaps. Measure latency.
4. **KR-4**: Implement hybrid context management - pin tool results, sliding window for conversation.

## What Was NOT Explored
- LLM model performance differences for tool calling
- Cost optimization for multi-turn sessions
- Mobile/responsive behavior
- Accessibility of chat-based entity management
- Multi-user collaboration
- Offline support