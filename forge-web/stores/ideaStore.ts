import { createEntityStore, withCreateLoading, withUpdate } from "./factory";
import { ideas as ideasApi } from "@/lib/api";
import type { Idea, IdeaCreate, IdeaUpdate } from "@/lib/types";

export const useIdeaStore = createEntityStore<Idea>({
  listFn: (s, p) => ideasApi.list(s, p),
  responseKey: "ideas",
  getItemId: (item) => item.id,
  wsEvents: {
    "idea.created": { op: "create" },
    "idea.updated": { op: "update" },
    "idea.committed": { op: "update" },
  },
});

export async function createIdea(slug: string, data: IdeaCreate[]): Promise<string[]> {
  return withCreateLoading(useIdeaStore, () => ideasApi.create(slug, data));
}

export async function updateIdea(slug: string, id: string, data: IdeaUpdate): Promise<void> {
  return withUpdate(useIdeaStore, (item) => item.id, id, () => ideasApi.update(slug, id, data));
}
