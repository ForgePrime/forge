import { create } from "zustand";
import type { ForgeEvent } from "@/lib/ws";

// --- Types ---

export interface EntitySliceState<T> {
  items: T[];
  count: number;
  loading: boolean;
  error: string | null;
}

interface WsEventMapping {
  op: "create" | "update" | "remove" | "replace";
  idKey?: string;
}

export interface EntityStoreConfig<T> {
  listFn: (
    slug: string,
    params?: Record<string, string>,
  ) => Promise<{ count: number; [key: string]: unknown }>;
  responseKey: string;
  getItemId: (item: T) => string;
  wsEvents: Record<string, WsEventMapping>;
}

export interface EntityBaseActions<T> {
  fetchAll: (slug: string, params?: Record<string, string>) => Promise<void>;
  handleWsEvent: (event: ForgeEvent) => void;
  clear: () => void;
}

export type EntityStoreType<T> = EntitySliceState<T> & EntityBaseActions<T>;

// --- Factory ---

export function createEntityStore<T>(config: EntityStoreConfig<T>) {
  let _fetchSeq = 0;

  return create<EntityStoreType<T>>((set, get) => ({
    items: [],
    count: 0,
    loading: false,
    error: null,

    fetchAll: async (slug, params) => {
      const seq = ++_fetchSeq;
      set({ loading: true, error: null });
      try {
        const res = await config.listFn(slug, params);
        if (_fetchSeq !== seq) return;
        const items = (res as Record<string, unknown>)[
          config.responseKey
        ] as T[];
        set({ items, count: res.count, loading: false });
      } catch (e) {
        if (_fetchSeq !== seq) return;
        set({ error: (e as Error).message, loading: false });
      }
    },

    handleWsEvent: (event: ForgeEvent) => {
      const mapping = config.wsEvents[event.event];
      if (!mapping) return;
      const { op, idKey } = mapping;
      const payload = event.payload as Record<string, unknown>;
      const payloadId =
        ((idKey ? payload[idKey] : payload.id) as string) ?? undefined;

      const state = get();
      switch (op) {
        case "update": {
          if (!payloadId) return;
          const mergeData = { ...payload };
          if ("new_status" in mergeData) {
            mergeData.status = mergeData.new_status;
            delete mergeData.new_status;
            delete mergeData.old_status;
          }
          set({
            items: state.items.map((item) =>
              config.getItemId(item) === payloadId
                ? ({ ...item, ...mergeData } as T)
                : item,
            ),
          });
          break;
        }
        case "remove": {
          if (!payloadId) return;
          const filtered = state.items.filter(
            (item) => config.getItemId(item) !== payloadId,
          );
          set({ items: filtered, count: filtered.length });
          break;
        }
        case "replace": {
          const arr = Object.values(payload).find(Array.isArray) as
            | T[]
            | undefined;
          if (arr) set({ items: arr, count: arr.length });
          break;
        }
        case "create":
        default: {
          if (!payloadId) return;
          if (
            state.items.some(
              (item) => config.getItemId(item) === payloadId,
            )
          )
            return;
          const items = [...state.items, payload as unknown as T];
          set({ items, count: items.length });
          break;
        }
      }
    },

    clear: () => set({ items: [], count: 0, loading: false, error: null }),
  }));
}

// --- CRUD Helpers ---

type StoreApi<T> = {
  getState: () => EntitySliceState<T>;
  setState: (partial: Partial<EntitySliceState<T>>) => void;
};

export async function withCreateLoading<T>(
  store: StoreApi<T>,
  fn: () => Promise<{ added: string[]; total: number }>,
): Promise<string[]> {
  store.setState({ loading: true, error: null });
  try {
    const res = await fn();
    store.setState({ loading: false });
    return res.added;
  } catch (e) {
    store.setState({ error: (e as Error).message, loading: false });
    throw e;
  }
}

export async function withUpdate<T>(
  store: StoreApi<T>,
  getItemId: (item: T) => string,
  id: string,
  fn: () => Promise<T>,
): Promise<void> {
  try {
    const updated = await fn();
    const state = store.getState();
    store.setState({
      items: state.items.map((item) =>
        getItemId(item) === id ? updated : item,
      ),
    } as Partial<EntitySliceState<T>>);
  } catch (e) {
    store.setState({ error: (e as Error).message });
  }
}
