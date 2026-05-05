# PATTERN — Deterministic Snapshot Validation

**Audience:** engineers implementing CI gates for output-stable systems
**Source:** extracted from `OPERATING_MODEL.md` v1.4 §9.4 during the framework v2.0 reorganization
**Status:** opt-in pattern. Adopt where output is stable and representable; do not blanket-apply.

---

## Purpose

Deterministic Snapshot Validation turns *"does this output behave correctly?"* (judgment) into *"does this output match its approved baseline byte-for-byte (or by declared equivalence rule)?"* (deterministic). The gate shifts from "reviewer assesses correctness" to "comparator executes and yields pass or fail."

This is the single highest-leverage transformation available for moving CGAID gates from judgment to determinism. When applicable, it converts entire classes of regression into CI-level failures.

For background on gate types (Deterministic / Rubric-based / Judgment-based), see [`ARCHITECTURE.md §5.1`](../framework/ARCHITECTURE.md).

---

## Five Components (all required)

**1. Baseline Artifact.** A stored, versioned representation of known-good output. It lives in the repository (or a controlled artifact store) under version control. It is the authoritative reference. Without a baseline, the pattern is not snapshot validation — it is assertion testing.

**2. Snapshot Producer.** A mechanism that generates the current output in a format structurally comparable to the baseline. Must be deterministic itself: same inputs produce the same output bytes. Non-determinism in the producer (timestamps, random IDs, environment-dependent values) poisons the entire pattern and must be normalized, injected, or stripped.

**3. Deterministic Comparator.** A function that compares current output to baseline and yields a binary result (pass / fail) plus, on fail, a diff. The comparator may apply declared equivalence rules (e.g., "ignore timestamps within this field", "treat whitespace-only differences as equivalent") but those rules are themselves versioned artifacts, not ad-hoc judgment.

**4. Drift Disposition.** Explicit policy for what happens when the comparator yields fail:
- **Block** (default for critical paths) — CI fails, merge refused, engineer investigates.
- **Warn-and-continue** — for low-stakes snapshots; generates PR comment but does not block.
- **Human-review-required** — diff is surfaced; reviewer explicitly approves or rejects the drift.
- Never: **silent auto-accept**. This collapses the pattern into security theater.

**5. Baseline Update Protocol.** The procedure by which a baseline is legitimately updated when intended behavior changes. Updates require explicit human approval — usually a separate PR or a reviewer-approved flag in the current PR (`baseline-update: approved`). Baseline changes have their own review discipline: a reviewer who would normally focus on code change now also evaluates *"is this drift the intended behavior?"*

---

## Where the Pattern Applies in CGAID Gates

The pattern can be installed at multiple stages:

- **Stage 1 volume check** — for any filter / CTE / aggregation introduced, baseline the row-count fingerprint of its output against a fixture input. An unexpected 96% row reduction fails the baseline comparator before merge.
- **Stage 3 exit — "code matches plan"** — where the plan includes a target output shape, snapshot-compare against that target.
- **Stage 4 business-outcome verification** — where outcome has a deterministic signature (specific rows appearing in a specific table, a specific metric crossing a threshold), snapshot-validate the signature.
- **Maintenance-mode regression detection** — every patch to a Standard+ feature runs the feature's baseline snapshot suite; any drift blocks unless explicitly approved.
- **Dependency update verification** — run snapshot suite before and after dependency bump; no drift = safe, drift = review.

---

## Concrete Applications Across Domains

| Domain | Baseline | Snapshot Producer | Comparator |
|---|---|---|---|
| UI rendering | Approved screenshot per page/component | Headless browser rendering | Pixel or structural diff (e.g., image diff, DOM tree hash) |
| SQL output | Known row-count / checksum per fixture | Query execution against fixture DB | Row-count + hash of sorted tuples |
| API response | Stored JSON payload per request fixture | HTTP call against test instance | JSON deep-equal with declared ignorable fields |
| Data pipeline | Expected output table state + row count + per-partition checksum | Pipeline execution against fixture input | Table-level and partition-level comparison |
| Document rendering | Expected PDF / HTML bytes or structural tree | Rendering engine output | Byte-equivalence or structural tree diff |
| ML model output | Expected prediction distribution on fixture dataset | Model inference | Statistical distribution comparison with tolerance |

---

## Canonical Example Already in Practice

The restore module's deep-proof test suite (commit `d4a180e` — *"Add 15 deep proof + concurrency + edge case tests with fingerprint comparison"*) is an in-practice implementation of this pattern. Fixture state → restore operation → fingerprint of resulting database state → compare to expected fingerprint. Drift blocks merge via CI; baseline updates require explicit code review of the new fingerprint value.

The pattern existed *before* CGAID formalized it. This document canonizes what was already working so that other adopters can implement it deliberately rather than re-discovering it accidentally.

---

## Anti-Patterns (failure modes of the pattern)

**Baseline drift.** Baselines updated casually, often bundled into unrelated PRs. Over time, the baseline no longer represents intended behavior — it represents *whatever the code happens to do*. Mitigation: require baseline updates to be their own PR or carry an explicit `baseline-update-approved` flag that the reviewer must sign.

**Flaky snapshots.** The Snapshot Producer is not fully deterministic — timestamps, random IDs, dictionary iteration order, floating-point rounding, or environment-dependent values leak into the output. Every PR produces noise diffs that engineers learn to ignore. Mitigation: identify and normalize all non-determinism sources in the producer; if you cannot normalize, do not use this pattern for that domain.

**Coverage illusion.** Snapshot passing means *"current output matches baseline"* — it does not mean *"behavior is correct."* A bug that was present when the baseline was captured remains a passing test. Mitigation: baselines are validated at creation by the same rigor as any other artifact (Stage 2 DoD applies to the baseline itself).

**Approval theater.** Baseline-update approvals become rubber-stamps because reviewers don't know what drift "should" look like. Mitigation: baseline-update PRs carry explicit rationale ("behavior changed because X"), and reviewer verifies the drift corresponds to that rationale rather than extra-drift.

**Silent auto-accept.** The worst version. The CI script, on comparator failure, silently replaces the baseline with the current output so that "the next run will pass." The pattern collapses to no gate at all. **This must be explicitly prohibited** in automation configuration.

---

## When *Not* to Use This Pattern

- **Legitimately variable output** — content that is personalized, time-dependent by design, or otherwise non-repeatable. A user dashboard showing "current timestamp" cannot be baseline-compared without extensive normalization; the maintenance cost exceeds the gate value.
- **Baseline maintenance cost exceeds gate value** — if the output changes daily (content-heavy pages, frequently iterated UX), baselines become churn rather than governance.
- **Gate is fundamentally about business outcome, not artifact correctness** — *"did the user achieve their intent?"* is not a snapshot question; it's a DoD question. Snapshot validation cannot substitute for Stage 4 business verification.
- **Output is continuously learned or optimized** — ML model outputs, recommender rankings, A/B-tested variants. Use statistical comparison patterns, not byte-equivalence.

---

## Relationship to CGAID Gate Spectrum

Deterministic Snapshot Validation is a **tool for moving a specific gate from judgment-based to deterministic**. It does not make all gates deterministic — it makes gates with stable, representable output deterministic. Judgment gates remain judgment gates. Rubric gates remain rubric gates. But a meaningful subset of CGAID's current judgment gates — specifically those about output correctness and regression detection — can be transformed by this pattern.

Framework recommendation: adopting organizations identify *one* gate they currently run as judgment-based where output is stable and representable, implement Deterministic Snapshot Validation there as a proof of concept, and expand from observed success. Attempting to blanket-apply the pattern before it has earned adopters' trust is a common failure mode.
