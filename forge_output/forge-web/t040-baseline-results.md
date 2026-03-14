# T-040: Tool Call Baseline Investigation Results

**Date**: 2026-03-14 20:48
**Total prompts**: 30
**Exact match**: 21/30 (70.0%)
**Acceptable match**: 21/30 (70.0%)

**Verdict**: MARGINAL — baseline 70.0% between 60-80%. Descriptions need improvement but no routing layer needed yet.

## Per-Operation Accuracy

| Operation | Total | Exact | Acceptable | Exact % | Accept % |
|-----------|-------|-------|------------|---------|----------|
| create | 6 | 4 | 4 | 67% | 67% |
| read | 6 | 5 | 5 | 83% | 83% |
| list | 6 | 5 | 5 | 83% | 83% |
| update | 6 | 1 | 1 | 17% | 17% |
| search | 6 | 6 | 6 | 100% | 100% |

## Per-Entity Accuracy

| Entity | Total | Exact | Acceptable | Exact % | Accept % |
|--------|-------|-------|------------|---------|----------|
| decisions | 5 | 4 | 4 | 80% | 80% |
| global | 1 | 1 | 1 | 100% | 100% |
| guidelines | 4 | 3 | 3 | 75% | 75% |
| ideas | 3 | 3 | 3 | 100% | 100% |
| knowledge | 4 | 3 | 3 | 75% | 75% |
| lessons | 1 | 1 | 1 | 100% | 100% |
| objectives | 3 | 1 | 1 | 33% | 33% |
| research | 3 | 3 | 3 | 100% | 100% |
| tasks | 6 | 2 | 2 | 33% | 33% |

## Detailed Results

| ID | Op | Entity | Expected | Actual | Match | Time |
|----|-----|--------|----------|--------|-------|------|
| C1 | create | tasks | createTask | NONE | MISS | 11.3s |
| C2 | create | decisions | createDecision | createDecision | OK | 16.4s |
| C3 | create | guidelines | createGuideline | createGuideline | OK | 22.6s |
| C4 | create | ideas | createIdea | createIdea | OK | 10.5s |
| C5 | create | objectives | createObjective | NONE | MISS | 16.6s |
| C6 | create | knowledge | createKnowledge | createKnowledge | OK | 17.3s |
| R1 | read | tasks | getEntity | __parse_error__ | MISS | 33.7s |
| R2 | read | decisions | getEntity | getEntity | OK | 43.7s |
| R3 | read | objectives | getEntity | getEntity | OK | 37.7s |
| R4 | read | research | getEntity | getEntity | OK | 27.1s |
| R5 | read | tasks | getTaskContext | getTaskContext | OK | 43.7s |
| R6 | read | global | getProjectStatus | getProjectStatus | OK | 14.8s |
| L1 | list | tasks | listEntities | NONE | MISS | 11.1s |
| L2 | list | decisions | listEntities | listEntities | OK | 41.5s |
| L3 | list | guidelines | listEntities | listEntities | OK | 21.1s |
| L4 | list | ideas | listEntities | listEntities | OK | 22.1s |
| L5 | list | knowledge | listEntities | listEntities | OK | 11.8s |
| L6 | list | research | listResearch | listResearch | OK | 11.4s |
| U1 | update | decisions | updateDecision | NONE | MISS | 18.8s |
| U2 | update | ideas | updateIdea | updateIdea | OK | 24.9s |
| U3 | update | guidelines | updateGuideline | NONE | MISS | 23.5s |
| U4 | update | objectives | updateObjective | getEntity | MISS | 25.5s |
| U5 | update | tasks | updateTask | NONE | MISS | 13.2s |
| U6 | update | knowledge | updateKnowledge | getEntity | MISS | 43.7s |
| S1 | search | tasks | searchEntities | searchEntities | OK | 23.2s |
| S2 | search | decisions | searchEntities | searchEntities | OK | 15.4s |
| S3 | search | guidelines | searchEntities | searchEntities | OK | 30.6s |
| S4 | search | knowledge | searchEntities | searchEntities | OK | 12.7s |
| S5 | search | lessons | searchEntities | searchEntities | OK | 16.2s |
| S6 | search | research | searchEntities | searchEntities | OK | 13.4s |

## Misses (need attention)

### C1: create tasks
- **Prompt**: Create a new task called 'Add login page' with type feature and description 'Implement OAuth login page with Google provider'
- **Expected**: createTask
- **Got**: NONE

### C5: create objectives
- **Prompt**: Create an objective 'Improve Developer Experience' with key result: reduce build time from 60s to under 15s.
- **Expected**: createObjective
- **Got**: NONE

### R1: read tasks
- **Prompt**: Show me the details of task T-040
- **Expected**: getEntity
- **Got**: __parse_error__

### L1: list tasks
- **Prompt**: List all tasks that are still TODO
- **Expected**: listEntities
- **Got**: NONE

### U1: update decisions
- **Prompt**: Close decision D-018 with action accept. The recommendation is solid.
- **Expected**: updateDecision
- **Got**: NONE

### U3: update guidelines
- **Prompt**: Change guideline G-001 weight from 'should' to 'must'
- **Expected**: updateGuideline
- **Got**: NONE

### U4: update objectives
- **Prompt**: Update O-003 KR-1 current value to 75%
- **Expected**: updateObjective
- **Got**: getEntity

### U5: update tasks
- **Prompt**: Update task T-041 description to 'Verify the full SWR revalidation pipeline including WebSocket dispatch'
- **Expected**: updateTask
- **Got**: NONE

### U6: update knowledge
- **Prompt**: Update knowledge K-001 content to reflect that we upgraded to Redis 7.4.1. Change reason: version bump.
- **Expected**: updateKnowledge
- **Got**: getEntity


## Root Cause Analysis

### Pattern 1: NONE responses (7 cases) — LLM returns text instead of calling tools
- **C1 (createTask)**, **C5 (createObjective)**: LLM asked for confirmation or additional details instead of calling create tools. These tools require complex nested parameters (e.g., `key_results` array for objectives, `acceptance_criteria` for tasks).
- **L1 (listEntities/tasks)**: LLM may have answered from context instead of querying.
- **U1, U3, U5**: Update tools require precise data payloads. LLM likely felt it lacked enough information to construct the correct JSON payload.
- **Root cause**: Tool descriptions lack parameter examples. The LLM sees complex required schemas and hesitates.

### Pattern 2: getEntity instead of update (2 cases: U4, U6)
- LLM tries to READ the entity first to understand current state before updating.
- This is reasonable multi-step behavior but burns iterations, often exhausting the 5-10 turn limit before reaching the update call.
- **Root cause**: Update tool descriptions don't emphasize "call directly with the fields you want to change" — LLM assumes it needs to read first.

### Pattern 3: Tasks entity struggles (4/6 miss)
- Tasks are stored in `tracker.json` under a different pattern than other entities.
- The `entity_type: "tasks"` vs `"task"` singular/plural confusion in getEntity causes errors.
- **Root cause**: Inconsistent entity_type naming (singular in scopes, plural in storage).

### Pattern 4: Parse errors (R1)
- LLM encountered an error in multi-turn: called getEntity with `entity_type: "task"` (singular), got error, retried with "tasks", still got "not found" (storage issue), eventually produced malformed tool call.
- **Root cause**: entity_type validation accepts both forms but storage only has plural.

## Recommendations

### For T-042 (fill-tool-crud-gaps):
1. Add parameter examples to all create/update tool descriptions (especially for complex nested fields)
2. Fix entity_type singular/plural inconsistency — accept both, normalize internally
3. Ensure tasks storage returns results for both `getEntity(tasks, T-040)` and `listEntities(tasks, status=TODO)`

### For T-047 (improve-app-context-tool-descriptions):
1. **Update tools**: Add "Call directly — no need to read the entity first. Only include fields you want to change." to all update tool descriptions
2. **Create tools**: Add one-line parameter examples showing minimal required fields
3. **Tasks tools**: Make description explicit about using `entity_type: "tasks"` (plural)
4. Consider adding `examples` field to ToolDef for in-context learning

### General:
1. No routing layer needed (confirms D-018) — tool descriptions + gap filling is sufficient
2. Search (100%) and read/list (83%) are already strong
3. Update (17%) is the critical improvement area — estimated to reach >80% with description improvements
4. Target after T-042 + T-047: >85% overall accuracy (KR-1 threshold: 95%)