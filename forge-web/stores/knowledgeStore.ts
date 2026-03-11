import { createEntityStore, withCreateLoading, withUpdate } from "./factory";
import { knowledge as knowledgeApi } from "@/lib/api";
import type { Knowledge, KnowledgeCreate, KnowledgeUpdate } from "@/lib/types";

export const useKnowledgeStore = createEntityStore<Knowledge>({
  listFn: (s, p) => knowledgeApi.list(s, p),
  responseKey: "knowledge",
  getItemId: (item) => item.id,
  wsEvents: {
    "knowledge.created": { op: "create", idKey: "knowledge_id" },
    "knowledge.updated": { op: "update", idKey: "knowledge_id" },
  },
});

export async function createKnowledge(slug: string, data: KnowledgeCreate[]): Promise<string[]> {
  return withCreateLoading(useKnowledgeStore, () => knowledgeApi.create(slug, data));
}

export async function updateKnowledge(slug: string, id: string, data: KnowledgeUpdate): Promise<void> {
  return withUpdate(useKnowledgeStore, (item) => item.id, id, () => knowledgeApi.update(slug, id, data));
}
