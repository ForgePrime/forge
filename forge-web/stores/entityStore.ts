import { create } from "zustand";
import {
  tasks as tasksApi,
  decisions as decisionsApi,
  objectives as objectivesApi,
  ideas as ideasApi,
  changes as changesApi,
  guidelines as guidelinesApi,
  knowledge as knowledgeApi,
  lessons as lessonsApi,
  acTemplates as acTemplatesApi,
  gates as gatesApi,
} from "../lib/api";
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
} from "../lib/types";
import type { ForgeEvent } from "../lib/ws";

/** Supported entity type keys. */
export type EntityType =
  | "tasks" | "decisions" | "objectives" | "ideas"
  | "changes" | "guidelines" | "knowledge" | "lessons"
  | "acTemplates" | "gates";

/** Union of all entity item types. */
type AnyEntity =
  | Task | Decision | Objective | Idea | ChangeRecord
  | Guideline | Knowledge | Lesson | ACTemplate | Gate;

interface EntitySlice {
  items: AnyEntity[];
  count: number;
  loading: boolean;
  error: string | null;
}

const emptySlice = (): EntitySlice => ({
  items: [],
  count: 0,
  loading: false,
  error: null,
});

/** Get the identifier for an entity item (most use 'id', gates use 'name'). */
function getItemId(item: AnyEntity, type: EntityType): string | undefined {
  if (type === "gates") return (item as Gate).name;
  return (item as { id: string }).id;
}

interface EntityState {
  /** Per-entity-type data. */
  slices: Record<EntityType, EntitySlice>;
  /** Request sequence numbers to prevent stale data from late-arriving responses. */
  _fetchSeq: Record<EntityType, number>;

  // List actions
  fetchEntities: (slug: string, type: EntityType, params?: Record<string, string>) => Promise<void>;

  // CRUD actions
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

  // WebSocket handler
  handleEvent: (event: ForgeEvent) => void;

  // Clear
  clearSlice: (type: EntityType) => void;
}

/** API list functions mapped by entity type. */
const listFns: Record<EntityType, (slug: string, params?: Record<string, string>) => Promise<{ count: number; [key: string]: unknown }>> = {
  tasks: (s, p) => tasksApi.list(s, p) as Promise<{ tasks: Task[]; count: number }>,
  decisions: (s, p) => decisionsApi.list(s, p) as Promise<{ decisions: Decision[]; count: number }>,
  objectives: (s) => objectivesApi.list(s) as Promise<{ objectives: Objective[]; count: number }>,
  ideas: (s, p) => ideasApi.list(s, p) as Promise<{ ideas: Idea[]; count: number }>,
  changes: (s, p) => changesApi.list(s, p) as Promise<{ changes: ChangeRecord[]; count: number }>,
  guidelines: (s, p) => guidelinesApi.list(s, p) as Promise<{ guidelines: Guideline[]; count: number }>,
  knowledge: (s, p) => knowledgeApi.list(s, p) as Promise<{ knowledge: Knowledge[]; count: number }>,
  lessons: (s) => lessonsApi.list(s) as Promise<{ lessons: Lesson[]; count: number }>,
  acTemplates: (s, p) => acTemplatesApi.list(s, p) as Promise<{ templates: ACTemplate[]; count: number }>,
  gates: (s) => gatesApi.list(s) as Promise<{ gates: Gate[]; count: number }>,
};

/** Maps entity type to the response key containing the array. */
const responseKeys: Record<EntityType, string> = {
  tasks: "tasks",
  decisions: "decisions",
  objectives: "objectives",
  ideas: "ideas",
  changes: "changes",
  guidelines: "guidelines",
  knowledge: "knowledge",
  lessons: "lessons",
  acTemplates: "templates",
  gates: "gates",
};

/** Maps WS event names to entity types and operation. */
const eventMap: Record<string, { type: EntityType; op: "create" | "update" | "remove" | "replace" }> = {
  "task.created": { type: "tasks", op: "create" },
  "task.updated": { type: "tasks", op: "update" },
  "task.completed": { type: "tasks", op: "update" },
  "task.failed": { type: "tasks", op: "update" },
  "task.removed": { type: "tasks", op: "remove" },
  "decision.created": { type: "decisions", op: "create" },
  "decision.updated": { type: "decisions", op: "update" },
  "objective.created": { type: "objectives", op: "create" },
  "objective.updated": { type: "objectives", op: "update" },
  "idea.created": { type: "ideas", op: "create" },
  "idea.updated": { type: "ideas", op: "update" },
  "idea.committed": { type: "ideas", op: "update" },
  "change.recorded": { type: "changes", op: "create" },
  "guideline.created": { type: "guidelines", op: "create" },
  "guideline.updated": { type: "guidelines", op: "update" },
  "knowledge.created": { type: "knowledge", op: "create" },
  "knowledge.updated": { type: "knowledge", op: "update" },
  "lesson.created": { type: "lessons", op: "create" },
  "gate.configured": { type: "gates", op: "replace" },
};

function setSlice(set: (fn: (s: EntityState) => Partial<EntityState>) => void, type: EntityType, patch: Partial<EntitySlice>) {
  set((s) => ({
    slices: {
      ...s.slices,
      [type]: { ...s.slices[type], ...patch },
    },
  }));
}

const initSeq: Record<EntityType, number> = {
  tasks: 0, decisions: 0, objectives: 0, ideas: 0, changes: 0,
  guidelines: 0, knowledge: 0, lessons: 0, acTemplates: 0, gates: 0,
};

/** Helper: wrap a create API call with loading/error state. */
async function withCreateLoading(
  set: (fn: (s: EntityState) => Partial<EntityState>) => void,
  type: EntityType,
  fn: () => Promise<{ added: string[]; total: number }>,
): Promise<string[]> {
  setSlice(set, type, { loading: true, error: null });
  try {
    const res = await fn();
    setSlice(set, type, { loading: false });
    return res.added;
  } catch (e) {
    setSlice(set, type, { error: (e as Error).message, loading: false });
    throw e;
  }
}

/** Helper: wrap an update API call with error handling and in-place item replacement. */
async function withUpdate<T extends AnyEntity>(
  set: (fn: (s: EntityState) => Partial<EntityState>) => void,
  type: EntityType,
  id: string,
  fn: () => Promise<T>,
): Promise<void> {
  try {
    const updated = await fn();
    set((s) => ({
      slices: {
        ...s.slices,
        [type]: {
          ...s.slices[type],
          items: s.slices[type].items.map((item) =>
            getItemId(item, type) === id ? updated : item,
          ),
        },
      },
    }));
  } catch (e) {
    setSlice(set, type, { error: (e as Error).message });
  }
}

export const useEntityStore = create<EntityState>((set, get) => ({
  slices: {
    tasks: emptySlice(),
    decisions: emptySlice(),
    objectives: emptySlice(),
    ideas: emptySlice(),
    changes: emptySlice(),
    guidelines: emptySlice(),
    knowledge: emptySlice(),
    lessons: emptySlice(),
    acTemplates: emptySlice(),
    gates: emptySlice(),
  },
  _fetchSeq: { ...initSeq },

  fetchEntities: async (slug, type, params) => {
    // Increment sequence to detect stale responses
    const seq = get()._fetchSeq[type] + 1;
    set((s) => ({ _fetchSeq: { ...s._fetchSeq, [type]: seq } }));
    setSlice(set, type, { loading: true, error: null });
    try {
      const res = await listFns[type](slug, params);
      // Discard if a newer request was started
      if (get()._fetchSeq[type] !== seq) return;
      const key = responseKeys[type];
      const items = (res as Record<string, unknown>)[key] as AnyEntity[];
      setSlice(set, type, { items, count: res.count, loading: false });
    } catch (e) {
      if (get()._fetchSeq[type] !== seq) return;
      setSlice(set, type, { error: (e as Error).message, loading: false });
    }
  },

  // -- Tasks --
  createTask: async (slug, data) =>
    withCreateLoading(set, "tasks", () => tasksApi.create(slug, data)),
  updateTask: async (slug, id, data) =>
    withUpdate(set, "tasks", id, () => tasksApi.update(slug, id, data)),
  removeTask: async (slug, id) => {
    // Optimistic: remove immediately, rollback on error
    const prev = get().slices.tasks.items;
    set((s) => {
      const items = s.slices.tasks.items.filter((item) => getItemId(item, "tasks") !== id);
      return { slices: { ...s.slices, tasks: { ...s.slices.tasks, items, count: items.length } } };
    });
    try {
      await tasksApi.remove(slug, id);
    } catch (e) {
      setSlice(set, "tasks", { items: prev, count: prev.length, error: (e as Error).message });
    }
  },

  // -- Decisions --
  createDecision: async (slug, data) =>
    withCreateLoading(set, "decisions", () => decisionsApi.create(slug, data)),
  updateDecision: async (slug, id, data) =>
    withUpdate(set, "decisions", id, () => decisionsApi.update(slug, id, data)),

  // -- Objectives --
  createObjective: async (slug, data) =>
    withCreateLoading(set, "objectives", () => objectivesApi.create(slug, data)),
  updateObjective: async (slug, id, data) =>
    withUpdate(set, "objectives", id, () => objectivesApi.update(slug, id, data)),

  // -- Ideas --
  createIdea: async (slug, data) =>
    withCreateLoading(set, "ideas", () => ideasApi.create(slug, data)),
  updateIdea: async (slug, id, data) =>
    withUpdate(set, "ideas", id, () => ideasApi.update(slug, id, data)),

  // -- Changes --
  createChange: async (slug, data) =>
    withCreateLoading(set, "changes", () => changesApi.create(slug, data)),

  // -- Guidelines --
  createGuideline: async (slug, data) =>
    withCreateLoading(set, "guidelines", () => guidelinesApi.create(slug, data)),
  updateGuideline: async (slug, id, data) =>
    withUpdate(set, "guidelines", id, () => guidelinesApi.update(slug, id, data)),

  // -- Knowledge --
  createKnowledge: async (slug, data) =>
    withCreateLoading(set, "knowledge", () => knowledgeApi.create(slug, data)),
  updateKnowledge: async (slug, id, data) =>
    withUpdate(set, "knowledge", id, () => knowledgeApi.update(slug, id, data)),

  // -- Lessons --
  createLesson: async (slug, data) =>
    withCreateLoading(set, "lessons", () => lessonsApi.create(slug, data)),

  // -- AC Templates --
  createACTemplate: async (slug, data) =>
    withCreateLoading(set, "acTemplates", () => acTemplatesApi.create(slug, data)),
  updateACTemplate: async (slug, id, data) =>
    withUpdate(set, "acTemplates", id, () => acTemplatesApi.update(slug, id, data)),

  // -- Gates --
  createGate: async (slug, data) => {
    setSlice(set, "gates", { loading: true, error: null });
    try {
      await gatesApi.create(slug, data);
      setSlice(set, "gates", { loading: false });
    } catch (e) {
      setSlice(set, "gates", { error: (e as Error).message, loading: false });
      throw e;
    }
  },

  // -- WebSocket event handler --
  handleEvent: (event: ForgeEvent) => {
    const mapping = eventMap[event.event];
    if (!mapping) return;
    const { type, op } = mapping;

    const payload = event.payload as Record<string, unknown>;
    const payloadId = (type === "gates")
      ? (payload?.name as string | undefined)
      : (payload?.id as string | undefined);

    set((s) => {
      const slice = s.slices[type];
      let items: AnyEntity[];

      switch (op) {
        case "update":
          // Merge payload into existing item to handle partial payloads
          if (!payloadId) return {};
          items = slice.items.map((item) =>
            getItemId(item, type) === payloadId
              ? ({ ...item, ...payload } as unknown as AnyEntity)
              : item,
          );
          break;

        case "remove":
          if (!payloadId) return {};
          items = slice.items.filter((item) => getItemId(item, type) !== payloadId);
          break;

        case "replace":
          // For gates: replace entire slice (gate.configured replaces all gates)
          if (Array.isArray(payload.gates)) {
            items = payload.gates as unknown as AnyEntity[];
          } else {
            return {};
          }
          break;

        case "create":
        default:
          if (!payloadId) return {};
          // Avoid duplicates: skip if already present
          if (slice.items.some((item) => getItemId(item, type) === payloadId)) return {};
          items = [...slice.items, payload as unknown as AnyEntity];
          break;
      }

      return {
        slices: {
          ...s.slices,
          [type]: { ...slice, items, count: items.length },
        },
      };
    });
  },

  clearSlice: (type) => {
    setSlice(set, type, emptySlice());
  },
}));
