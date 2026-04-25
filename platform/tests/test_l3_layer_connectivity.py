"""L3 layer-connectivity contract test — Phase L3 end-to-end.

Per MASTER_IMPLEMENTATION_PLAN §3 Implementation Closure Theorem:
each layer must EXIST + CONNECTED + CONTROLLED + MEASURED + RECOVERABLE.

This test exercises the full L3 chain:

    ContractSchema (E.1)
        └─> ContextProjector (B.4)
            └─> ContextBudget.fit() (L3.3)
                └─> ModelRouter (L3.4)
                    └─> PromptAssembler (L3.1)
                        └─> FailureRecovery (L3.5) on simulated failure
                            └─> CostTracker (L3.6) post-call accounting

Pure-Python end-to-end; no DB; no LLM; no network.

Asserts:
- The chain composes without import errors.
- Determinism is preserved end-to-end (P6).
- Each layer's output is the next layer's valid input.
- The full pipeline produces a stable assembly_checksum.
- Failure-recovery + cost-tracking integrate with the rest of the chain.

This is the kind of test that catches "module A and module B both pass
their unit tests but the contract between them is broken" — the most
common integration failure mode.
"""

from __future__ import annotations

from decimal import Decimal

from app.evidence.causal_graph import EdgeView, InMemoryEdgeSource, Node
from app.evidence.context_projector import project as project_context
from app.llm.context_budget import fit as fit_context
from app.llm.cost_tracker import (
    DEFAULT_PRICE_TABLE,
    BudgetVerdict,
    compute_cost,
    evaluate_budget,
)
from app.llm.failure_recovery import (
    DEFAULT_TRANSIENT_RETRY_BUDGET,
    ErrorCode,
    RecoveryAction,
    decide as decide_recovery,
)
from app.llm.model_router import (
    Ceremony,
    ModelFamily,
    Reversibility,
    RoutingInputs,
    route as route_model,
)
from app.llm.prompt_assembler import assemble as assemble_prompt
from app.validation.contract_schemas import FEATURE_STANDARD_CONTRACT


# --- Fixture builders ----------------------------------------------------


def _causal_graph_for_task(task_id: int):
    """Build a small but realistic causal graph: 2 decisions + 2 evidence
    references pointing to a feature task."""
    return InMemoryEdgeSource([
        EdgeView(
            src_type="dec", src_id=10,
            dst_type="task", dst_id=task_id,
            relation="decision",
        ),
        EdgeView(
            src_type="dec", src_id=11,
            dst_type="task", dst_id=task_id,
            relation="depends_on",
        ),
        EdgeView(
            src_type="evid", src_id=20,
            dst_type="task", dst_id=task_id,
            relation="evidences",
        ),
        EdgeView(
            src_type="kn", src_id=30,
            dst_type="task", dst_id=task_id,
            relation="reference",
        ),
    ])


def _routing_inputs() -> RoutingInputs:
    """Standard ceremony, medium complexity, reversible change."""
    return RoutingInputs(
        ceremony=Ceremony.STANDARD,
        complexity_score=50,
        reversibility=Reversibility.REVERSIBLE,
        autonomy_level=3,
    )


# --- The main pipeline test ----------------------------------------------


def test_l3_full_pipeline_composes_end_to_end():
    """Full L3 chain composes without errors and produces an
    AssembledPrompt with a valid checksum."""
    # Step 1: Build context graph (B.1 / B.3)
    graph = _causal_graph_for_task(task_id=42)
    task_node = Node(type="task", id=42)

    # Step 2: Project context (B.4)
    projection = project_context(
        graph_source=graph,
        task_node=task_node,
        depth=5,
    )
    assert len(projection.items) > 0  # graph yielded items
    assert projection.task_node == task_node

    # Step 3: Budget-fit the projection items (L3.3)
    fit_result = fit_context(projection.items, budget_tokens=10_000)
    assert fit_result.status == "ACCEPTED"

    # Step 4: Route to a model (L3.4)
    routing = _routing_inputs()
    model_choice = route_model(routing)
    # STANDARD ceremony + medium complexity + REVERSIBLE -> Haiku
    assert model_choice.model_family == ModelFamily.HAIKU
    assert model_choice.reason_code == "default_low_complexity"

    # Step 5: Assemble the prompt (L3.1)
    contract = FEATURE_STANDARD_CONTRACT
    user_intent = "Add a /health endpoint that returns {status: ok}."
    assembled = assemble_prompt(
        contract_schema=contract,
        projection=projection,
        user_intent=user_intent,
        model_family=model_choice.model_family,
        extra_context_items=fit_result.included,
    )
    # Sanity checks across all layers
    assert assembled.model_family == "haiku"
    assert assembled.schema_version == contract.schema_version
    assert len(assembled.assembly_checksum) == 64  # sha256 hex
    assert user_intent in assembled.user_prompt
    assert "REASONING" in assembled.system_prompt  # from contract render
    assert "[CONFIRMED]" in assembled.system_prompt  # from contract reminder

    # Step 6: Cost-estimate the would-be call (L3.6)
    estimated_input_tokens = max(1, len(assembled.user_prompt) // 4)
    estimated_output_tokens = 500
    cost_estimate = compute_cost(
        model_family=assembled.model_family,
        input_tokens=estimated_input_tokens,
        output_tokens=estimated_output_tokens,
        price_table=DEFAULT_PRICE_TABLE,
    )
    assert cost_estimate.cost_usd > Decimal("0")

    # Step 7: BudgetGuard pre-flight (L3.6)
    budget_decision = evaluate_budget(
        cumulative_cost_usd=Decimal("0"),
        next_call_estimate_usd=cost_estimate.cost_usd,
        tau_cost_usd=Decimal("2.00"),
    )
    assert budget_decision.verdict == BudgetVerdict.PASS

    # Step 8: Simulate a transient failure mid-call -> recovery (L3.5)
    recovery = decide_recovery(ErrorCode.PROVIDER_5XX, retry_count=0)
    assert recovery.action == RecoveryAction.RETRY_SAME_PROMPT


# --- Determinism end-to-end (P6) -----------------------------------------


def test_l3_pipeline_determinism_across_runs():
    """Same task + same graph + same routing -> same assembly_checksum."""
    user_intent = "Add a settings page to the dashboard"

    def _run() -> str:
        graph = _causal_graph_for_task(task_id=99)
        projection = project_context(
            graph_source=graph,
            task_node=Node(type="task", id=99),
            depth=5,
        )
        fit_result = fit_context(projection.items, budget_tokens=10_000)
        routing = _routing_inputs()
        model_choice = route_model(routing)
        assembled = assemble_prompt(
            contract_schema=FEATURE_STANDARD_CONTRACT,
            projection=projection,
            user_intent=user_intent,
            model_family=model_choice.model_family,
            extra_context_items=fit_result.included,
        )
        return assembled.assembly_checksum

    checksums = [_run() for _ in range(5)]
    assert len(set(checksums)) == 1  # all 5 identical


# --- Routing-driven contract (different model -> different prompt) -------


def test_high_ceremony_routes_to_sonnet_and_changes_checksum():
    """Higher ceremony -> Sonnet -> different assembly_checksum vs Haiku."""
    graph = _causal_graph_for_task(task_id=1)
    projection = project_context(
        graph_source=graph,
        task_node=Node(type="task", id=1),
    )

    # Low-ceremony route -> Haiku
    haiku = route_model(_routing_inputs())
    assembled_haiku = assemble_prompt(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=projection,
        user_intent="X",
        model_family=haiku.model_family,
    )
    assert assembled_haiku.model_family == "haiku"

    # CRITICAL ceremony -> Opus
    sonnet_or_opus = route_model(RoutingInputs(
        ceremony=Ceremony.CRITICAL,
        complexity_score=50,
        reversibility=Reversibility.REVERSIBLE,
        autonomy_level=3,
    ))
    assembled_critical = assemble_prompt(
        contract_schema=FEATURE_STANDARD_CONTRACT,
        projection=projection,
        user_intent="X",
        model_family=sonnet_or_opus.model_family,
    )
    assert assembled_critical.model_family == "opus"
    # Checksums differ because model_family is part of the checksum input
    assert assembled_haiku.assembly_checksum != assembled_critical.assembly_checksum


# --- BudgetGuard pre-flight halts pipeline -------------------------------


def test_budget_overflow_halts_before_assemble():
    """If projected cost > tau, BudgetGuard rejects — caller should halt."""
    # Simulate cumulative cost already near tau
    cost = compute_cost(
        model_family="opus",
        input_tokens=50_000,
        output_tokens=20_000,
        price_table=DEFAULT_PRICE_TABLE,
    )
    decision = evaluate_budget(
        cumulative_cost_usd=Decimal("1.50"),  # already at 75% of tau
        next_call_estimate_usd=cost.cost_usd,
        tau_cost_usd=Decimal("2.00"),
    )
    assert decision.verdict == BudgetVerdict.REJECTED
    assert "projected_cost_exceeds_tau_cost" in decision.reason


# --- Failure-recovery integration ----------------------------------------


def test_failure_recovery_chain_at_budget_exhaustion():
    """At retry budget exhausted, FAILURE_RECOVERY says fall-back to next model."""
    decision = decide_recovery(
        ErrorCode.PROVIDER_5XX,
        retry_count=DEFAULT_TRANSIENT_RETRY_BUDGET,  # exhausted
    )
    assert decision.action == RecoveryAction.FALLBACK_MODEL
    # ModelRouter exposes the fallback chain that would consume this signal
    routing = _routing_inputs()
    choice = route_model(routing)
    # For Haiku, the fallback chain is empty — caller would BLOCK after
    # exhausting this option.
    assert choice.fallback_chain == ()


def test_failure_recovery_chain_for_higher_model_has_fallback_options():
    """Opus-routed call has a non-empty fallback chain on transient error."""
    routing = RoutingInputs(
        ceremony=Ceremony.CRITICAL,
        complexity_score=50,
        reversibility=Reversibility.REVERSIBLE,
        autonomy_level=3,
    )
    choice = route_model(routing)
    assert choice.model_family == ModelFamily.OPUS
    assert ModelFamily.SONNET in choice.fallback_chain
    assert ModelFamily.HAIKU in choice.fallback_chain


# --- Required-context-categories alignment between E.1 and F.10 ----------


def test_contract_schema_categories_align_with_f10_expectations():
    """E.1 ContractSchema.required_context_categories() returns the 6 ECITP
    C11 categories that F.10 StructuredTransferGate enforces."""
    cats = FEATURE_STANDARD_CONTRACT.required_context_categories()
    # FEATURE_STANDARD has fields tagged with several structural categories
    # (ambiguity_state, evidence_refs, dependency_relations, test_obligations
    # are all present in the seed contract).
    assert "ambiguity_state" in cats
    assert "evidence_refs" in cats
    assert "dependency_relations" in cats
    # All categories are valid enum values per ADR-027
    valid_categories = {
        "requirements", "evidence_refs", "ambiguity_state",
        "test_obligations", "dependency_relations", "hard_constraints",
    }
    assert cats.issubset(valid_categories)
