# CGAID Operating Model

**Contract-Governed AI Delivery — Operational Detail**

Version 1.4 · 2026-04-19 · Audience: engineering, Framework Stewards, adoption teams

---

## Positioning

This is the **operational detail** of how Contract-Governed AI Delivery (CGAID) runs day to day. Three other documents sit around it:

- **[MANIFEST.md](MANIFEST.md)** — the ten-principle cultural foundation. What is true, what is required.
- **[WHITEPAPER.md](WHITEPAPER.md)** — the public case for why governance matters now. Industry evidence, pathologies, economic reframing.
- **[DATA_CLASSIFICATION.md](DATA_CLASSIFICATION.md)** — the operational instrument of Stage 0.
- **[PRACTICE_SURVEY.md](PRACTICE_SURVEY.md)** — the empirical foundation of the framework.

If MANIFEST says *what* and WHITEPAPER says *why*, this document says *how*.

---

## 1. Framework Architecture — Four Layers

```
╔═══════════════════════════════════════════════════════════════╗
║  LAYER 1 — PRINCIPLES                                         ║
║   Spec-Driven · Test-Driven · Business-Driven                 ║
║   AI Under Operational Contract · Evidence Over Opinion       ║
║   Verify Before Claim · Review Is Mandatory                   ║
╠═══════════════════════════════════════════════════════════════╣
║  LAYER 2 — TOOLING (tailored, versioned, evolving)            ║
║   Solutioning Cockpit (business intent & specification)       ║
║   Project-Tailored AI Skills & Micro-Skills                   ║
║   Operational Contract (.ai/CONTRACT.md)                      ║
║   Curated Shared Instructions (CLAUDE.md / AGENTS.md)         ║
║   Persistent Memory System                                    ║
╠═══════════════════════════════════════════════════════════════╣
║  LAYER 3 — DELIVERY (stage-gated, reproducible)               ║
║   Evidence → Plan → Build → Verify                            ║
║   Every gate has defined entry and exit criteria              ║
╠═══════════════════════════════════════════════════════════════╣
║  LAYER 4 — CONTROL (enforced, not advisory)                   ║
║   Stage 0 Data Classification Gate · Mandatory PR Review      ║
║   Standardized Handoffs · Decision Records                    ║
║   Business-Level Definition of Done                           ║
║   Data Handling (retention · PII scan · erasure)              ║
║   Verification Loop Closed on Business Outcome                ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## 2. Delivery Stages (Stage 0 Gate + Four Delivery Stages)

### Stage 0 — Data Classification (Gate)

> **Honesty statement on enforcement.** Stage 0 is a *policy-level gate* enforced by discipline and process, not by technical controls. Unless the adopting organization deploys DLP (Data Loss Prevention), enterprise AI connectors that accept only pre-classified content, or approved file-sharing boundaries, any engineer with direct access to an AI tool can bypass the gate (copy-paste, screenshot, ad-hoc upload). For Confidential+ processing at enterprise scale — especially in regulated industries — technical enforcement is strongly recommended in addition to the policy gate described here. Adopting organizations must either (a) accept the residual risk of a discipline-based gate and document that acceptance, or (b) implement technical enforcement before processing Confidential+ material. Failure to do either is a known CGAID adoption anti-pattern.

- *Input:* any client material — documents, meeting notes, specifications, emails, data samples — before it enters the Solutioning Cockpit, the codebase, or any AI-accessible memory.
- *Activity:* classify every item under the four-tier Data Classification Rubric (artifact #10): **Public / Internal / Confidential / Secret**. Route accordingly:
  - *Public & Internal* → may enter AI workflows under default vendor terms.
  - *Confidential* → requires client consent + AI vendor Data Processing Agreement (DPA) review + routing to zero-retention processing tiers only.
  - *Secret* → excluded from AI workflows entirely; processed by humans, with AI usage prohibited for that content.
- *Exit criteria:* every item classified and routed; confidential+ content carries a provenance marker through all downstream stages; classification decisions logged and reviewable by Framework Stewards.
- *Purpose:* prevents irreversible client IP / PII exposure to AI vendors. This is a **hard gate** — no other stage may begin for a given piece of client material until it has passed Stage 0.

### Stage 1 — Evidence

- *Input:* client documentation, meeting notes, domain context, prior incidents.
- *Activity:* analyze, cross-reference, hunt inconsistencies, name assumptions, list unknowns.
- *Exit criteria:*
  - list of inconsistencies produced; open questions escalated to client
  - nothing tagged `UNKNOWN` carried forward silently
  - **volume-and-coverage check** for any filter, CTE, aggregation, or join introduced: stated expected output volume range; flag if the assumption would exclude >10% of input (addresses Practice Survey Gap 3 / incident `6ee9561` where a date filter excluded 96% of settlements)

### Stage 2 — Plan

- *Input:* evidence pack from Stage 1.
- *Activity:* master plan in Solutioning Cockpit (business intent); execution plan alongside the codebase (technical decisions); risks, decisions, edge cases, and verification criteria surfaced.
- *Exit criteria:* every risk has an owner; every decision has a record; edge-case test list exists; business-level Definition of Done defined.

### Stage 3 — Build

- *Input:* approved execution plan.
- *Activity:* implementation against the plan, not against the ticket. AI operates under contract — every non-trivial assumption tagged `CONFIRMED`, `ASSUMED`, or `UNKNOWN`. No silent shortcuts.
- *Exit criteria:* code matches plan; if it diverges, the plan is updated first; pull request opened with traceability to plan, tests, and decisions.

### Stage 4 — Verify

- *Input:* pull request.
- *Activity:* mandatory code review; automated test verification; business outcome verification against DoD; feedback loop until closed.
- *Exit criteria:* business outcome observed in the target environment; verification artifact filed; lessons captured as framework changelog entries if applicable.

---

## 3. Standardized Artifacts (no improvisation)

Every CGAID project produces the same artifact set:

1. **Evidence Pack** — inconsistencies, assumptions, unknowns, open questions.
2. **Master Plan** (Solutioning Cockpit) — business intent, scope, success criteria.
3. **Execution Plan** (in-repo, `.ai/PLAN_*.md`) — phased, with status per phase.
4. **Handoff Document** (Cockpit → codebase) — intent, scope, assumptions, unknowns, decisions needed, risks, edge cases, verification criteria.
5. **Architecture Decision Records** (`.ai/decisions/NNN-*.md`) — context, options, chosen path, rationale, impact.
6. **Edge-Case Test Plan** — failure modes first, happy paths by implication.
7. **Business-Level Definition of Done** — expected business behavior observed, edge cases verified, assumptions resolved or explicitly accepted, PR reviewed, post-implementation verification closed.
8. **Skill Change Log** — what failed, what changed, why, observed impact.
9. **Framework Manifest & Changelog** — this document and related framework documents, versioned.
10. **Data Classification Rubric** (`.ai/framework/DATA_CLASSIFICATION.md`) — the four-tier classification scheme (Public / Internal / Confidential / Secret) with routing rules, examples per tier, log template, and AI-vendor DPA mapping. Applied at Stage 0.
11. **Side-Effect Map** — enumeration of every function, external system, database table, flag, and mutating operation a feature's code paths touch. Required for Standard and Critical tiers when the feature interacts with external systems, production data, mutating endpoints, or cross-module state. Produced at Stage 2 Plan; referenced at Stage 3 Build and Stage 4 Verify. Addresses Practice Survey Gap 2 / live-side-effects incident (fake-ID test triggered real flag flips on live because the call-path side-effect graph was not traced before execution). Suggested format: table with columns *function/endpoint · side-effects triggered · reversibility · preconditions for safe invocation*.

---

## 4. The AI Operational Contract (Layer 1 enforcement)

The contract is the signature element of CGAID and the direct enterprise counterpart to the Linux Kernel's `Assisted-by` policy. AI operating under CGAID must declare, for every non-trivial claim, one of three epistemic states:

- **`CONFIRMED`** — verified by **runtime evidence** (execution with observable output) or by **direct citation** of a specific file line. Reading code without executing it is `ASSUMED`, not `CONFIRMED`. This closes the "I read the code, so it's verified" loophole.
- **`ASSUMED`** — believed true for a stated reason, not verified by runtime evidence or citation.
- **`UNKNOWN`** — cannot be determined; triggers a stop-and-ask gate. If, after escalation, the responsible human explicitly accepts the risk and directs the AI to proceed, the claim is recorded as `ASSUMED: accepted-by=<role>, date=<YYYY-MM-DD>` — acceptance does not transmute an assumption into verification.

In addition, seven behaviors must be disclosed by AI the moment they occur:

1. Assumption in place of verification
2. Partial implementation
3. Happy-path-only coverage
4. Narrow interpretation of scope
5. Selective context
6. False completeness
7. Failure to propagate change

Silence on any of the seven is a contract violation — treated with the same severity as a failing test. The full contract text lives in `.ai/CONTRACT.md`, versioned and enforceable.

### 4.1 Cascade-level tagging (compression for propagation contexts)

In cascade, propagation, or idempotency contexts — where 20+ dependent decisions share a common invariant — tagging every step inflates the output without adding information. CGAID permits **invariant-level tagging** as a compression.

Rule: a single tagged statement may cover N dependent decisions if and only if the invariant is explicitly named and the decisions are verifiable against it.

- ✅ `ASSUMED: cascade_restore preserves idempotency across N ≥ 1 invocations (verified by test X; untested for concurrent invocations)`
- ❌ `ASSUMED: everything works` (no invariant, no verification condition)

Per-step tagging is still required when dependent decisions are **not** covered by a named invariant (they are individually non-trivial). Cascade compression is a tool, not a license. Framework Steward may reject a compression as insufficient and require per-step tagging during review.

Addresses Practice Survey Gap 1 (cascade decision compression — observed in incidents `f6d24dc`, `318f74a`, `71fa577`, `c31b116`, `bf66299`).

### 4.2 Multi-agent contract (v1.x stub, v3.x expansion)

When a CGAID-governed engineer delegates to a secondary AI agent (subagent, autonomous tool, specialist model), the contract does not re-bind from scratch. The following rules apply:

1. **Delegation does not reset accountability.** The delegating party (human or AI) inherits responsibility for the delegate's output. No "the subagent did it" defense.
2. **Epistemic states propagate.** If the subagent returns a CONFIRMED claim, the delegating party must still verify the claim against its own context. A CONFIRMED from a subagent is ASSUMED at the parent level until independently verified.
3. **Contract violations are transitive.** A violation by any agent in the delegation chain is a violation by the chain. Disclosure obligations flow upward.
4. **Side-effects aggregate.** The side-effect map (artifact #11) at the parent level must include side-effects introduced by any subagent's actions.

**v1.x scope:** these rules apply to explicit subagent invocations (Agent tool in Claude Code, MCP tool use with mutating effects, any tool whose output is consumed without human intermediation).

**v3.x trajectory:** as multi-agent becomes standard, this section expands into a full inter-agent contract specification covering delegation protocols, conflict resolution between agents, and attribution of accountability across multiple independent AI contributors to a single system. Current stub is the placeholder preventing the framework from being silent on a technology that is already in production use.

### 4.3 Rule lifecycle (operationalizing Zasada 10)

MANIFEST Zasada 10 requires that every incident produces a rule, test, or tooling improvement. Without a retirement mechanism, this produces rulebook bloat over 12–24 months. CGAID therefore defines a rule lifecycle.

**Rule creation** — an incident becomes a rule when (a) it has been encountered at least twice, or (b) its blast radius would have justified prevention at any frequency. Lead Steward confirms the promotion. Rule is added to the relevant document (`.ai/CONTRACT.md`, `.ai/standards.md`, a skill, or a checklist).

**Runtime incidents (v1.5 addition).** Failures observed in deployed code — production incidents, user-reported regressions, monitoring-surfaced anomalies — count as framework-level failures for MANIFEST Principle 10 **if they reveal a gap in Stage 1, 2, or 3 coverage**. That is: the incident would have been preventable had a different assumption been tagged, a different edge case tested, or a different side-effect mapped during the original delivery. Such runtime incidents are prioritized for rule creation regardless of frequency — blast radius alone justifies prevention, per criterion (b) above. Runtime incidents that do *not* reveal coverage gaps (pure infrastructure failures, third-party outages, acts of nature) are outside Principle 10 scope and handled by standard incident-response processes; no framework rule is generated from them. This distinction is critical — conflating all runtime incidents with framework gaps produces rulebook bloat and dilutes signal.

**Rule measurement** — each rule carries a creation date and a stated scenario it prevents. At each quarterly adoption audit, Stewards review every rule older than 90 days for prevention evidence (has this rule caught or prevented anything in the last quarter?).

**Rule retirement triggers** — a rule is a candidate for retirement when any holds:
- It has prevented zero observable incidents for 12 consecutive months (no evidence it is load-bearing).
- Another rule covers the same scenario with broader scope (merge into the broader rule).
- The underlying cause no longer exists (e.g., the subsystem it guarded was removed; a newer mechanism makes the rule unnecessary).

**Retirement process** — proposed retirement goes through the standard change process (observed evidence + Lead Steward + peer Steward sign-off). Retired rules are moved to an archive (`.ai/archive/retired_rules.md`) with date, reason, and any residual guidance.

**Rationale:** a rulebook that only grows becomes unreadable. A rulebook that only shrinks becomes uninsured. This lifecycle keeps both pressures balanced — it is the mechanism that makes Zasada 10 sustainable rather than bloating.

Addresses deep-risk finding: without retirement, Zasada 10 produces unreadable rulebook in 18 months.

### 4.4 Contract enforceability — requirements on `.ai/CONTRACT.md`

The three epistemic states, seven disclosure behaviors, cascade compression rule, and multi-agent rules above are prescriptive principles. For them to be enforceable at runtime — i.e., for silence to become a visible absence rather than a default — the contract file must **operationalize** them. A framework-compliant `.ai/CONTRACT.md` is required to specify the following. Missing any of these renders the contract unenforceable and is itself a framework-level violation.

1. **Structural format for each disclosure.** Abstract "disclose the assumption" degrades to silence under pressure. The contract must define **concrete labeled checkpoints** — fixed field names with mandatory slots — so that a slot being empty is itself a visible signal. The labels are `DID / DID NOT / CONCLUSION` (evidence report), `ASSUMING / VERIFIED / ALTERNATIVES` (pre-implementation), `MODIFYING / IMPORTED BY / NOT MODIFYING` (scope declaration), `DONE / SKIPPED / FAILURE SCENARIOS` (completion report), `IMPACT / ROLLBACK / COST` (pre-change discipline — applies universally to every non-trivial change, not only debug). Any adopting organization may rename the labels, but must keep the property that a missing slot is detectable.

2. **Runtime-evidence semantics for `CONFIRMED`.** Per §4 above: CONFIRMED requires execution with observable output or direct citation; reading code without executing is `ASSUMED`. The contract must encode this strictly — using the weaker "verified" alone re-opens the loophole.

3. **Operational definition of non-trivial.** The 7 disclosure behaviors trigger on "non-trivial claims". Without a test for non-triviality, under pressure classification defaults to trivial and the contract evaporates. The contract must specify: **positive criteria** (≥ 7 conditions that make a claim non-trivial — data impact, contract change, assumption-about-other-code, cascade, compliance, timing/idempotency, external-integration), **trivial exceptions** (≥ 3 — cosmetic, private symbol, test-already-covered), and **concrete examples from project practice** with commit references. This is what elevates the definition from rhetoric to rubric.

4. **Self-check triggers beyond structural disclosure.** Several failure modes are not caught by the 7 disclosure behaviors and require reflexive checks that fire when the AI notices the pattern in itself — not on a scheduled checkpoint. The contract must list at minimum: **false agreement** (agreeing on the basis of the user's claim, not own verification), **competence boundary** (guessing outside domain knowledge — legal, financial formulas, vendor specifics), and **solo-verifier** (marking one's own just-produced artifact as verified in the same turn; see §9.2).

5. **Subagent delegation rules (runtime-level).** The multi-agent principles in §4.2 must be expressed in the contract in runtime terms: delegation does not reset accountability, a subagent's `CONFIRMED` is `ASSUMED` at the parent, violations are transitive, side-effects aggregate upward into the parent's completion report. These are not optional — Claude Code, the Agent tool, and MCP tool invocations are day-one subagent vectors.

6. **Organization-specific behavioral guardrails.** Rules about what the AI may initiate — scope minimality (no refactor-adjacent), configuration/dependency touch-policies (ask before changing build / lock / env files), data-preservation posture (never `DELETE FROM` without consent) — are local to each adopting team. The contract carries these so they are bound to the same review cadence and visibility as the disclosure rules, not scattered across ad-hoc documents.

7. **Full enumeration of the 7 disclosure behaviors.** The 7 behaviors named in §4 intro (assumption-in-place-of-verification, partial implementation, happy-path-only, narrow-scope interpretation, selective context, false completeness, failure to propagate) must be reproduced in CONTRACT.md as a single contiguous list (e.g., as a table), with a "what must be disclosed" column per behavior. An abstract mention of "the seven" is not sufficient — the reader at runtime must see the full set without leaving the contract file.

8. **Cascade compression rule reproduced with good/bad examples.** The §4.1 invariant-level tagging rule must appear in CONTRACT.md with (a) the three permissibility conditions (named invariant, verification condition, explicit scope), (b) a `good` example with all three satisfied, (c) a `bad` example that fails the named-invariant condition. Cross-reference to §4.1 for governance override is sufficient; the operational rule itself must live in CONTRACT so it is applied at runtime, not looked up from governance.

9. **Strategic enforcement gates (deterministic invocation).** Beyond local self-check (clause 4), the contract must define gates that fire **deterministically based on external state**, independent of whether the AI flags the situation itself. Required content per gate: (a) trigger condition (mechanically checkable — e.g., last commit affecting a target file is `<24h` old; current change classified non-trivial per the rubric), (b) mandatory action (literal output of a specific structural format or auto-invocation of a named skill), (c) escape rule (when the gate does not apply). Self-check (clause 4) catches local violations; strategic gates catch loop patterns that operate **across multiple compliant fixes**. Empirical anchor: TD-20..TD-25 defensive-fix ladder  — 5 fixes deep without model re-evaluation; each fix individually passed §A/§B disclosure; the cumulative drift required reverting 4 of 5 commits. Self-check was structurally insufficient.

10. **Skill-pointer convention for task-specific strategic rules.** Rules that apply only to a specific work mode (debug, plan, verify, explore, build) — loop-detection counters, baseline-lock formats, adversarial-pre-code challenge prompts, alternatives-override of simple-bug exception, etc. — live in `.claude/skills/<name>/SKILL.md`, not in CONTRACT.md. The contract carries only (a) a pointer to the relevant skill, and (b) the trigger that auto-invokes it via clause 9. This separates **universal disclosure** (CONTRACT.md owns end-to-end) from **task-specific enforcement** (skills own end-to-end), avoiding ontology duplication and keeping the runtime contract focused on what every change must produce regardless of mode.

### 4.5 Validation — how the contract is audited

Framework Steward at each quarterly adoption audit verifies that the contract file still satisfies §4.4 clauses 1–10. A contract that has drifted (structural format abandoned, CONFIRMED loosened, non-trivial definition removed, subagent rules missing, 7 disclosure behaviors not enumerated, cascade compression rule delegated out of the contract, strategic gates absent or non-deterministic, skill-pointer convention violated by re-inlining task-specific rules) is treated with the same severity as a skipped Stage 1 gate: the framework is not operating.

---

## 5. Metrics Surface

CGAID is measurable. Every project reports seven metrics. **Each metric has an operational playbook stating how it is collected; metrics without infrastructure are flagged as such, not hidden.**

### Metric 1 — Inconsistencies caught pre-code (Stage 1 output)

- **What it measures:** count of inconsistencies, assumptions, and unknowns surfaced during Stage 1 Evidence, before planning or implementation begins.
- **Who measures:** Framework Steward (Lead) reviews Stage 1 outputs at end of each feature.
- **Tool:** the Evidence Pack (artifact #1) is the source — counted directly from the list it produces.
- **Frequency:** per feature at Stage 1 exit; aggregated quarterly.
- **Baseline:** established at Day 90; expected range depends on feature size (small: 2–5, medium: 5–15, large: 15+).
- **Infrastructure:** trivially collectable from day 1 — requires only that Evidence Pack be produced. No missing infrastructure.

### Metric 2 — Decisions surfaced in planning vs. surfaced in production (ratio)

- **What it measures:** proportion of architectural and business decisions that were identified and recorded in Stage 2 Plan (and logged as ADRs) versus those that surfaced reactively during or after implementation.
- **Who measures:** Framework Steward, in coordination with the engineer(s) on the feature.
- **Tool:** requires (a) ADR log (`.ai/decisions/`), (b) a post-implementation review that classifies each decision as "planned" or "unplanned."
- **Frequency:** per feature at Stage 4 close; quarterly aggregate.
- **Baseline:** **must be established during first quarter of adoption.** Initial ratio is unknown and will vary by domain (SQL-heavy work may have more unplanned decisions than greenfield logic).
- **Infrastructure gap:** requires a post-implementation review step that currently is not standardized. Until the review step is operational, this metric is **"baseline in progress"** and should not be reported as a current number.

### Metric 3 — Edge cases caught in test planning vs. in production (ratio)

- **What it measures:** proportion of edge cases and failure modes that were listed in the Edge-Case Test Plan (artifact #6) during Stage 2 versus those that surfaced as bugs in production or during integration testing.
- **Who measures:** engineer closing the feature, reviewed by Steward.
- **Tool:** requires (a) Edge-Case Test Plan per feature, (b) incident log that attributes production bugs to "was this edge case in the plan? yes/no."
- **Frequency:** per feature at Stage 4; quarterly aggregate.
- **Baseline:** as Metric 2 — established during first quarter.
- **Infrastructure gap:** requires incident-to-plan attribution not currently standardized. Attribution is subjective; dispute resolution via Steward decision.

### Metric 4 — AI contract violations disclosed vs. detected downstream

- **What it measures:** of all surfaced contract violations (epistemic tag omitted, happy-path shortcut, unpropagated change), what proportion was self-disclosed by the AI at time of action versus detected later by a reviewer, audit, or incident.
- **Who measures:** Framework Steward, during quarterly adoption audit.
- **Tool:** requires (a) contract violation log, (b) classification of each violation as "self-disclosed" or "detected downstream."
- **Frequency:** quarterly.
- **Baseline:** target > 95% self-disclosed after first quarter.
- **Infrastructure gap:** requires a formal "contract violation log" that does not currently exist. **Until the log is operational, Metric 4 is aspirational, not measurable.** This metric's existence is arguably a research question (is the contract effective?) rather than an operational indicator.

### Metric 5 — Skill changes with before/after outcome

- **What it measures:** for each change to a custom skill (Layer 2 tooling), did the change reduce downstream defect or rework rate for tasks governed by that skill, over the 30 days following the change?
- **Who measures:** Framework Steward reviewing Skill Change Log (artifact #8).
- **Tool:** requires (a) Skill Change Log, (b) attribution of defects/rework to specific skill-governed actions.
- **Frequency:** per skill change; aggregated quarterly.
- **Baseline:** established empirically; no universal target.
- **Infrastructure gap:** attribution of defects to skill-governed actions requires instrumentation currently not standardized. **In practice, v1.x this is qualitative ("we think skill X helps") rather than quantitative.** True before/after measurement requires defect-to-skill attribution infrastructure — flagged as v2.x work.

### Metric 6 — Time from merge to business-outcome verification

- **What it measures:** elapsed time between pull request merge and confirmation that the intended business outcome is observed in the target environment (per Principle 6 of MANIFEST and Business-Level DoD).
- **Who measures:** engineer closing the feature; Steward validates.
- **Tool:** requires definition of "business verification event" per feature — must be specified in the Business-Level DoD at Stage 2.
- **Frequency:** per feature; quarterly aggregate.
- **Baseline:** should trend down over time; no universal target.
- **Infrastructure gap (partial):** for some features (e.g., settlement detection correctness) the business verification event is weeks or months after merge. Metric is measurable but its value materializes slowly. Short-cycle features (UI tweaks, simple bug fixes) have same-day verification and provide the near-term signal.

### Metric 7 — PR review cycle time

- **What it measures:** time from pull request open to merge, including review.
- **Who measures:** engineering team; standard DevOps metric.
- **Tool:** GitHub/GitLab/Bitbucket native reporting.
- **Frequency:** continuous; dashboard visible to team.
- **Baseline:** pre-CGAID baseline measured before adoption; target: no regression against pre-CGAID level (guards against the +91% AI-team regression documented by Faros AI).
- **Infrastructure:** trivially collectable. No gap.

### Honest summary of measurability

| Metric | Collectable from Day 1 | Requires new infrastructure | Notes |
|---|---|---|---|
| 1. Inconsistencies pre-code | ✅ | No | Requires only that Evidence Pack be produced |
| 2. Decisions plan vs. prod | ⚠ | Yes (attribution process) | Baseline during Q1 |
| 3. Edge cases plan vs. prod | ⚠ | Yes (attribution process) | Baseline during Q1 |
| 4. Contract violations disclosed vs. detected | ❌ | Yes (violation log) | Aspirational until log exists |
| 5. Skill change outcomes | ❌ | Yes (defect attribution) | Qualitative in v1.x; quantitative in v2.x |
| 6. Merge → business verification | ⚠ | Partial (DoD must name event) | Measurable; value slow |
| 7. PR review cycle time | ✅ | No | DevOps-standard |

**Without the honest assessment above, metrics are marketing, not operations. CGAID chooses honesty: two metrics collectable today, two more collectable after ~1 quarter of operational discipline, three flagged as requiring infrastructure before they become real.** Report numbers for 1 and 7 immediately. Report 2, 3, and 6 after the infrastructure is in place. Treat 4 and 5 as v2.x targets.

---

## 6. Data Handling Requirements

CGAID operates on client data by design. Three data-handling practices are mandatory, not optional.

**Memory retention.** The persistent memory system operates on a rolling window. Defaults: 90 days for project-level memory, 30 days for session-level artifacts. Entries older than the window are either archived to controlled storage (not AI-accessible) or deleted. The retention policy is configurable per client contract and explicitly recorded in the Data Classification Rubric.

**PII scanning and control.** Memory and Solutioning Cockpit content are subject to:
- *Automated PII scan on every write* — pattern-matched detection of emails, phone numbers, national IDs, financial identifiers, and names in role context.
- *Quarterly manual audit* of randomly sampled memory and specification content.
- *Findings protocol*: detected PII outside its expected classification triggers a Stage 0 re-classification review; if mis-routed, erasure plus an incident log entry are mandatory.

**Implementation guidance (v1.5 addition).** CGAID does not ship a PII scanner. Recommended tooling options:
- **Microsoft Presidio** — open source, pattern + ML-based detection, self-hostable; default recommendation for teams needing to avoid sending content to third-party services for scanning.
- **AWS Comprehend PII** — managed, API-based; appropriate where AWS is already the processing substrate.
- **Google Cloud DLP** — managed, pattern-based; similarly for GCP-native stacks.
- **Enterprise DLP** (Symantec, Microsoft Purview, etc.) — where already deployed organization-wide.

Pattern library for custom detectors (business-specific identifiers, internal employee ID formats, client-specific number schemes) should be published as `.ai/pii_patterns.md` in the adoption repository — this is an adoption artifact, not part of framework core. Pattern library reviewed quarterly during the manual audit. False positives are expected and are triaged in the quarterly audit.

**If no scanner is deployed, §6 PII-scanning requirement is aspirational**, not operational. This must be documented in the organization's adoption record and flagged for closure within the first quarter of adoption. Adopting without a scanner is a **known CGAID adoption anti-pattern** — parallel to Stage 0 policy-only enforcement (see §2) — acceptable only as an explicit time-bounded gap, never as a permanent state.

**Right-to-erasure.** On client or individual request, PII and associated context are erased within 72 hours across memory, Cockpit, and any AI vendor system that supports user-initiated deletion. Each erasure is logged with timestamp, requestor, and per-system confirmation. **Vendor systems without erasure support are flagged in the Data Classification Rubric and excluded from Confidential+ processing**, regardless of other contractual arrangements.

These practices address specific obligations under GDPR (Art. 5 storage limitation and data minimization, Art. 17 right to erasure) and equivalent sectoral frameworks. Regulatory mapping lives in **Appendix B — Regulatory Alignment Notes**.

---

## 7. Adaptive Rigor — Operationalization

MANIFEST operational rule defines three rigor tiers. This section defines what they mean in practice and which artifacts are required at each tier.

### 7.1 Tier definitions and required artifacts

| Stage / Artifact | Fast Track | Standard | Critical |
|---|---|---|---|
| **Stage 0 — Data Classification** | Required for any client material, regardless of tier | Required | Required |
| **Stage 1 — Evidence Pack** | Optional (inline in PR description acceptable) | Required | Required — with explicit inconsistency-hunt narrative |
| **Stage 2 — Master Plan (Cockpit)** | Optional | Required | Required |
| **Stage 2 — Execution Plan** (`.ai/PLAN_*.md`) | Optional | Required | Required |
| **Stage 2 — Handoff Document** | Optional | Required | Required |
| **Stage 2 — ADRs** | Only for decisions that change architecture | Required for non-trivial technical decisions | Required for every material decision |
| **Stage 2 — Edge-Case Test Plan** | Optional (tests-in-PR sufficient) | Required | Required — with explicit failure-mode enumeration |
| **Stage 2 — Business-Level DoD** | Optional | Required | Required |
| **Stage 2 — Side-Effect Map (#11)** | Not required | Required when external systems / mutating ops / cross-module state are touched | Always required |
| **Stage 3 — AI Operational Contract tagging** | Required (CONFIRMED/ASSUMED/UNKNOWN always) | Required | Required |
| **Stage 4 — Mandatory PR Review** | Required | Required | Required — plus a second reviewer with domain expertise |
| **Stage 4 — Business-outcome verification** | Validated by test coverage alone is acceptable | Required — observed in target env | Required — observed in target env with documented evidence artifact |
| **Legal review prior to start** | Not required | Not required unless regulated data involved | Required if any regulated data or EU-AI-Act high-risk domain |

**Traceability granularity by tier (v1.5 — operationalizing MANIFEST Principle 8).** The Manifest says requirements, decisions, code, and validation must be "traceable end-to-end," but end-to-end traceability is not free. Granularity scales with tier:

- **Fast Track — PR-to-requirement.** The PR description links to a ticket, note, or conversation stating the requirement addressed. One hop. Sufficient for cosmetic and unambiguously local changes.
- **Standard — PR-to-ADR + PR-to-requirement.** Each non-trivial technical decision has an ADR in `.ai/decisions/`. PR description references relevant ADR numbers and the requirement. Two-hop traceability.
- **Critical — full three-hop plus regulatory mapping.** All of Standard, plus: each ADR names the code section(s) it governs (file paths and ranges); Stage 4 reviewer verifies the mapping; for regulated contexts, the ADR additionally references the Appendix B regulatory clause the decision is serving.

The word "traceable" in Manifest Principle 8 is intentionally tier-parameterized — the same principle binds more tightly for Critical-tier work.

### 7.2 Fast Track preconditions (all must hold)

A change may be routed as Fast Track **only when all four conditions hold**. If any condition fails, the change defaults to Standard tier.

1. **Local scope** — single function, single module, or single UI component. No cross-module signatures change, no shared state schema change, no API contract change.
2. **No external-system interaction** — does not touch production databases, live third-party APIs, or external file systems during its operation. (Read-only reference to external configuration is acceptable.)
3. **Existing test coverage** — the area being changed has pre-existing automated test coverage that will run against the change.
4. **Reversibility** — the change can be reverted by a simple revert commit without cascade effects on other systems.

**Typical Fast Track candidates:** UI polish, string/copy changes, cosmetic CSS/styling, alphabetic sorting of a visible list, small dropdown UX fixes (see e.g. `ac9a665 Countries alphabetic sorting` or `6d4160a Legal entities - list fixed`).

**Typical Fast Track rejections:** any change to SQL filter/aggregation logic (even a one-line change — see `6ee9561` where a single-line date filter excluded 96% of settlements); any change touching mutating endpoints or cascade-invalidation behaviour; any change to pricing, settlement, restore, or regulatory-adjacent code paths.

### 7.3 Tier classification authority

- **Fast Track** — proposed by implementing engineer; validated by PR reviewer at Stage 4 (reviewer may reject the tier classification and require a Standard-tier retrofit before merge).
- **Standard** — default tier; proposed by implementing engineer; confirmed in PR description.
- **Critical** — proposed by implementing engineer, Framework Steward, or Product/Business owner; requires Lead Steward sign-off before Stage 1 exits. Any feature marked high-risk under EU AI Act Art. 6 (Appendix B) is automatically Critical.

### 7.4 Tier escalation triggers

A Fast Track or Standard change **must be escalated to the next tier by the engineer** if any of the following surface during delivery:

- An `UNKNOWN` epistemic tag that cannot be resolved within the current tier's planning scope.
- A side-effect discovered during Stage 3 that was not in the pre-existing side-effect map (or: a side-effect map was not produced because tier didn't require one).
- A test failure that cannot be classified as covered by the edge-case plan (or: there was no edge-case plan).
- Any regulatory consideration raised by review — client data classification shift, new PII surfaced, vendor DPA question.

**Enforcement mechanism (v1.5 clarification).** The word "automatic" was removed from this section in v1.5 because it implied automation that does not exist in v1.x. Escalation is **engineer-initiated** at the moment a trigger surfaces. To prevent self-deception under pressure, the Stage 4 PR template includes a required confirmation:

> *"No tier-escalation triggers surfaced during delivery; or, if they did, the PR has been reclassified to the correct tier and retrofitted with the required artifacts before this submission."*

A reviewer who identifies an unaddressed trigger **blocks merge** until retrofit is complete. This shifts the "automatic" language from unfulfilled promise to human-verified checkpoint.

Escalation is tracked in the PR; the fact of escalation is a signal for the quarterly adoption audit (Pattern: how often do we mis-classify tier at start?).

### 7.5 Emergency Response Pattern

Production fires at 2am do not wait for Stage 2. The framework must handle them without becoming voluntary during crisis. This section defines the bypass and the compulsory retrospective that is its price.

**Authorization.** On-call engineer or escalation target may declare Emergency Response for any change where production impact is actively occurring or imminent (customer-visible outage, data-integrity threat, security incident in progress, regulatory breach window). Declaration is logged with timestamp, trigger event, and declaring engineer's name.

**In-flight bypass.** During Emergency Response, Stage 1 and Stage 2 artifacts are **not required pre-commit**. The engineer proceeds to Stage 3 with minimum viable scope — the goal is fix, revert, or isolate, not feature completion. The AI operational contract remains fully in effect: CONFIRMED / ASSUMED / UNKNOWN tagging applies to the emergency change. Stage 4 mandatory review still applies, though review may occur post-merge if the change was merged to stop active harm (with immediate retrospective — see below).

**Mandatory retrospective (the price of bypass).** Within **48 hours** of incident resolution:

- **Evidence Pack** (artifact #1) — retroactively produced. What inconsistency, assumption, or unknown enabled the incident?
- **Execution Plan** (artifact #3) — retroactively produced. What was the plan that would have prevented this had it existed?
- **ADRs** (artifact #5) — every decision made during emergency is now documented formally, in particular any architectural concession made under time pressure.
- **Side-Effect Map** (artifact #11) — for the change made and the system state touched. Emergency changes typically have larger blast radius than planned changes; this map is especially important.
- **Edge-Case Test Plan** (artifact #6) — what edge case did the emergency reveal? Add to regression suite immediately; do not wait for next feature.

**Rule promotion trigger.** Every Emergency Response automatically generates a candidate rule for MANIFEST Principle 10 — creation date, stated scenario, prevention path. Framework Steward reviews at the next adoption audit whether the candidate is promoted to permanent rule or retired as a one-off.

**Abuse protection.** If the retrospective reveals the declaration was for a non-emergency (no active harm, no imminent threat — the engineer used Emergency to skip planning), the declaration is reversed; the change is treated as an unauthorized Fast Track bypass and goes through full Standard-tier retrofit. **Repeat declarations by the same engineer are an escalation signal to Stewards** — pattern of abuse, not pattern of bad luck.

**What this section does NOT authorize.** Emergency Response does not bypass Stage 0 (Data Classification) — no Confidential+ client material is processed on unclassified channels even in emergency. It does not bypass Stage 4 mandatory review — review happens, timing shifts. It does not bypass the AI operational contract — the contract is tighter during emergencies, not looser.

### 7.6 Maintenance-mode changes

Active features deliver under tiered rigor. Post-launch maintenance (bug fixes, minor behavior adjustments, dependency updates on released features) does not automatically warrant the full tier the original feature carried.

**Default rule.** Maintenance changes **inherit the tier of the original feature** unless the change is **unambiguously local**. A change is unambiguously local when all of the following hold:

- scope is within a single function or contained logical unit
- no cross-module signature change, no API contract change
- **no change to SQL filter, aggregation, CTE, or JOIN logic** — per Stage 1 volume check rule, even a one-line filter change is not local for this purpose
- no change to mutating endpoints or cascade-invalidation behavior
- pre-existing automated test coverage for the area being changed

When unambiguously local, **Fast Track applies regardless of original feature tier**.

**Examples.**

| Change | Tier | Reason |
|---|---|---|
| UI label typo fix on Critical-tier feature | Fast Track | Cosmetic, local, no behavior change |
| CSS styling adjustment on Standard-tier page | Fast Track | Cosmetic, local |
| Adding new input validation path in Critical-tier feature | Critical (inherited) | Changes behavior on critical path |
| Modifying a filter condition in a Standard-tier report | Standard (inherited) | Filter logic is explicitly non-local |
| Refactor of private helper in a Standard-tier module | Fast Track if no API change | Unambiguously local |
| Patch-level dependency bump | Inherited tier | May surface side-effects outside original planning scope |
| Minor or major version dependency bump | Escalate to Standard minimum | New behaviors possible regardless of original feature tier |

**Dependency updates deserve a specific note.** They inherit the original feature's tier for routine patch-level updates (e.g., `1.2.3 → 1.2.4`) but escalate to at least Standard for minor/major version bumps regardless of original feature tier — because dependency updates can surface behaviors that were not in the original feature's planning scope and may exceed the testing that was sufficient at original shipping.

---

## 8. Client Stakeholder Engagement (consulting-delivery pattern)

CGAID was developed in a consulting-delivery context. The client is not external to the delivery loop — client stakeholders are active co-authors of decisions. This section addresses patterns the rest of the framework assumes but does not specify.

### 8.1 Client roles mapped to CGAID elements

| Client role | CGAID interaction |
|---|---|
| Business logic owner (e.g. client Treasury lead) | Confirms Stage 1 Evidence interpretations; signs off on Stage 2 Business-Level DoD; arbiter on domain-level decisions |
| Operations lead (e.g. client operations manager) | Defines Stage 4 business-outcome verification events; provides access to target environments for verification |
| Security / data protection contact | Signs off on Stage 0 Confidential+ routing decisions; approves Data Processing Agreements |
| Client architect / technical counterpart | Reviews ADRs affecting integration contracts; may co-own Handoff Documents |

Each role should be named (individual + contact) in the Master Plan at Stage 2 for any feature where their sign-off is a gate.

### 8.2 Client as Stage 0 classifier

Client documents ARE the primary input to Stage 0. The client is therefore a **classifier** in the sense defined by `DATA_CLASSIFICATION.md`, often without being aware of it. CGAID-governed delivery handles this through:

1. **Classification proposals to client** — when client material arrives, the delivery team proposes a classification tier. Client confirms, corrects, or escalates. The proposal-plus-confirmation is the log entry.
2. **Consent recording** — Confidential+ routing requires recorded consent. A contract clause is best; a targeted email confirmation is acceptable; silence is never acceptable.
3. **Client classification overrides** — if the client asserts a tier different from what the Rubric would produce, the client's classification wins on items they own, provided it is more restrictive. A client request to downgrade (e.g., "this is fine, just use public tier") goes through the Rubric's escalation path — client preference does not downgrade without Rubric criteria support.

### 8.3 Client disagreement with Stewardship

When client and Framework Steward disagree on a framework-mediated decision:

- **On classification (Stage 0)** — client wins on more-restrictive direction; Steward wins on less-restrictive direction (asymmetry of risk).
- **On business decision (Stage 2)** — client wins. Framework provides structure; client provides business authority. Decisions contradicting Steward recommendation are recorded as ADRs with rationale.
- **On technical decision (Stage 2/3)** — Steward wins when decision affects CGAID artifact integrity or regulatory posture; client wins on domain-specific technical preferences (e.g., preferred integration patterns they own).
- **On verification (Stage 4)** — client's acceptance of business outcome is the ultimate gate. Steward may flag concerns (residual unknowns, regulatory gaps) but may not veto client acceptance of their own outcome.

### 8.4 Client work products as framework artifacts

Some CGAID artifacts are co-produced with the client:

- **Master Plan (artifact #2)** — lives in Solutioning Cockpit; client is reader and contributor
- **Handoff Document (artifact #4)** — client signs off at handoff; content is jointly authored
- **Business-Level DoD (artifact #7)** — defined with client; client is the adjudicator of "done"

These artifacts carry dual authority — team's and client's — and are governed by client-specific change processes (NDA, DPA, contractual amendment) in addition to CGAID change process.

---

## 9. What Makes It Enforceable

A framework is enforceable when three properties hold:

1. **Reproducible by outsiders** — a new team, with the documentation alone, can operate it.
2. **Artifact-driven, not personality-driven** — quality does not depend on which engineer is in the room.
3. **Gated, not voluntary** — stage transitions require evidence, not approval-by-vibe.

CGAID is designed to satisfy all three: every layer has versioned documentation, every stage has checklistable entry and exit criteria, and the operational contract makes the most opaque actor in the delivery loop — the AI — the most auditable. These properties are established by construction; empirical validation — particularly the "reproducible by outsiders" test — is conducted at the end of each 90-day adoption cycle, with findings fed back into framework changelog entries.

### 9.1 Gate Mechanics — Deterministic, Rubric-based, or Judgment

The framework uses the word "gate" throughout. For the claim *"Gated, not voluntary"* (property 3 above) to carry operational weight, every gate must be classifiable by **how** it is evaluated. Without that classification, "gate" is rhetoric — it sounds like enforcement but is in practice voluntary interpretation under deadline pressure. This section makes the classification explicit (added v1.3 following framework-wide deep-verify).

#### The Gate Spectrum

Every CGAID gate sits somewhere on this spectrum:

```
Deterministic ───────── Rubric-based ─────────── Judgment-based
 (script / CI)           (rule applied by                  (subjective
  pass/fail              human or AI                        evaluation
  automated              with artifact                      without
                         as reference)                      reference)
```

**Deterministic gates** are evaluated by script or automated check. Pass/fail is not open to interpretation. Examples: *"File exists"*, *"PR description contains reference to `.ai/decisions/NNN-*.md`"*, *"No `UNKNOWN` tag present in merged code"*, *"Test coverage ≥ N%"*. These are the strongest gates — they do not degrade under pressure because they are not administered by humans under pressure.

**Rubric-based gates** are evaluated by a human or AI applying an explicit rule set, with the rubric itself as the artifact of record. Pass/fail requires judgment but the judgment is constrained by documented criteria. Examples: Data Classification Rubric decision tree (`DATA_CLASSIFICATION.md`), Fast Track preconditions (§7.2 — four stated conditions, all must hold), non-trivial claim classification via `.ai/CONTRACT.md` definition. These degrade under pressure only where the rubric has ambiguity.

**Judgment-based gates** are evaluated by a human or AI without explicit rubric. Relies on expertise, context, and care. Examples: *"Evidence Pack is complete"*, *"Every risk has an owner"*, *"Business outcome observed"*, PR review approval. These are the weakest gates — not because judgment is bad, but because judgment is compromised under pressure and hard to audit retrospectively.

**No gate is inherently better — gates must match their context.** A gate like *"business outcome observed in target environment"* cannot be fully deterministic by nature — business outcome is a human construct. What matters is: (a) honesty about which gates are which, (b) deliberate movement toward determinism where the cost of a bypass is high, and (c) matching verification effort to the blast radius of failure at each gate.

#### Current Gate Classification (v1.3 baseline)

| Gate | Stage | Current mechanism | Target |
|---|---|---|---|
| Classification log entry exists for every client file entering AI-accessible space | Stage 0 exit | Rubric-based (human applies Rubric) | Deterministic — pre-commit hook or DLP blocks unclassified content |
| Client consent recorded for Confidential+ routing | Stage 0 exit | Rubric-based with log | Rubric-based — mechanism is contract / email; cannot be fully deterministic |
| Evidence Pack produced (non-empty, with inconsistencies / assumptions / unknowns sections) | Stage 1 exit | Judgment-based | Rubric-based — schema validator for Evidence Pack structure |
| Open questions escalated to client | Stage 1 exit | Judgment-based | Rubric-based — tracked in log with client reference |
| Volume / coverage check for filters, CTEs, aggregations (v1.5 addition) | Stage 1 exit | Judgment-based | Rubric-based — checklist item in Evidence Pack template |
| Every risk has an owner | Stage 2 exit | Judgment-based | Rubric-based — risk register schema with required owner field |
| Every decision has an ADR | Stage 2 exit | Judgment-based | **Deterministic** — PR description grep for `decisions/NNN-*.md` references |
| Edge-case test list exists | Stage 2 exit | Judgment-based | Rubric-based — edge-case test plan template with required sections |
| Business-Level DoD defined | Stage 2 exit | Judgment-based | Rubric-based — DoD template per tier |
| Side-Effect Map present (Standard / Critical on qualifying changes) | Stage 2 exit | Judgment-based | **Deterministic** — tier-triggered file-existence check at PR |
| Fast Track preconditions (4 conditions, all hold) | Stage 2 → tier classification | Rubric-based | Partially deterministic — scope size, test coverage grep-checkable |
| Tier escalation triggers (v1.5) | Stage 3 / 4 | Rubric-based (engineer-initiated, reviewer-verified) | Keep rubric — triggers are contextual by design |
| Every non-trivial assumption tagged | Stage 3 exit | Judgment-based (even with v1.5 definition) | Judgment-based — application is inherently contextual; reviewer is the check |
| No `UNKNOWN` tag at merge | Stage 3 exit | Judgment-based | **Deterministic** — pre-merge grep for `UNKNOWN` in changed files |
| PR opened with traceability per tier (v1.5 T3.9) | Stage 3 exit | Rubric-based | Partially deterministic — required-field check on PR template |
| Mandatory PR review | Stage 4 exit | Judgment-based (reviewer approves) | **Deterministic enforcement** (branch protection requires approval) + rubric-based content review |
| Automated test verification | Stage 4 exit | **Deterministic** (CI pass/fail) | Already optimal |
| Business outcome observed in target environment | Stage 4 exit | Judgment-based | Judgment-based — cannot be fully deterministic by nature; DoD checklist reduces ambiguity |
| Verification artifact filed | Stage 4 exit | Judgment-based | **Deterministic** — file-existence check per DoD requirement |

**Honest summary of v1.3 state:** of ~19 identified gates, **2 are already deterministic** (automated tests, CI coverage), **7 are rubric-based** (classification, consent, tier preconditions, escalation triggers, traceability, non-trivial tagging, DoD template), and **~10 are judgment-based**. The framework's claim of *"gated, not voluntary"* is therefore **partially hypothetical today** — most gates are voluntary in the sense that a compromised engineer-under-pressure can pass them without meeting intent. This is the next major lever of framework maturity.

#### 9.2 The AI-as-solo-verifier anti-pattern

A specific failure mode applies when AI is both producer and verifier at the same gate.

**The problem.** If AI produces a Stage 2 plan and AI also verifies the plan meets Stage 2 exit criteria, verification is self-referential. AI can output *"all risks have owners, all decisions have records, plan is complete"* with the same confidence whether this is true or fluent-wrongness. This is Pathology 2.1 (Fluent Wrongness) applied to framework self-enforcement — the framework's internal version of the same failure mode it was designed to defend against externally.

**The rule (v1.3).** **AI cannot be solo verifier of its own work at any CGAID gate.** At minimum, one of the following must hold:

1. **A human verifies** — the engineer, Framework Steward, or PR reviewer independently evaluates the gate before passing.
2. **A different AI instance verifies** — a separate AI session, without access to the original reasoning trace, evaluates against the rubric. Not a follow-up turn in the same conversation. Not the same agent "reviewing its own work" in-context.
3. **A deterministic check verifies** — script, CI, or grep evaluates the gate. Pass/fail is machine-produced.

An AI saying *"I have reviewed the plan and it meets all criteria"* in the same turn that produced the plan is **not verification** — it is consistent inference from the same priors. Framework treats this as a contract violation: **false completeness** (Kontrakt operacyjny behavior #6 in `.ai/CONTRACT.md`).

**Application in practice.** In a conversation where AI and human are collaborating, the human is the second-party verifier. In autonomous agentic workflows (v3.x trajectory — §11 Horizon), explicit verifier-agent separation is required. The framework does not require the verifier to be *more capable* than the producer — only that verification is a **distinct operation with a distinct actor or mechanism**.

**Edge case — AI subagents.** If a CGAID-governed engineer delegates work to a subagent (per §4.2 Multi-agent contract), the delegating engineer cannot use "the subagent verified its own work" as gate evidence. Subagent verification of subagent work is AI-as-solo-verifier with extra steps. The delegating party (human or parent AI) must independently verify or use a deterministic check.

#### 9.3 Automation Roadmap (v1.7+)

Gates targeted for movement toward determinism, ordered by leverage-to-effort ratio:

**High leverage, low effort (v1.7 priority):**
- **Pre-merge grep for `UNKNOWN` tags** in changed files — block merge if present. Single shell command as git pre-push hook or CI check. *Effort: < 1 day. Leverage: closes Stage 3 largest judgment gap.*
- **PR description grep for ADR references** — enforces Standard-tier traceability. *Effort: < 1 day. Leverage: operationalizes Principle 8 traceability.*
- **Branch protection requiring PR approval** (GitHub/GitLab native setting) — not new infrastructure, just configuration. *Effort: minutes. Leverage: turns Stage 4 review from judgment-enforcement into deterministic-enforcement.*
- **File-existence check for tier-required artifacts** — Side-Effect Map for Standard+, Evidence Pack for all non-Fast-Track, Edge-Case Test Plan for Standard+. *Effort: 1–2 days for CI workflow. Leverage: eliminates "artifact forgotten" failure mode.*

**Medium leverage, medium effort:**
- **Schema validator for Evidence Pack** — required sections, non-empty lists, proper markdown structure. *Effort: 2–3 days. Leverage: turns Stage 1 from judgment to rubric.*
- **Tier-triggered artifact requirement check** — workflow in `.github/workflows/cgaid-tier-check.yml` that reads declared tier from PR template and enforces required artifact presence. *Effort: 3–5 days. Leverage: enforces Adaptive Rigor matrix (§7.1).*
- **Classification log consistency check** — every file in PR diff must have a classification log entry; CI fails otherwise. *Effort: 1 week. Leverage: moves Stage 0 toward determinism.*

**Lower leverage, higher effort (research before building):**
- AI-output scanner for missing epistemic tags on non-trivial claims — would require an ML classifier, not regex. Research whether existing LLM-eval tools can serve this.
- Automated business-outcome detection for specific feature types — domain-specific; only sensible for features with clearly instrumented outcomes (e.g., funnel conversion, latency SLO).
- Static cascade-effect tracer — cross-module side-effect propagation analysis. High value for features like restore, settlement detection; substantial build effort.

**Gates deliberately NOT targeted for determinism:**
- **PR review approval by a person** — approval-by-person is the point; automating it would remove the human checkpoint that Stage 4 exists to be.
- **Business outcome observation** — fundamentally a human (or client) judgment; DoD rubric reduces ambiguity but does not eliminate it.
- **Non-trivial claim classification at the point of writing** — contextual; determinism would require an oracle that does not exist. Reviewer check at Stage 4 is the fallback.

**Governance.** Automation roadmap items are tracked in `.ai/automation_roadmap.md` (adoption artifact, not framework core). Each item moves through proposal → pilot → adoption, governed by the Framework Stewards' quarterly framework review meeting.

#### 9.4 Reference Pattern — Deterministic Snapshot Validation

This subsection canonizes a generic pattern for converting judgment-based gates into deterministic gates. The pattern is abstract by design — it applies across domains (UI rendering, SQL output, API responses, data-pipeline transformations, document rendering) and is not tied to any specific tool. Adopting organizations implement it with tools appropriate to their context.

##### Purpose

Deterministic Snapshot Validation turns *"does this output behave correctly?"* (judgment) into *"does this output match its approved baseline byte-for-byte (or by declared equivalence rule)?"* (deterministic). The gate shifts from "reviewer assesses correctness" to "comparator executes and yields pass or fail."

This is the single highest-leverage transformation available for moving CGAID gates from judgment to determinism. When applicable, it converts entire classes of regression into CI-level failures.

##### Five Components (all required)

**1. Baseline Artifact.** A stored, versioned representation of known-good output. It lives in the repository (or a controlled artifact store) under version control. It is the authoritative reference. Without a baseline, the pattern is not snapshot validation — it is assertion testing.

**2. Snapshot Producer.** A mechanism that generates the current output in a format structurally comparable to the baseline. Must be deterministic itself: same inputs produce the same output bytes. Non-determinism in the producer (timestamps, random IDs, environment-dependent values) poisons the entire pattern and must be normalized, injected, or stripped.

**3. Deterministic Comparator.** A function that compares current output to baseline and yields a binary result (pass / fail) plus, on fail, a diff. The comparator may apply declared equivalence rules (e.g., "ignore timestamps within this field", "treat whitespace-only differences as equivalent") but those rules are themselves versioned artifacts, not ad-hoc judgment.

**4. Drift Disposition.** Explicit policy for what happens when the comparator yields fail:
- **Block** (default for critical paths) — CI fails, merge refused, engineer investigates.
- **Warn-and-continue** — for low-stakes snapshots; generates PR comment but does not block.
- **Human-review-required** — diff is surfaced; reviewer explicitly approves or rejects the drift.
- Never: **silent auto-accept**. This collapses the pattern into security theater.

**5. Baseline Update Protocol.** The procedure by which a baseline is legitimately updated when intended behavior changes. Updates require explicit human approval — usually a separate PR or a reviewer-approved flag in the current PR ("baseline-update: approved"). Baseline changes have their own review discipline: a reviewer who would normally focus on code change now also evaluates *"is this drift the intended behavior?"*

##### Where the Pattern Applies in CGAID Gates

The pattern can be installed at multiple stages:

- **Stage 1 volume check (v1.5 addition)** — for any filter / CTE / aggregation introduced, baseline the row-count fingerprint of its output against a fixture input. An unexpected 96% row reduction fails the baseline comparator before merge.
- **Stage 3 exit — "code matches plan"** — where the plan includes a target output shape, snapshot-compare against that target.
- **Stage 4 business-outcome verification** — where outcome has a deterministic signature (specific rows appearing in a specific table, a specific metric crossing a threshold), snapshot-validate the signature.
- **Maintenance-mode regression detection (§7.6)** — every patch to a Standard+ feature runs the feature's baseline snapshot suite; any drift blocks unless explicitly approved.
- **Dependency update verification** — run snapshot suite before and after dependency bump; no drift = safe, drift = review.

##### Concrete Applications Across Domains

| Domain | Baseline | Snapshot Producer | Comparator |
|---|---|---|---|
| UI rendering | Approved screenshot per page/component | Headless browser rendering | Pixel or structural diff (e.g., image diff, DOM tree hash) |
| SQL output | Known row-count / checksum per fixture | Query execution against fixture DB | Row-count + hash of sorted tuples |
| API response | Stored JSON payload per request fixture | HTTP call against test instance | JSON deep-equal with declared ignorable fields |
| Data pipeline | Expected output table state + row count + per-partition checksum | Pipeline execution against fixture input | Table-level and partition-level comparison |
| Document rendering | Expected PDF / HTML bytes or structural tree | Rendering engine output | Byte-equivalence or structural tree diff |
| ML model output | Expected prediction distribution on fixture dataset | Model inference | Statistical distribution comparison with tolerance |

##### Canonical Example Already in Practice

The restore module's deep-proof test suite (commit `d4a180e` — *"Add 15 deep proof + concurrency + edge case tests with fingerprint comparison"*) is an in-practice implementation of this pattern. Fixture state → restore operation → fingerprint of resulting database state → compare to expected fingerprint. Drift blocks merge via CI; baseline updates require explicit code review of the new fingerprint value.

The pattern existed *before* CGAID formalized it. This subsection canonizes what was already working so that other adopters can implement it deliberately rather than re-discovering it accidentally.

##### Anti-Patterns (failure modes of the pattern)

**Baseline drift.** Baselines updated casually, often bundled into unrelated PRs. Over time, the baseline no longer represents intended behavior — it represents *whatever the code happens to do*. Mitigation: require baseline updates to be their own PR or carry an explicit `baseline-update-approved` flag that the reviewer must sign.

**Flaky snapshots.** The Snapshot Producer is not fully deterministic — timestamps, random IDs, dictionary iteration order, floating-point rounding, or environment-dependent values leak into the output. Every PR produces noise diffs that engineers learn to ignore. Mitigation: identify and normalize all non-determinism sources in the producer; if you cannot normalize, do not use this pattern for that domain.

**Coverage illusion.** Snapshot passing means *"current output matches baseline"* — it does not mean *"behavior is correct."* A bug that was present when the baseline was captured remains a passing test. Mitigation: baselines are validated at creation by the same rigor as any other artifact (Stage 2 DoD applies to the baseline itself).

**Approval theater.** Baseline-update approvals become rubber-stamps because reviewers don't know what drift "should" look like. Mitigation: baseline-update PRs carry explicit rationale ("behavior changed because X"), and reviewer verifies the drift corresponds to that rationale rather than extra-drift.

**Silent auto-accept.** The worst version. The CI script, on comparator failure, silently replaces the baseline with the current output so that "the next run will pass." The pattern collapses to no gate at all. **This must be explicitly prohibited** in automation configuration.

##### When *Not* to Use This Pattern

- **Legitimately variable output** — content that is personalized, time-dependent by design, or otherwise non-repeatable. A user dashboard showing "current timestamp" cannot be baseline-compared without extensive normalization; the maintenance cost exceeds the gate value.
- **Baseline maintenance cost exceeds gate value** — if the output changes daily (content-heavy pages, frequently iterated UX), baselines become churn rather than governance.
- **Gate is fundamentally about business outcome, not artifact correctness** — *"did the user achieve their intent?"* is not a snapshot question; it's a DoD question. Snapshot validation cannot substitute for Stage 4 business verification.
- **Output is continuously learned or optimized** — ML model outputs, recommender rankings, A/B-tested variants. Use statistical comparison patterns, not byte-equivalence.

##### Relationship to CGAID Gate Spectrum

Deterministic Snapshot Validation is a **tool for moving a specific gate from judgment-based to deterministic**. It does not make all gates deterministic — it makes gates with stable, representable output deterministic. Judgment gates remain judgment gates. Rubric gates remain rubric gates. But a meaningful subset of CGAID's current judgment gates — specifically those about output correctness and regression detection — can be transformed by this pattern.

Framework recommendation: adopting organizations identify *one* gate they currently run as judgment-based where output is stable and representable, implement Deterministic Snapshot Validation there as a proof of concept, and expand from observed success. Attempting to blanket-apply the pattern before it has earned adopters' trust is a common failure mode.

---

## 10. Adoption Path — First 90 Days

CGAID is designed for progressive adoption. No SDLC rebuild required.

**Days 0–30 — Establish the contract and the data gate**
- Adopt the AI Operational Contract (7 disclosure behaviors, 3 epistemic states).
- **Stand up Stage 0 (Data Classification Gate) first.** No real client data flows through any AI system until the Rubric and routing rules are operational. This is a hard prerequisite, not a parallel track.
- Publish the Framework Manifest and supporting documents in the engineering repository.
- Name three Framework Stewards; designate the rotating Lead for the first quarter.
- Retro-fit one pilot feature through Stage 0 plus all four delivery stages. **Pilot-feature selection criteria (v1.5) — all should hold:**
  - *Scope is medium* (1–3 week engineer effort) — not the smallest available (too little learning) nor the largest (too high failure risk).
  - *Touches at least one Confidential data category* — exercises Stage 0 Rubric and routing rules.
  - *Has a clear business verification event within 4–6 weeks of merge* — enables early feedback on Metric 6.
  - *Not on a critical external deadline* — gives the adoption team room to learn without pressure amplifying errors.
  - *Has at least one clear architectural decision requiring an ADR* — exercises artifact #5.
  - *Can tolerate 20–30% delivery overhead vs pre-CGAID baseline* — first-pass adoption is slower by design; stakeholders must be informed and accept.

**Days 31–60 — Standardize artifacts**
- Roll out the ten standardized artifacts as templates.
- Introduce Stage 1 (Evidence) as a gate before any new feature planning.
- Publish Data Handling Requirements procedures (retention, PII scanning, erasure).
- Document curated shared instructions (CLAUDE.md / AGENTS.md) at the repository root.
- Begin the Skill Change Log retrospectively — document the last 60 days of tool evolution.
- Commission the first **legal and regulatory review** (6-month cadence starts here).

**Days 61–90 — Measure and iterate**
- Baseline the seven metrics on one team ("baseline in progress" status permitted through Day 90; hard numbers required by Day 180).
- Conduct the first **quarterly adoption audit** — measure *use*, not compliance. Rotate auditor among Stewards.
- Publish the first framework changelog entry grounded in observed data, not intent.
- Extend adoption to a second team using documentation alone — this is the test of the "reproducibility by outsiders" property.

At 90 days, an organization is positioned to have: a signed contract with its AI, a reproducible delivery loop, the first measured baselines for its metrics surface, and a versioned framework that improves with use. Outcomes are demonstrable once baselines are established.

---

## 11. The Horizon — 12 to 24 Months

**Today (v1.x)** — AI is a co-producer. Humans own the contract, gates, and verification. CGAID makes co-production safe and measurable.

**12 months (v2.x)** — AI operates at higher autonomy on bounded tasks (refactoring, test generation, migration). The contract and gates expand to cover autonomous execution windows. Verification becomes continuous, not episodic.

**24 months (v3.x)** — Multi-agent delivery is standard. CGAID governs *inter-agent* contracts alongside human-AI contracts. The framework handles delegation, conflict resolution, and accountability across multiple AI contributors to a single system. The human role shifts from co-producer to governor of the delivery system itself.

The organizations that will be ready for v3.x are the ones that adopt v1.x now. Those that wait will not transition — they will have to transform under incident pressure.

---

## 12. Kill Criteria — When to Abandon This Framework

Every methodology eventually outlives its usefulness. Waterfall survived decades past the point it helped; many SAFe implementations became cost centers. A methodology that cannot name its own termination conditions becomes a cult. CGAID therefore publishes its kill criteria.

If any single criterion below is met, Framework Stewards must convene a formal termination review within 30 days. Termination review produces one of three outcomes: **continue unchanged**, **substantial redesign**, or **abandon**. All three outcomes are legitimate.

### K1. Cultural failure (theater confirmed)

**Signal:** two consecutive quarterly adoption audits show that artifacts are being created but not read or cited. Specifically: ADR citation rate below threshold (see methodology), plan update frequency shows plans modified only at phase start, artifact modification patterns show template-fill without substantive editing.

**Measurement methodology for ADR citation rate (v1.5 addition).** Once per quarter, the rotating audit Steward executes:

1. `grep -r 'decisions/[0-9]' <PR descriptions of the quarter>` — count PR descriptions referencing an ADR by path or number.
2. `grep -r 'decisions/[0-9]' <PR review comments of the quarter>` — count reviewer references.
3. `grep -r 'decisions/[0-9]' <recorded decision meeting notes of the quarter>` — count meeting references.
4. Divide (distinct ADRs referenced at least once) by (total ADRs active in the quarter, i.e., produced or still governing code).

Meetings without recorded notes do not count in step 3 — this is a known limitation. **If fewer than 30% of decision meetings in the quarter produce notes, the signal is indeterminate, not zero** — Stewards convene to either strengthen meeting-note discipline or adjust the K1 threshold for this organization before declaring cultural failure.

**Threshold bands:**
- Citation rate < 20% → **K1 fires** (theater signal confirmed if repeated in the next quarter)
- 20% ≤ rate < 40% → **watch** (not firing, but trending; investigate at next audit)
- ≥ 40% → **healthy**

**Interpretation:** framework is being performed, not practiced. Work continues while paying lip service to CGAID.

**Action:** abandonment or radical simplification. Maintaining the framework as-is wastes resources without producing governance value.

### K2. Outcome stagnation

**Signal:** six months of operation with no improvement on any of the collectable metrics (Metric 1, 6, 7 at minimum) versus the pre-CGAID baseline. No reduction in bug rate, no improvement in business-verification time, no improvement in review cycle time.

**Interpretation:** framework is not producing the outcomes it claims. Either the hypothesis is wrong (CGAID does not amplify engineering discipline for this team/domain) or the framework is not actually being applied.

**Action:** investigation — determine whether non-application (→ enforcement problem) or non-effect (→ framework problem). Redesign or abandon accordingly.

### K3. Capability mismatch

**Signal:** fundamental shift in AI capabilities makes core principles no longer applicable. Example: AI reaches provable reliability tier where self-reporting is redundant because outputs are verified automatically at scale. Or: new AI paradigm emerges where epistemic tagging is not expressible (e.g., non-LLM code synthesis from formal specifications).

**Interpretation:** the environment that CGAID was designed for no longer exists.

**Action:** retire the principles affected by the capability shift; retain only those still relevant. May result in a narrower, more targeted v2.x.

### K4. Cost parasite

**Signal:** framework maintenance (Stewardship hours, audit cycles, legal review, artifact production) exceeds 15% of engineering capacity consistently, with no corresponding outcome improvement. Alternative: framework overhead produces zero measurable improvement in pre-CGAID incident rates over two consecutive quarters.

**Interpretation:** framework costs more than it saves. This is the explicit trigger of the Anti-bureaucracy Clause (MANIFEST operational rule 3) at whole-framework scale.

**Action:** radical simplification first (remove artifacts, merge stages, reduce audit cadence). If simplification does not recover efficiency, abandon.

### K5. Regulatory obsolescence

**Signal:** scheduled legal review (Appendix B, 6-month cadence) finds that regulatory changes (e.g., EU AI Act secondary legislation, AI Liability Directive enactment, sectoral updates) invalidate more than 50% of Appendix B's alignment mapping. Or: specific legal opinion concludes that CGAID's "Direct" alignment claims are not defensible in the adopting jurisdiction.

**Interpretation:** framework's regulatory posture is a liability rather than a protection. Adoption creates false confidence.

**Action:** rewrite Appendix B with qualified counsel, or explicitly scope CGAID as operationally useful but not a compliance artifact. If the latter is unacceptable for the client portfolio, abandon.

### K6. Champion collapse

**Signal:** despite the three-Steward rotation, framework loses active ownership — two consecutive quarterly framework reviews occur with no attendance, no changelog entries, no adoption audit outputs. Framework Stewards role becomes unclaimed for one full quarter.

**Interpretation:** framework is no longer part of the organization's live practice. It exists only as documentation.

**Action:** formal retirement. Framework documents are archived; active use is discontinued. Future attempts to revive require fresh practice survey and new Stewards.

### Governance of kill decisions

- Termination review is convened by any Framework Steward; attendance required from all three.
- Review output is a formal decision recorded in the changelog.
- **The decision to abandon is not a failure of the framework — it is the framework working as designed.** A methodology that cannot be abandoned is a methodology that cannot be evaluated.
- Post-abandonment, a retrospective document is produced explaining what worked, what did not, and what should inform the next delivery methodology adopted.

---

## Governance of This Document

- **Owners:** Engineering. Framework ownership follows a **scale-tiered governance model** (see subsection below), with **Lead Steward role rotating quarterly** in all tiers.

### Scale-tiered governance

One governance shape does not fit all team sizes. The three-Steward model originally published in v1.3 assumed a team of roughly 10–20. For smaller teams it dilutes ownership; for larger teams it becomes a bottleneck. CGAID therefore parameterises governance by team scale.

| Team size | Steward model | Lead rotation | Audit cadence | Notes |
|---|---|---|---|---|
| **< 5 engineers** | **Two Stewards** (not three) | Quarterly | Quarterly | Three Stewards would be 60% of the team; decisions become consensus and ownership dilutes. Two Stewards with rotation retains accountability at smaller scale. |
| **5 – 20 engineers** | **Three Stewards** (baseline) | Quarterly | Quarterly | Original model. Rotation prevents single-person dependency; Lead accountability remains clear. |
| **20 – 50 engineers** | **Steward Council** (5 members) | Lead rotates quarterly; Council membership rotates annually | Quarterly | Scale-out requires more hands for audits and reviews; Council membership elected by engineers, approved by Engineering leadership. |
| **50+ engineers** | **Federated Stewardship** — per-product or per-team Stewards reporting to a central Council | Lead rotates quarterly within each unit; Council chair rotates annually | Quarterly at team level; half-yearly at Council level | At this scale, central ownership cannot track per-team reality; federated model pushes operational audit to team-level Stewards while Council owns framework-level changes. |

Adopting organizations choose the tier matching their headcount at adoption and re-evaluate at each quarterly framework review. Moving between tiers is not automatic — it is a governance decision requiring observed evidence (team size has stabilised at the new level; current model is either diluted or bottlenecking).
- **Version:** 1.4 (Gate Mechanics + Deterministic Snapshot Validation pattern — see changelog)
- **Status:** Foundational — adopted as the delivery operating model for AI-assisted work in this organization
- **Review cadence:**
  - *Quarterly* — framework review meeting, mandatory attendance by all Stewards. Changes captured in the changelog below.
  - *Quarterly* — **adoption audit**: not a compliance audit, a *use* audit. Measures whether artifacts are read and cited (ADR citation rate, plan update frequency during active work, artifact modification patterns). Auditor role rotates among Stewards.
  - *Every 6 months* — **legal and regulatory review** (see Appendix B) covering EU AI Act, GDPR, and sectoral obligations applicable to the active client portfolio.
  - *Annually* — **external peer review** of framework health: adoption outcomes, audit findings, regulatory posture. Reviewers invited from outside the Steward group.
- **Change process:** any substantive change requires (a) a proposed amendment, (b) **observed evidence** from at least one delivered feature — data, not intent, (c) sign-off by the Lead Steward plus one peer Steward.

### Budget model (operational cost transparency)

Framework governance is not free labour; its cost must be visible to the organisation funding it. Estimated time commitments per Steward, per quarter:

| Activity | Time per Steward | Frequency | Quarterly total |
|---|---|---|---|
| Framework review meeting | 2h | 1× per quarter | 2h |
| Adoption audit (rotating; one Steward per quarter) | 8h | 1× per quarter | 8h / 3 ≈ 2.7h avg |
| Feature-level Stage 1 / Stage 4 reviews | 0.5h per feature × ~10 features | Ongoing | ~5h |
| ADR review & sign-off | 0.25h per ADR × ~8 ADRs | Ongoing | ~2h |
| Skill Change Log maintenance | 1h | Continuous | ~1h |
| Classification log review (Stage 0 audit sample) | 1h | Monthly | ~3h |
| Legal review coordination (every 6 months) | 2h (in one Steward's quarter) | Biannual | ~0.7h avg |
| Annual external peer review prep (once per year) | 4h (distributed) | Annual | ~1h avg |
| **Total estimated per Steward** | — | — | **≈ 17h / quarter ≈ 1.3h / week** |

For a 3-Steward team of 15 engineers: framework governance costs ~51 Steward-hours per quarter, or ~4.3% of aggregate Steward capacity (assuming 8h/day × 5 days × 13 weeks = 520h gross quarterly capacity per Steward; 51h / 1560h = 3.3% of total team capacity).

For the 15%-cap Kill Criterion (K4 — Cost parasite), framework maintenance includes Stewardship time **plus** Stage 1/2/4 ceremony time across the team (not only Stewards). The 15% cap targets that aggregate figure, not Stewardship alone.

**Adopting organizations must explicitly budget Steward hours.** Treating Stewardship as "extra work on top of normal duties" is the single most common cause of R-CHAMPION collapse in methodology implementations. If no budget exists, the framework is under-resourced at the moment of adoption and K6 (Champion collapse) becomes the most probable termination mode within 12 months.

### Career path for Stewards

Adopting organizations must decide whether Stewardship is **career-accelerating** (visible leadership role, governance experience, cross-team influence — counted in promotion criteria) or **career-limiting** (time away from product, invisible to performance reviews). This is an organizational-policy question CGAID cannot answer, but one it flags explicitly:

- If career-accelerating: Stewardship will attract senior engineers and become a growth path.
- If career-limiting: Stewardship will be a rotating burden; quality will degrade; K6 (Champion collapse) becomes a design feature rather than a risk.

The organization's choice is a leading indicator of long-term framework health. CGAID recommends explicitly including Stewardship in performance-review criteria for participating engineers.

### Changelog

---

## Appendix A — Glossary

- **CGAID** — Contract-Governed AI Delivery.
- **AI-Native Delivery** — software delivery designed from the ground up to assume AI is a co-producer, not an assistant.
- **Operational Contract** — the enforceable agreement governing AI behavior during software delivery; lives in `.ai/CONTRACT.md`.
- **Epistemic State** — one of `CONFIRMED` / `ASSUMED` / `UNKNOWN`; required tag on every non-trivial AI claim.
- **Handoff Document** — the standardized artifact transferring business intent from the Solutioning Cockpit to the codebase execution layer.
- **Stage Gate** — a transition between delivery stages (Evidence / Plan / Build / Verify) with defined entry and exit criteria.
- **Skill** — a tailored AI capability unit, versioned and evolvable per project.
- **Solutioning Cockpit** — the business-intent and specification layer, separate by design from the execution codebase.
- **Fluent Wrongness** — the pathology of AI output that is plausible, convincing, and incorrect — with no warning signal.
- **AI Sprawl** — the organizational pathology of parallel, unreviewed AI artifacts (agents, prompts, mini-apps) produced without standards or oversight.
- **Architecture Drift** — the degradation of system coherence when AI optimizes locally without full system awareness.
- **Framework Steward** — one of three named owners of the framework; shared ownership with quarterly rotating Lead role.
- **Data Classification Rubric** — the four-tier scheme (Public / Internal / Confidential / Secret) applied at Stage 0 to every piece of client material before it reaches an AI system.

---

## Appendix B — Regulatory Alignment Notes

This appendix maps CGAID elements to the principal regulatory frameworks most likely to apply in client engagements. It is **not legal advice.** It is a framework self-assessment intended to be validated by qualified legal counsel for each adopting organization and each regulated client engagement.

### B.1 EU AI Act (Regulation (EU) 2024/1689)

The EU AI Act establishes obligations based on AI system risk classification. AI-assisted software *development* for general-purpose business systems typically falls under **limited-risk** or **minimal-risk** categories. However, **high-risk** classification applies when:
- the software being produced is itself a high-risk AI system (e.g., used in employment decisions, credit scoring, critical infrastructure, law enforcement, biometrics), or
- the development process is embedded within a regulated sector that attracts sector-specific AI obligations.

| EU AI Act Article / Obligation | CGAID Element | Alignment |
|---|---|---|
| Art. 13 — Transparency and provision of information to deployers | AI Operational Contract (`.ai/CONTRACT.md`); epistemic tagging `CONFIRMED` / `ASSUMED` / `UNKNOWN` | **Direct** — every AI claim carries an explicit epistemic state |
| Art. 14 — Human oversight | Mandatory PR review; Stage 4 Verify gate; closed verification loop against business outcome | **Direct** — AI never closes its own delivery loop |
| Art. 15 — Accuracy, robustness, cybersecurity | Edge-case test planning (artifact #6); verification against business-level Definition of Done | **Partial** — CGAID addresses correctness; cybersecurity requires supplementary controls outside this framework |
| Art. 17 — Quality management system | Framework versioning and changelog; quarterly adoption audit; annual external peer review | **Direct** — CGAID is a quality management system for AI-assisted delivery |
| Art. 26 — Obligations on deployers of high-risk AI systems | §6 Data Handling Requirements; Stage 0 Data Classification Gate | **Direct** |

**Known gap for high-risk contexts:** CGAID does not currently produce an EU AI Act *conformity assessment* artifact. For high-risk deployment contexts, supplementary documentation (technical file, risk management system, post-market monitoring plan) is required in addition to CGAID artifacts.

### B.1.1 AI Liability Directive (proposed — status as of 2026-04)

The EU AI Liability Directive (proposal COM(2022) 496) modifies the burden of proof in civil liability cases involving AI systems. As of April 2026 the directive remains in legislative process; its enactment is expected to materially shift civil liability exposure for AI-assisted software:

- **Disclosure obligations** — under the directive, a claimant can compel disclosure of information about a high-risk AI system's operation. CGAID's artifact trail (ADRs, Handoff Documents, classification log, Skill Change Log) materially reduces the cost of compelled disclosure — the evidence is already organised.
- **Presumption of causality** — the directive introduces a rebuttable presumption of causality between AI defect and damage in specified circumstances. Strong pre-code Evidence Packs and explicit Stage 2 Side-Effect Maps (artifact #11) support rebuttal of the presumption by demonstrating reasonable engineering care.
- **Residual exposure** — CGAID does not eliminate liability. It produces the documentation trail that would be introduced in a defense.

Adopting organizations should track directive enactment at each 6-month legal review and update this appendix with the enacted text reference when it is available.

### B.2 GDPR (Regulation (EU) 2016/679)

| GDPR Article | CGAID Element | Alignment |
|---|---|---|
| Art. 5 — Principles (lawfulness, minimization, storage limitation) | §6 Data Handling (retention windows, PII scanning) | **Direct** |
| Art. 6 — Lawful basis for processing | Stage 0 classification routing includes legal basis field | **Direct**, when the Data Classification Rubric records legal basis per item |
| Art. 17 — Right to erasure | §6 erasure procedure (72h SLA, per-system confirmation, vendor capability flagging) | **Direct** |
| Art. 25 — Data protection by design and by default | Stage 0 Data Classification Gate as hard prerequisite before AI access | **Direct** |
| Art. 32 — Security of processing | §6 PII scanning (automated + quarterly manual audit) | **Partial** — organizational security controls required in addition |
| Art. 35 — DPIA for high-risk processing | Framework audit trail supports DPIA inputs | **Facilitative** — the DPIA itself is a separate artifact owned by the Data Protection Officer |

### B.3 Sectoral Regulations (apply per client context)

**Financial services** (MiFID II, **DORA** in the EU, SOX in the US, UK FCA regimes): audit trail and traceability align well with CGAID artifacts. Specific requirements around change management for trading and settlement systems may require supplementary controls — see active project context in `.ai/PROJECT_PLAN.md`.

**DORA specifically (Digital Operational Resilience Act — Regulation (EU) 2022/2554, in force January 2025):** establishes ICT operational-resilience obligations for financial entities. Implications for CGAID adoption in financial-services contexts:

- **Art. 5-10 (ICT risk management framework)** — CGAID's Stage 0 Data Classification plus §6 Data Handling partially implement required data/ICT risk controls; DORA requires additional risk-management framework artifacts beyond CGAID.
- **Art. 11-13 (ICT-related incident management)** — CGAID's incident-to-rule loop (§4.3) aligns with DORA incident classification and reporting; DORA's mandatory reporting timelines (4h initial, 72h intermediate, 1-month final) are not implemented by CGAID alone.
- **Art. 28-30 (third-party risk management)** — CGAID's AI vendor DPA requirements (DATA_CLASSIFICATION.md routing matrix) provide partial coverage; full DORA compliance requires vendor register, exit strategies, and critical-third-party tracking beyond CGAID.


**Digital services and AI-generated output** (EU Digital Services Act — Regulation (EU) 2022/2065): if CGAID-delivered software generates content shown to end users (not only code), DSA obligations may apply to that content — particularly around AI-generated content disclosure, illegal-content handling, and transparency reporting. CGAID artifacts do not directly produce DSA compliance documentation; adopting organizations producing user-facing AI output must supplement the framework with DSA-specific artifacts.

**Healthcare** (HIPAA in the US, EU Medical Device Regulation, local health data frameworks): Stage 0 classification must recognize Protected Health Information (PHI) as its own category. Default posture in the Data Classification Rubric should elevate PHI from Confidential to **Secret by default** (excluded from AI workflows) unless a specific Business Associate Agreement or equivalent authorizes otherwise.

**Public sector** (procurement regulations, national security classifications): the four-tier Rubric may need extension to align with government classification schemes. Many AI vendor Data Processing Agreements are incompatible with certain public-sector contracts — this must be verified per engagement before Stage 0 routing decisions.

**Employment and labor** (relevant whenever the engagement touches HR/staffing/workforce systems): AI systems used in employment decisions are classified as high-risk under Art. 6 of the EU AI Act. For any CGAID engagement producing AI features that influence hiring, performance management, or worker treatment, the "high-risk" pathway applies and conformity assessment artifacts become mandatory.

### B.4 Legal Review Commitment

Every **six months**, a designated counsel reviews:
1. Regulatory changes since the last review (EU AI Act secondary legislation, GDPR enforcement guidance, sectoral updates)
2. The active client portfolio and which regulations apply
3. Framework amendments affecting compliance posture

Findings are incorporated into the framework changelog with cross-reference to this appendix. Legal review findings that require framework change follow the standard change process (observed evidence + Lead Steward + peer Steward sign-off).

### B.5 Disclaimer

This appendix represents the framework owners' good-faith mapping of CGAID to major regulatory frameworks **as of v1.0 of OPERATING_MODEL (April 2026)**. Regulations, enforcement guidance, and case law evolve. This mapping is a starting point for legal review, not a substitute for it. Adopting organizations must obtain their own legal review before using CGAID:
- with data subject to regulatory requirements,
- in regulated sectors,
- across jurisdictions with local AI, data protection, or sectoral requirements that diverge from the EU frameworks described here.

---

## Appendix D — Non-trivial claim definition: evidentiary history and governance

This appendix stores the historical / evidentiary material that underpins the "non-trivial" definition operationalized in `.ai/CONTRACT.md`. The contract file carries the runtime-enforceable rule; this appendix carries the *why* — origin, audit trail, governance override — which belongs in framework-governance context rather than in the daily-work contract.

### D.1 Origin of the definition

The term "non-trivial claim" is central to the AI Operational Contract: every such claim must be tagged `CONFIRMED` / `ASSUMED` / `UNKNOWN`. Prior to v1.5, the term had no operational definition. The `deep-verify` v2.0 audit of the full framework (2026-04-19) surfaced this as **Finding F1 — largest definitional gap in the framework**: under deadline pressure, engineers and AI classify claims as trivial to avoid tagging overhead, and the tag system degenerates into theater.

The v1.5 response was the seven-criterion definition plus four trivial exceptions, plus the asymmetric-risk rule ("gdy masz wątpliwość — tag") and the one-sentence rule of thumb. That definition is now the enforceable text in `.ai/CONTRACT.md`; this appendix documents its origin.

### D.2 Commits that motivated the definition

The 10-row examples table in `.ai/CONTRACT.md` references concrete incidents. Full evidentiary trail:

| Commit | Pattern |
|---|---|
| `6ee9561` | One-line WHERE-filter change excluded 96% of settlement rows — highest single-commit blast radius in the 2026-Q2 window. Motivates criterion 1 (data filtering). |
| `351ac6a` | Edge-case fallback value silently wrong — passed tests because tests did not cover the subtle case. Motivates criterion 3 (assumption about other code's behavior). |
| `f6d24dc` | Restore cascade invalidation — cross-module propagation that required 12+ downstream verifications. Motivates criterion 4 (cascade / propagation). |
| `318f74a`, `71fa577`, `c31b116`, `bf66299` | Cascade / idempotency pattern in restore and buy modules — motivates both criterion 4 and the cascade-compression rule (D.3 below). |

These commits are referenced by short hash in `.ai/CONTRACT.md`; the appendix holds the link between hash and pattern.

### D.3 Cascade-tagging compression: governance override

`.ai/CONTRACT.md` §"Tag compression in cascade contexts" specifies three conditions under which cascade compression is permitted. Governance additions that live here (not in the contract itself, to keep the runtime contract focused):

1. **Framework Steward override.** Framework Steward may reject a compression as insufficient during PR review and require per-step tagging. The three conditions (named invariant, verification condition, explicit scope boundaries) are necessary but not sufficient — Steward judgment can demand tighter granularity when invariant breadth hides material risk.

2. **Audit trail.** Every compression decision in merged code must be justified in the PR description (which condition each of the three criteria satisfies). This is how adoption-audit traces compression use vs. abuse.

3. **Abuse signal.** If >30% of non-trivial cascades in a quarter use compression, Stewards review whether the compression rule is being used to avoid tagging work rather than to represent genuine invariants.

### D.4 Relationship to Practice Survey

Both Appendix D.1–D.2 (non-trivial definition) and D.3 (cascade compression) are the operational responses to Practice Survey Gap 1 (cascade decision compression) and the v1.5 deep-verify F1 finding. See `.ai/framework/PRACTICE_SURVEY.md` for the full incident list and gap analysis.

---

*End of Operating Model v1.2.1.*
