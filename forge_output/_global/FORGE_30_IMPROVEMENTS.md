# Forge — 30 significant improvements

Organized by dimension. Each: **what**, **why it matters** (grounded in per-objective iterative flow), and **what it prevents**.

Design lens throughout: Forge is skeptical, not reassuring. Every improvement either (a) makes the LLM genuinely better, (b) gives the user *more* doubt (faster audit), or (c) earns autonomy through evidence — never by vibe.

---

## A. Context and awareness — the LLM must know where it is

### 1. Page-level AI context (from forge-web pattern)
Every screen self-describes to the LLM: page id, current entity (objective / task), visible data, available actions. Injected automatically when user chats.
**Why:** LLM today starts cold each turn. With page context, it answers "I see T-005 has 3 open AC and 2 failing tests — which should I triage?" instead of "please share the task details". Removes the coldstart tax, makes asking for help trivially cheap.
**Prevents:** user re-explaining the situation 5 times per session.

### 2. Objective-level compressed memory
Per-objective rolling summary (~500 tokens): decisions taken, rationale, resolved ambiguities, hard constraints. Injected into every LLM call for that objective.
**Why:** Iterations lose context. When re-analysis fires with new user answers, new run needs to know "we already decided on-prem, Django, PostgreSQL". Compression forces the model to decide what matters.
**Prevents:** LLM silently re-opening settled decisions ("should we consider AWS?") because old reasoning fell out of context.

### 3. Recent user-action trail (LLM-visible)
LLM sees last ~20 user actions: "resolved Q-007 with option A", "added AC-3", "re-ran challenger with security scope". Included as implicit context.
**Why:** The user's history IS the context. LLM shouldn't ask "did you resolve the auth question?" if the user did 3 minutes ago. Feeling-of-awareness is a usability multiplier.
**Prevents:** LLM asking questions it should know the answer to → user frustration.

### 4. `@entity` mentions in chat
User types `@T-005` or `@Q-007`, LLM inlines the entity. Works across all entity types (SRC, O, T, Q, AC, KR, skill IDs).
**Why:** Natural language reference. No copy-paste. Same mechanism LLM uses internally when citing sources.
**Prevents:** bulky copy-paste-the-task-description pattern.

### 5. Conflict-aware retrieval before answering
Before LLM answers any question, a cheap scan checks: does this answer contradict resolved decisions or hard constraints? If yes, flag.
**Why:** Eliminates "confident wrong" where LLM suggests S3 despite SRC-004 on-prem constraint. Catches drift early.
**Prevents:** user catching the contradiction 3 hours later in code review.

---

## B. Interaction & feedback — bi-directional, not one-shot

### 6. Slash commands globally
`/find-ambiguity`, `/write-adr`, `/generate-scenarios`, `/run-skill foo`, `/replay T-005 with current skills`. Each invokes a skill or primitive.
**Why:** Power users progress 5x faster. Same commands from forge-web but project-wide.
**Prevents:** 7-click navigation to do common operations.

### 7. "Why did you write that?" inline button
Every LLM-generated artifact (AC, task, finding, ADR section) has a tiny `?` — shows reasoning trace: which SRCs read, which decisions considered, what was rejected.
**Why:** Skeptical UX as default. User audits without asking. Reduces trust-by-vibe.
**Prevents:** silent acceptance of hallucinated claims.

### 8. Stream the LLM's work in real time
SSE (not polling). User sees Claude reading files, running tools, drafting output as it happens.
**Why:** 60-90s cisza = anxiety + lost redirect opportunity. Watching LLM work is cheap and calming.
**Prevents:** "is it frozen?" × 10 per session.

### 9. Interrupt + redirect mid-run
"Wait — focus on migration rollback, not new endpoints." LLM stops, incorporates redirection, continues.
**Why:** LLM going wrong direction at t=10s wastes $0.40 if you wait until t=90s. Interrupt = partial-refund.
**Prevents:** expensive re-runs because you couldn't stop in time.

### 10. "Plan before executing" toggle on every action
Every Run / Plan / Execute button has a "Plan first" mode. LLM outputs steps it *would* take; user approves or edits before real work.
**Why:** Especially for crafted-mode ($0.50+). Catches bad prompts before you pay.
**Prevents:** "oh that's not what I meant" after spending $1.

### 11. Suggestion chips contextual to current screen
On objective page: "Generate non-happy-path scenarios", "Find missing KR", "Compare with similar objective in O-001". Specific, actionable.
**Why:** Discoverability. User doesn't know what Forge can do until shown.
**Prevents:** underused platform features.

---

## C. Trust & verification — every claim has scope and source

### 12. Source attribution mandatory on all LLM output
Every AC, decision resolution, description paragraph MUST cite SRC-xxx / O-xxx / DEC-xxx. If none possible → badge "invented by LLM" shown prominently, user must accept or remove.
**Why:** Forces LLM to ground claims. User sees what's synthesized vs hallucinated.
**Prevents:** silent fabrication that only shows in code review.

### 13. Scope-limit disclosure in every summary
Every LLM summary ends with "what I did NOT check". Not optional; mechanically enforced in prompt + post-check.
**Why:** Kills "sounds confident → must be right". Turns known-unknowns into visible queue.
**Prevents:** overtrust; bridges the trust-debt dashboard.

### 14. Adversarial self-challenge skill
After any artifact is produced, a skill generates 3 challenging questions user should ask about it. Surfaced on the deliverable.
**Why:** Counter sycophancy. LLM tries to break its own work — often catches things challenger doesn't.
**Prevents:** user approving without asking the obvious questions.

### 15. Cross-family challenger rotation
Don't always use Claude Opus as challenger. Rotate: Opus, GPT-4, Gemini, local Qwen. Track agreement rates per family pair.
**Why:** Claude↔Claude agreement has lower signal than Claude↔non-Claude. Diversity catches blind spots in the Claude family.
**Prevents:** echo-chamber verification.

### 16. "Run 3× and diff" for critical tasks
For high-risk objectives (auth, billing, data migration), run same prompt 3 times. Surface divergence. If divergent → user reviews.
**Why:** LLMs are non-deterministic. Triangulation catches fragile answers.
**Prevents:** single-sample bias on high-blast-radius code.

### 17. Replay harness
Every LLM call's (prompt, response, skills-attached, contract-version) stored immutably. User clicks "replay" on any historical task — runs again with *today's* config.
**Why:** Regression testing of the platform itself. Did new skills improve quality? Replay archived tasks and compare.
**Prevents:** blind platform evolution — no way to know if changes helped.

### 18. Reverse-trace UI (bug → SOW paragraph)
From a deployed bug, trace backward: which code? which task? which objective? which prompt element? which SRC? which user answer?
**Why:** Post-mortem without archaeology. Blast radius and authorship of bad decisions visible in one click.
**Prevents:** "why did we build it this way?" unanswerable 3 months later.

---

## D. Autonomization — earned, not granted

### 19. Autonomy levels L1–L5 with mechanical promotion criteria
L1 assistant → L5 autonomous. Promotion requires: N clean runs without user override, audit queue empty, no violated hard constraints for N days.
**Why:** Trust is earned. Not a toggle; not arbitrary. User sees exactly what unlocks next level.
**Prevents:** premature autonomy → silent quality regression.

### 20. Per-objective watchlist (opt-out of autonomy)
User marks critical objectives "I personally review every stage". L3+ autonomy skips these.
**Why:** Partial autonomy. Not all objectives equal. User keeps hands-on for high-stakes.
**Prevents:** autonomous Forge shipping HIPAA-touching code without human.

### 21. Autonomy budget cap
Each level has spend cap per day. L5 = max $20/day without asking. Exceed → ask.
**Why:** Runaway cost in autonomy = biggest fear. Cap = insurance.
**Prevents:** 2am surprise bill.

### 22. Veto clauses — autonomy stopwords
Autonomous Forge stops on: conflict with MUST-constraint, budget 80%, deliverable touching flagged files (billing, migrations/prod), any resolved-decision reversal.
**Why:** Autonomy never overrides deliberate constraints. Hard-coded rules.
**Prevents:** "L5 autonomous agent reverts my architecture decision".

### 23. Digest mode for autonomous runs
Don't ping per event. Daily digest: "24 tasks DONE, 2 re-opens, 3 decisions resolved by Forge using contract, $18 spent".
**Why:** Autonomy's value eaten if you get 200 notifications. Digest = trust without noise.
**Prevents:** notification fatigue → user disables all alerts → silent failures.

---

## E. Knowledge and memory — project gets smarter over time

### 24. Lessons log per objective
After each ACHIEVED objective, a skill extracts 3-5 lessons (what worked, what didn't, why). Stored in project KB. Injected into future objectives' analysis phase.
**Why:** Project learns. Amnesia → re-making same mistakes.
**Prevents:** "we already tried this in O-001 and it failed" unnoticed in O-005.

### 25. Anti-pattern registry
When re-open happens, LLM captures "what was wrong with first attempt". Stored as negative example. Next planning phase sees it.
**Why:** Concrete "don't" examples beat abstract guidelines. LLMs learn faster from negatives.
**Prevents:** same bad pattern appearing in sibling objectives.

### 26. Skill effectiveness scoring
Per skill: cost spent, issues caught, issues missed, user overrides. Rank by ROI. Low-ROI skills surfaced for pruning.
**Why:** Skill bloat kills both cost and quality. Data-driven pruning.
**Prevents:** 50-skill bloat where half never fire.

### 27. Cross-project pattern library (org-level marketplace)
Patterns that worked across ≥3 projects get promoted to org marketplace. Other projects' users see "this skill worked for 7 projects with 85% success".
**Why:** Consultancy scales via reuse. Also: peer-reviewed skills > one-off customs.
**Prevents:** 12 variants of "security review" per project, each half-baked.

---

## F. Economy — cost is a first-class citizen

### 28. Cost pre-flight before any LLM call
Before invoking, show estimate + breakdown: base prompt (420t), skills (1200t), KB references (800t), expected output (1500t) = ~$0.18. User can trim inline.
**Why:** Surprise-bill prevention. Transparent tradeoff. User learns which skills cost what.
**Prevents:** $5 unexpected bill on a "quick" planning task.

### 29. Cost forensic drill-down per task
Per task: which phase cost most? How many retries? Context growth across retries? Root cause?
**Why:** "T-007 cost 45% of run" needs explanation. Without it, user can't improve.
**Prevents:** silent cost creep — small waste × 100 tasks = big waste.

### 30. Mid-run budget trajectory forecast
During orchestrate: "current pace projects $24/$20 remaining — consider pausing".
**Why:** Budget enforcement after-the-fact (hard cap) is too late. Forecast = early warning.
**Prevents:** mid-run BUDGET_EXCEEDED with partial work done.

---

## Things Forge should NOT do (anti-list)

- Auto-dismiss findings without user reason
- Hide scope limits of challenger
- Pre-fill user answers without marking "unedited" badge
- Auto-merge DONE → release without explicit user act
- Silently truncate KB context to fit budget (must warn)
- Allow `--no-verify` / `--force` without audit log entry
- Present green metrics without paired "but didn't check X"
- Let ACHIEVED objective go read-only (always re-openable)
- Default to "Approve" as primary button

---

## What this means for mockup roadmap

The 30 items above imply 6 mockup updates / new screens:

1. **AI sidebar + page context** (applied across all screens, like forge-web)
2. **Reverse-trace UI** (bug → SOW)
3. **Cost forensic drill-down + mid-run forecast**
4. **Anti-pattern registry / replay harness**
5. **Autonomy dashboard** (levels, promotion criteria, stopwords)
6. **Lessons log / skill-ROI leaderboard**

All consistent with the skeptical design contract and the per-objective iterative flow.
