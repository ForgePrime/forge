import { createEntityStore, withCreateLoading, withUpdate } from "./factory";
import { decisions as decisionsApi } from "@/lib/api";
import type { Decision, DecisionCreate, DecisionUpdate } from "@/lib/types";

export const useDecisionStore = createEntityStore<Decision>({
  listFn: (s, p) => decisionsApi.list(s, p),
  responseKey: "decisions",
  getItemId: (item) => item.id,
  wsEvents: {
    "decision.created": { op: "create", idKey: "decision_id" },
    "decision.updated": { op: "update", idKey: "decision_id" },
    "decision.closed": { op: "update", idKey: "decision_id" },
  },
});

export async function createDecision(slug: string, data: DecisionCreate[]): Promise<string[]> {
  return withCreateLoading(useDecisionStore, () => decisionsApi.create(slug, data));
}

export async function updateDecision(slug: string, id: string, data: DecisionUpdate): Promise<void> {
  return withUpdate(useDecisionStore, (item) => item.id, id, () => decisionsApi.update(slug, id, data));
}
