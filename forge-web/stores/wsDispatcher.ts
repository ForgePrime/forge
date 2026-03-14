/**
 * Centralized WebSocket event dispatcher.
 * Routes incoming ForgeEvents to the appropriate per-entity store
 * and triggers SWR cache revalidation.
 */
import { mutate } from "swr";
import type { ForgeEvent } from "@/lib/ws";
import { useTaskStore } from "./taskStore";
import { useDecisionStore } from "./decisionStore";
import { useObjectiveStore } from "./objectiveStore";
import { useIdeaStore } from "./ideaStore";
import { useChangeStore } from "./changeStore";
import { useGuidelineStore } from "./guidelineStore";
import { useKnowledgeStore } from "./knowledgeStore";
import { useLessonStore } from "./lessonStore";
import { useACTemplateStore } from "./acTemplateStore";
import { useGateStore } from "./gateStore";
import { useResearchStore } from "./researchStore";
import { useSkillStore } from "./skillStore";
import { useChatStore } from "./chatStore";
import { useWorkflowStore } from "./workflowStore";
import { isRecentMutation } from "@/lib/mutationTracker";
import { llm } from "@/lib/api";
import { useToastStore } from "./toastStore";
import { useActivityStore } from "./activityStore";
import { useNotificationStore } from "./notificationStore";
import { useNotificationEntityStore } from "./notificationEntityStore";
import { notifications as notificationsApi } from "@/lib/api";

/** All stores that handle WS events, in dispatch order. */
const stores = [
  useTaskStore,
  useDecisionStore,
  useObjectiveStore,
  useIdeaStore,
  useChangeStore,
  useGuidelineStore,
  useKnowledgeStore,
  useLessonStore,
  useACTemplateStore,
  useGateStore,
  useResearchStore,
  useSkillStore,
  useNotificationEntityStore,
] as const;

/** Maps WS event prefixes to API entity paths for SWR revalidation. */
const EVENT_TO_ENTITY: Record<string, string> = {
  task: "tasks",
  decision: "decisions",
  objective: "objectives",
  idea: "ideas",
  change: "changes",
  guideline: "guidelines",
  knowledge: "knowledge",
  lesson: "lessons",
  ac_template: "ac-templates",
  gate: "gates",
  research: "research",
  skill: "skills",
  notification: "notifications",
};

/** Global entities use /{path} instead of /projects/{slug}/{path}. */
const GLOBAL_ENTITIES = new Set(["skill"]);

/**
 * Maps LLM write-tool names to EVENT_TO_ENTITY keys for SWR revalidation.
 * Read-only tools (search/get/list/preview/lint) are intentionally excluded.
 * When adding a new write tool to tool_registry.py, add it here too.
 */
const TOOL_TO_ENTITY: Record<string, string> = {
  createTask: "task",
  updateTask: "task",
  completeTask: "task",
  draftPlan: "task",
  approvePlan: "task",
  createObjective: "objective",
  updateObjective: "objective",
  createIdea: "idea",
  updateIdea: "idea",
  createDecision: "decision",
  updateDecision: "decision",
  createKnowledge: "knowledge",
  updateKnowledge: "knowledge",
  createGuideline: "guideline",
  updateGuideline: "guideline",
  createLesson: "lesson",
  promoteLesson: "lesson",
  recordChange: "change",
  createResearch: "research",
  updateResearch: "research",
  updateSkillContent: "skill",
  updateSkillMetadata: "skill",
  addSkillFile: "skill",
  removeSkillFile: "skill",
  instantiateACTemplate: "ac_template",
};

/** Pending revalidation timers, keyed by "entityPrefix:project". */
const _revalidationTimers = new Map<string, ReturnType<typeof setTimeout>>();
const REVALIDATION_DEBOUNCE_MS = 300;

/** Pending toast timers, keyed by "entityPrefix:project". */
const _toastTimers = new Map<string, ReturnType<typeof setTimeout>>();
const TOAST_DEBOUNCE_MS = 500;

/**
 * Schedule debounced SWR revalidation + toast for an AI-modified entity.
 * Multiple rapid tool calls for the same entity batch into one refresh.
 */
function _scheduleEntityRevalidation(entityPrefix: string, project?: string): void {
  const entityPath = EVENT_TO_ENTITY[entityPrefix];
  if (!entityPath) return;

  const key = `${entityPrefix}:${project ?? "_global"}`;

  // --- Debounced SWR revalidation ---
  const existingTimer = _revalidationTimers.get(key);
  if (existingTimer) clearTimeout(existingTimer);

  _revalidationTimers.set(
    key,
    setTimeout(() => {
      _revalidationTimers.delete(key);

      if (GLOBAL_ENTITIES.has(entityPrefix)) {
        mutate(
          (k) => typeof k === "string" && k.startsWith(`/${entityPath}`),
          undefined,
          { revalidate: true },
        );
      } else if (project) {
        mutate(
          (k) => typeof k === "string" && k.startsWith(`/projects/${project}/${entityPath}`),
          undefined,
          { revalidate: true },
        );
      }
    }, REVALIDATION_DEBOUNCE_MS),
  );

  // --- Debounced toast ---
  const toastKey = `toast:${key}`;
  const existingToast = _toastTimers.get(toastKey);
  if (existingToast) clearTimeout(existingToast);

  _toastTimers.set(
    toastKey,
    setTimeout(() => {
      _toastTimers.delete(toastKey);
      const label = entityPath.replace(/-/g, " ");
      useToastStore.getState().addToast({
        message: `AI updated ${label}`,
        entityType: entityPrefix,
        action: "updated",
        project: project,
      });
    }, TOAST_DEBOUNCE_MS),
  );
}

/**
 * Extract entity prefix and ID from a WS event.
 * e.g. "task.created" → { prefix: "task", entityId: payload.id }
 */
function parseEvent(event: ForgeEvent): { prefix: string; entityId?: string } {
  const prefix = event.event.split(".")[0];
  const payload = event.payload as Record<string, unknown>;
  const entityId = (payload.id ?? payload.task_id ?? payload.decision_id) as string | undefined;
  return { prefix, entityId };
}

/**
 * Dispatch a WebSocket event to all per-entity stores
 * and trigger SWR cache revalidation for the affected entity type.
 */
export function dispatchWsEvent(event: ForgeEvent): void {
  const { prefix, entityId } = parseEvent(event);

  // Track last event timestamp for connection status monitoring
  _lastEventTimestamp = new Date().toISOString();

  // LLM session lifecycle events — revalidate sessions SWR cache
  if (prefix === "llm") {
    mutate(
      (key) => typeof key === "string" && key.startsWith("/llm/sessions"),
      undefined,
      { revalidate: true },
    );
    return;
  }

  // Workflow events go to workflowStore for real-time step progress
  if (prefix === "workflow") {
    useWorkflowStore.getState().handleWsEvent(event);
    return;
  }

  // Chat events go to chatStore; tool_results also trigger entity revalidation
  if (prefix === "chat") {
    useChatStore.getState().handleWsEvent(event);

    // When AI executes a write tool, refresh the affected entity data
    if (event.event === "chat.tool_result") {
      const payload = event.payload as Record<string, unknown>;
      const toolName = payload.name as string | undefined;
      if (toolName) {
        const entityPrefix = TOOL_TO_ENTITY[toolName];
        if (entityPrefix) {
          _scheduleEntityRevalidation(entityPrefix, event.project);
        }
      }
    }

    // Session paused/resumed → revalidate sessions list
    if (event.event === "chat.paused" || event.event === "chat.resumed") {
      mutate(
        (key) => typeof key === "string" && key.startsWith("/llm/sessions"),
        undefined,
        { revalidate: true },
      );
    }
    return;
  }

  // Skip SWR revalidation if this is an echo of our own mutation
  const skipSWR = entityId ? isRecentMutation(entityId) : false;

  // 1. Dispatch to Zustand stores (always — for optimistic update reconciliation)
  for (const store of stores) {
    store.getState().handleWsEvent(event);
  }

  // Decision created → persistent notification popup (requires user action)
  if (event.event === "decision.created") {
    const payload = event.payload as Record<string, unknown>;
    useNotificationStore.getState().addDecision({
      decisionId: (payload.decision_id ?? payload.id ?? "") as string,
      type: (payload.type ?? "standard") as string,
      issue: (payload.issue ?? "") as string,
      taskId: (payload.task_id as string) || undefined,
      severity: (payload.severity as string) || undefined,
      project: event.project,
    });
  }

  // Notification created → priority-based display (D-014)
  if (event.event === "notification.created") {
    const payload = event.payload as Record<string, unknown>;
    const priority = (payload.priority as string) ?? "normal";
    if (priority === "critical" || priority === "high") {
      // Immediate popup for critical/high
      useNotificationStore.getState().addDecision({
        decisionId: (payload.notification_id ?? "") as string,
        type: (payload.notification_type ?? "alert") as string,
        issue: (payload.title ?? "") as string,
        severity: priority,
        project: event.project,
      });
      // Critical also gets a toast
      if (priority === "critical") {
        useToastStore.getState().addToast({
          message: `CRITICAL: ${(payload.title as string) ?? "Notification"}`,
          entityType: "notification",
          action: "created",
          project: event.project,
        });
      }
    }
    // Normal/low → debounced SWR revalidation only (bell badge increments, no popup)
    // Already handled by the general entity routing above
  }

  // Decision closed → auto-resume any paused session waiting for this decision
  if (event.event === "decision.closed" || event.event === "decision.status_changed") {
    const payload = event.payload as Record<string, unknown>;
    const status = (payload.status as string) || "";
    if (status === "CLOSED" || status === "MITIGATED" || status === "ACCEPTED" || event.event === "decision.closed") {
      const decisionId = (payload.decision_id ?? payload.id ?? "") as string;
      if (decisionId) {
        _tryResumeBlockedSessions(decisionId);
      }
    }
  }

  // 2. Trigger SWR revalidation for entity lists (unless it's our own echo)
  if (!skipSWR) {
    const entityPath = EVENT_TO_ENTITY[prefix];
    if (entityPath) {
      if (GLOBAL_ENTITIES.has(prefix)) {
        // Global entities: revalidate /{entityPath} keys (no project prefix)
        const pattern = `/${entityPath}`;
        mutate(
          (key) => typeof key === "string" && key.startsWith(pattern),
          undefined,
          { revalidate: true },
        );
      } else if (event.project) {
        // Project-scoped entities: revalidate /projects/{slug}/{entityPath}
        const pattern = `/projects/${event.project}/${entityPath}`;
        mutate(
          (key) => typeof key === "string" && key.startsWith(pattern),
          undefined,
          { revalidate: true },
        );
      }
    }

    // 3. Show toast notification for entity events (skip own mutations)
    const action = parseAction(event.event);
    if (action) {
      const payload = event.payload as Record<string, unknown>;
      const name = (payload.name ?? payload.title ?? payload.issue ?? payload.metric ?? "") as string;
      const entityName = EVENT_TO_ENTITY[prefix] ?? prefix;
      const label = entityName.replace(/-/g, " ").replace(/s$/, "");
      const message = name
        ? `${capitalize(label)} ${action}: ${name}`
        : `${capitalize(label)} ${action}`;

      useToastStore.getState().addToast({
        message,
        entityId: entityId,
        entityType: prefix,
        action: action as "created" | "updated" | "deleted" | "completed" | "failed" | "info",
        project: event.project,
      });

      // Record to activity feed (persists more events than toast)
      useActivityStore.getState().addEvent({
        event: event.event,
        entityId,
        entityType: prefix,
        project: event.project ?? "",
        timestamp: new Date().toISOString(),
        message,
        action,
      });
    }
  }
}

/** Parse and normalize action from WS event name. e.g. "task.created" → "created" */
function parseAction(eventName: string): string | null {
  const parts = eventName.split(".");
  if (parts.length < 2) return null;
  const action = parts[1];
  const NORMALIZE: Record<string, string> = {
    status_changed: "updated",
    committed: "updated",
    recorded: "created",
    configured: "updated",
    removed: "deleted",
    closed: "completed",
    promoted: "updated",
  };
  return NORMALIZE[action] ?? action;
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/**
 * Try to resume any sessions that were paused waiting for a specific decision.
 * Fetches sessions list, finds paused ones blocked by the given decision, and resumes them.
 */
async function _tryResumeBlockedSessions(decisionId: string): Promise<void> {
  try {
    const { sessions } = await llm.listSessions(200);
    for (const session of sessions) {
      if (
        session.session_status === "paused" &&
        session.blocked_by_decision_id === decisionId
      ) {
        await llm.resumeSession(session.session_id);
      }
    }
  } catch {
    // Best-effort: don't crash on resume failure
  }
}

/** Track the last WS event timestamp (for connection status). */
let _lastEventTimestamp: string | null = null;

export function getLastEventTimestamp(): string | null {
  return _lastEventTimestamp;
}

export function setLastEventTimestamp(ts: string): void {
  _lastEventTimestamp = ts;
}

/**
 * Fetch unread notifications on WS reconnect (D-013 mitigation).
 * Ensures zero missed notifications during connection gaps.
 */
export async function fetchUnreadOnReconnect(slug: string): Promise<void> {
  try {
    const res = await notificationsApi.list(slug, { status: "UNREAD" });
    const items = res.notifications ?? [];
    if (items.length > 0) {
      // Merge into entity store
      useNotificationEntityStore.getState().fetchAll(slug, { status: "UNREAD" });
    }
  } catch {
    // Best-effort: don't crash on reconnect fetch
  }
}
