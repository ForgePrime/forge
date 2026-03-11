import { createEntityStore, withCreateLoading } from "./factory";
import { changes as changesApi } from "@/lib/api";
import type { ChangeRecord, ChangeCreate } from "@/lib/types";

export const useChangeStore = createEntityStore<ChangeRecord>({
  listFn: (s, p) => changesApi.list(s, p),
  responseKey: "changes",
  getItemId: (item) => item.id,
  wsEvents: {
    "change.recorded": { op: "create", idKey: "change_id" },
  },
});

export async function createChange(slug: string, data: ChangeCreate[]): Promise<string[]> {
  return withCreateLoading(useChangeStore, () => changesApi.create(slug, data));
}
