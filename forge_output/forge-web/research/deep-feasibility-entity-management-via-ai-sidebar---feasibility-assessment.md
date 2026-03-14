# Feasibility: Full Entity Management via AI Sidebar (O-003)

## Verdict: CONDITIONAL GO

## Dimension Scores

| Dimension | Score | Evidence | Binding? |
|-----------|-------|----------|----------|
| Technical | 4/5 | 42 tools exist, SWR revalidation works, skill injection built, WebSocket streaming operational | No |
| Resource | 4/5 | Single developer project, all code in-house, no external services to procure | No |
| Knowledge | 4/5 | Team built the existing infrastructure, patterns well-documented (factory, SWR+Zustand, scope negotiation) | No |
| Organizational | 5/5 | Solo developer, no cross-team coordination needed | No |
| Temporal | 3/5 | Medium appetite = weeks. Incremental approach fits. But 95% success rate target may require iteration cycles. | No |
| Compositional | 4/5 | Frontend-backend integration patterns established. Tool registry -> agent loop -> WS streaming -> SWR revalidation pipeline proven. Gaps are additive, not structural. | No |
| Economic | 4/5 | LLM API costs scale with usage. Multi-turn sessions with tool calls cost more per conversation. But sidebar already exists - marginal cost is small. | No |
| Scale | 4/5 | Redis session storage, SWR caching, debounced revalidation - all handle reasonable scale. Not targeting thousands of concurrent users. | No |
| Cognitive | 3/5 | 42 tools + slash commands + workflow state + multi-turn context = complex system. But incremental approach manages complexity per-task. | No |
| Dependency | 3/5 | LLM provider tool-calling quality is external dependency. If model struggles with 42+ tools, 95% target is hard. | Soft binding |

Average: 3.8/5

## Binding Constraints

**Soft binding: LLM tool-calling accuracy (Dependency, 3/5)**
- The 95% success rate target (KR-1) depends entirely on LLM provider quality
- With 42+ tools, the LLM must reliably select the correct tool AND fill parameters correctly
- No baseline measurement exists - we assume it works but haven't measured
- This isn't a hard blocker (3/5, not 1-2) but it's the weakest link

## Planning Fallacy Check

Stated timeline: medium appetite (weeks)

Reference class:
- **Cursor AI chat integration**: 6+ months from basic to production (but built from scratch)
- **GitHub Copilot Workspace**: 6+ months (entirely new product)
- **Forge platform-v2 AI sidebar (Phase 4)**: ~3 weeks for 43 tasks (built the current infrastructure)
- **Forge platform-v2 Phase 3 (Web UI)**: ~4 weeks for 80+ tasks

Typical overrun: 1.3x-1.5x for enhancement work on existing codebase

Adjusted estimate: The incremental approach (fill gaps, not rebuild) maps closest to Phase 4 work. Estimate: 2-3 weeks for core KRs, +1 week for polish and 95% accuracy tuning.

Total realistic: 3-4 weeks.

## Most Optimistic Assumption

**Assumption**: Improving tool descriptions and adding few-shot examples will push LLM tool-call accuracy from unknown baseline to 95%.

**If wrong**: The 95% target may require a routing/classification layer (Option B from deep-explore), adding significant complexity and 1-2 weeks of work. Or the target needs to be lowered to 85-90%.

## Conditions (for full GO)

1. **Measure baseline tool-call accuracy** - Before implementing KR-1 improvements, run 20-30 test prompts and measure current success rate. If already >80%, improvements to descriptions should reach 95%. If <60%, routing layer may be needed.
   - Owner: developer
   - Deadline: before KR-1 work begins
   - Verification: documented test results

2. **Verify entity WS event emission** - Confirm that LLM tool handlers emit entity-specific events (task.created, objective.updated) not just chat events. If not, add them.
   - Owner: developer
   - Deadline: before KR-3 work begins
   - Verification: WebSocket event log shows entity events after tool execution