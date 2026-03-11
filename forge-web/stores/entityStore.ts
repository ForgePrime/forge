/**
 * Backward-compatible facade over per-entity stores.
 *
 * Consumers that use `useEntityStore()` continue to work unchanged.
 * New code should import from per-entity stores directly.
 */
import { useCallback, useMemo } from "react";
import type { ForgeEvent } from "@/lib/ws";
import type {
  Task, TaskCreate, TaskUpdate,
  Decision, DecisionCreate, DecisionUpdate,
  Objective, ObjectiveCreate, ObjectiveUpdate,
  Idea, IdeaCreate, IdeaUpdate,
  ChangeRecord, ChangeCreate,
  Guideline, GuidelineCreate, GuidelineUpdate,
  Knowledge, KnowledgeCreate, KnowledgeUpdate,
  Lesson, LessonCreate,
  ACTemplate, ACTemplateCreate, ACTemplateUpdate,
  Gate, GateCreate,
} from "@/lib/types";
import type { EntitySliceState } from "./factory";

import { useTaskStore, createTask, updateTask, removeTask } from "./taskStore";
import { useDecisionStore, createDecision, updateDecision } from "./decisionStore";
import { useObjectiveStore, createObjective, updateObjective } from "./objectiveStore";
import { useIdeaStore, createIdea, updateIdea } from "./ideaStore";
import { useChangeStore, createChange } from "./changeStore";
import { useGuidelineStore, createGuideline, updateGuideline } from "./guidelineStore";
import { useKnowledgeStore, createKnowledge, updateKnowledge } from "./knowledgeStore";
import { useLessonStore, createLesson } from "./lessonStore";
import { useACTemplateStore, createACTemplate, updateACTemplate } from "./acTemplateStore";
import { useGateStore, createGate } from "./gateStore";
import { dispatchWsEvent } from "./wsDispatcher";

// Re-export EntityType for consumers
export type EntityType =
  | "tasks" | "decisions" | "objectives" | "ideas"
  | "changes" | "guidelines" | "knowledge" | "lessons"
  | "acTemplates" | "gates";

type AnyEntity = Task | Decision | Objective | Idea | ChangeRecord | Guideline | Knowledge | Lesson | ACTemplate | Gate;

// Maps EntityType to the correct per-entity store hook
const storeHooks = {
  tasks: useTaskStore,
  decisions: useDecisionStore,
  objectives: useObjectiveStore,
  ideas: useIdeaStore,
  changes: useChangeStore,
  guidelines: useGuidelineStore,
  knowledge: useKnowledgeStore,
  lessons: useLessonStore,
  acTemplates: useACTemplateStore,
  gates: useGateStore,
} as const;

const fetchFns = {
  tasks: useTaskStore.getState().fetchAll,
  decisions: useDecisionStore.getState().fetchAll,
  objectives: useObjectiveStore.getState().fetchAll,
  ideas: useIdeaStore.getState().fetchAll,
  changes: useChangeStore.getState().fetchAll,
  guidelines: useGuidelineStore.getState().fetchAll,
  knowledge: useKnowledgeStore.getState().fetchAll,
  lessons: useLessonStore.getState().fetchAll,
  acTemplates: useACTemplateStore.getState().fetchAll,
  gates: useGateStore.getState().fetchAll,
} as const;

/**
 * Backward-compatible hook that presents the same API as the old monolithic store.
 * Uses individual per-entity Zustand stores under the hood.
 */
export function useEntityStore(): {
  slices: Record<EntityType, EntitySliceState<AnyEntity>>;
  fetchEntities: (slug: string, type: EntityType, params?: Record<string, string>) => Promise<void>;
  createTask: (slug: string, data: TaskCreate[]) => Promise<string[]>;
  updateTask: (slug: string, id: string, data: TaskUpdate) => Promise<void>;
  removeTask: (slug: string, id: string) => Promise<void>;
  createDecision: (slug: string, data: DecisionCreate[]) => Promise<string[]>;
  updateDecision: (slug: string, id: string, data: DecisionUpdate) => Promise<void>;
  createObjective: (slug: string, data: ObjectiveCreate[]) => Promise<string[]>;
  updateObjective: (slug: string, id: string, data: ObjectiveUpdate) => Promise<void>;
  createIdea: (slug: string, data: IdeaCreate[]) => Promise<string[]>;
  updateIdea: (slug: string, id: string, data: IdeaUpdate) => Promise<void>;
  createChange: (slug: string, data: ChangeCreate[]) => Promise<string[]>;
  createGuideline: (slug: string, data: GuidelineCreate[]) => Promise<string[]>;
  updateGuideline: (slug: string, id: string, data: GuidelineUpdate) => Promise<void>;
  createKnowledge: (slug: string, data: KnowledgeCreate[]) => Promise<string[]>;
  updateKnowledge: (slug: string, id: string, data: KnowledgeUpdate) => Promise<void>;
  createLesson: (slug: string, data: LessonCreate[]) => Promise<string[]>;
  createACTemplate: (slug: string, data: ACTemplateCreate[]) => Promise<string[]>;
  updateACTemplate: (slug: string, id: string, data: ACTemplateUpdate) => Promise<void>;
  createGate: (slug: string, data: GateCreate[]) => Promise<void>;
  handleEvent: (event: ForgeEvent) => void;
  clearSlice: (type: EntityType) => void;
} {
  // Subscribe to all per-entity stores
  const taskSlice = useTaskStore();
  const decisionSlice = useDecisionStore();
  const objectiveSlice = useObjectiveStore();
  const ideaSlice = useIdeaStore();
  const changeSlice = useChangeStore();
  const guidelineSlice = useGuidelineStore();
  const knowledgeSlice = useKnowledgeStore();
  const lessonSlice = useLessonStore();
  const acTemplateSlice = useACTemplateStore();
  const gateSlice = useGateStore();

  const slices = useMemo(() => ({
    tasks: taskSlice as unknown as EntitySliceState<AnyEntity>,
    decisions: decisionSlice as unknown as EntitySliceState<AnyEntity>,
    objectives: objectiveSlice as unknown as EntitySliceState<AnyEntity>,
    ideas: ideaSlice as unknown as EntitySliceState<AnyEntity>,
    changes: changeSlice as unknown as EntitySliceState<AnyEntity>,
    guidelines: guidelineSlice as unknown as EntitySliceState<AnyEntity>,
    knowledge: knowledgeSlice as unknown as EntitySliceState<AnyEntity>,
    lessons: lessonSlice as unknown as EntitySliceState<AnyEntity>,
    acTemplates: acTemplateSlice as unknown as EntitySliceState<AnyEntity>,
    gates: gateSlice as unknown as EntitySliceState<AnyEntity>,
  }), [
    taskSlice, decisionSlice, objectiveSlice, ideaSlice, changeSlice,
    guidelineSlice, knowledgeSlice, lessonSlice, acTemplateSlice, gateSlice,
  ]);

  const fetchEntities = useCallback(
    (slug: string, type: EntityType, params?: Record<string, string>) =>
      fetchFns[type](slug, params),
    [],
  );

  const clearSlice = useCallback((type: EntityType) => {
    storeHooks[type].getState().clear();
  }, []);

  return {
    slices,
    fetchEntities,
    createTask,
    updateTask,
    removeTask,
    createDecision,
    updateDecision,
    createObjective,
    updateObjective,
    createIdea,
    updateIdea,
    createChange,
    createGuideline,
    updateGuideline,
    createKnowledge,
    updateKnowledge,
    createLesson,
    createACTemplate,
    updateACTemplate,
    createGate,
    handleEvent: dispatchWsEvent,
    clearSlice,
  };
}

