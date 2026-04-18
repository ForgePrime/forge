"""Crafter (E1) — two-stage prompt mode.

Flow:
  1. Parser builds a *seed* prompt (usual enriched prompt).
  2. Crafter LLM reads the seed + inspects KB sources and code snippets → writes a detailed,
     context-specific executor prompt.
  3. Executor LLM runs the crafted prompt.

Cost: ~+40-80% of direct. Quality: measurably higher on complex tasks with heavy KB context.
Use crafted mode when task touches >3 files, has crossreferenced KB, or is flagged high-risk.
"""
import json
from dataclasses import dataclass

from app.services.claude_cli import invoke_claude, CLIResult


CRAFTER_SYSTEM_PROMPT = """You are the Forge CRAFTER. Your job is NOT to solve the task.
Your job is to write a detailed, specific executor prompt that will enable another LLM
(the executor) to solve the task with highest quality.

Rules:
- Read the seed prompt below carefully.
- Inspect any file/code references mentioned in the seed (you have tool access).
- Identify ambiguities, missing constraints, or edge cases the seed does not handle.
- Produce an EXECUTOR PROMPT that:
    * states the outcome explicitly
    * lists concrete files/paths to modify
    * enumerates edge cases to handle
    * mentions what the executor MUST NOT do (anti-patterns from project contract)
    * ends with: "NOT_CHECKED:" section listing what you were not able to verify yourself

Output format: a single markdown block, plain text, no JSON wrapper.

## Seed prompt follows:

{seed}
"""


@dataclass
class CraftResult:
    executor_prompt: str
    crafter_call: CLIResult
    not_checked: list[str]


def craft_executor_prompt(
    *, seed_prompt: str, workspace_dir: str, model: str = "opus",
    api_key: str | None = None, max_budget_usd: float = 2.0, timeout_sec: int = 300,
) -> CraftResult:
    """Run the crafter and return the executor prompt it wrote."""
    crafter_prompt = CRAFTER_SYSTEM_PROMPT.format(seed=seed_prompt)
    cli = invoke_claude(
        prompt=crafter_prompt, workspace_dir=workspace_dir, model=model,
        max_budget_usd=max_budget_usd, timeout_sec=timeout_sec, api_key=api_key,
    )
    text = (cli.agent_response or "").strip()
    # Extract NOT_CHECKED section
    import re
    m = re.search(r"\n+NOT[_ ]CHECKED:\s*\n(.*?)\s*\Z", text, re.DOTALL | re.IGNORECASE)
    not_checked: list[str] = []
    executor_prompt = text
    if m:
        bullets_raw = m.group(1)
        executor_prompt = text[: m.start()].strip()
        for line in bullets_raw.splitlines():
            line = line.strip()
            line = re.sub(r"^[-*•\d.)]\s*", "", line).strip()
            if line:
                not_checked.append(line)
    return CraftResult(
        executor_prompt=executor_prompt or text,
        crafter_call=cli,
        not_checked=not_checked,
    )
