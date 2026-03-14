"use client";

import { useEffect } from "react";
import { useNotificationModal } from "./useNotificationModal";

/**
 * Processes the popup queue from useNotificationModal.
 * When a notification is queued (by wsDispatcher) and the modal is free,
 * opens it for user action.
 */
export function NotificationPopupManager() {
  const popupQueue = useNotificationModal((s) => s.popupQueue);
  const dequeuePopup = useNotificationModal((s) => s.dequeuePopup);
  const modalNotification = useNotificationModal((s) => s.notification);
  const openModal = useNotificationModal((s) => s.open);

  useEffect(() => {
    if (popupQueue.length === 0 || modalNotification !== null) return;
    const next = popupQueue[0];
    openModal(next);
    dequeuePopup();
  }, [popupQueue, modalNotification, openModal, dequeuePopup]);

  return null;
}
