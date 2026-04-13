# Deep-Verify Report: Forge V2 Plan

```
SETUP
  Artifact: forge_output/_global/FORGE_V2_PLAN.md
  Mode: DEEP (high stakes — fundamental architecture redesign)
  Scope: 
    IN: V1 diagnosis accuracy, architectural soundness, module interfaces,
        implementation plan feasibility, internal consistency, risk coverage
    OUT: Web UI implementation details (React/FastAPI specifics), 
         specific Python code correctness, LLM prompt engineering quality
  Assumptions:
    - The plan is meant to be executed by Claude Code agents using Forge's existing infrastructure
    - "Interpreter vs compiler" is a metaphor, not literal
    - The author has direct experience with V1's operational problems
    - The plan will be refined further; this is a DRAFT review
```

---

## VERDICT

**VERDICT: UNCERTAIN** | Score: **5.6** | Confidence: **MEDIUM**

The plan correctly identifies real problems in V1 but proposes a solution that is structurally overengineered for some problems and fundamentally misguided for one critical claim. The "independent verification" concept is architecturally sound but practically unimplemented — the plan does not actually specify HOW to achieve it. The implementation plan has realistic phasing but unrealistic scope for an 8-week timeline.

---

## EXECUTIVE SUMMARY

The V1 diagnosis is largely accurate and well-evidenced from real code. Four of five identified problems (W-1, W-2, W-4, W-5) are real and confirmed by codebase inspection. One problem (W-3, "student grades own exam") misdiagnoses the issue — the problem is not SELF-assessment but ABSENT assessment. The proposed solution introduces 5 new modules plus a full web application, creating a large surface area where the core value could be delivered with 2-3 focused changes. The plan's internal interfaces are well-designed but contain assumption gaps about execution context (Claude Code hooks, "independent" verification).

---

## FINDINGS

### F-1: CRITICAL — "Independent verification" is never actually specified

**Quote**: "Oddzielny proces weryfikacji (nie ta sama AI)" (Section 2.1, VERIFY box)

**Analysis**: The plan claims verification must be done by a separate process, not the same AI. But the plan never specifies what this separate process IS. Section 3.4 (Verification Engine) describes WHAT is checked but not WHO or HOW independently. The 5 verification layers (gates, scenarios, guidelines, briefing diff, quality) are all things the same Claude Code agent could run. The only truly independent parts are the automated gates (pytest, lint), which V1 already has.

Open decision D-1 acknowledges this: "Kto robi niezalezna weryfikacje?" with option (c) "human + automated" recommended. But the entire architecture is drawn as if independent verification is solved, when it is the plan's central unsolved problem.

**Adversarial self-review**:
1. Alternative explanation: Author may intend "independent" to mean "structurally separate phase" not "different agent" — the diagram separates EXECUTE from VERIFY as distinct phases. *Partially weakens.*
2. Hidden context: The Web UI could enable a human to perform verification by reviewing the report. *Does not fully address — human review of auto-generated reports is still dependent on report quality.*
3. Domain exception: No. Separation of concerns in verification is a well-established principle.
4. Confirmation bias: Reading in different order would still surface this gap.

**Result**: 1/4 challenges weaken. **KEEP at CRITICAL.** (+3 points)

---

### F-2: IMPORTANT — W-3 misdiagnoses the testing problem

**Quote**: "Weryfikacja = AI sprawdza swoj wlasny kod = student ocenia wlasny egzamin" (Section 1.2, W-3)

**Analysis**: The actual V1 code in `skills/next/SKILL.md` Step 5 calls for deep-verify AND guidelines compliance check. The problem is not that the AI grades its own work — it is that the AI may SKIP verification entirely (W-2, soft enforcement). The "student grades own exam" metaphor implies the solution is a different grader, but in practice, a second LLM call is not meaningfully more independent than the first. The real fix is making verification non-skippable and evidence-based, which the plan also proposes — but frames it as solving W-3 when it actually solves W-2.

**Adversarial self-review**:
1. Alternative explanation: Author may be arguing that even when verification runs, it is biased because the same agent wrote AND checks. *Reasonable, but the proposed solution (Verification Engine) does not eliminate this bias — it just adds structure.*
2. Hidden context: In multi-agent setups, a different agent could verify. *The plan does not propose multi-agent verification.*
3. Domain exception: Code review by different developers IS standard practice. *But the plan does not implement this — see F-1.*
4. Confirmation bias: No change.

**Result**: 2/4 challenges partially weaken. **KEEP at IMPORTANT.** (+1 point)

---

### F-3: IMPORTANT — Execution Tracer relies on unvalidated mechanism

**Quote**: "Tracer dziala jako wrapper wokol tool calls w Claude Code: Hook na Read -> event file_read, Hook na Edit/Write -> event file_create/file_edit" (Section 3.5)

**Analysis**: The plan proposes hooking into Claude Code's tool calls via "Claude Code hooks (settings.json)". Claude Code hooks exist but have significant constraints: they run shell commands before/after tool calls, receive limited context, and cannot easily capture tool parameters like file paths or reasoning. The plan assumes hooks can capture "every tool call with timestamp" including purpose and file paths. The fallback ("wrapper w skills/next/SKILL.md ktory instruuje AI by raportowala kazda akcje") is the EXACT "interpreter" approach the plan criticizes V1 for.

**Adversarial self-review**:
1. Alternative explanation: Author may know Claude Code hooks well and believe they suffice. *Possible, but no evidence provided.*
2. Hidden context: Claude Code hooks may have evolved. *Plausible but unverified.*
3. Domain exception: No.
4. Confirmation bias: No change.

**Result**: 1/4 challenges weaken. **KEEP at IMPORTANT.** (+1 point)

---

### F-4: IMPORTANT — Scope creep: Web UI is 50%+ of the plan

**Quote**: "Faza 2: Web Backend (tydzien 3-4)" + "Faza 3: Web Frontend (tydzien 5-7)" — 19 tasks out of ~40 total

**Analysis**: The core value proposition (briefing compiler, scenarios, verification, findings, hard enforcement) requires 12 tasks in Phase 1. The Web UI adds 19 more tasks (Phases 2-3), representing 61% of implementation effort. Risk R-5 acknowledges this: "Web UI scope creep (3 weeks -> 8 weeks)" but the plan does not act on it — the full web UI is still in the implementation plan. Decision D-5 recommends MVP ("briefing + pipeline only") but this is not reflected in the task list, which includes FindingTriage, ObjectiveTracker, GuidelineManager, SourceTrace, and other non-MVP features.

**Adversarial self-review**:
1. Alternative explanation: The full task list is aspirational; D-5 is the actual plan. *If so, the task list should reflect this.*
2. Hidden context: The team may have frontend capacity. *Nothing suggests this.*
3. Domain exception: No.
4. Confirmation bias: No change.

**Result**: 1/4 challenges weaken. **KEEP at IMPORTANT.** (+1 point)

---

### F-5: IMPORTANT — Briefing approval creates a blocking bottleneck

**Quote**: "HARD BLOCK: bez zatwierdzenia execution nie startuje" (Section 2.1, APPROVE box) and "briefing.approved_at MUSI istniec przed cmd_next pozwoli na execution" (Section 3.6)

**Analysis**: Every task requires human approval of a briefing before execution can begin. For a project with 20+ tasks, this means 20+ approval cycles. The plan provides no mechanism for batch approval, auto-approval of low-risk tasks, or trust escalation. This directly contradicts the existing `/run` command (continuous task execution) and the `/do` quick path, which are designed for low-ceremony work. The plan does not address how these commands work under the new regime.

**Adversarial self-review**:
1. Alternative explanation: Author may intend this for critical tasks only. *But "HARD BLOCK" and "STRUCTURAL (kod nie pozwala ominac)" suggest universal enforcement.*
2. Hidden context: Auto-approval could be added later. *Yes, but the plan explicitly rejects the V1 pattern of "soft enforcement" — adding auto-approval later would re-introduce the same problem.*
3. Domain exception: In safety-critical systems, approval before execution is standard. *Forge is a code orchestrator, not a nuclear reactor.*
4. Confirmation bias: No change.

**Result**: 1/4 challenges weaken. **KEEP at IMPORTANT.** (+1 point)

---

### F-6: MINOR — V1 test coverage claim is imprecise

**Quote**: "Testy Forge: 45% modulow (12/22) bez testow" (Section 1.3)

**Analysis**: Codebase inspection shows ~35 core Python files (including submodules under `core/llm/`) and 10 test files. The claim of "22 modules" appears to count only top-level core files. This is not wrong per se, but imprecise — the actual coverage gap may be larger or smaller depending on how you count. The claim "Zero testow end-to-end. Zero testow behawioralnych" is verifiable and appears accurate — no e2e or behavioral test files exist.

**Result**: **MINOR** (+0.3 points)

---

### F-7: MINOR — Scenario Generator assumes LLM-quality output from deterministic code

**Quote**: "ADVERSARIAL -> sabotage/edge case scenarios: '10K concurrent requests na ten sam klucz', 'Corrupt JSON w cache entry'" (Section 3.2)

**Analysis**: The Scenario Generator is described as a Python module (`core/scenarios.py`) that "generates adversarial test scenarios from risks, guidelines, dependencies." But generating meaningful adversarial scenarios requires understanding the task's domain and code context — this is inherently an LLM task, not a deterministic code generation task. The plan does not clarify whether this module calls an LLM or uses templates.

**Result**: **MINOR** (+0.3 points)

---

### F-8: IMPORTANT — Circular dependency in verification trigger

**Quote**: "AI NIE oznacza zadania jako DONE" (EXECUTE box) combined with "DOPIERO po przejsciu -> DONE" (VERIFY box)

**Analysis**: The plan says the AI should NOT mark a task as DONE — only verification can. But who triggers verification? If the AI must call `verification run` and then `pipeline complete`, the AI is still in control of the completion flow. If verification is triggered externally (Web UI, human), then the AI is blocked waiting with no mechanism to proceed. The plan does not specify the trigger mechanism for verification. This creates either: (a) the same self-grading problem the plan criticizes, or (b) a deadlock where the AI cannot proceed.

**Adversarial self-review**:
1. Alternative explanation: The Web UI triggers verification. *Then CLI-only usage (which is 100% of current usage) is broken.*
2. Hidden context: A hook on git commit could trigger verification. *Not mentioned in the plan.*
3. Domain exception: CI/CD systems solve this with automation. *But the plan does not propose CI/CD integration.*
4. Confirmation bias: No change.

**Result**: 1/4 challenges weaken. **KEEP at IMPORTANT.** (+1 point)

---

### Clean Method Passes

- **Vocabulary consistency**: Terms are used consistently throughout (briefing, scenario, finding, verification). **-0.5 points**
- **Dependency graph structure**: The DAG in Section 4 is valid — no circular dependencies in the implementation plan. **-0.5 points**

---

## SCORE CALCULATION

| Finding | Severity | Points |
|---------|----------|--------|
| F-1: Independent verification unspecified | CRITICAL | +3.0 |
| F-2: W-3 misdiagnosis | IMPORTANT | +1.0 |
| F-3: Tracer mechanism unvalidated | IMPORTANT | +1.0 |
| F-4: Web UI scope creep | IMPORTANT | +1.0 |
| F-5: Approval bottleneck | IMPORTANT | +1.0 |
| F-6: Test coverage imprecise | MINOR | +0.3 |
| F-7: Scenario generation ambiguity | MINOR | +0.3 |
| F-8: Verification trigger gap | IMPORTANT | +1.0 |
| Clean: Vocabulary consistency | - | -0.5 |
| Clean: DAG structure valid | - | -0.5 |
| **TOTAL** | | **6.6** |

Post-adversarial adjustments: F-5 modestly adjusted (-1.0 → consideration for tiered approval). 

**Adjusted Total: 5.6** — UNCERTAIN, leaning toward REJECT without revisions.

---

## STEEL-MAN (strongest argument against this verdict)

The plan's core insight — that V1 has no visible intermediate artifacts and enforcement is soft — is correct and important. Even if "independent verification" is not truly independent, the structured Briefing + Scenario + Verification pipeline creates VISIBLE ARTIFACTS at each step, which is a massive improvement over V1's invisible context assembly and optional checkpoints. The Web UI, even if overscoped, addresses the fundamental transparency problem. The approval bottleneck is a deliberate design choice favoring correctness over velocity, and in practice, most tasks in a Forge project are complex enough to benefit from a briefing review. The execution tracer, even if implemented via SKILL.md instructions rather than hooks, still produces better audit trails than V1's empty reasoning_trace fields.

**Counter to steel-man**: The steel-man holds partially — the visibility improvements ARE valuable. But the plan positions itself as solving the "self-grading" problem (W-3) and achieving "independent verification," which it does not. If the plan were reframed as "structured visibility and hard enforcement" rather than "independent verification," it would be more honest and still deliver 80% of the value.

---

## WHAT WAS NOT EXAMINED

1. **Actual forge_output/ data quality** — The plan cites specific evidence (C-001 to C-005, reasoning traces, AC verification) that was not re-verified against actual files
2. **Web UI technical feasibility** — React/FastAPI architecture not evaluated for correctness
3. **Performance implications** — Whether briefing compilation and scenario generation add unacceptable latency
4. **Migration path** — Whether V1 projects can actually be migrated to V2 format
5. **Multi-agent interaction** — How the new flow interacts with the existing multi-agent claim protocol
6. **Cost analysis** — Whether the additional LLM calls (scenario generation, etc.) are economically viable
7. **Tool call failure rate claim** (t040: 33-50%) — Not verified against actual data

---

## RECOMMENDATIONS

1. **CRITICAL — Resolve the verification trigger problem (F-1 + F-8)**. Specify concretely: after AI finishes execution, what happens? Options: (a) AI calls `verification run` then `pipeline complete` — accept this is self-triggered but structurally enforced; (b) git commit hook triggers verification; (c) human triggers via Web UI/CLI. Pick one and design for it.

2. **IMPORTANT — Reframe W-3**. The problem is not "student grades own exam" but "exam has no rubric and grading is optional." The solution (scenarios + evidence + hard enforcement) addresses THIS problem. Drop the "independent verification" claim unless you actually implement multi-agent verification.

3. **IMPORTANT — Scope the Web UI to MVP immediately (F-4)**. Remove T-032 through T-038 from the initial plan. Keep: Dashboard (T-037), BriefingPanel (T-031), PipelineView (T-034). Add everything else as Phase 5 stretch goals.

4. **IMPORTANT — Add approval tiers (F-5)**. Three tiers: (a) auto-approve for tasks with type=chore and no MUST guidelines; (b) review-on-screen for standard tasks (show briefing, 10-second timeout, auto-approve if no objection); (c) hard-block for tasks with HIGH risks or blocked_by_decisions. This preserves the safety benefit without creating a bottleneck.

5. **IMPORTANT — Validate the tracer mechanism (F-3)**. Before committing to the architecture, prototype a Claude Code hook that captures file path from a Read tool call. If hooks cannot do this, redesign the tracer as a SKILL.md instruction pattern (and accept the "interpreter" tradeoff explicitly).

6. **MINOR — Clarify scenario generation mechanism (F-7)**. Is `core/scenarios.py` a template engine, an LLM caller, or both? This affects the entire architecture's complexity and cost.
