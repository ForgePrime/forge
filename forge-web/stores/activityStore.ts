import { create } from "zustand";
import type { ActivityEvent } from "@/components/shared/ActivityFeed";

interface ActivityState {
  events: ActivityEvent[];
  /** Last error from WS event parsing or connection. */
  lastError: unknown;
  addEvent: (event: Omit<ActivityEvent, "id">) => void;
  setError: (error: unknown) => void;
  clear: () => void;
}

const MAX_EVENTS = 50;

let _seq = 0;

export const useActivityStore = create<ActivityState>((set) => ({
  events: [],
  lastError: null,

  addEvent: (event) => {
    const id = `evt-${++_seq}`;
    set((state) => {
      const updated = [{ ...event, id }, ...state.events];
      return { events: updated.slice(0, MAX_EVENTS), lastError: null };
    });
  },

  setError: (error) => set({ lastError: error }),

  clear: () => set({ events: [], lastError: null }),
}));
