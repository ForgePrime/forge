import type { ComponentType } from "react";
import type { Notification } from "@/lib/types";
import { DecisionRenderer } from "./renderers/DecisionRenderer";
import { ApprovalRenderer } from "./renderers/ApprovalRenderer";
import { QuestionRenderer } from "./renderers/QuestionRenderer";
import { AlertRenderer } from "./renderers/AlertRenderer";

/**
 * Props passed to notification type-specific renderers.
 * Each renderer provides the content + actions for its notification type.
 */
export interface NotificationRendererProps {
  notification: Notification;
  onRespond: (response: string, action?: string) => Promise<void>;
  onDismiss: () => Promise<void>;
  loading: boolean;
}

/**
 * Registry of notification type renderers (D-016: pluggable content slots).
 * Each notification_type maps to a React component that renders the detail view.
 * New types can be added by registering a renderer here.
 */
export const NOTIFICATION_RENDERERS = new Map<
  string,
  ComponentType<NotificationRendererProps>
>();

/**
 * Register a renderer for a notification type.
 */
export function registerRenderer(
  type: string,
  component: ComponentType<NotificationRendererProps>,
): void {
  NOTIFICATION_RENDERERS.set(type, component);
}

// Register built-in renderers
NOTIFICATION_RENDERERS.set("decision", DecisionRenderer);
NOTIFICATION_RENDERERS.set("approval", ApprovalRenderer);
NOTIFICATION_RENDERERS.set("question", QuestionRenderer);
NOTIFICATION_RENDERERS.set("alert", AlertRenderer);
