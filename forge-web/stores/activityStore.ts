import { create } from "zustand";
import type { ActivityEvent } from "@/components/shared/ActivityFeed";

interface ActivityState {
  events: ActivityEvent[];
  addEvent: (event: Omit<ActivityEvent, "id">) => void;
  clear: () => void;
}

const MAX_EVENTS = 50;

let _seq = 0;

export const useActivityStore = create<ActivityState>((set) => ({
  events: [],

  addEvent: (event) => {
    const id = `evt-${++_seq}`;
    set((state) => {
      const updated = [{ ...event, id }, ...state.events];
      return { events: updated.slice(0, MAX_EVENTS) };
    });
  },

  clear: () => set({ events: [] }),
}));
