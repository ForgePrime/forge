"""L3 LLM orchestration package.

Per PLAN_LLM_ORCHESTRATION:
- L3.1 PromptAssembler — deterministic template engine.
- L3.2 ToolCatalog — authority + idempotency enforcement.
- L3.3 ContextBudget — MUST/SHOULD/NICE bucket fitting.
- L3.4 ModelRouter — deterministic decision tree.
- L3.5 FailureRecovery — rule-based retry classification.
- L3.6 CostTracker + BudgetGuard — per-call accounting + pre-flight halt.

Each module is pure Python, deterministic, no LLM-in-loop on the test
side. The LLM call boundary itself is non-deterministic; everything
on this side of it is mechanically reproducible.
"""
