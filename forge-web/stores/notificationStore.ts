/**
 * Notification store — persistent decision notifications that require user action.
 *
 * Unlike toasts (auto-dismiss), these stay until the user takes action
 * (View, Close, Defer, or dismiss).
 */
import { create } from "zustand";

export interface DecisionNotification {
  id: string;
  decisionId: string;
  type: string;
  issue: string;
  taskId?: string;
  severity?: string;
  project?: string;
  createdAt: number;
}

interface NotificationState {
  decisions: DecisionNotification[];
  addDecision: (n: Omit<DecisionNotification, "id" | "createdAt">) => void;
  removeDecision: (id: string) => void;
  clearAll: () => void;
}

function genId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

export const useNotificationStore = create<NotificationState>((set) => ({
  decisions: [],

  addDecision: (n) => {
    const id = `notif-${genId()}`;
    set((state) => ({
      decisions: [...state.decisions, { ...n, id, createdAt: Date.now() }],
    }));
  },

  removeDecision: (id) => {
    set((state) => ({
      decisions: state.decisions.filter((d) => d.id !== id),
    }));
  },

  clearAll: () => set({ decisions: [] }),
}));
