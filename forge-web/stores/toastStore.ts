import { create } from "zustand";

export interface ToastItem {
  id: string;
  message: string;
  entityId?: string;
  entityType?: string;
  action: "created" | "updated" | "deleted" | "completed" | "failed" | "info";
  project?: string;
  createdAt: number;
}

interface ToastState {
  toasts: ToastItem[];
  addToast: (toast: Omit<ToastItem, "id" | "createdAt">) => void;
  removeToast: (id: string) => void;
  clearAll: () => void;
}

const MAX_VISIBLE = 3;

function genId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],

  addToast: (toast) => {
    const id = `toast-${genId()}`;
    const item: ToastItem = { ...toast, id, createdAt: Date.now() };
    set((state) => {
      // Keep max visible, remove oldest if over limit
      const updated = [...state.toasts, item];
      return { toasts: updated.slice(-MAX_VISIBLE) };
    });
  },

  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },

  clearAll: () => set({ toasts: [] }),
}));
