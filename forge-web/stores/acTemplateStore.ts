import { createEntityStore, withCreateLoading, withUpdate } from "./factory";
import { acTemplates as acTemplatesApi } from "@/lib/api";
import type { ACTemplate, ACTemplateCreate, ACTemplateUpdate } from "@/lib/types";

export const useACTemplateStore = createEntityStore<ACTemplate>({
  listFn: (s, p) => acTemplatesApi.list(s, p),
  responseKey: "templates",
  getItemId: (item) => item.id,
  wsEvents: {},
});

export async function createACTemplate(slug: string, data: ACTemplateCreate[]): Promise<string[]> {
  return withCreateLoading(useACTemplateStore, () => acTemplatesApi.create(slug, data));
}

export async function updateACTemplate(slug: string, id: string, data: ACTemplateUpdate): Promise<void> {
  return withUpdate(useACTemplateStore, (item) => item.id, id, () => acTemplatesApi.update(slug, id, data));
}
