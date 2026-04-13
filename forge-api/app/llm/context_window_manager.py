"""Context Window Manager (ADR-3, T-045)

Manages multi-turn conversation context within a token budget using
hybrid pinning: pin recent tool results + sliding window for conversation.

Strategy:
1. System prompt is always kept (never trimmed)
2. Last N tool_result messages are pinned (never trimmed)
3. Most recent messages kept up to budget (sliding window)
4. At 80% budget, inject a warning note
"""

from __future__ import annotations

import logging
from typing import Any

from _future.llm.provider import Message

logger = logging.getLogger(__name__)

# Defaults (configurable via session_manager or config)
DEFAULT_TOKEN_BUDGET = 30_000
DEFAULT_PIN_TOOL_RESULTS = 5
DEFAULT_SUMMARY_INTERVAL = 10
CHARS_PER_TOKEN = 4  # Simple heuristic: 1 token ≈ 4 chars
BUDGET_WARNING_THRESHOLD = 0.80


def estimate_tokens(text: str) -> int:
    """Estimate token count using chars/4 heuristic."""
    return max(1, len(text) // CHARS_PER_TOKEN)


def message_tokens(msg: Message) -> int:
    """Estimate tokens for a single message (content + role overhead)."""
    content = msg.content or ""
    # Tool results may be dicts
    if isinstance(content, dict):
        import json
        content = json.dumps(content, ensure_ascii=False)
    elif isinstance(content, list):
        import json
        content = json.dumps(content, ensure_ascii=False)
    overhead = 4  # role + framing tokens
    return estimate_tokens(str(content)) + overhead


def total_tokens(messages: list[Message]) -> int:
    """Estimate total tokens across all messages."""
    return sum(message_tokens(m) for m in messages)


def trim_history(
    messages: list[Message],
    budget_tokens: int = DEFAULT_TOKEN_BUDGET,
    pin_count: int = DEFAULT_PIN_TOOL_RESULTS,
    summary_interval: int = DEFAULT_SUMMARY_INTERVAL,
) -> list[Message]:
    """Trim conversation history to fit within token budget.

    Strategy:
    1. System messages (role=system) are always kept at the front.
    2. The last user message is always kept.
    3. Last `pin_count` tool result messages are pinned.
    4. Remaining messages are kept newest-first until budget is met.
    5. At 80% budget, a system note is injected.

    Args:
        messages: Full conversation history.
        budget_tokens: Maximum token budget for the returned messages.
        pin_count: Number of recent tool_result messages to pin.
        summary_interval: Not used currently (reserved for future summary injection).

    Returns:
        Trimmed list of messages that fits within budget.
    """
    if not messages:
        return messages

    current_total = total_tokens(messages)
    if current_total <= budget_tokens:
        # Under budget — check if we need a warning
        if current_total > budget_tokens * BUDGET_WARNING_THRESHOLD:
            return _inject_budget_warning(messages, current_total, budget_tokens)
        return messages

    # Separate system messages (always kept at front)
    system_msgs: list[Message] = []
    other_msgs: list[Message] = []
    for msg in messages:
        if msg.role == "system":
            system_msgs.append(msg)
        else:
            other_msgs.append(msg)

    if not other_msgs:
        return messages

    # Always keep the last user message
    last_user_idx = None
    for i in range(len(other_msgs) - 1, -1, -1):
        if other_msgs[i].role == "user":
            last_user_idx = i
            break

    # Find and pin last N tool_result messages
    pinned_indices: set[int] = set()
    tool_result_count = 0
    for i in range(len(other_msgs) - 1, -1, -1):
        if other_msgs[i].role == "tool" and tool_result_count < pin_count:
            pinned_indices.add(i)
            tool_result_count += 1

    # Also pin the last user message
    if last_user_idx is not None:
        pinned_indices.add(last_user_idx)

    # Calculate budget used by system + pinned messages
    system_tokens = sum(message_tokens(m) for m in system_msgs)
    pinned_tokens = sum(message_tokens(other_msgs[i]) for i in pinned_indices)
    remaining_budget = budget_tokens - system_tokens - pinned_tokens

    if remaining_budget <= 0:
        # Even pinned messages exceed budget — keep only system + last user + minimal pinned
        result = system_msgs[:]
        if last_user_idx is not None:
            result.append(other_msgs[last_user_idx])
        return result

    # Fill remaining budget newest-first (excluding pinned — they're already counted)
    kept_indices: set[int] = set(pinned_indices)
    used_tokens = 0
    for i in range(len(other_msgs) - 1, -1, -1):
        if i in kept_indices:
            continue
        msg_tok = message_tokens(other_msgs[i])
        if used_tokens + msg_tok <= remaining_budget:
            kept_indices.add(i)
            used_tokens += msg_tok
        # else: skip this message (trimmed)

    # Build result maintaining original order
    trimmed_other = [other_msgs[i] for i in sorted(kept_indices)]
    result = system_msgs + trimmed_other

    # Add budget warning
    final_total = total_tokens(result)
    if final_total > budget_tokens * BUDGET_WARNING_THRESHOLD:
        result = _inject_budget_warning(result, final_total, budget_tokens)

    trimmed_count = len(messages) - len(result)
    if trimmed_count > 0:
        logger.info(
            "Trimmed %d messages. Before: ~%d tokens, after: ~%d tokens (budget: %d)",
            trimmed_count, current_total, total_tokens(result), budget_tokens,
        )

    return result


def _inject_budget_warning(
    messages: list[Message],
    current_tokens: int,
    budget_tokens: int,
) -> list[Message]:
    """Inject a system note about nearing the token budget."""
    pct = int(current_tokens / budget_tokens * 100)
    warning = Message(
        role="system",
        content=(
            f"[Context window at {pct}% capacity ({current_tokens}/{budget_tokens} tokens). "
            f"Consider starting a new session for complex follow-up tasks.]"
        ),
    )
    # Insert before the last message
    result = list(messages)
    if len(result) > 1:
        result.insert(-1, warning)
    else:
        result.append(warning)
    return result


def get_token_stats(messages: list[Message], budget: int = DEFAULT_TOKEN_BUDGET) -> dict[str, Any]:
    """Get token usage statistics for a conversation."""
    current = total_tokens(messages)
    return {
        "current_tokens": current,
        "budget_tokens": budget,
        "usage_pct": round(current / budget * 100, 1) if budget > 0 else 0,
        "remaining_tokens": max(0, budget - current),
        "message_count": len(messages),
    }
