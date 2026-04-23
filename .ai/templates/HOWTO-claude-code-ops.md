---
name: claude-code-ops
description: KIEDY: konfigurujesz .claude/ (hooki, skille, CLAUDE.md) lub audytujesz MCP/skill overhead. Cztery wzorce: MCP vs CLI, docs index, HARD-GATE, hook wiring.
argument-hint: "[mcp-audit | docs-index | hard-gate | hook-wiring]"
disable-model-invocation: true
---

# Claude Code — Execution-Layer Patterns

> Operational patterns for `.claude/` and agent workflow in ITRP.
> Source: `.ai/compass_artifact.md` (survey of 2025–2026 practice, spot-checked against Vercel/Anthropic/Cognition primary sources).
> Scope: Claude Code tool-level patterns. Out of scope: CGAID framework policy (`.ai/framework/`).

---

## 1. MCP vs CLI — prefer CLI, audit MCP quarterly

**Rule.** Reach for `gh`, `gcloud`, `bq`, `gsutil` before any MCP wrapper of the same capability.

**Why.** Measured token burn from MCP tool definitions: 81k–98k tokens consumed *before the first prompt* with 5+ MCPs active; single MCP (Task Master) = 63.7k tokens / 59 tool defs. LLMs already know `<tool> --help` — MCP is duplicate schema weight in every context window.

**Audit (quarterly).**

1. `claude mcp list` (or `/mcp`) — count active servers.
2. For each: identify the CLI equivalent. Remove MCP if CLI exists and is callable from Bash tool.
3. Keep only MCPs with no viable CLI (e.g., browser automation, proprietary internal systems).

**ITRP-specific.** For GCP work default to `gcloud`, `gsutil`, `bq`, `gh` — all already available via Bash. MCP layer is justified only where CLI does not exist.

**Anti-pattern.** Adding an MCP "because it's available" without auditing token cost. One idle MCP at 10k tokens × every session = permanent context tax.

---

## 2. CLAUDE.md as docs index — passive context > active skills for always-on rules

**Rule.** Always-on rules (session protocol, coding standards pointer, file index) live in `.claude/CLAUDE.md` as *passive* context — loaded every session, no invocation needed. Workflow skills (`/analyze`, `/deep-*`, `/plan`, `/develop`) remain user-invokable.

**Why.** Vercel Next.js 16 eval: a skill carrying documentation was invoked 44% of the time; the agent never invoked it in 56% of cases. The same ~8KB docs index embedded directly in AGENTS.md reached **100%** baseline compliance. Explicit "use the skill" instructions maxed at 79%. Skills that *may* be invoked are not a reliable substitute for context that *is* loaded.

**Pattern.**

- Target ≤60 lines for `.claude/CLAUDE.md`. Current ITRP file = 43 lines, within budget.
- Structure: session-start protocol → mandatory files → contextual files → framework files (read-on-explicit-request).
- **Pointers only, no prose.** Full content lives in `.ai/*.md`. CLAUDE.md is an index, not a book.

**What stays passive (in CLAUDE.md):** session-start contract reference, reference-file index, always-applicable constraints.
**What stays active (as skills):** multi-step workflows the user explicitly triggers.

**Anti-pattern.** Running `/init` and accepting the auto-generated CLAUDE.md. LLM-generated CLAUDE.md measurably degrades agent performance (Zazencodes benchmark). Write by hand. Treat CLAUDE.md edits as ADRs — reviewable.

---

## 3. HARD-GATE in skills — advisory language gets rationalized away

**Rule.** Skills with enforcement intent use a `<HARD-GATE>` block with negative constraints. Polite verbs ("present", "consider", "prefer") get rationalized away under pressure.

**Why.** Superpowers v4.3.0 documented the failure mode directly: advisory skill prose was ignored by the model when it "decided" the task was simple. Adding a `<HARD-GATE>` block with explicit prohibitions + stop condition restored compliance. Prose that reads like guidance gets treated as guidance; prose that reads like a gate gets treated as a gate.

**Block template.**

```
<HARD-GATE name="<gate-id>">
Do NOT <action list>
until <prerequisite artifact> exists AND contains <required marker>.
Violation = abandon task and request human review.
</HARD-GATE>
```

**Red-flag table (paste into the skill).**

| Rationalization Claude may produce | Stock reply |
|---|---|
| "This is a simple task, skill is overkill" | Skills tell you HOW. Check first. |
| "I need more context before gating" | Context does not relax the gate. Gate first, context after. |
| "The user probably meant to skip this" | If unspecified, the gate applies. Ask, don't infer. |

**Pair with a hook.** Every `<HARD-GATE>` with enforcement intent should have a matching `PreToolUse` hook (see §4) that `grep`s for the required marker in the prerequisite artifact. Prose + hook = two-layer enforcement. Prose alone = 70–90% compliance, not a gate.

**Where to apply in ITRP skills.**

- `guard` — already standards-oriented; add HARD-GATE for "no Edit/Write on `.py`/`.ts` until standards-check.sh has been run in this session."
- `develop` — gate on presence of accepted plan artifact before first Write.
- Any new skill whose description contains "must be invoked before" or "required before".

---

## 4. Hook wiring — exit code 2 is the only real enforcement mechanism

**Rule.** Deterministic enforcement (lint, type check, forbidden patterns, prod deny-list) goes into `.claude/hooks/*.sh` and is wired via `.claude/settings.json`. Exit `0` = allow; exit `2` = **block**; exit `1` is non-blocking (Claude Code treats it as "proceed anyway").

**Why.** Field reports: prompt-based rules = 70–90% compliance. Hooks with exit `2` = 100%. The gap between "usually" and "always" is where production incidents happen. CLAUDE.md saying "always run the linter" is *advice*; a PostToolUse hook running it is *guarantee*.

**Current ITRP state (2026-04-22 snapshot).**

- `.claude/hooks/standards-check.sh` **exists** (4KB) — checks router→DB access, `except Exception: pass`, undefined `logger`, `Any` in type hints, pipeline↔backend cross-imports.
- `.claude/settings.json` **does not exist** → hook file is probably not registered → enforcement theatre risk.

**Verify the hook is running (30-min test).**

1. Create `/tmp/test_hook.py` containing:
   ```python
   def f():
       try:
           do_it()
       except Exception:
           pass
   ```
2. Open/edit that file via Claude Code's Edit tool.
3. Expected: `⛔ STANDARDS VIOLATION: 'except Exception: pass' found` on stderr.
4. If silent → hook is not wired. Create `settings.json` (template below).

**Wiring template — `.claude/settings.json`.**

[ASSUMED] schema verified against Claude Code public docs current at time of writing; re-verify against installed CC version before committing.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/standards-check.sh" }
        ]
      }
    ]
  }
}
```

**Exit code contract (do not confuse).**

| Exit | Meaning in Claude Code | Use for |
|---|---|---|
| `0` | Allow; stderr shown as warnings | Soft advice, style hints |
| `1` | **Non-blocking error** ("proceed anyway") | Do not use — creates false sense of enforcement |
| `2` | **Block**; stderr returned to Claude as error context for self-correction | Hard standards violations, prod deny-list |

**What belongs in hooks.** Deterministic checks: `ruff`, `tsc --noEmit`, `grep` for forbidden patterns, path-based deny-list (`terraform/prod/`, `.env*`, `secrets/`), command deny-list (`bq rm`, `DROP TABLE`, `--no-verify`, `gcloud ... --project=<prod>`).

**What does NOT belong in hooks.** LLM-shaped judgments: "is this code clean", "does this architecture match the plan", semantic correctness. That work stays in skills. *"Claude is not an expensive linter"* — move deterministic checks out of the LLM.

**Subagent coverage.** A `SubagentStop` hook applies to sub-agent sessions automatically. Without it, a delegated sub-agent can "finish" with broken tests or skipped standards. For any hook that encodes a rule the parent owns (per CONTRACT.md B§Subagent delegation), add a matching `SubagentStop` entry.

**Anti-pattern: `allowUnsandboxedCommands: true`.** Default is true, which means Claude can retry a blocked command outside the sandbox. Explicit deny-list entries for `git commit -n`, `--no-verify`, and any bypass pattern. Otherwise the hook can be walked around.

---

## References

- `.ai/compass_artifact.md` — full survey with source citations.
- Vercel, *AGENTS.md outperforms skills in our agent evals*: https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals
- Anthropic, *How we built our multi-agent research system*: https://www.anthropic.com/engineering/multi-agent-research-system
- obra/superpowers — HARD-GATE pattern origin: https://github.com/obra/superpowers
- Claude Code hooks documentation — verify current schema for `settings.json` before wiring.

## Relationship to CGAID

These are **execution-layer** patterns (Claude Code tool usage). They do **not** belong in `.ai/framework/` — CGAID is tool-agnostic governance. Patterns that prove themselves here may later inform OPERATING_MODEL §4.4 (enforceability) or §7 (rigor tiers), but only after empirical validation in ITRP practice.
