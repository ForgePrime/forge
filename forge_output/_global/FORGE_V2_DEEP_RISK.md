# Deep-Risk Report: Forge V2 Plan

**Scope:** Full Forge V2 plan as documented in `FORGE_V2_PLAN.md` — 7 new modules, refactoring of 6 existing modules, Web UI (backend + frontend), 44 tasks across 4 phases, estimated 8 weeks.

**Boundary:** In scope: technical feasibility, organizational adoption, timeline, dependencies, knowledge gaps. Out of scope: hosting/infrastructure costs, team hiring, legal/licensing.

**What is at stake:** Developer time (solo developer + AI agent), existing V1 project data, Forge's usability as a tool, and the risk of creating a system so complex it defeats its own purpose.

**Time horizon:** 8 weeks (plan estimate), extended to 16 weeks for realistic assessment.

---

## Risk Register

| # | Risk | P | I | V | D | R | Composite | Category |
|---|------|---|---|---|---|---|-----------|----------|
| R-01 | Web UI scope creep (3 weeks becomes 12+) | 5 | 4 | 2 | 3 | 2 | 27 | Temporal |
| R-02 | Scenario generation produces low-value noise | 4 | 4 | 3 | 4 | 2 | 25 | Technical |
| R-03 | Complexity explosion: V2 becomes unusable | 4 | 5 | 2 | 4 | 4 | 30 | Organizational |
| R-04 | Override becomes the new --force | 3 | 4 | 3 | 3 | 2 | 20 | Organizational |
| R-05 | Claude Code hook integration is fragile/impossible | 4 | 3 | 4 | 3 | 3 | 22 | Dependency |
| R-06 | Independent verification = double LLM cost | 4 | 3 | 2 | 2 | 1 | 17 | Technical |
| R-07 | V1 project migration breaks existing data | 3 | 4 | 4 | 3 | 4 | 23 | Technical |
| R-08 | Briefing approval becomes rubber-stamping | 4 | 4 | 2 | 5 | 2 | 25 | Organizational |
| R-09 | Finding queue noise overwhelms user | 3 | 3 | 2 | 3 | 1 | 15 | Organizational |
| R-10 | Plan assumes solo execution but scopes like a team | 4 | 4 | 2 | 3 | 3 | 24 | Temporal |
| R-11 | Execution tracer overhead degrades Claude Code UX | 3 | 3 | 3 | 2 | 2 | 16 | Technical |
| R-12 | 7 new JSON files per task = storage/management burden | 3 | 2 | 2 | 2 | 2 | 12 | Technical |
| R-13 | Tight coupling between Briefing, Scenarios, Verification | 3 | 3 | 3 | 3 | 3 | 18 | Technical |
| R-14 | No existing tests for core modules being refactored | 4 | 3 | 4 | 2 | 3 | 21 | Knowledge |
| R-15 | Adversarial scenario design requires domain expertise AI lacks | 3 | 3 | 2 | 4 | 2 | 17 | Knowledge |

**Composite score formula:** (P x I) + V + D + R

---

## Top 5 Risks (by composite score)

### 1. R-03: Complexity explosion — V2 becomes unusable (Composite: 30)

**Description:** The plan adds 7 new modules (briefing, scenarios, findings, verification, tracer, observatory API, observatory frontend), 3 new JSON artifact types per task (briefing, trace, verification report), a mandatory approval gate, and a full Web UI. The current system has ~22 core modules. This nearly doubles the surface area. A solo developer using an AI tool for productivity could find the ceremony overhead exceeds the value delivered. The cure becomes worse than the disease.

**5D Scores:**
- **Probability (4):** The plan already contains 44 tasks. Each new module adds interfaces, contracts, tests, and integration points. History shows V1 already has 45% untested modules — adding more will compound the debt.
- **Impact (5):** Existential — if V2 is too complex to use, the entire effort is wasted and the developer returns to ad-hoc AI usage.
- **Velocity (2):** Slow onset — complexity accumulates gradually during implementation. Won't be felt until Phase 2-3.
- **Detectability (4):** Hard to detect in-progress. Each module feels "reasonable" in isolation. The cumulative weight only shows when running the full workflow.
- **Reversibility (4):** Once modules are built with cross-dependencies, simplifying requires significant refactoring.

**Mitigation:**
- Define a "Minimum Viable V2" with ONLY: (a) Briefing Compiler with visible context, (b) hard enforcement replacing --force, (c) context transparency (excluded section). Ship this. Measure if it solves core problems.
- Defer scenarios, findings, verification engine, tracer, and Web UI to later phases.
- Apply the plan's own "appetite" concept: SMALL appetite (days, not weeks) per module.
- Metric: if V2 workflow for a simple bug fix takes >3x longer than V1, the design failed.

**Cobra Effect Check:** Defining MVP too narrowly could mean shipping something that doesn't solve W-2 (soft enforcement). Ensure MVP includes hard enforcement, not just briefings. **Risk: LOW.**

---

### 2. R-01: Web UI scope creep (Composite: 27)

**Description:** The plan allocates 3 weeks for the frontend (Phase 3) with 10 tasks (T-030 through T-039), including ReactFlow DAG visualization, WebSocket real-time execution monitoring, source tracing popups, and finding triage UI. Web frontends are notorious for scope creep. The spec is already at "full product" level, not MVP.

**5D Scores:**
- **Probability (5):** The spec includes component trees, store architecture, page layouts. This is already too detailed for a 3-week estimate.
- **Impact (4):** Could consume entire timeline and delay core improvements that matter.
- **Velocity (2):** Slow — scope creep is incremental ("just one more feature").
- **Detectability (3):** Somewhat visible — if deadlines slip, it's noticeable. But feature additions feel productive.
- **Reversibility (2):** Frontend code can be abandoned without affecting core modules.

**Mitigation:**
- Cut Phase 3 entirely from V2. Core value works via CLI.
- If Web UI desired, start with single read-only page: briefing viewer that renders briefing JSON as formatted HTML. No WebSocket, no DAG, no triage. One afternoon of work.
- Move full Web UI to separate project/phase.

**Cobra Effect Check:** Cutting Web UI removes "observatory" value proposition. But the plan's diagnosis identifies 5 structural flaws, none requiring a Web UI to fix. **Risk: LOW.**

---

### 3. R-02: Scenario generation produces low-value noise (Composite: 25)

**Description:** The Scenario Generator proposes auto-generating adversarial, failure-mode, integration, compliance, and performance scenarios from task instructions, risks, guidelines, and dependencies. AI-generated test scenarios tend to be either obvious/trivial, impossible to automate without deep domain context, or so numerous they become noise. Minimum 3 scenarios per task x 44 tasks = 132+ scenarios to review.

**5D Scores:**
- **Probability (4):** Current AI output quality in forge_output shows identical descriptions, placeholder reasoning. Scenario quality will likely follow the same pattern.
- **Impact (4):** Bad scenarios give false confidence. Users think they have test coverage but the scenarios don't catch real bugs.
- **Velocity (3):** Fast — noise appears immediately when scenario generation starts.
- **Detectability (4):** Bad scenarios look plausible on paper. "Test that cache returns correct data" sounds useful but is trivially obvious.
- **Reversibility (2):** Scenarios are just JSON — easy to delete and start over.

**Mitigation:**
- Start with manual scenario writing for first 5 tasks. Observe patterns. Then template common types.
- Drop minimum scenario count requirement. Require scenarios only for tasks with HIGH risks or cross-module dependencies.
- Validate scenario quality: can this scenario actually be executed with existing test infrastructure?

**Cobra Effect Check:** Reducing scenario count could leave edge cases uncovered. Counter: current system has zero scenarios. A few well-crafted ones beat 132 auto-generated ones. **Risk: LOW.**

---

### 4. R-08: Briefing approval becomes rubber-stamping (Composite: 25)

**Description:** The plan's central innovation is COMPILE -> APPROVE -> EXECUTE. But if briefings are long (~100 lines JSON in the example), users will develop approval fatigue and rubber-stamp without reading. This recreates prompt opacity with a different wrapper.

**5D Scores:**
- **Probability (4):** Human nature with repetitive approval gates. Well-documented in UX research.
- **Impact (4):** If users don't actually read briefings, the entire transparency value is lost. Money spent on briefing compilation is wasted.
- **Velocity (2):** Slow onset — first few briefings will be read carefully. Fatigue sets in by task 10-15.
- **Detectability (5):** Invisible — approval timestamps look normal. No way to measure whether user actually read the content.
- **Reversibility (2):** UI can be redesigned to show summaries. But behavioral patterns are harder to change.

**Mitigation:**
- Make briefings SHORT: executive summary (5 lines max) + expandable detail. Approval = approving the summary.
- Highlight ONLY what changed or what's unusual (risks, excluded guidelines, new scenarios).
- Add "briefing diff from template" showing ONLY non-standard parts.
- Tiered approval: auto-approve LOW-risk tasks, review-on-screen MEDIUM, hard-block HIGH.

**Cobra Effect Check:** Auto-approving standard tasks could let bad briefings through. Counter: auto-approval is a designed policy, not an escape hatch like `--force`. Clear risk classification criteria needed. **Risk: MEDIUM.**

---

### 5. R-10: Plan assumes solo execution but scopes like a team project (Composite: 24)

**Description:** 44 tasks across 4 phases over 8 weeks. Single developer with AI assistance. Phase 1 alone (12 tasks including 5 new modules from scratch) estimated at 2 weeks. Based on existing codebase velocity (10 test files for 22 modules = 45% coverage), the velocity of test-writing is low.

**5D Scores:**
- **Probability (4):** Scope/time mismatch is measurable against historical velocity.
- **Impact (4):** Partially built modules create technical debt if abandoned.
- **Velocity (2):** Slow — timeline slip happens gradually.
- **Detectability (3):** Visible through missed milestones.
- **Reversibility (3):** Partially built modules can be completed later, but integration debt accumulates.

**Mitigation:**
- Replan with realistic velocity based on how long existing modules took.
- Sequence strictly: one module at a time, fully tested, before starting the next.
- Drop Phase 3 (Web UI) and Phase 4 from V2 scope.
- Realistic Phase 1: 4-6 weeks for 5 new modules + pipeline refactor + tests.

**Cobra Effect Check:** Extending timeline could cause motivation loss. Counter: shipping 3 solid modules beats shipping 7 half-finished ones. **Risk: LOW.**

---

## Risk Interactions

| Risk A | Risk B | Interaction | Cascade? |
|--------|--------|-------------|----------|
| R-01 (Web UI creep) | R-10 (Solo, team scope) | Web UI delays cascade into Phase 4, consuming all buffer time | Yes — R-01 triggers R-10 |
| R-03 (Complexity) | R-08 (Rubber-stamping) | More ceremony = more approval fatigue = less actual review | Yes — R-03 amplifies R-08 |
| R-02 (Scenario noise) | R-09 (Finding noise) | Both produce high-volume low-signal artifacts, compounding user fatigue | Shared root cause: over-automation |
| R-05 (Hook fragile) | R-11 (Tracer overhead) | If hooks are unreliable, tracer retries/fallbacks add more overhead | Yes — R-05 amplifies R-11 |
| R-03 (Complexity) | R-04 (Override = force) | If system too complex, users find workarounds including liberal override | Yes — R-03 triggers R-04 |
| R-10 (Timeline) | R-14 (No tests) | Time pressure leads to skipping tests for refactored code | Yes — R-10 amplifies R-14 |
| R-07 (V1 migration) | R-06 (Double cost) | Migration + verification cost could make V2 economically unattractive | Shared consequence: V2 abandonment |
| R-02 (Scenario noise) | R-08 (Rubber-stamping) | Noisy scenarios make briefings longer, increasing rubber-stamp likelihood | Yes — R-02 amplifies R-08 |

### Cascade Diagram

```
R-01 (Web UI scope) ──────────► R-10 (Timeline blown)
                                     │
                                     ▼
                               R-14 (Tests skipped)
                                     │
                                     ▼
                          CONSEQUENCE: V2 ships with same
                          quality problems as V1

R-03 (Complexity) ────────────► R-08 (Rubber-stamping)
       │                             │
       ▼                             ▼
R-04 (Override abuse)       CONSEQUENCE: Transparency
                            theater — looks good, no value

R-02 (Scenario noise) ──┐
                         ├──► R-08 (Rubber-stamping)
R-09 (Finding noise) ───┘         │
  (shared root cause)             ▼
                          CONSEQUENCE: User ignores
                          all Forge output
```

---

## Mitigations + Cobra Effect Check

| Mitigation | Fixes | Could Cause/Amplify | Cobra? |
|------------|-------|---------------------|--------|
| Define Minimum Viable V2 (briefing + hard enforcement + context transparency only) | R-03, R-01, R-10 | Could ship too minimal, not solving core problems | LOW — must include hard enforcement |
| Cut Web UI entirely from V2 | R-01, R-10 | Loses "observatory" value; no visual DAG, no triage UI | LOW — CLI covers 100% functionality |
| Manual scenarios instead of auto-generation | R-02 | Slows planning phase; fewer scenarios | LOW — quality over quantity |
| Auto-approve LOW-risk task briefings | R-08 | Could let bad briefings through for surprise-complex tasks | MEDIUM — needs clear risk classification |
| Drop minimum scenario count | R-02, R-09 | Could leave edge cases uncovered | LOW — zero scenarios (V1) is baseline |
| Extend Phase 1 to 4-6 weeks | R-10, R-14 | Motivation loss, extended time-to-value | LOW — ship incrementally |
| Override frequency alerting | R-04 | Requires dashboard (R-01 scope creep) | MEDIUM — CLI-based audit instead |
| Cache briefing compilation | R-11 | Cache invalidation complexity | LOW |
| Migration script with backward compat | R-07 | Two-format maintenance increases code complexity | MEDIUM — set sunset date |
| Require scenarios only for HIGH-risk tasks | R-02 | Medium-risk tasks may lack coverage | LOW — acceptable tradeoff |

---

## Uncertainties (distinct from risks)

These are genuine unknowns where probability distribution is not estimable:

1. **Claude Code hook API stability.** Hooks in settings.json may change, be removed, or have undocumented limitations. No public API contract or SLA exists for this integration path.

2. **User behavior with mandatory approval gates.** No data on how users interact with approval gates in AI-assisted development. Could be loved or hated — genuinely unknown.

3. **AI-generated adversarial scenario quality.** Whether the AI can consistently generate non-obvious, useful adversarial scenarios for arbitrary codebases is unknown. Current evidence (forge_output quality) suggests mediocre baseline.

4. **Verification engine effectiveness without second AI agent.** How much of the 5-layer verification can be automated with pattern matching vs requiring LLM assessment is unknown.

5. **Performance of Forge with 100+ tasks and 7+ JSON files per task.** Flat JSON files at scale — no benchmarks exist.

---

## Not Assessed

- **Security risks** of the Web UI (authentication, authorization, CORS, XSS)
- **Hosting and infrastructure costs** for Web UI and multiple AI agents
- **Licensing and IP** implications of Claude Code hook integration
- **Alternative architectures** (database-backed, plugin-based, etc.)
- **Impact on existing Forge users** beyond migration
- **Competitive landscape** — similar tools solving these problems
- **Observer effect** — whether heavy instrumentation changes AI behavior unexpectedly (e.g., more conservative code to pass scenarios, gaming quality checks)

---

## Counter-Checks

- [x] All 5 identification lenses used (Technical, Organizational, Temporal, Dependency, Knowledge)
- [x] All 5 scoring dimensions applied (P, I, V, D, R) for every risk
- [x] Every mitigation checked for Cobra Effect
- [x] Risks separated from uncertainties (5 uncertainties identified)
- [x] "Not Assessed" honestly lists 7 scope gaps

---

## Executive Summary

The Forge V2 plan correctly diagnoses real problems (soft enforcement, prompt opacity, lack of testing, information loss). However, **the plan's scope is approximately 3-4x larger than what a solo developer with AI assistance can deliver in 8 weeks**, and the added complexity risks creating a system that is harder to use than V1.

**The single highest-priority action is to define a Minimum Viable V2** consisting of:
1. **Briefing Compiler** (context visibility) — solves W-1
2. **Hard enforcement** replacing --force with --override --reason — solves W-2
3. **Context transparency** (excluded section in context.py) — solves W-4
4. **Pipeline refactor** for these changes — solves W-2

This is roughly 4 tasks instead of 44. It can be delivered in 2-3 weeks and validated before expanding scope. The Web UI, Scenario Generator, Finding System, Verification Engine, and Execution Tracer should be deferred to subsequent phases with their own objectives and appetite assessments.
