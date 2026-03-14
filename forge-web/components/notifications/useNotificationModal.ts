"use client";

import { create } from "zustand";
import type { Notification } from "@/lib/types";

interface NotificationModalState {
  notification: Notification | null;
  popupQueue: Notification[];
  open: (n: Notification) => void;
  close: () => void;
  enqueuePopup: (n: Notification) => void;
  dequeuePopup: () => void;
}

export const useNotificationModal = create<NotificationModalState>((set) => ({
  notification: null,
  popupQueue: [],
  open: (n) => set({ notification: n }),
  close: () => set({ notification: null }),
  enqueuePopup: (n) =>
    set((state) => {
      // Dedup: skip if same source entity already queued
      if (state.popupQueue.some((q) => q.source_entity_id === n.source_entity_id)) return state;
      return { popupQueue: [...state.popupQueue, n] };
    }),
  dequeuePopup: () =>
    set((state) => ({ popupQueue: state.popupQueue.slice(1) })),
}));
