import { createEntityStore, withUpdate } from "./factory";
import { notifications as notificationsApi } from "@/lib/api";
import type { Notification, NotificationStatusUpdate, NotificationRespond, BulkStatusUpdate } from "@/lib/types";

export const useNotificationEntityStore = createEntityStore<Notification>({
  listFn: (s, p) => notificationsApi.list(s, p),
  responseKey: "notifications",
  getItemId: (item) => item.id,
  wsEvents: {
    "notification.created": { op: "create", idKey: "notification_id" },
    "notification.updated": { op: "update", idKey: "notification_id" },
    "notification.resolved": { op: "update", idKey: "notification_id" },
  },
});

export async function respondToNotification(
  slug: string,
  id: string,
  data: NotificationRespond,
): Promise<void> {
  return withUpdate(
    useNotificationEntityStore,
    (item) => item.id,
    id,
    () => notificationsApi.respond(slug, id, data),
    { status: "RESOLVED" as const },
    { slug, entityPath: "notifications" },
  );
}

export async function markAsRead(slug: string, id: string): Promise<void> {
  return withUpdate(
    useNotificationEntityStore,
    (item) => item.id,
    id,
    () => notificationsApi.update(slug, id, { status: "READ" }),
    { status: "READ" as const },
    { slug, entityPath: "notifications" },
  );
}

export async function dismissNotification(slug: string, id: string): Promise<void> {
  return withUpdate(
    useNotificationEntityStore,
    (item) => item.id,
    id,
    () => notificationsApi.update(slug, id, { status: "DISMISSED" }),
    { status: "DISMISSED" as const },
    { slug, entityPath: "notifications" },
  );
}

export async function markAllRead(slug: string): Promise<void> {
  const data: BulkStatusUpdate = { status: "READ" };
  await notificationsApi.bulkUpdate(slug, data);
  // Refresh the store to reflect bulk changes
  const state = useNotificationEntityStore.getState();
  useNotificationEntityStore.setState({
    items: state.items.map((n) =>
      n.status === "UNREAD" ? { ...n, status: "READ" as const } : n,
    ),
  });
}
