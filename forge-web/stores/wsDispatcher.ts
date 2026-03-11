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
import { useSkillStore } from "./skillStore";
import { isRecentMutation } from "@/lib/mutationTracker";
import { useToastStore } from "./toastStore";
import { useActivityStore } from "./activityStore";

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
  useSkillStore,
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
  skill: "skills",
};

/** Global entities use /{path} instead of /projects/{slug}/{path}. */
const GLOBAL_ENTITIES = new Set(["skill"]);

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

  // Skip SWR revalidation if this is an echo of our own mutation
  const skipSWR = entityId ? isRecentMutation(entityId) : false;

  // 1. Dispatch to Zustand stores (always — for optimistic update reconciliation)
  for (const store of stores) {
    store.getState().handleWsEvent(event);
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

/** Track the last WS event timestamp (for connection status). */
let _lastEventTimestamp: string | null = null;

export function getLastEventTimestamp(): string | null {
  return _lastEventTimestamp;
}

export function setLastEventTimestamp(ts: string): void {
  _lastEventTimestamp = ts;
}
