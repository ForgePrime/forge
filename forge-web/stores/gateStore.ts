import { createEntityStore } from "./factory";
import { gates as gatesApi } from "@/lib/api";
import type { Gate, GateCreate } from "@/lib/types";

export const useGateStore = createEntityStore<Gate>({
  listFn: (s) => gatesApi.list(s),
  responseKey: "gates",
  getItemId: (item) => item.name,
  wsEvents: {
    "gate.configured": { op: "replace" },
  },
});

export async function createGate(slug: string, data: GateCreate[]): Promise<void> {
  useGateStore.setState({ loading: true, error: null });
  try {
    await gatesApi.create(slug, data);
    useGateStore.setState({ loading: false });
  } catch (e) {
    useGateStore.setState({ error: (e as Error).message, loading: false });
    throw e;
  }
}
