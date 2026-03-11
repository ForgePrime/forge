/**
 * Centralized WebSocket event dispatcher.
 * Routes incoming ForgeEvents to the appropriate per-entity store.
 */
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
] as const;

/**
 * Dispatch a WebSocket event to all per-entity stores.
 * Each store checks its own wsEvents mapping and ignores irrelevant events.
 */
export function dispatchWsEvent(event: ForgeEvent): void {
  for (const store of stores) {
    store.getState().handleWsEvent(event);
  }
}
