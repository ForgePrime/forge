# Automation Roadmap — moving CGAID gates from judgment to determinism

**Status:** opt-in adoption artifact (not framework core)
**Source:** extracted from `OPERATING_MODEL.md` v1.4 §9.3 during the framework v2.0 reorganization
**Audience:** Framework Stewards + engineers tasked with automating gate enforcement

For background on gate types and the spectrum, see [`framework/ARCHITECTURE.md §5.1`](framework/ARCHITECTURE.md). For the current classification of every CGAID gate (which is judgment / rubric / deterministic today, target tomorrow), see `framework/DELIVERY.md §8.1`.

---

## High leverage, low effort (priority)

- **Pre-merge grep for `UNKNOWN` tags** in changed files — block merge if present. Single shell command as git pre-push hook or CI check. *Effort: < 1 day. Leverage: closes Stage 3 largest judgment gap.*
- **PR description grep for ADR references** — enforces Standard-tier traceability. *Effort: < 1 day. Leverage: operationalizes Principle 8 traceability.*
- **Branch protection requiring PR approval** (GitHub/GitLab native setting) — not new infrastructure, just configuration. *Effort: minutes. Leverage: turns Stage 4 review from judgment-enforcement into deterministic-enforcement.*
- **File-existence check for tier-required artifacts** — Side-Effect Map for Standard+, Evidence Pack for all non-Fast-Track, Edge-Case Test Plan for Standard+. *Effort: 1–2 days for CI workflow. Leverage: eliminates "artifact forgotten" failure mode.*

## Medium leverage, medium effort

- **Schema validator for Evidence Pack** — required sections, non-empty lists, proper markdown structure. *Effort: 2–3 days. Leverage: turns Stage 1 from judgment to rubric.*
- **Tier-triggered artifact requirement check** — workflow in `.github/workflows/cgaid-tier-check.yml` that reads declared tier from PR template and enforces required artifact presence. *Effort: 3–5 days. Leverage: enforces Adaptive Rigor matrix (DELIVERY §6.1).*
- **Classification log consistency check** — every file in PR diff must have a classification log entry; CI fails otherwise. *Effort: 1 week. Leverage: moves Stage 0 toward determinism.*

## Lower leverage, higher effort (research before building)

- AI-output scanner for missing epistemic tags on non-trivial claims — would require an ML classifier, not regex. Research whether existing LLM-eval tools can serve this.
- Automated business-outcome detection for specific feature types — domain-specific; only sensible for features with clearly instrumented outcomes (e.g., funnel conversion, latency SLO).
- Static cascade-effect tracer — cross-module side-effect propagation analysis. High value for features like restore, settlement detection; substantial build effort.

## Gates deliberately NOT targeted for determinism

- **PR review approval by a person** — approval-by-person is the point; automating it would remove the human checkpoint that Stage 4 exists to be.
- **Business outcome observation** — fundamentally a human (or client) judgment; DoD rubric reduces ambiguity but does not eliminate it.
- **Non-trivial claim classification at the point of writing** — contextual; determinism would require an oracle that does not exist. Reviewer check at Stage 4 is the fallback.

## Reference pattern for output-stable gates

Several items above (snapshot fixtures, fingerprint comparison) instantiate the [Deterministic Snapshot Validation pattern](templates/PATTERN-snapshot-validation.md). Adopt that pattern explicitly before implementing — it has component-level guarantees and well-known failure modes.

---

## Governance

Roadmap items move through proposal → pilot → adoption, governed by the Framework Stewards' quarterly framework review meeting. Items adopted are removed from this list and reflected in DELIVERY §8.1 gate-classification table (current column updated).

This file is **opt-in**: adopting organizations may build their own roadmap from the same gate inventory. The list above represents the framework owners' current ranking by leverage-to-effort, not a prescription.
