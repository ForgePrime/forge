"""PromptAssembler — Phase L3 Stage L3.1.

Pure-function deterministic prompt assembler. Takes:
- ContractSchema (E.1, just shipped)
- ContextProjection (B.4)
- Optional FitResult (L3.3) — projector output already budget-fitted
- ModelChoice (L3.4) — which model family the prompt targets

Returns AssembledPrompt with deterministic assembly_checksum
(sha256 of normalized inputs) so replay over historical executions
verifies byte-identical output.

Per FORMAL_PROPERTIES_v2 P6 + P12:
- P6: same inputs -> same prompt bytes (no clock/random/network).
- P12: render derives from ContractSchema.render_prompt_fragment(),
  which is the same source as validator_rules() — caller cannot
  observe drift between prompt and validator.

Per PLAN_LLM_ORCHESTRATION L3.1: 5 mandatory CONTRACT §B blocks:
1. Operational contract reminder.
2. ASSUMING / VERIFIED / ALTERNATIVES placeholder (pre-implementation).
3. MODIFYING / IMPORTED BY / NOT MODIFYING (pre-modification).
4. DONE / SKIPPED / FAILURE SCENARIOS placeholder (pre-completion).
5. Tagging rule injection ([CONFIRMED]/[ASSUMED]/[UNKNOWN]).

This commit ships blocks 1 + 5 baked into the system_prompt; blocks
2-4 are caller-supplied placeholders the LLM must fill (per CONTRACT
§B.3-B.5). Caller passes existing ASSUMING/VERIFIED if known.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from app.evidence.context_projector import ContextProjection
from app.llm.context_budget import ContextItem
from app.llm.model_router import ModelFamily
from app.validation.contract_schema import ContractSchema


# CONTRACT §B operational reminder injected into every system prompt.
# Static — same across all assemblies. Bumping this is a breaking change
# (replay determinism breaks; bump schema version).
_CONTRACT_REMINDER = """\
# Operational Contract (CONTRACT §A + §B)

You operate under the following discipline:

1. **Tag every non-trivial claim** with [CONFIRMED] / [ASSUMED] /
   [UNKNOWN] per CONTRACT §B.2. [CONFIRMED] requires you to have
   either executed the check (with output you can quote) or read a
   specific file:line you can cite. [ASSUMED] = inference without
   execution. [UNKNOWN] = STOP, ask.
2. **Disclose immediately** the seven silences (CONTRACT §A): assumption
   instead of verification, partial implementation, happy path only,
   narrow scope, selective context, false completeness, failure to
   propagate.
3. **Evidence-first** before any "works"/"done"/"OK" claim. Use:
   DID: <what> -> <literal output>
   DID NOT: <what> -> <why>
   CONCLUSION: <based ONLY on DID>
4. **Pre-completion structure** (CONTRACT §B.5):
   DONE: [list with evidence per item]
   SKIPPED: [list with rationale + completion plan]
   FAILURE SCENARIOS: minimum 3 (data empty / timeout / concurrent)
5. **Working principles**: do not guess - check; disclose shortcuts;
   push back when something is wrong; trace impact of changes.
"""


@dataclass(frozen=True)
class AssembledPrompt:
    """Deterministic output of PromptAssembler.assemble()."""

    system_prompt: str
    user_prompt: str
    stop_sequences: tuple[str, ...]
    model_family: str  # ModelFamily.value (string)
    schema_version: int  # ContractSchema.schema_version
    assembly_checksum: str  # sha256 hex of normalized inputs

    @property
    def total_chars(self) -> int:
        """Diagnostic: total characters in the assembled prompt."""
        return len(self.system_prompt) + len(self.user_prompt)


def _canonicalize_for_checksum(
    *,
    contract_schema_dump: str,
    projection_signature: str,
    model_family: str,
    extra_user_intent: str,
) -> str:
    """Build the canonical-JSON-serialized checksum input.

    Order + content fixed so the checksum is reproducible across
    Python versions / platforms / dict-ordering quirks.
    """
    payload = {
        "contract_schema_dump": contract_schema_dump,
        "projection_signature": projection_signature,
        "model_family": model_family,
        "extra_user_intent": extra_user_intent,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _projection_signature(projection: ContextProjection) -> str:
    """Stable string capturing the projection's identity for checksum.

    Includes the source_refs (which are already-deterministic strings),
    NOT the content (content can vary in encoding without changing the
    semantic identity — for replay we care about WHICH edges were
    selected, not their literal text).
    """
    sigs = sorted(item.source_ref for item in projection.items)
    return f"{projection.task_node.type}:{projection.task_node.id}|" + "|".join(sigs)


def assemble(
    *,
    contract_schema: ContractSchema,
    projection: ContextProjection,
    user_intent: str,
    model_family: ModelFamily | str,
    extra_context_items: tuple[ContextItem, ...] = (),
) -> AssembledPrompt:
    """Assemble a deterministic prompt for an LLM call.

    Args:
        contract_schema: the schema spec for this (task_type, ceremony).
            ContractSchema.render_prompt_fragment() is consumed here.
        projection: the BFS-projected causal context (B.4 output).
        user_intent: the actual task description (Issue body / task
            instruction). The "what" the LLM should do.
        model_family: ModelFamily enum or its string value. Some prompts
            may differ slightly per model family (e.g. tool-call format).
        extra_context_items: additional ContextItems already budget-
            fitted by L3.3 — appended to the user_prompt verbatim.

    Returns:
        AssembledPrompt with all 5 §B blocks present in the system
        prompt and assembly_checksum reproducible across runs.
    """
    family_str = model_family.value if isinstance(model_family, ModelFamily) else model_family

    # ---- system prompt ----
    contract_fragment = contract_schema.render_prompt_fragment()
    system_parts = [
        _CONTRACT_REMINDER,
        "",  # spacer
        contract_fragment,
    ]
    system_prompt = "\n".join(system_parts)

    # ---- user prompt ----
    user_parts: list[str] = []
    user_parts.append("# Task")
    user_parts.append(user_intent.strip())
    user_parts.append("")

    if projection.items:
        user_parts.append("# Context (causal-graph projection)")
        # Emit in stable order matching ContextItem.source_ref ascending
        for item in sorted(projection.items, key=lambda i: i.source_ref):
            user_parts.append(f"- [{item.bucket.value}] {item.content}")
        user_parts.append("")

    if extra_context_items:
        user_parts.append("# Additional context")
        for item in sorted(extra_context_items, key=lambda i: i.source_ref):
            user_parts.append(f"- [{item.bucket.value}] {item.content}")
        user_parts.append("")

    user_parts.append(
        "Produce output strictly per the Output Contract above. "
        "Tag every non-trivial claim per CONTRACT §B.2."
    )
    user_prompt = "\n".join(user_parts)

    # ---- checksum ----
    checksum_input = _canonicalize_for_checksum(
        contract_schema_dump=contract_schema.model_dump_json(),
        projection_signature=_projection_signature(projection),
        model_family=family_str,
        extra_user_intent=user_intent,
    )
    checksum = hashlib.sha256(checksum_input.encode("utf-8")).hexdigest()

    # ---- stop sequences ----
    # Conservative default; per-model override in future.
    stop_sequences: tuple[str, ...] = (
        "\n\n# End of response",
    )

    return AssembledPrompt(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        stop_sequences=stop_sequences,
        model_family=family_str,
        schema_version=contract_schema.schema_version,
        assembly_checksum=checksum,
    )
