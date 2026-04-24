"""Validation layer — Phase A Stage A.1-A.5 per PLAN_GATE_ENGINE.

This module contains deterministic validation primitives:
  - VerdictEngine: pure function evaluate(artifact, evidence, rules) → Verdict
  - GateRegistry: static (entity, from_state, to_state) → [rule_refs] map
  - RuleAdapter: protocol for adapting existing validators to VerdictEngine

Shadow mode: VERDICT_ENGINE_MODE=off by default. These stubs exist to
establish import paths and test scaffolding without changing runtime behavior.
Full behavior wiring happens at Phase A.4 (enforcement cutover).

Status: DRAFT — pending distinct-actor review per ADR-003 + ADR-014
(C2 sufficiency gate placement).
"""
