import { createEntityStore, withCreateLoading, withUpdate } from "./factory";
import { objectives as objectivesApi } from "@/lib/api";
import type { Objective, ObjectiveCreate, ObjectiveUpdate } from "@/lib/types";

export const useObjectiveStore = createEntityStore<Objective>({
  listFn: (s) => objectivesApi.list(s),
  responseKey: "objectives",
  getItemId: (item) => item.id,
  wsEvents: {
    "objective.created": { op: "create" },
    "objective.updated": { op: "update" },
  },
});

export async function createObjective(slug: string, data: ObjectiveCreate[]): Promise<string[]> {
  return withCreateLoading(useObjectiveStore, () => objectivesApi.create(slug, data));
}

export async function updateObjective(slug: string, id: string, data: ObjectiveUpdate): Promise<void> {
  return withUpdate(useObjectiveStore, (item) => item.id, id, () => objectivesApi.update(slug, id, data));
}
