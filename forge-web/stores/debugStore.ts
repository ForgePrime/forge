import { create } from "zustand";

export interface ApiEntry {
  id: number;
  method: string;
  url: string;
  status: number | null;
  duration: number;
  timestamp: number;
  requestBody?: unknown;
  responseBody?: unknown;
  requestHeaders?: Record<string, string>;
  error?: string;
}

interface DebugStoreState {
  entries: ApiEntry[];
  totalRequests: number;
  errorCount: number;

  addEntry: (entry: Omit<ApiEntry, "id">) => void;
  clear: () => void;
  getEntry: (id: number) => ApiEntry | undefined;
}

const MAX_ENTRIES = 200;
let _nextId = 0;

export const useDebugStore = create<DebugStoreState>((set, get) => ({
  entries: [],
  totalRequests: 0,
  errorCount: 0,

  addEntry: (entry) => {
    const id = ++_nextId;
    const full: ApiEntry = { ...entry, id };
    const isError = full.status !== null && full.status >= 400;

    set((state) => {
      const entries = [...state.entries, full];
      // Circular buffer: drop oldest when exceeding max
      if (entries.length > MAX_ENTRIES) {
        entries.splice(0, entries.length - MAX_ENTRIES);
      }
      return {
        entries,
        totalRequests: state.totalRequests + 1,
        errorCount: state.errorCount + (isError ? 1 : 0),
      };
    });
  },

  clear: () => set({ entries: [], totalRequests: 0, errorCount: 0 }),

  getEntry: (id) => get().entries.find((e) => e.id === id),
}));

/** Computed: average response time of all entries. */
export function getAvgResponseTime(): number {
  const entries = useDebugStore.getState().entries;
  if (entries.length === 0) return 0;
  const total = entries.reduce((sum, e) => sum + e.duration, 0);
  return Math.round(total / entries.length);
}
