import { createEntityStore, withCreateLoading, withUpdate } from "./factory";
import { tasks as tasksApi } from "@/lib/api";
import type { Task, TaskCreate, TaskUpdate } from "@/lib/types";

export const useTaskStore = createEntityStore<Task>({
  listFn: (s, p) => tasksApi.list(s, p),
  responseKey: "tasks",
  getItemId: (item) => item.id,
  wsEvents: {
    "task.created": { op: "create", idKey: "task_id" },
    "task.updated": { op: "update", idKey: "task_id" },
    "task.status_changed": { op: "update", idKey: "task_id" },
    "task.completed": { op: "update", idKey: "task_id" },
    "task.failed": { op: "update", idKey: "task_id" },
    "task.removed": { op: "remove", idKey: "task_id" },
  },
});

export async function createTask(slug: string, data: TaskCreate[]): Promise<string[]> {
  return withCreateLoading(useTaskStore, () => tasksApi.create(slug, data));
}

export async function updateTask(slug: string, id: string, data: TaskUpdate): Promise<void> {
  return withUpdate(useTaskStore, (item) => item.id, id, () => tasksApi.update(slug, id, data));
}

export async function removeTask(slug: string, id: string): Promise<void> {
  const prev = useTaskStore.getState().items;
  const filtered = prev.filter((item) => item.id !== id);
  useTaskStore.setState({ items: filtered, count: filtered.length });
  try {
    await tasksApi.remove(slug, id);
  } catch (e) {
    useTaskStore.setState({ items: prev, count: prev.length, error: (e as Error).message });
  }
}
