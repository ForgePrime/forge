# T-040: Tool Call Baseline Investigation Results

**Date**: 2026-03-14 21:48
**Total prompts**: 30
**Exact match**: 22/30 (73.3%)
**Acceptable match**: 22/30 (73.3%)

**Verdict**: MARGINAL — baseline 73.3% between 60-80%. Descriptions need improvement but no routing layer needed yet.

## Per-Operation Accuracy

| Operation | Total | Exact | Acceptable | Exact % | Accept % |
|-----------|-------|-------|------------|---------|----------|
| create | 6 | 3 | 3 | 50% | 50% |
| read | 6 | 5 | 5 | 83% | 83% |
| list | 6 | 6 | 6 | 100% | 100% |
| update | 6 | 2 | 2 | 33% | 33% |
| search | 6 | 6 | 6 | 100% | 100% |

## Per-Entity Accuracy

| Entity | Total | Exact | Acceptable | Exact % | Accept % |
|--------|-------|-------|------------|---------|----------|
| decisions | 5 | 4 | 4 | 80% | 80% |
| global | 1 | 0 | 0 | 0% | 0% |
| guidelines | 4 | 4 | 4 | 100% | 100% |
| ideas | 3 | 2 | 2 | 67% | 67% |
| knowledge | 4 | 3 | 3 | 75% | 75% |
| lessons | 1 | 1 | 1 | 100% | 100% |
| objectives | 3 | 1 | 1 | 33% | 33% |
| research | 3 | 3 | 3 | 100% | 100% |
| tasks | 6 | 4 | 4 | 67% | 67% |

## Detailed Results

| ID | Op | Entity | Expected | Actual | Match | Time |
|----|-----|--------|----------|--------|-------|------|
| C1 | create | tasks | createTask | NONE | MISS | 15.5s |
| C2 | create | decisions | createDecision | createDecision | OK | 22.7s |
| C3 | create | guidelines | createGuideline | createGuideline | OK | 33.5s |
| C4 | create | ideas | createIdea | NONE | MISS | 11.1s |
| C5 | create | objectives | createObjective | NONE | MISS | 12.3s |
| C6 | create | knowledge | createKnowledge | createKnowledge | OK | 17.7s |
| R1 | read | tasks | getEntity | getEntity | OK | 33.7s |
| R2 | read | decisions | getEntity | getEntity | OK | 99.2s |
| R3 | read | objectives | getEntity | getEntity | OK | 27.3s |
| R4 | read | research | getEntity | getEntity | OK | 30.8s |
| R5 | read | tasks | getTaskContext | getTaskContext | OK | 34.3s |
| R6 | read | global | getProjectStatus | NONE | MISS | 14.1s |
| L1 | list | tasks | listEntities | listEntities | OK | 13.3s |
| L2 | list | decisions | listEntities | listEntities | OK | 17.8s |
| L3 | list | guidelines | listEntities | listEntities | OK | 12.9s |
| L4 | list | ideas | listEntities | listEntities | OK | 22.5s |
| L5 | list | knowledge | listEntities | listEntities | OK | 11.7s |
| L6 | list | research | listResearch | listResearch | OK | 21.7s |
| U1 | update | decisions | updateDecision | NONE | MISS | 112.3s |
| U2 | update | ideas | updateIdea | updateIdea | OK | 8.6s |
| U3 | update | guidelines | updateGuideline | updateGuideline | OK | 24.5s |
| U4 | update | objectives | updateObjective | NONE | MISS | 10.2s |
| U5 | update | tasks | updateTask | NONE | MISS | 14.2s |
| U6 | update | knowledge | updateKnowledge | __parse_error__ | MISS | 17.7s |
| S1 | search | tasks | searchEntities | searchEntities | OK | 22.2s |
| S2 | search | decisions | searchEntities | searchEntities | OK | 23.0s |
| S3 | search | guidelines | searchEntities | searchEntities | OK | 16.3s |
| S4 | search | knowledge | searchEntities | searchEntities | OK | 13.7s |
| S5 | search | lessons | searchEntities | searchEntities | OK | 17.5s |
| S6 | search | research | searchEntities | searchEntities | OK | 10.9s |

## Misses (need attention)

### C1: create tasks
- **Prompt**: Create a new task called 'Add login page' with type feature and description 'Implement OAuth login page with Google provider'
- **Expected**: createTask
- **Got**: NONE

### C4: create ideas
- **Prompt**: I have an idea: 'Add dark mode support'. Category: feature. It would improve UX for users working at night.
- **Expected**: createIdea
- **Got**: NONE

### C5: create objectives
- **Prompt**: Create an objective 'Improve Developer Experience' with key result: reduce build time from 60s to under 15s.
- **Expected**: createObjective
- **Got**: NONE

### R6: read global
- **Prompt**: What is the current project status? How many tasks are done?
- **Expected**: getProjectStatus
- **Got**: NONE

### U1: update decisions
- **Prompt**: Close decision D-018 with action accept. The recommendation is solid.
- **Expected**: updateDecision
- **Got**: NONE

### U4: update objectives
- **Prompt**: Update O-003 KR-1 current value to 75%
- **Expected**: updateObjective
- **Got**: NONE

### U5: update tasks
- **Prompt**: Update task T-041 description to 'Verify the full SWR revalidation pipeline including WebSocket dispatch'
- **Expected**: updateTask
- **Got**: NONE

### U6: update knowledge
- **Prompt**: Update knowledge K-001 content to reflect that we upgraded to Redis 7.4.1. Change reason: version bump.
- **Expected**: updateKnowledge
- **Got**: __parse_error__


## Recommendations

1. Improve tool descriptions for missed entity types
2. Consider adding examples to tool descriptions
3. No routing layer needed yet — descriptions improvement should suffice