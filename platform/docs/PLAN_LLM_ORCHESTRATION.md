# PLAN: LLM Orchestration — L3 Layer Specification

**Status:** DRAFT — pending distinct-actor review per ADR-003.
**Date:** 2026-04-25
**Depends on:**
- PLAN_GATE_ENGINE (G_A) — VerdictEngine + RuleAdapter required for tool-authority gating.
- PLAN_MEMORY_CONTEXT (G_B) — ContextProjector + StructuredTransferGate are L3's input boundary.
- PLAN_CONTRACT_DISCIPLINE (G_CD partial) — ContractSchema (E.1) feeds prompt-template assembly; F.10 StructuredTransferGate must be active before L3 LLM calls dispatch.
**Must complete before:** Phase 1 vertical-slice MVP (per MASTER_IMPLEMENTATION_PLAN §7) — without L3, no LLM call can be dispatched.
**ROADMAP phases:** L3.1 → L3.6 (new operational layer; not in current ROADMAP §1 phases A-G — see §0 below).
**Source spec:** MASTER_IMPLEMENTATION_PLAN §3 L3 (a-f); FORMAL_PROPERTIES_v2.md §6 (P6 determinism applied to LLM call assembly), §11.2 (P25 — TestSynthesizer is the structural cousin of PromptAssembler); MVP_SCOPE.md §L3.
**Soundness theorem source:** `.ai/theorems/Context-Complete Evidence-Guided Agent Process.md`.

> **Known unverified claim (CONTRACT §A.6 disclosure):** L3 wraps a non-deterministic LLM. The plan enforces *structural* determinism around the call (prompt assembly, tool dispatch, retry/recovery, cost accounting) — every component on this side of the LLM boundary is pure. The LLM itself is not deterministic; output non-determinism is mitigated via temperature=0 + seed-pinning where the provider supports it (per ADR-006), property tests over expected output **shapes** (not exact strings), and golden-file comparisons. Output-content fidelity at scale is empirical and out of scope of G_L3 — same scope split as PLAN_GOVERNANCE G_GOV.

---

## 0. Why this plan is necessary

The plan corpus established at PLAN_PRE_FLIGHT through PLAN_GOVERNANCE specifies L1 (Governance) and L2 (Execution Engine) thoroughly. ROADMAP phases A-G close those layers. But MASTER_IMPLEMENTATION_PLAN §3 names **seven** layers; ROADMAP touches L1+L2 only. L3 LLM Orchestration is the layer that:

- Assembles the prompt deterministically from `(ContractSchema, ContextProjection, task, ceremony_level)`.
- Routes the call to a model based on a deterministic decision tree (Haiku/Sonnet/Opus).
- Executes tool calls with authority enforcement (`@side_effect` registry from C.2 + tool authority levels).
- Recovers from transient failures within an Execution without burning idempotency tokens.
- Tracks cost per call into `llm_calls` for budget_guard pre-flight estimates.

Without this plan, every guarantee from L1+L2 is upstream of an unspecified call boundary. **L3 is what makes the corpus operationally complete.**

---

## 1. Soundness conditions addressed

This plan does not close CCEGAP conditions directly — those are closed by L1+L2. L3 closes the **boundary completeness condition**: that the L1+L2 outputs (ContextProjection, ContractSchema, EvidenceSet) are *consumed correctly* by the LLM call boundary, and the LLM call's outputs are routed back into L1+L2's audit trail via `llm_calls` + EvidenceSet linking.

| Soundness mechanism | What "addressed" means | Closed in |
|---|---|---|
| **Boundary determinism** | PromptAssembler is a pure function `(ContractSchema, ContextProjection, task, ceremony) → str`; same inputs produce byte-identical prompts; replay harness over 100 historical executions confirms | Stage L3.1 exit |
| **Tool authority enforcement** | Every tool call validated against `tool.authority_level ≤ execution.autonomy_level`; mutating tools require `@side_effect` decorator from C.2 + `idempotency_key` from A.5 | Stage L3.2 exit |
| **Context budget correctness** | MUST/SHOULD/NICE priority buckets enforce hard guarantee: `MUST` always fits; deterministic priority order on overflow; budget never silently exceeded | Stage L3.3 exit |
| **Model routing determinism** | Decision tree based on `(ceremony_level, task.complexity_score, change.reversibility_class, autonomy_level)`; same inputs → same model; routing table audited per ADR-006 model pinning | Stage L3.4 exit |
| **Failure recovery without idempotency-token burn** | Transient-failure retry within Execution preserves `(execution_id, tool_call_id)`; classification of transient vs permanent is rule-based, not LLM-based | Stage L3.5 exit |
| **Cost accounting** | Every LLM call inserts `llm_calls` row with token counts + cost; `budget_guard` pre-flight estimate halts Execution if projected cost > τ_cost (ADR-004) | Stage L3.6 exit |

CCEGAP conditions **5** (deterministic T_i) and **6** (gate discipline) are *applied to L3 itself* — every stage's exit test is deterministic; every gate is conjunctive and blocking. Conditions **1, 2, 3, 4, 7** are inherited from upstream plans (this plan does not re-close them; it consumes their outputs correctly).

---

## 2. Theorem variable bindings

```
For each stage i ∈ {L3.1, L3.2, L3.3, L3.4, L3.5, L3.6}:

C_i = upstream plan outputs (G_A + G_B + partial G_CD) + ADR-006 model pinning
R_i = MASTER §3 L3 (a-f) + MVP_SCOPE §L3 + FORMAL_PROPERTIES_v2 P6 (determinism)
A_i = ambiguities listed per stage
T_i = pytest / hypothesis / grep / golden-file-comparison — no LLM-in-loop on the test side
O_i = code artifact (PromptAssembler, ToolCatalog, ContextBudget, ModelRouter,
      FailureRecovery, CostTracker)
G_i = all T_i pass + regression green + replay determinism confirmed
```

**Determinism boundary:** L3 *side* of the LLM call is deterministic; the LLM itself is not. Tests verify structural determinism (same prompt input → same prompt output) and shape-determinism on LLM output (response parses to same schema), not content equality of LLM responses.

**Cost-tracking unit:** USD per call, computed as `(input_tokens × input_price[model] + output_tokens × output_price[model])` per ADR-006 price table; price-table version pinned per call.

---

## 3. Phase L3 — LLM Orchestration

### Stage L3.1 — PromptAssembler (deterministic prompt template engine)

**Closes:** L3.a Prompt Templates per MASTER §3. Boundary determinism for the prompt side.

**Entry conditions:**
- G_A = PASS (VerdictEngine available — PromptAssembler is a RuleAdapter consumer).
- G_{B.4} = PASS (ContextProjector output is the structured input to the assembler).
- G_{E.1} = PASS (ContractSchema provides typed task spec → typed prompt fragment).
- G_{F.10} = PASS (StructuredTransferGate validates projection structure before assembly).
- ADR-006 CLOSED (model versions pinned — needed for template-per-model-family).

**A_{L3.1}:**
- Template indexing key: `(task_type, ceremony_level, capability, model_family)` 4-tuple — [ASSUMED: matches FORMAL §P12 self-adjointness pattern; one ContractSchema produces one prompt template + one validator rule. If wrong → templates proliferate and drift. Mitigation: drift test asserts ≤1 template per key.]
- Template DSL choice: Jinja2 vs structured Pydantic-rendered text vs hand-written f-string functions — [ASSUMED: structured Pydantic-rendered text — typed inputs, deterministic output, no template-injection surface. Document choice in module docstring.]
- Pre-flight ASSUMING/VERIFIED/ALTERNATIVES required at *prompt* level (CONTRACT §B.3) — [CONFIRMED: prompt template has dedicated sections for these per CONTRACT §B; each template renders all three by structural walk.]

**Work:**
1. `app/llm/prompt_assembler.py`:
   - `PromptAssembler.assemble(task, ceremony, projection, schema, model_family) → AssembledPrompt` — pure function.
   - `AssembledPrompt = {system_prompt: str, user_prompt: str, tool_specs: List[ToolSpec], stop_sequences: List[str], assembly_checksum: str}`.
   - SHA-256 of `(template_key, normalized_inputs)` stored as `assembly_checksum` for replay verification.
2. Template registry: `app/llm/templates/` directory; one `.py` file per template-key tuple; each exports a single `render(task, projection, schema) → AssembledPrompt` function.
3. Integration with CONTRACT §B sections — every template renders 5 mandatory blocks:
   - Operational contract reminder (CONTRACT §B preamble).
   - ASSUMING / VERIFIED / ALTERNATIVES (pre-implementation per §B.3).
   - MODIFYING / IMPORTED BY / NOT MODIFYING (pre-modification per §B.4).
   - DONE / SKIPPED / FAILURE SCENARIOS placeholders (pre-completion per §B.5).
   - Tagging rule injection (`[CONFIRMED]/[ASSUMED]/[UNKNOWN]` per CONTRACT §B.2 + P19 binding).
4. ContractSchema-derived sections: `render_prompt_fragment()` from E.1 inserted as the typed task-spec block.
5. Drift test against E.1 ContractSchema: mutating any ContractSchema field changes both `validator_rules()` (E.1) AND `assemble().user_prompt` (this stage); desync → fail.

**Exit test T_{L3.1} (deterministic):**
```bash
# T1: pure function — no wall-clock, no rand, no network in assemble()
grep -nE "datetime\.now|random\.|requests\.|httpx\.|time\.sleep|os\.environ" app/llm/prompt_assembler.py
# exits 1 (no matches in assemble() body — env reads only at import time, frozen)

# T2: same inputs → byte-identical prompt
pytest tests/llm/test_prompt_assembler.py::test_byte_identical_on_repeat -x
# PASS: assemble(task, c, proj, schema, m) called 100x with same inputs → 100 identical
# AssembledPrompt.assembly_checksum values

# T3: replay over 100 historical executions
pytest tests/llm/test_prompt_assembler.py::test_replay_determinism -x
# PASS: for 100 stored (Execution, projection, schema) tuples with stored
# AssembledPrompt.assembly_checksum, re-running assemble() produces byte-identical
# outputs → checksums match. (Storage: llm_calls.assembled_prompt_checksum from L3.6.)

# T4: drift test against E.1 ContractSchema
pytest tests/llm/test_prompt_assembler.py::test_e1_lockstep -x
# PASS: mutating a ContractSchema field changes both validator_rules() output
# (from E.1 drift test) AND assemble().user_prompt (this test); desync → drift_test fails

# T5: 5 mandatory CONTRACT §B blocks present in every rendered prompt
pytest tests/llm/test_prompt_assembler.py::test_contract_b_blocks_present -x
# PASS: for each template in app/llm/templates/, rendered prompt contains all 5 blocks
# (regex assertions for each block header)

# T6: tagging rule injection
pytest tests/llm/test_prompt_assembler.py::test_tagging_rule_injected -x
# PASS: rendered prompt contains [CONFIRMED]/[ASSUMED]/[UNKNOWN] tagging instruction

# T7: ≤1 template per (task_type, ceremony, capability, model_family) key
pytest tests/llm/test_prompt_assembler.py::test_one_template_per_key -x
# PASS: enumerating app/llm/templates/ produces no duplicate keys

# T8: regression
pytest tests/ -x
```

**Gate G_{L3.1}:** T1–T8 pass → PASS. **Boundary determinism on prompt side closed**: prompt assembly is reproducible byte-for-byte; drift from E.1 is mechanically detected.

**ESC-4 impact:** New `app/llm/prompt_assembler.py` + `app/llm/templates/`. Consumes E.1 ContractSchema (read-only); consumes B.4 ContextProjection (read-only); consumes F.10 StructuredTransferGate result (read-only). **ESC-5 invariants preserved:** E.1 self-adjointness extended one more direction (validator_rules + prompt_fragment + AssembledPrompt all derive from same source); F.10 structural categories preserved into prompt structure. **ESC-7 failure modes:** (a) template-key collision → T7 grep-gate; (b) ContractSchema field added without template update → T4 drift detects; (c) prompt-injection via projection content → projection content escaped per category (RequirementRef serialized as JSON, not interpolated as raw string).

---

### Stage L3.2 — ToolCatalog with authority enforcement

**Closes:** L3.b Tool Registry per MASTER §3. Tool authority enforcement.

**Entry conditions:**
- G_{A.5} = PASS (MCP idempotency available — mutating tools require idempotency_key).
- G_{C.2} = PASS (`@side_effect` registry exists — every mutating tool tagged).
- G_{E.3} = PASS (Autonomy ledger available — tool authority gated by autonomy level).

**A_{L3.2}:**
- Tool authority enum — [ASSUMED: `{read_only, idempotent_write, side_effecting_write, irreversible_write, external_call}` — 5 levels matching ESC-7 failure-mode taxonomy + matching AIOS A6 5-category boundary typing semantically.]
- Authority-vs-autonomy mapping — [UNKNOWN: ADR-004 must specify per-autonomy-level `max_authority` ceiling. Stage L3.2 BLOCKED until ADR-004 entry added (see Q1).]
- MCP tool inventory at L3.2 entry — [CONFIRMED via grep: `forge_execute`, `forge_deliver`, `forge_decision`, `forge_finding`, `forge_challenge`, `forge_get`, `forge_list`, `forge_status` per CHANGE_PLAN_v2 §2.2.6; A.5 T5 enumerates the 4 mutating tools].

**Work:**
1. `app/llm/tool_catalog.py`:
   - `Tool` Pydantic model: `{name: str, description: str, json_schema: dict, authority_level: AuthorityEnum, requires_idempotency_key: bool, requires_side_effect_decorator: bool, max_invocations_per_execution: int | None}`.
   - `ToolCatalog.register(tool)` — adds to in-memory registry; rejects on duplicate name, missing JSON Schema, or authority mismatch with `@side_effect` decorator presence.
   - `ToolCatalog.dispatch(call, execution) → ToolResult` — single dispatch path.
2. Authority gate (runs before dispatch):
   - `tool.authority_level <= autonomy_state.max_authority(execution.capability)`. Violation → REJECTED with `reason='tool_authority_exceeds_autonomy'`.
   - `tool.requires_side_effect_decorator AND tool.fn not in side_effect_registry` → REJECTED at registration time (deterministic, runs at module import).
   - `tool.requires_idempotency_key AND call.idempotency_key is None` → REJECTED with `reason='missing_idempotency_key'`.
3. Per-execution invocation cap: `max_invocations_per_execution` enforced via `tool_invocations(execution_id, tool_name, count)` row; deterministic `cap_exceeded` error.
4. Tool inventory seeded with the MVP 5: `read_file, edit_file, run_tests, git_diff, check_spec` (per MVP_SCOPE §L3) + the 4 mutating MCP tools + 5 reads.

**Exit test T_{L3.2} (deterministic):**
```bash
# T1: registry rejects on duplicate name
pytest tests/llm/test_tool_catalog.py::test_duplicate_name_rejected -x

# T2: registry rejects mutating tool without @side_effect decorator
pytest tests/llm/test_tool_catalog.py::test_side_effect_required -x
# PASS: register Tool(authority='side_effecting_write', fn=untagged_fn) → raises at registration

# T3: registry rejects missing JSON Schema
pytest tests/llm/test_tool_catalog.py::test_json_schema_required -x

# T4: dispatch rejects authority > autonomy
pytest tests/llm/test_tool_catalog.py::test_authority_gate -x
# PASS: tool with authority='irreversible_write' + autonomy_state.max_authority='idempotent_write'
# → dispatch returns Verdict(REJECTED, reason='tool_authority_exceeds_autonomy')

# T5: dispatch rejects mutating call without idempotency_key
pytest tests/llm/test_tool_catalog.py::test_idempotency_key_required -x

# T6: per-execution invocation cap
pytest tests/llm/test_tool_catalog.py::test_invocation_cap -x
# PASS: tool with max_invocations_per_execution=3, fourth call → REJECTED

# T7: 14 tools registered (5 MVP read + 4 mutating MCP + 5 reads)
pytest tests/llm/test_tool_catalog.py::test_inventory_count -x
# PASS: ToolCatalog.list() returns ≥14 entries (≥ allows future additions)

# T8: regression
pytest tests/ -x
```

**Gate G_{L3.2}:** T1–T8 pass → PASS. **Tool authority enforcement closed**: no tool dispatched without authority ≤ autonomy + idempotency-key (where required) + `@side_effect` decorator (where required).

**ESC-4 impact:** New `app/llm/tool_catalog.py`. Consumes C.2 SideEffectRegistry (read-only); consumes A.5 MCP idempotency (read-only); consumes E.3 AutonomyState (read-only). New `tool_invocations` table for per-execution cap. **ESC-5 invariants preserved:** A.5 idempotency semantics unchanged (this plan extends to LLM-side gating); C.2 `@side_effect` decorator extended to tool registration validation. **ESC-7 failure modes:** (a) tool author forgets `@side_effect` → T2 catches at module import (fail-fast); (b) autonomy demoted mid-Execution → next dispatch re-checks authority; (c) malformed JSON Schema → T3 catches.

---

### Stage L3.3 — ContextBudget algorithm (MUST/SHOULD/NICE buckets)

**Closes:** L3.c Context Budget per MASTER §3. Hard MUST guarantee; deterministic priority on overflow.

**Entry conditions:**
- G_{B.4} = PASS (ContextProjection has typed structured fields per L3.1 dependency).
- G_{F.10} = PASS (StructuredTransferGate guarantees the 6 structural categories).
- ADR-006 CLOSED (token-counter library + per-model context-window sizes).

**A_{L3.3}:**
- Tokenizer choice — [ASSUMED: `tiktoken` for OpenAI-compatible models per MVP_SCOPE §L3 ("simple token-counting"); per-model encoding map. If wrong → over/under-fill within ~5% — acceptable margin per ADR-006].
- Bucket priority order within MUST/SHOULD/NICE — [CONFIRMED per FORMAL §P15 binding: must-guidelines → recent decisions → evidence → knowledge].
- Budget-overflow action — [CONFIRMED: deterministic priority truncation, never silent drop; if even MUST exceeds budget → REJECTED, no truncation of MUST allowed].

**Work:**
1. `app/llm/context_budget.py`:
   - `Bucket` enum: `{MUST, SHOULD, NICE}`.
   - `ContextItem = {content: str, bucket: Bucket, priority_within_bucket: int, source_ref: str, token_count: int}`.
   - `ContextBudget.fit(items, budget_tokens) → FitResult` — pure function:
     - Compute total MUST tokens. If > budget → return `FitResult(status='REJECTED', reason='must_exceeds_budget', must_tokens, budget_tokens)`.
     - Sort SHOULD by `priority_within_bucket` desc; greedily admit until budget exhausted.
     - Sort NICE same; admit remaining.
     - Return `FitResult(status='ACCEPTED', included=[...], excluded=[...], total_tokens=...)`.
2. Bucket assignment from ContextProjection (B.4 output):
   - MUST: hard_constraints (Invariants), requirements (typed RequirementRef), ambiguity_state (UNKNOWN items per F.4), ContractSchema task block.
   - SHOULD: recent decisions (CausalEdge BFS ancestors of current task, depth ≤ 3), evidence_refs (typed EvidenceRef from EvidenceSet), test_obligations.
   - NICE: knowledge (Knowledge entity ancestors), dependency_relations (relation_semantic from B.6), historical similar tasks.
3. Budget input: `model_router.context_window(model) - reserved_for_response - safety_margin` (per ADR-006).

**Exit test T_{L3.3} (deterministic):**
```bash
# T1: pure function — no wall-clock, no rand
grep -nE "datetime\.now|random\.|requests\.|httpx\." app/llm/context_budget.py
# exits 1

# T2: MUST always fits when total_must <= budget
pytest tests/llm/test_context_budget.py::test_must_always_fits -x

# T3: must_exceeds_budget → REJECTED (no silent truncation)
pytest tests/llm/test_context_budget.py::test_must_exceeds_rejected -x

# T4: deterministic priority on overflow
pytest tests/llm/test_context_budget.py::test_priority_ordering -x
# PASS: same items + same budget called 100x → 100 identical FitResult.included orderings

# T5: budget correctness on 100 fixtures
pytest tests/llm/test_context_budget_fixtures.py -x
# PASS: 100 (items, budget) fixtures from MVP_SCOPE benchmark cases — each FitResult
# matches expected included/excluded sets (golden-file)

# T6: token counting consistent with model encoder
pytest tests/llm/test_context_budget.py::test_token_count_matches_model -x
# PASS: token_count for "hello world" matches tiktoken cl100k_base count

# T7: bucket assignment from ContextProjection
pytest tests/llm/test_context_budget.py::test_bucket_assignment -x
# PASS: ContextProjection with 6 categories → fit() input has correct bucket per category

# T8: regression
pytest tests/ -x
```

**Gate G_{L3.3}:** T1–T8 pass → PASS. **Budget correctness closed on 100 fixtures**: MUST guaranteed; SHOULD/NICE deterministic; overflow either accepted with deterministic truncation or REJECTED on MUST overflow.

**ESC-4 impact:** New `app/llm/context_budget.py`. Consumes B.4 ContextProjection (read-only); consumes ADR-006 model context-window sizes. **ESC-5 invariants preserved:** F.10 StructuredTransferGate still validates 6 categories upstream of bucket assignment; B.4 priority order respected. **ESC-7 failure modes:** (a) tokenizer drift between budget compute and LLM provider → T6 catches mismatch; (b) MUST overflow → REJECTED, Execution stays pending until task is decomposed (NOT silent truncation); (c) numeric overflow on huge token counts → token_count is `int` (Python arbitrary precision).

---

### Stage L3.4 — ModelRouter (deterministic decision tree)

**Closes:** L3.d Model Routing per MASTER §3.

**Entry conditions:**
- G_{C.4} = PASS (Reversibility classification — input to routing).
- G_{E.3} = PASS (Autonomy state — input to routing).
- G_{L3.3} = PASS (Budget computation — context window per model is the lookup driver).
- ADR-006 CLOSED (model versions + price table + routing weights).

**A_{L3.4}:**
- Routing decision tree — [ASSUMED draft per MASTER §3 L3.d:
  ```
  if ceremony_level == 'CRITICAL' or change.reversibility_class == 'IRREVERSIBLE':
      → Opus (highest capability)
  elif ceremony_level == 'FULL' or task.complexity_score >= τ_high:
      → Sonnet
  else:
      → Haiku
  ```
  Calibration constants τ_high, ceremony thresholds in ADR-006. If wrong → cost up or quality down; T5 measures]
- Sonnet-only MVP override — [CONFIRMED per MVP_SCOPE §L3: until benchmark ≥ 0.6 on Task-bench-01/02/03 with full routing, MVP runs Sonnet-only via env flag `LLM_ROUTER_MODE=sonnet_only`].
- Fallback when chosen model unavailable — [ASSUMED: deterministic fallback chain per ADR-006: Opus→Sonnet→Haiku; never silent. Logged as Finding(severity=MEDIUM, kind='model_unavailable_fallback')].

**Work:**
1. `app/llm/model_router.py`:
   - `ModelRouter.route(task, change, autonomy, ceremony) → ModelChoice` — pure function over the inputs.
   - `ModelChoice = {model_name: str, model_version: str, provider: str, reason_code: str, fallback_chain: List[str]}`.
   - Reads decision-tree config from `app/llm/config/routing_table.yaml` (versioned, ADR-006).
2. Sonnet-only MVP gate: env `LLM_ROUTER_MODE=sonnet_only` overrides decision tree → all calls Sonnet; logged once at startup, not per call.
3. Fallback handling: `dispatch(model_choice)` catches provider 5xx / rate-limit; tries next in fallback_chain; emits Finding on each fallback step; if entire chain exhausted → Execution.status=BLOCKED with `reason='all_models_unavailable'`.
4. Routing audit: every call writes `llm_calls.routing_inputs` (JSONB snapshot of the 4 inputs) + `llm_calls.routing_decision` for replay.

**Exit test T_{L3.4} (deterministic):**
```bash
# T1: pure function over inputs
grep -nE "datetime\.now|random\." app/llm/model_router.py
# exits 1

# T2: same inputs → same model
pytest tests/llm/test_model_router.py::test_determinism -x
# PASS: 100 calls with same (task, change, autonomy, ceremony) → 100 identical ModelChoice

# T3: IRREVERSIBLE always routes to Opus
pytest tests/llm/test_model_router.py::test_irreversible_to_opus -x

# T4: ceremony_level=CRITICAL always routes to Opus
pytest tests/llm/test_model_router.py::test_critical_to_opus -x

# T5: routing audit on canonical fixtures
pytest tests/llm/test_model_router.py::test_canonical_routing -x
# PASS: 20 (task, change, autonomy, ceremony) fixtures → routing matches expected
# (golden-file from ADR-006 routing examples)

# T6: Sonnet-only override
pytest tests/llm/test_model_router.py::test_sonnet_only_override -x
# PASS: with LLM_ROUTER_MODE=sonnet_only, even IRREVERSIBLE inputs → Sonnet

# T7: fallback chain on provider unavailability
pytest tests/llm/test_model_router.py::test_fallback_chain -x
# PASS: simulate Opus 503 → Sonnet attempted; simulate Sonnet 503 → Haiku attempted;
# Finding(kind='model_unavailable_fallback') emitted per step

# T8: all-models-unavailable → BLOCKED
pytest tests/llm/test_model_router.py::test_all_unavailable_blocks -x
# PASS: simulate full chain unavailable → Execution.status=BLOCKED, reason='all_models_unavailable'

# T9: routing inputs persisted for replay
pytest tests/llm/test_model_router.py::test_routing_audit -x

# T10: regression
pytest tests/ -x
```

**Gate G_{L3.4}:** T1–T10 pass + ADR-006 CLOSED → PASS. **Model routing determinism closed**: same inputs → same model; fallback deterministic and disclosed; Sonnet-only override honored.

**ESC-4 impact:** New `app/llm/model_router.py` + `app/llm/config/routing_table.yaml`. Consumes C.4 Reversibility (read-only); consumes E.3 AutonomyState (read-only); consumes ADR-006 (config). **ESC-5 invariants preserved:** Reversibility classifier output unchanged; Autonomy demote() runs orthogonally. **ESC-7 failure modes:** (a) provider rate-limit → fallback chain; (b) model deprecated mid-Execution → ADR-006 supersession + routing_table.yaml version bump; (c) routing_table.yaml malformed → fail at startup, not per call (parse on import).

---

### Stage L3.5 — FailureRecovery within Execution

**Closes:** L3.e Failure Recovery per MASTER §3.

**Entry conditions:**
- G_{A.5} = PASS (MCP idempotency — retries must preserve idempotency_key).
- G_{F.4} = PASS (BLOCKED state — terminal failure routes here).
- G_{L3.4} = PASS (model fallback chain is one form of recovery).

**A_{L3.5}:**
- Transient vs permanent classification — [CONFIRMED: rule-based, NOT LLM-based:
  - **Transient** (retryable): provider 5xx, network timeout, rate-limit (429), JSON parse error on output, schema-mismatch on tool args (single retry with regenerated prompt explaining schema).
  - **Permanent** (BLOCKED): authentication failure, model deprecated, budget exceeded, all-models-unavailable, schema-mismatch repeated 2x.
- Retry budget — [ASSUMED: 1 retry on timeout, 2 retries on malformed output per MVP_SCOPE §L3. Calibration per ADR-006.]
- Retry preserves idempotency_key — [CONFIRMED per A.5 binding: `(execution_id, tool_call_id)` reused across retries; provider sees same key → same idempotency-window response].

**Work:**
1. `app/llm/failure_recovery.py`:
   - `FailureClassifier.classify(error) → {'transient', 'permanent'}` — pure rule-based dict lookup; no LLM.
   - `RecoveryStrategy.attempt(execution, error, retry_count) → RecoveryAction` — returns one of:
     - `RetryWithSamePrompt` (transient, retry_count < budget).
     - `RetryWithSchemaReminder` (output parse error, retry_count < malformed_budget).
     - `FallbackModel` (model-side error, fallback chain not exhausted).
     - `BlockExecution` (permanent OR retry budget exhausted).
2. `llm_calls.retry_count`, `llm_calls.failure_class`, `llm_calls.recovery_action` columns track per-call state.
3. Integration with VerdictEngine: on `BlockExecution`, Execution.status=BLOCKED with `blocked_reason=<failure_class>:<error_code>`; reuses F.4 BLOCKED pattern.

**Exit test T_{L3.5} (deterministic):**
```bash
# T1: classification deterministic
pytest tests/llm/test_failure_recovery.py::test_classification_deterministic -x
# PASS: same error string → same classification across 100 calls

# T2: transient retry with same prompt + same idempotency_key
pytest tests/llm/test_failure_recovery.py::test_transient_retry_idempotent -x
# PASS: simulate timeout → retry preserves (execution_id, tool_call_id)

# T3: malformed output → schema-reminder retry
pytest tests/llm/test_failure_recovery.py::test_malformed_schema_reminder -x

# T4: retry budget exhausted → BLOCKED
pytest tests/llm/test_failure_recovery.py::test_budget_exhausted_blocks -x
# PASS: 3rd transient failure → Execution.status=BLOCKED

# T5: permanent failure → immediate BLOCKED
pytest tests/llm/test_failure_recovery.py::test_permanent_blocks -x
# PASS: auth_failure → no retry, immediate BLOCKED

# T6: integration test full failure path
pytest tests/llm/test_failure_recovery_integration.py -x
# PASS: end-to-end Execution with simulated transient + recovery succeeds; same with
# permanent → BLOCKED with correct reason

# T7: idempotency_key preserved across retries
pytest tests/llm/test_failure_recovery.py::test_idempotency_preserved -x
# PASS: 3 retries → 3 calls all share (execution_id, tool_call_id); A.5 dedup works

# T8: regression
pytest tests/ -x
```

**Gate G_{L3.5}:** T1–T8 pass → PASS. **Failure recovery without idempotency-token burn closed**: transient retries preserve keys; permanent failures route to BLOCKED via F.4 pattern; classification is rule-based (no LLM-in-loop on the recovery decision).

**ESC-4 impact:** New `app/llm/failure_recovery.py`. Consumes A.5 idempotency (read-only key behavior); consumes F.4 BLOCKED state. New `llm_calls` columns for retry tracking. **ESC-5 invariants preserved:** A.5 idempotency semantics unchanged (retries deterministically reuse keys); F.4 BLOCKED state unchanged (new `blocked_reason` values only). **ESC-7 failure modes:** (a) classifier missing new error code → defaults to `permanent` (fail-safe); (b) retry budget too low for legit recovery → ADR-006 calibration; (c) infinite retry loop → hard cap on retry_count enforced at DB level via CHECK constraint.

---

### Stage L3.6 — CostTracker + budget_guard

**Closes:** L3.f Cost Tracking per MASTER §3. Pre-flight halt on projected overrun.

**Entry conditions:**
- G_{L3.4} = PASS (price-per-model from ADR-006 routing table).
- G_{F.4} = PASS (BLOCKED state for budget overrun).
- ADR-004 CLOSED (τ_cost — per-Execution cost ceiling).

**A_{L3.6}:**
- Cost formula — [CONFIRMED: `cost_usd = input_tokens × input_price_per_1k_tokens / 1000 + output_tokens × output_price_per_1k_tokens / 1000`; prices versioned per ADR-006].
- Pre-flight estimate accuracy — [ASSUMED: estimated input_tokens from PromptAssembler.token_count; estimated output_tokens from ContractSchema.expected_output_size or fallback constant. Estimate within ±20% acceptable per MVP_SCOPE; below 80% → no halt, between 80-100% → warning Finding, > 100% → BLOCKED.]
- Cost-tracking unit — [CONFIRMED: USD per call; aggregated per Execution; global cumulative for Project per quarter].

**Work:**
1. Alembic migration: `llm_calls(id, execution_id FK, tool_call_id, model_name, model_version, provider, input_tokens, output_tokens, cost_usd, price_table_version, routing_inputs JSONB, routing_decision, retry_count, failure_class TEXT NULL, recovery_action TEXT NULL, assembled_prompt_checksum TEXT, started_at, completed_at)`. Unique on `(execution_id, tool_call_id, retry_count)`.
2. `app/llm/cost_tracker.py`:
   - `CostTracker.estimate(prompt, schema, model) → CostEstimate` — pre-flight estimate.
   - `CostTracker.record(call_result) → llm_calls row` — post-call actual.
   - `CostTracker.execution_total(execution_id) → Decimal` — sum over llm_calls for Execution.
3. `BudgetGuard.evaluate(execution, estimate) → Verdict`:
   - Pre-flight: if `CostTracker.execution_total(exec_id) + estimate.cost_usd > τ_cost (ADR-004)` → REJECTED with `reason='projected_cost_exceeds_tau_cost'`.
   - Post-call (audit): if `CostTracker.execution_total > 1.5 × τ_cost` (overrun beyond estimate) → Finding(severity=HIGH, kind='cost_overrun_post_hoc') + Execution.status=BLOCKED.
4. Project quarterly cumulative dashboard endpoint: `GET /projects/{slug}/llm-costs/quarter` returning per-Project totals + per-capability breakdown.

**Exit test T_{L3.6} (deterministic):**
```bash
# T1: migration round-trip
uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head

# T2: cost formula correctness
pytest tests/llm/test_cost_tracker.py::test_cost_formula -x
# PASS: known (input_tokens, output_tokens, model) → cost matches ADR-006 price table
# to 6 decimal places

# T3: pre-flight estimate within ±20% of actual on 50 historical
pytest tests/llm/test_cost_tracker.py::test_estimate_accuracy -x
# PASS: 50 stored (estimate, actual) pairs → estimate within [0.8, 1.0] × actual on
# at least 45/50 cases (±20% tolerance per A_{L3.6})

# T4: budget_guard pre-flight halt
pytest tests/llm/test_cost_tracker.py::test_budget_guard_preflight -x
# PASS: synthetic Execution with cumulative_cost=$1.80, τ_cost=$2.00,
# estimate.cost_usd=$0.50 → BudgetGuard returns REJECTED with
# reason='projected_cost_exceeds_tau_cost'

# T5: post-hoc overrun → BLOCKED
pytest tests/llm/test_cost_tracker.py::test_post_hoc_overrun -x
# PASS: actual cost = 1.6 × τ_cost → Finding(kind='cost_overrun_post_hoc') + BLOCKED

# T6: per-Execution total computation
pytest tests/llm/test_cost_tracker.py::test_execution_total -x
# PASS: 5 llm_calls rows for one Execution → execution_total returns sum

# T7: price_table_version pinned per call
pytest tests/llm/test_cost_tracker.py::test_price_table_versioned -x
# PASS: every llm_calls row has non-null price_table_version matching ADR-006 entry

# T8: quarterly dashboard endpoint
pytest tests/llm/test_cost_tracker.py::test_quarterly_endpoint -x

# T9: regression
pytest tests/ -x
```

**Gate G_{L3.6}:** T1–T9 pass + ADR-004 τ_cost CLOSED + ADR-006 price table CLOSED → PASS. **Cost accounting closed**: every LLM call accounted; pre-flight halt prevents runaway; post-hoc overrun caught.

**ESC-4 impact:** New `llm_calls` table; `app/llm/cost_tracker.py`; quarterly dashboard endpoint. Integrates with L3.4 (price table read-only) + F.4 (BLOCKED state). **ESC-5 invariants preserved:** F.4 BLOCKED unchanged (new `blocked_reason` values); L3.5 retry tracking integrates additively (one llm_calls row per retry attempt). **ESC-7 failure modes:** (a) provider price change mid-Execution → price_table_version pinning catches at next ADR-006 update; (b) estimate consistently low → T3 fails (forces calibration); (c) cumulative over-spend across long-running Project → quarterly dashboard surfaces.

---

## 4. Phase L3 exit gate (G_L3)

```
G_L3 = PASS iff:
  G_{L3.1} = PASS  (PromptAssembler — deterministic, replay-correct over 100 historical)
  AND G_{L3.2} = PASS  (ToolCatalog — authority + idempotency + side-effect enforcement)
  AND G_{L3.3} = PASS  (ContextBudget — MUST guarantee + 100-fixture correctness)
  AND G_{L3.4} = PASS  (ModelRouter — deterministic over 4-input tree + fallback chain)
  AND G_{L3.5} = PASS  (FailureRecovery — rule-based classification + idempotency-preserving retries)
  AND G_{L3.6} = PASS  (CostTracker + BudgetGuard — every call accounted, pre-flight halt active)
  AND pytest tests/ -x → all upstream + L3 tests green
  AND every llm_calls row has assembled_prompt_checksum + routing_inputs + price_table_version (DB invariant query: COUNT(*) WHERE any of these IS NULL = 0)
  AND replay over 100 historical Executions produces byte-identical AssembledPrompt checksums
  AND no LLM call dispatch path bypasses ToolCatalog: grep -rnE "anthropic\.messages|openai\.chat|provider\.(invoke|create)" app/ | grep -v app/llm/tool_catalog.py = 0 matches
```

**Soundness conditions closed at G_L3:**

*L3-specific boundary conditions:*
- **Boundary determinism (prompt side)** — PromptAssembler pure function; replay over 100 historical → byte-identical. [T_{L3.1} T2, T3]
- **Tool authority enforcement** — `tool.authority_level ≤ autonomy.max_authority` enforced at dispatch; mutating tools require `@side_effect` + idempotency_key. [T_{L3.2} T2, T4, T5]
- **Context budget correctness** — MUST guaranteed; SHOULD/NICE deterministic priority; overflow → REJECT, not silent drop. [T_{L3.3} T2, T3, T4, T5]
- **Model routing determinism** — same 4-input → same model; fallback chain disclosed; Sonnet-only override honored. [T_{L3.4} T2, T5, T6]
- **Failure recovery without idempotency-token burn** — rule-based classification; retries preserve `(execution_id, tool_call_id)`. [T_{L3.5} T1, T2, T7]
- **Cost accounting + pre-flight halt** — every LLM call tracked; budget_guard halts before τ_cost exceeded. [T_{L3.6} T2, T4]

*CCEGAP conditions applied to L3 itself (not re-closures of upstream):*
- **Condition 5 (deterministic T_i)** — every L3 stage exit test is pytest/grep/golden-file; no LLM-in-loop on the test side.
- **Condition 6 (gate discipline)** — every G_{L3.x} is conjunctive; LLM dispatch path forced through ToolCatalog (grep-gate).

*Cross-plan integrations (read-only consumers):*
- E.1 ContractSchema → PromptAssembler typed task block (drift test asserts lockstep).
- B.4 ContextProjection → ContextBudget bucket assignment + L3.3 input.
- F.10 StructuredTransferGate → upstream of PromptAssembler (precondition).
- C.2 SideEffectRegistry → ToolCatalog registration validation.
- C.4 Reversibility → ModelRouter input.
- E.3 AutonomyState → ToolCatalog authority gate + ModelRouter input.
- A.5 MCP idempotency → ToolCatalog dispatch + FailureRecovery retry semantics.
- F.4 BLOCKED state → FailureRecovery + BudgetGuard terminal failure path.

**NOT closed by this plan:**
- LLM **content fidelity** (was the response semantically correct?) — empirical, requires Phase 1 MVP benchmark scoring per QUALITY_EVALUATION.md (deferred).
- Multi-agent **session isolation** — soak/concurrency tests deferred to post-G_L3 (same scope split as G_GOV per CONTRACT §A.6).
- **Prompt injection hardening** beyond structural escaping — security-research scope; tracked in AUTONOMOUS_AGENT_FAILURE_MODES.md §2.4.

---

## 5. Failure scenarios (ASPS Clause 11)

| # | Scenario | Status | Mechanism / Justification |
|---|---|---|---|
| 1 | null_or_empty_input | Handled | L3.1 PromptAssembler signature requires typed inputs (Pydantic) — None on any required arg → ValidationError at boundary; L3.2 ToolCatalog rejects dispatch with empty/missing tool name; L3.3 empty items list → empty FitResult (deterministic, not crash); L3.6 estimate on empty prompt → cost_usd=0 (deterministic). |
| 2 | timeout_or_dependency_failure | Handled | L3.4 ModelRouter fallback chain on provider 5xx/timeout; L3.5 FailureClassifier classifies provider timeout as transient (retryable) or permanent based on rule table; chained timeouts exhausting retry budget → Execution.status=BLOCKED via F.4 pattern. No silent failure. |
| 3 | repeated_execution | Handled | L3.2 ToolCatalog dispatch threads `idempotency_key` from A.5 through every LLM tool call; retries in L3.5 preserve `(execution_id, tool_call_id)` so provider-side dedup honored; L3.6 llm_calls unique on `(execution_id, tool_call_id, retry_count)` so duplicate-call detection at audit layer. |
| 4 | missing_permissions | Handled | L3.2 authority gate blocks `tool.authority_level > autonomy.max_authority(capability)`; provider auth failure classified `permanent` in L3.5 → immediate BLOCKED with `reason='auth_failure'`; per-execution invocation cap (L3.2 T6) prevents runaway. |
| 5 | migration_or_old_data_shape | Handled | L3.6 `llm_calls` migration alembic round-trip (T1); `price_table_version` pinned per call so historical rows survive ADR-006 supersession; L3.4 routing_inputs JSONB tolerates schema evolution (additive). |
| 6 | frontend_not_updated | Handled | L3.6 quarterly dashboard endpoint surfaces costs (UI consumer); other L3 stages backend-only; if future plan adds prompt-debugging UI → ADR + revisit. |
| 7 | rollback_or_restore | Handled | L3.4 env flag `LLM_ROUTER_MODE=sonnet_only` reversible; L3.6 `BudgetGuard` env flag `BUDGET_GUARD_MODE=warn|enforce|off` reversible per phased-rollout pattern (B.5/F.10 idiom); L3.1 templates versioned in repo with git history → revert via PR. All migrations have `down_revision`. |
| 8 | monday_morning_user_state | Handled | L3 stages stateless per call — PromptAssembler/ContextBudget/ModelRouter pure; L3.6 cost aggregation reads from persistent `llm_calls`; L3.5 retry_count is per-call DB column. Process restart → same behavior on next call. |
| 9 | warsaw_missing_data | JustifiedNotApplicable | L3 operates on Task/Execution/llm_calls entities + LLM provider responses. No geographic or regional data dimension. |

---

## 6. Open questions (UNKNOWN — condition 7 applies)

| # | Question | Blocks (hard — stage cannot start until resolved per CONTRACT §B.2) |
|---|---|---|
| Q1 | ADR-004 per-autonomy-level `max_authority` mapping (L3.2 authority gate) — must be CLOSED before L3.2. | Stage L3.2 (BLOCKING) |
| Q2 | ADR-006 model-version pinning + price table + routing_table.yaml shape — full closure required for L3.4 and L3.6. | Stages L3.4, L3.6 (BLOCKING) |
| Q3 | ADR-004 τ_cost (per-Execution cost ceiling) — must be CLOSED before L3.6. | Stage L3.6 (BLOCKING) |
| Q4 | Tokenizer choice for non-OpenAI-compatible providers (Anthropic uses different encoding) — confirm tiktoken vs anthropic-tokenizer mapping per provider before L3.3 ships beyond Sonnet-only. | Stage L3.3 (BLOCKING when MVP scope expands beyond Sonnet-only) |
| Q5 | `app/llm/templates/` initial inventory: minimum 3 per MVP_SCOPE (`code_change_generate`, `ambiguity_extract`, `candidate_evaluate`); full set per task_type × ceremony × capability × model_family is open-ended — establish minimum viable count before L3.1 ships. | Stage L3.1 (informational; minimum 3 enforced in T_{L3.1} T7 via grep) |
| Q6 | Does the existing prompt_parser code have `datetime.now()` calls inside? Grep before wrapping (per upstream A.3 Q2 same concern). | Stage L3.1 (BLOCKING — re-runs A.3 Q2) |
| Q7 | Anthropic provider response schema for Tool Use — JSON exact shape; confirm against current SDK version before L3.2 finalizes JSON Schema validation. | Stage L3.2 (BLOCKING on first non-stub integration) |
| Q8 | Does `llm_calls` table conflict with any existing table from the prior plans? Grep `llm_calls` across codebase before L3.6 migration. | Stage L3.6 (BLOCKING; resolution = either reuse existing or rename) |
| Q9 | Pre-flight estimate accuracy validation — collect 50 historical (estimate, actual) pairs from initial integration runs before T3 of L3.6 is meaningful. Bootstrap problem on first deployment. | Stage L3.6 T3 (informational; baseline-mode allowed for first 50 calls per `evidence_replay.py` first-run pattern from D.5) |

---

## 7. Cross-plan dependencies summary

This plan **consumes** outputs from:

| Upstream stage | What's consumed | How |
|---|---|---|
| A.5 MCP idempotency | `(execution_id, tool_call_id)` keys | L3.2 dispatch + L3.5 retries preserve |
| B.4 ContextProjector | `ContextProjection` with 6 typed fields | L3.1 input + L3.3 bucket assignment |
| B.6 SemanticRelationTypes | `relation_semantic` ENUM on CausalEdge | L3.3 NICE bucket assignment (dependency_relations) |
| C.2 SideEffectRegistry | `@side_effect` decorator presence | L3.2 registration validation |
| C.4 Reversibility | `Change.reversibility_class` | L3.4 routing input |
| E.1 ContractSchema | `render_prompt_fragment()` + `validator_rules()` | L3.1 typed prompt block + drift lockstep |
| E.3 AutonomyState | `max_authority(capability)` + `level` | L3.2 authority gate + L3.4 routing input |
| F.4 BLOCKED state | Terminal failure path | L3.5 + L3.6 escalation |
| F.10 StructuredTransferGate | 6-category projection validation | L3.1 precondition |
| ADR-004 | τ, τ_cost, q_min, max_authority per level | L3.2, L3.6 calibration |
| ADR-006 | Model versions + prices + routing weights | L3.4, L3.6 calibration |

This plan **produces** (consumed by Phase 1 MVP and downstream plans):

| Stage | Output | Consumer |
|---|---|---|
| L3.1 | `AssembledPrompt` (typed) + assembly_checksum | LLM provider call site; L3.6 audit |
| L3.2 | `ToolResult` (typed) + tool_invocations row | Execution flow; L3.6 audit |
| L3.3 | `FitResult` (typed) | L3.1 input pipeline |
| L3.4 | `ModelChoice` (typed) | LLM provider dispatch |
| L3.5 | `RecoveryAction` (typed) | LLM provider dispatch retry loop |
| L3.6 | `llm_calls` row + `BudgetGuard` Verdict | Audit / dashboard / pre-flight gate |

---

## 8. Authorship + versioning

- v1 (2026-04-25) — initial L3 spec; 6 stages closing L3.a-f per MASTER §3.
- Updates require explicit version bump + distinct-actor review per ADR-003.
