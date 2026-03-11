import { createEntityStore, withCreateLoading, withUpdate } from "./factory";
import { skills as skillsApi } from "@/lib/api";
import type { Skill, SkillCreate, SkillUpdate } from "@/lib/types";
import { trackMutation } from "@/lib/mutationTracker";

export const useSkillStore = createEntityStore<Skill>({
  // Skills are global — slug is ignored by the API client
  listFn: (_slug, params) => skillsApi.list(params),
  responseKey: "skills",
  getItemId: (item) => item.id,
  wsEvents: {
    "skill.created": { op: "create" },
    "skill.updated": { op: "update" },
    "skill.deleted": { op: "remove" },
    "skill.promoted": { op: "update" },
  },
});

/** Fetch all skills (global — no slug needed). */
export async function fetchSkills(params?: Record<string, string>): Promise<void> {
  return useSkillStore.getState().fetchAll("_global", params);
}

export async function createSkill(data: SkillCreate[]): Promise<string[]> {
  return withCreateLoading(useSkillStore, () => skillsApi.create(data));
}

export async function updateSkill(id: string, data: SkillUpdate): Promise<void> {
  return withUpdate(
    useSkillStore,
    (item) => item.id,
    id,
    () => skillsApi.update(id, data),
    data,
  );
}

export async function removeSkill(id: string): Promise<void> {
  const prev = useSkillStore.getState().items;
  const filtered = prev.filter((item) => item.id !== id);
  useSkillStore.setState({ items: filtered, count: filtered.length });
  try {
    await skillsApi.remove(id);
    trackMutation(id);
  } catch (e) {
    useSkillStore.setState({ items: prev, count: prev.length, error: (e as Error).message });
  }
}
