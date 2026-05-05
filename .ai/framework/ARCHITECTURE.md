# CGAID Architecture

**Contract-Governed AI Delivery — Theoretical Foundation**

Version 2.0 · Audience: Framework Stewards, auditors, external reviewers

---

## Positioning

This document is the **theoretical foundation** of CGAID — the model and its governing properties. It states what must be true for the framework to operate. The procedural twin — *how* you perform CGAID work step by step — lives in [`DELIVERY.md`](DELIVERY.md).

If MANIFEST says *what is required* and WHITEPAPER says *why now*, this document says *what must hold for delivery to be CGAID-compliant*.

Three other docs sit around it:

- [`MANIFEST.md`](MANIFEST.md) — ten-principle cultural foundation
- [`DELIVERY.md`](DELIVERY.md) — operational procedures, artifacts, metrics, governance
- [`DATA_CLASSIFICATION.md`](DATA_CLASSIFICATION.md) — Stage 0 instrument
- [`PRACTICE_SURVEY.md`](PRACTICE_SURVEY.md) — empirical foundation
- [`REGULATORY_ALIGNMENT.md`](REGULATORY_ALIGNMENT.md) — regulatory mapping

---

## §0 Scope — two-layer audience

CGAID is scoped at two layers, not two separate frameworks.

**Primary (direct).** The engineer using CGAID to deliver code — solo or with AI as co-producer. All principles, stages, artifacts, metrics, and governance in MANIFEST + DELIVERY apply directly to this audience. This is the framework's load-bearing scope.

**Secondary (derived).** The end-user of a product delivered using CGAID — when that product is itself an agent (customer service, HR assistant, recommendation system). Obligations for end-user-facing products (transparency about agent involvement, education on agent capabilities and failure modes) become **verification targets at Stage 4** rather than a separate framework path. CGAID does not govern the runtime behavior of those products — it governs the discipline by which engineers ensure those products meet their own end-user obligations.

**What this scope rules out.** CGAID is not a runtime monitoring framework for deployed agents (that work belongs to ops/SRE practice — see DELIVERY §"Post-deploy ops" for the minimal hand-off). CGAID is not a customer-facing product policy. CGAID is not a substitute for sectoral compliance (see REGULATORY_ALIGNMENT.md).

---

## §1 Framework Architecture — Four Layers

```
╔═══════════════════════════════════════════════════════════════╗
║  LAYER 1 — PRINCIPLES                                         ║
║   See MANIFEST.md (10 principles + 3 operational rules + DoD) ║
╠═══════════════════════════════════════════════════════════════╣
║  LAYER 2 — TOOLING (tailored, versioned, evolving)            ║
║   Solutioning Cockpit (business intent & specification)       ║
║   Project-Tailored AI Skills & Micro-Skills                   ║
║   Operational Contract (.ai/CONTRACT.md)                      ║
║   Curated Shared Instructions (CLAUDE.md / AGENTS.md)         ║
║   Persistent Memory System                                    ║
╠═══════════════════════════════════════════════════════════════╣
║  LAYER 3 — DELIVERY (stage-gated, reproducible)               ║
║   Stage 0 → Evidence → Plan → Build → Verify                  ║
║   Every gate has defined entry and exit criteria              ║
║   See DELIVERY.md §1 for stage definitions                    ║
╠═══════════════════════════════════════════════════════════════╣
║  LAYER 4 — CONTROL (enforced, not advisory)                   ║
║   Stage 0 Data Classification Gate · Mandatory PR Review      ║
║   Standardized Handoffs · Decision Records                    ║
║   Business-Level Definition of Done                           ║
║   Data Handling (retention · PII scan · erasure)              ║
║   Verification Loop Closed on Business Outcome                ║
╚═══════════════════════════════════════════════════════════════╝
```

The diagram is the architecture. Each layer's content lives in its dedicated location — Layer 1 in MANIFEST, Layer 2 in tooling configuration files, Layer 3 in DELIVERY §1–§3, Layer 4 in DELIVERY §5–§7.

---

## §2 The AI Operational Contract (overview)

The contract is the signature element of CGAID and the direct enterprise counterpart to the Linux Kernel's `Assisted-by` policy. AI operating under CGAID must declare every non-trivial claim with one of three epistemic states (`CONFIRMED` / `ASSUMED` / `UNKNOWN`) and disclose seven behaviors when they occur (assumption-in-place-of-verification, partial implementation, happy-path-only, narrow-scope interpretation, selective context, false completeness, failure to propagate).

The full runtime form — definitions, structural disclosure templates, self-check triggers, subagent rules — lives in [`.ai/CONTRACT.md`](../CONTRACT.md). This section is overview only; nothing here is binding on AI behavior. CONTRACT.md is.

---

## §3 Multi-agent contract — v3.x trajectory

The current contract (CONTRACT.md §B "Subagent delegation") covers AI-to-subagent delegation in the v1.x form: accountability does not reset, epistemic states degrade on crossing, violations are transitive, side-effects aggregate.

**v3.x trajectory:** as multi-agent becomes standard practice, this section will expand into a full inter-agent contract specification covering delegation protocols, conflict resolution between agents, attribution of accountability across multiple independent AI contributors to a single system, agent identity (per-agent tokens, scoped permissions, recursive-delegation logging), and dynamic permission management. The current v1.x stub is the placeholder preventing the framework from being silent on a technology that is already in production use; the v3.x expansion is deliberately deferred until practice surfaces concrete patterns to codify.

---

## §4 Contract enforceability — requirements on `.ai/CONTRACT.md`

For the principles in §2 to be enforceable at runtime — for silence to become a visible absence rather than a default — the contract file must operationalize them. A framework-compliant `.ai/CONTRACT.md` must specify:

1. **Structural format for each disclosure.** Concrete labeled checkpoints (`DID/DID NOT/CONCLUSION`, `ASSUMING/VERIFIED/ALTERNATIVES`, `MODIFYING/IMPORTED BY/NOT MODIFYING`, `DONE/SKIPPED/FAILURE SCENARIOS`, `IMPACT/ROLLBACK/COST`) so a missing slot is detectable.
2. **Runtime-evidence semantics for `CONFIRMED`.** Execution with observable output OR direct citation; reading code without executing is `ASSUMED`.
3. **Operational definition of non-trivial.** ≥7 positive criteria, ≥3 trivial exceptions, concrete examples with commit references.
4. **Self-check triggers beyond structural disclosure.** At minimum: false agreement, competence boundary, solo-verifier.
5. **Subagent delegation rules** in runtime terms, per §3 above.
6. **Organization-specific behavioral guardrails.** Scope minimality, dependency touch-policies, data-preservation posture.
7. **Full enumeration of the 7 disclosure behaviors** as a single contiguous list with "what must be disclosed" per behavior.
8. **Cascade compression rule** with the three permissibility conditions, a good example, a bad example.
9. **Strategic enforcement gates** — deterministic invocation triggers (e.g., last-commit < 24h auto-invokes `/debug` Phase 1).
10. **Skill-pointer convention** — task-specific rules live in `.claude/skills/<name>/SKILL.md`, not in CONTRACT.md.

Missing any of these renders the contract unenforceable and is a framework-level violation. Framework Steward verifies at each quarterly adoption audit (DELIVERY §11).

---

## §5 Enforceability properties

A framework is enforceable when three properties hold:

1. **Reproducible by outsiders** — a new team, with the documentation alone, can operate it.
2. **Artifact-driven, not personality-driven** — quality does not depend on which engineer is in the room.
3. **Gated, not voluntary** — stage transitions require evidence, not approval-by-vibe.

CGAID is designed to satisfy all three: every layer has versioned documentation, every stage has checklistable entry and exit criteria (DELIVERY §1), and the operational contract (§2) makes the most opaque actor in the delivery loop — the AI — the most auditable. These properties are established by construction; empirical validation is conducted at the end of each 90-day adoption cycle (DELIVERY §9).

### §5.1 Gate types — definitions

For property 3 ("gated, not voluntary") to carry operational weight, every gate must be classifiable by **how** it is evaluated. Without that classification, "gate" is rhetoric — it sounds like enforcement but is in practice voluntary interpretation under deadline pressure.

Every CGAID gate sits somewhere on this spectrum:

```
Deterministic ───────── Rubric-based ─────────── Judgment-based
 (script / CI)           (rule applied by                  (subjective
  pass/fail              human or AI                        evaluation
  automated              with artifact                      without
                         as reference)                      reference)
```

- **Deterministic gates** — evaluated by script or automated check. Pass/fail not open to interpretation. Examples: *"file exists"*, *"PR description references `decisions/NNN-*.md`"*, *"no `UNKNOWN` tag in merged code"*. Strongest gates — they do not degrade under pressure because they are not administered by humans under pressure.
- **Rubric-based gates** — human or AI applies an explicit rule set, with the rubric as the artifact of record. Judgment is constrained by documented criteria. Examples: Data Classification Rubric decision tree, Fast Track preconditions (DELIVERY §6.2), non-trivial claim classification per CONTRACT.md. Degrade under pressure only where the rubric has ambiguity.
- **Judgment-based gates** — human or AI without explicit rubric. Relies on expertise, context, care. Examples: *"Evidence Pack is complete"*, *"Every risk has an owner"*, *"Business outcome observed"*, PR review approval. Weakest gates — judgment is compromised under pressure and hard to audit retrospectively.

**No gate is inherently better — gates must match their context.** What matters is: (a) honesty about which gates are which, (b) deliberate movement toward determinism where the cost of a bypass is high, (c) matching verification effort to blast radius of failure.

The current state of every CGAID gate (with target classification) is tabulated in DELIVERY §8.1.

---

## §6 Solo-verifier rule

A specific failure mode applies when AI is both producer and verifier at the same gate.

**The problem.** If AI produces a Stage 2 plan and AI also verifies the plan meets Stage 2 exit criteria, verification is self-referential. AI can output *"all risks have owners, all decisions have records, plan is complete"* with the same confidence whether this is true or fluent-wrongness. This is Pathology 2.1 (Fluent Wrongness — see WHITEPAPER) applied to framework self-enforcement.

**The rule.** AI cannot be solo verifier of its own work at any CGAID gate. At minimum, one of the following must hold:

1. **A human verifies** — engineer, Framework Steward, or PR reviewer independently evaluates the gate.
2. **A different AI instance verifies** — separate session, without access to the original reasoning trace, evaluates against the rubric. Not a follow-up turn in the same conversation. Not the same agent "reviewing its own work" in-context.
3. **A deterministic check verifies** — script, CI, or grep evaluates the gate.

An AI saying *"I have reviewed the plan and it meets all criteria"* in the same turn that produced the plan is **not verification** — it is consistent inference from the same priors. Treated as a contract violation: false completeness (CONTRACT §A.6).

**Edge case — AI subagents.** If a CGAID-governed engineer delegates work to a subagent (per §3 multi-agent), the delegating engineer cannot use "the subagent verified its own work" as gate evidence. Subagent verification of subagent work is AI-as-solo-verifier with extra steps. The delegating party must independently verify or use a deterministic check.

---

## §7 Horizon — 12 to 24 months

**Today (v1.x)** — AI is a co-producer. Humans own the contract, gates, and verification. CGAID makes co-production safe and measurable.

**12 months (v2.x)** — AI operates at higher autonomy on bounded tasks (refactoring, test generation, migration). Contract and gates expand to cover autonomous execution windows. Verification becomes continuous, not episodic.

**24 months (v3.x)** — Multi-agent delivery is standard. CGAID governs *inter-agent* contracts alongside human-AI contracts. Framework handles delegation, conflict resolution, accountability across multiple AI contributors. Human role shifts from co-producer to governor of the delivery system itself.

The organizations that will be ready for v3.x are the ones that adopt v1.x now. Those that wait will not transition — they will have to transform under incident pressure.

---

## Governance of this document

- **Owners:** Framework Stewards (see DELIVERY §11 Governance for scale-tiered model)
- **Status:** Foundational. Theoretical claims here govern the procedural realization in DELIVERY.md
- **Change process:** any change to §1–§6 requires (a) proposed amendment, (b) **observed evidence** from at least one delivered feature — data, not intent, (c) sign-off by Lead Steward plus one peer Steward
- **Review cadence:** annually as part of framework health review; immediately on any framework-level violation found in adoption audit

Source material: this document was extracted from `OPERATING_MODEL.md` v1.4 §1, §4 intro, §4.2 trajectory, §4.4, §9 intro, §9.1 spectrum, §9.2, §11 during the v2.0 reorganization.
