"""EventBus — Redis Pub/Sub based event system for real-time updates."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis


# All defined event types (Section 8.2)
EVENT_TYPES = {
    "task.status_changed",
    "task.progress",
    "decision.created",
    "decision.closed",
    "knowledge.updated",
    "knowledge.impact",
    "change.recorded",
    "gate.result",
    "execution.output",
    "ai.suggestion",
    "debug.session",
    "idea.status_changed",
    "skill.created",
    "skill.updated",
    "skill.deleted",
    "skill.promoted",
}


def _channel(slug: str) -> str:
    """Redis Pub/Sub channel name for a project."""
    return f"forge:events:{slug}"


class EventBus:
    """Publish events via Redis Pub/Sub for consumption by WebSocket clients."""

    def __init__(self, redis: aioredis.Redis):
        self._redis = redis

    async def emit(self, slug: str, event_type: str, payload: dict[str, Any]) -> int:
        """Publish an event to the project's channel.

        Returns the number of subscribers that received the message.
        """
        if event_type not in EVENT_TYPES:
            raise ValueError(f"Unknown event type: {event_type}")
        message = {
            "event": event_type,
            "project": slug,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        return await self._redis.publish(_channel(slug), json.dumps(message))

    async def subscribe(self, slug: str) -> aioredis.client.PubSub:
        """Return a PubSub subscription for a project's event channel."""
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(_channel(slug))
        return pubsub
