import { createEntityStore, withCreateLoading, withUpdate } from "./factory";
import { guidelines as guidelinesApi } from "@/lib/api";
import type { Guideline, GuidelineCreate, GuidelineUpdate } from "@/lib/types";

export const useGuidelineStore = createEntityStore<Guideline>({
  listFn: (s, p) => guidelinesApi.list(s, p),
  responseKey: "guidelines",
  getItemId: (item) => item.id,
  wsEvents: {
    "guideline.created": { op: "create" },
    "guideline.updated": { op: "update" },
  },
});

export async function createGuideline(slug: string, data: GuidelineCreate[]): Promise<string[]> {
  return withCreateLoading(useGuidelineStore, () => guidelinesApi.create(slug, data));
}

export async function updateGuideline(slug: string, id: string, data: GuidelineUpdate): Promise<void> {
  return withUpdate(useGuidelineStore, (item) => item.id, id, () => guidelinesApi.update(slug, id, data));
}
