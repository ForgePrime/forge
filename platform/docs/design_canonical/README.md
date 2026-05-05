# `design_canonical/` — canonical UX truth

**Role:** the single source of truth for what the Forge UI **should look like**
at the structural level (component names, tab order, field set, route shape).
NOT the source of truth for *how* it is implemented.

## Why this directory exists

Per ADR-028 Decision 1 (SSR-only stack) + the §A.1/§A.5 long-term + AI-autonomy
lens: the redesign was authored as a React SPA, but Forge implements UI in
Jinja+HTMX. The two stacks must stay structurally parallel forever — when
the AI changes a Jinja partial, it needs a deterministic check against the
canonical UX, not a self-judgment "does this look right?"

This directory is that deterministic check's *reference target*.

## Contents

| File | Role |
|---|---|
| `../Forge redesign - standalone.html` (sibling at `platform/docs/`) | Bundled React SPA — the canonical reference. Open in any browser. |
| `../forge_redesign_extracted/` (sibling at `platform/docs/`) | Per-module decoded JS/JSX from the bundle (10 files). The extraction script lives at … (TBD when bootstrapped). |
| `MAPPING.md` (TBD) | One-row-per-route mapping: `/route → React component file → Jinja template file → snapshot test file`. |

> **Note (current state):** the canonical bundle and extracted modules
> already live in `platform/docs/` (sibling). This directory holds the
> *index* and *mapping*, not duplicate copies of the bundle.

## Verification protocol (deterministic gate)

Per task #28 (Deterministic ADR Gate Pipeline), each Jinja template port
gets:

1. **Component-name parity check.** Each Jinja partial includes a
   `{# canonical: <component_name> #}` comment naming the matching React
   component. CI greps for these and asserts every route has parity rows.
2. **Tab/section-set parity.** The tab list rendered by a Jinja `for`-loop
   must match the React component's `tabs` array (set equality, order
   preserved). Asserted by snapshot test that diffs the rendered DOM
   structure (not pixel positions) against the React reference.
3. **Field-set parity.** Each form field present in the React component
   exists in the Jinja partial. Asserted by HTML form-attribute scrape
   diff.

Pixel-level positioning is NOT in scope — designer review is reserved
for *canonical updates*, not implementation reviews.

## When the canonical updates

- A new feature requires a new component → designer authors React update
  → `Forge redesign - standalone.html` is regenerated → the corresponding
  module in `forge_redesign_extracted/` updates → MAPPING.md gets a new row
  → the parity tests fail until the matching Jinja partial is added.
- The cycle is: **canonical-first**, then implementation. AI cannot ship
  a Jinja change that has no canonical counterpart (parity test fails).

## Why this matters in 6 months

When Forge is largely AI-developed, this directory is the single decision
point for "what UX changes are we making?" Implementation churn happens
below it; design churn happens here. The boundary is testable.

> **Status note (2026-04-25):** companion artefact created per ADR-028
> Decision 1 ratification. Snapshot tests + MAPPING.md are scheduled with
> task #27 (DashboardView impl) — not yet authored.
