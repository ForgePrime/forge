"""LLM Session Manager — chat conversation persistence in Redis.

Each conversation is a session with message history, token tracking,
cost estimation, and a 24h TTL. Events are emitted on lifecycle changes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Per-session locks for concurrent access protection
_session_locks: dict[str, asyncio.Lock] = {}

SESSION_TTL_SECONDS = 24 * 60 * 60  # 24 hours
SESSION_KEY_PREFIX = "chat:session:"
SESSION_INDEX_KEY = "chat:sessions"


@dataclass
class ChatMessage:
    """A single message in a chat session."""

    id: str = ""
    role: str = ""            # "user" | "assistant" | "system" | "tool"
    content: str = ""
    tool_calls: list[dict] | None = None
    tool_results: list[dict] | None = None
    tokens_used: int = 0
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"msg-{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class ChatSession:
    """A chat session with message history and token tracking."""

    session_id: str = ""
    context_type: str = ""    # "skill" | "task" | "global" | etc.
    context_id: str = ""      # Entity ID (e.g., SK-001)
    project: str = ""         # Project slug (if project-scoped)
    messages: list[ChatMessage] = field(default_factory=list)
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    estimated_cost: float = 0.0
    model_used: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = f"sess-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for Redis storage."""
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChatSession | None:
        """Deserialize from Redis-stored dict. Returns None on malformed data."""
        try:
            messages_raw = data.pop("messages", [])
            messages = [ChatMessage(**m) for m in messages_raw if isinstance(m, dict)]
            return cls(messages=messages, **data)
        except (TypeError, KeyError) as e:
            logger.warning("Failed to deserialize ChatSession: %s", e)
            return None


class SessionManager:
    """Manages chat sessions in Redis with TTL and event emission.

    Sessions are stored as JSON in Redis with a 24h TTL.
    A session index set tracks all active session IDs.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        event_bus: Any | None = None,
    ) -> None:
        self._redis = redis_client
        self._event_bus = event_bus

    def _key(self, session_id: str) -> str:
        """Build Redis key for a session."""
        return f"{SESSION_KEY_PREFIX}{session_id}"

    @staticmethod
    def _get_lock(session_id: str) -> asyncio.Lock:
        """Get or create a per-session asyncio lock."""
        return _session_locks.setdefault(session_id, asyncio.Lock())

    async def create(
        self,
        context_type: str = "global",
        context_id: str = "",
        project: str = "",
        model: str = "",
    ) -> ChatSession:
        """Create a new chat session.

        Args:
            context_type: Entity context type.
            context_id: Entity ID.
            project: Project slug.
            model: Model identifier.

        Returns:
            The created ChatSession.
        """
        session = ChatSession(
            context_type=context_type,
            context_id=context_id,
            project=project,
            model_used=model,
        )

        await self._save(session)

        # Track in index
        await self._redis.sadd(SESSION_INDEX_KEY, session.session_id)

        # Emit event
        if self._event_bus:
            slug = project or "_global"
            try:
                await self._event_bus.emit(slug, "llm.session_started", {
                    "session_id": session.session_id,
                    "context_type": context_type,
                    "context_id": context_id,
                    "model": model,
                })
            except Exception:
                pass  # Don't fail session creation on event error

        return session

    async def load(self, session_id: str) -> ChatSession | None:
        """Load a session from Redis.

        Returns None if session expired or not found.
        """
        raw = await self._redis.get(self._key(session_id))
        if raw is None:
            # Clean up index if session expired
            await self._redis.srem(SESSION_INDEX_KEY, session_id)
            return None
        return ChatSession.from_dict(json.loads(raw))

    async def _save(self, session: ChatSession) -> None:
        """Save session to Redis with TTL."""
        session.updated_at = datetime.now(timezone.utc).isoformat()
        await self._redis.setex(
            self._key(session.session_id),
            SESSION_TTL_SECONDS,
            json.dumps(session.to_dict()),
        )

    async def save(self, session: ChatSession) -> None:
        """Save session (public interface)."""
        await self._save(session)

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: list[dict] | None = None,
        tool_results: list[dict] | None = None,
        tokens_used: int = 0,
        is_input: bool = True,
    ) -> ChatMessage | None:
        """Add a message to a session and update token counters.

        Args:
            session_id: Session to add to.
            role: Message role.
            content: Message content.
            tool_calls: Optional tool call data.
            tool_results: Optional tool result data.
            tokens_used: Tokens consumed by this message.
            is_input: True if input tokens, False if output tokens.

        Returns:
            The created ChatMessage, or None if session not found.
        """
        session = await self.load(session_id)
        if session is None:
            return None

        message = ChatMessage(
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_results=tool_results,
            tokens_used=tokens_used,
        )
        session.messages.append(message)

        # Update token counters
        if is_input:
            session.total_tokens_in += tokens_used
        else:
            session.total_tokens_out += tokens_used

        await self._save(session)
        return message

    async def update_tokens(
        self,
        session_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_per_1k_input: float = 0.0,
        cost_per_1k_output: float = 0.0,
    ) -> None:
        """Update token counters and cost estimation for a session.

        Args:
            session_id: Session to update.
            input_tokens: Input tokens to add.
            output_tokens: Output tokens to add.
            cost_per_1k_input: Cost per 1K input tokens (USD).
            cost_per_1k_output: Cost per 1K output tokens (USD).
        """
        session = await self.load(session_id)
        if session is None:
            return

        session.total_tokens_in += input_tokens
        session.total_tokens_out += output_tokens
        session.estimated_cost += (
            (input_tokens / 1000) * cost_per_1k_input
            + (output_tokens / 1000) * cost_per_1k_output
        )
        await self._save(session)

    async def delete(self, session_id: str) -> bool:
        """Delete a session from Redis.

        Returns True if deleted, False if not found.
        """
        key = self._key(session_id)
        deleted = await self._redis.delete(key)
        await self._redis.srem(SESSION_INDEX_KEY, session_id)

        if self._event_bus and deleted:
            try:
                await self._event_bus.emit("_global", "llm.session_ended", {
                    "session_id": session_id,
                })
            except Exception:
                pass

        return bool(deleted)

    async def list_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        """List active sessions (summary only, no full message history).

        Returns list of session summaries sorted by updated_at desc.
        """
        session_ids = await self._redis.smembers(SESSION_INDEX_KEY)
        summaries = []

        for sid in session_ids:
            raw = await self._redis.get(self._key(sid))
            if raw is None:
                # Expired — clean up index
                await self._redis.srem(SESSION_INDEX_KEY, sid)
                continue
            data = json.loads(raw)
            summaries.append({
                "session_id": data.get("session_id"),
                "context_type": data.get("context_type"),
                "context_id": data.get("context_id"),
                "project": data.get("project"),
                "model_used": data.get("model_used"),
                "message_count": len(data.get("messages", [])),
                "total_tokens_in": data.get("total_tokens_in", 0),
                "total_tokens_out": data.get("total_tokens_out", 0),
                "estimated_cost": data.get("estimated_cost", 0.0),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
            })

        # Sort by updated_at descending
        summaries.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return summaries[:limit]
