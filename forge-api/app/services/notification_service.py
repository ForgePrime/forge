"""NotificationService — intercepts forge events and generates notification records."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.routers._helpers import _get_lock, load_entity, next_id, save_entity

logger = logging.getLogger(__name__)

# Dedup window in seconds
DEDUP_WINDOW = 5.0

# ---------------------------------------------------------------------------
# Event-to-notification mapping
# ---------------------------------------------------------------------------

# Each entry: (notification_type, priority, title_template)
# title_template uses {payload_key} placeholders
_EVENT_MAP: dict[str, tuple[str, str, str]] = {
    "decision.created": (
        "decision",
        "_dynamic",  # priority determined by decision type/risk
        "New decision: {issue}",
    ),
    "decision.closed": (
        "decision",
        "low",
        "Decision resolved: {decision_id}",
    ),
    "chat.error": (
        "alert",
        "high",
        "Chat error: {error}",
    ),
    "task.status_changed": (
        "alert",
        "_dynamic",  # depends on new_status
        "Task {task_id}: {new_status}",
    ),
    "gate.result": (
        "alert",
        "_dynamic",  # depends on pass/fail
        "Gate {gate_name}: {result}",
    ),
    "workflow.paused": (
        "question",
        "high",
        "Workflow paused: {reason}",
    ),
    "workflow.failed": (
        "alert",
        "critical",
        "Workflow failed: {reason}",
    ),
    "workflow.completed": (
        "alert",
        "low",
        "Workflow completed",
    ),
}


def _resolve_priority(event_type: str, payload: dict[str, Any]) -> str:
    """Determine notification priority from event payload."""
    if event_type == "decision.created":
        dtype = payload.get("type", "")
        if dtype == "risk":
            severity = payload.get("severity", "").upper()
            if severity in ("CRITICAL", "HIGH"):
                return "critical"
            return "high"
        status = payload.get("status", "OPEN")
        if status == "OPEN":
            return "normal"
        return "low"

    if event_type == "task.status_changed":
        new_status = payload.get("new_status", "")
        if new_status == "FAILED":
            return "high"
        if new_status == "DONE":
            return "low"
        return "normal"

    if event_type == "gate.result":
        result = payload.get("result", "")
        if result in ("FAIL", "fail", "failed"):
            return "high"
        return "low"

    return "normal"


def _format_title(template: str, payload: dict[str, Any]) -> str:
    """Format title template with payload values, graceful on missing keys."""
    try:
        return template.format_map({k: str(v) for k, v in payload.items()})
    except (KeyError, IndexError):
        return template


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class NotificationService:
    """Maps forge events to notification records with dedup and priority.

    Instantiated once during app lifespan and stored on app.state.
    Called from routers/event handlers to create notifications.
    """

    def __init__(self, storage, event_bus):
        self._storage = storage
        self._event_bus = event_bus
        # Dedup cache: (source_event, source_entity_id) -> timestamp
        self._dedup: dict[tuple[str, str], float] = {}

    def _is_duplicate(self, source_event: str, source_entity_id: str) -> bool:
        """Check if this event was already processed within DEDUP_WINDOW."""
        key = (source_event, source_entity_id)
        now = time.monotonic()
        # Purge expired entries (lazy cleanup)
        expired = [k for k, ts in self._dedup.items() if now - ts > DEDUP_WINDOW]
        for k in expired:
            del self._dedup[k]
        if key in self._dedup:
            return True
        self._dedup[key] = now
        return False

    async def process_event(
        self,
        slug: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> str | None:
        """Process a forge event and create a notification if mapped.

        Returns the notification ID if created, None if skipped.
        """
        mapping = _EVENT_MAP.get(event_type)
        if mapping is None:
            return None

        notification_type, priority, title_template = mapping

        # Resolve dynamic priority
        if priority == "_dynamic":
            priority = _resolve_priority(event_type, payload)

        # Extract source entity for dedup
        source_entity_id = (
            payload.get("source_entity_id")
            or payload.get("decision_id")
            or payload.get("task_id")
            or payload.get("execution_id")
            or ""
        )

        # Dedup check
        if source_entity_id and self._is_duplicate(event_type, source_entity_id):
            logger.debug("Dedup: skipping %s for %s", event_type, source_entity_id)
            return None

        title = _format_title(title_template, payload)
        ts = datetime.now(timezone.utc).isoformat()

        # Determine source entity type from ID prefix
        source_entity_type = ""
        if source_entity_id:
            prefix = source_entity_id.split("-")[0] if "-" in source_entity_id else ""
            type_map = {
                "D": "decision", "T": "task", "O": "objective",
                "I": "idea", "K": "knowledge", "R": "research",
            }
            source_entity_type = type_map.get(prefix, "")

        notification = {
            "notification_type": notification_type,
            "priority": priority,
            "title": title,
            "message": payload.get("message", ""),
            "source_event": event_type,
            "source_entity_type": source_entity_type,
            "source_entity_id": source_entity_id,
            "workflow_id": payload.get("workflow_id", payload.get("execution_id", "")),
            "workflow_step": payload.get("workflow_step", payload.get("step_id", "")),
            "ai_options": payload.get("ai_options", []),
        }

        # Write to storage
        try:
            async with _get_lock(slug, "notifications"):
                data = await load_entity(self._storage, slug, "notifications")
                notifications = data.get("notifications", [])
                nid = next_id(notifications, "N")
                record = {
                    "id": nid,
                    **notification,
                    "status": "UNREAD",
                    "project": slug,
                    "response": None,
                    "response_at": None,
                    "created_at": ts,
                    "resolved_at": None,
                }
                notifications.append(record)
                data["notifications"] = notifications
                data["unread_count"] = sum(
                    1 for n in notifications if n.get("status") == "UNREAD"
                )
                await save_entity(self._storage, slug, "notifications", data)
        except Exception:
            logger.exception("Failed to create notification for %s in %s", event_type, slug)
            return None

        # Emit notification.created event
        try:
            await self._event_bus.emit(slug, "notification.created", {
                "notification_id": nid,
                "notification_type": notification_type,
                "priority": priority,
                "title": title,
                "source_entity_type": source_entity_type,
                "source_entity_id": source_entity_id,
            })
        except Exception:
            logger.debug("Failed to emit notification.created for %s", nid)

        return nid
