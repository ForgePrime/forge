"use client";

import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { useEntityData } from "@/hooks/useEntityData";
import { notifications as notificationsApi } from "@/lib/api";
import { markAsRead, dismissNotification, markAllRead } from "@/stores/notificationEntityStore";
import type { Notification, NotificationPriority, NotificationType } from "@/lib/types";

// ---------------------------------------------------------------------------
// Priority / type constants
// ---------------------------------------------------------------------------

const PRIORITY_ORDER: Record<NotificationPriority, number> = {
  critical: 0,
  high: 1,
  normal: 2,
  low: 3,
};

const PRIORITY_STYLES: Record<NotificationPriority, { badge: string; dot: string }> = {
  critical: { badge: "bg-red-100 text-red-700", dot: "bg-red-500" },
  high: { badge: "bg-orange-100 text-orange-700", dot: "bg-orange-500" },
  normal: { badge: "bg-blue-100 text-blue-700", dot: "bg-blue-500" },
  low: { badge: "bg-gray-100 text-gray-500", dot: "bg-gray-400" },
};

const TYPE_CONFIG: Record<NotificationType, { icon: string; style: string; label: string }> = {
  decision: { icon: "D", style: "bg-purple-100 text-purple-600", label: "Decision" },
  approval: { icon: "A", style: "bg-green-100 text-green-600", label: "Approval" },
  question: { icon: "?", style: "bg-amber-100 text-amber-600", label: "Question" },
  alert: { icon: "!", style: "bg-red-100 text-red-600", label: "Alert" },
};

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}

function isBlocking(n: Notification): boolean {
  return n.notification_type === "decision" || n.notification_type === "approval" || n.notification_type === "question";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const params = useParams();
  const slug = params?.slug as string | undefined;

  // SWR-based reactive data (auto-revalidates on WS events via wsDispatcher)
  const { items: rawItems, isLoading } = useEntityData<Notification>(
    slug ?? null,
    "notifications",
  );

  // Also fetch unread count from API for accurate badge
  const { items: unreadItems } = useEntityData<Notification>(
    slug ?? null,
    "notifications",
    { status: "UNREAD" },
  );

  const unreadCount = unreadItems.length;

  // Sort: priority (critical first) then newest first
  const sortedItems = [...rawItems]
    .filter((n) => n.status !== "DISMISSED" && n.status !== "RESOLVED")
    .sort((a, b) => {
      const pa = PRIORITY_ORDER[a.priority] ?? 2;
      const pb = PRIORITY_ORDER[b.priority] ?? 2;
      if (pa !== pb) return pa - pb;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const handleDismiss = async (n: Notification, e: React.MouseEvent) => {
    e.stopPropagation();
    if (slug) {
      await dismissNotification(slug, n.id);
    }
  };

  const handleMarkRead = async (n: Notification) => {
    if (slug && n.status === "UNREAD") {
      await markAsRead(slug, n.id);
    }
  };

  const handleDismissAll = async () => {
    if (slug) {
      await markAllRead(slug);
    }
  };

  const handleRespond = (n: Notification, e: React.MouseEvent) => {
    e.stopPropagation();
    // Response modal will be implemented in T-025/T-026
    // For now, mark as read and navigate to source entity
    handleMarkRead(n);
  };

  return (
    <div ref={panelRef} className="relative">
      {/* Bell icon */}
      <button
        onClick={() => setOpen(!open)}
        className="relative flex items-center justify-center w-8 h-8 rounded-md text-gray-300 hover:text-white hover:bg-gray-800 transition-colors"
        title="Notifications"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
            {unreadCount > 99 ? "99" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute right-0 top-full mt-1 w-96 max-h-[28rem] overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-xl z-[100]">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 border-b bg-gray-50">
            <span className="text-xs font-semibold text-gray-600">
              Notifications {unreadCount > 0 && `(${unreadCount} unread)`}
            </span>
            {unreadCount > 0 && (
              <button
                onClick={handleDismissAll}
                className="text-[10px] text-gray-400 hover:text-gray-600"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* Items */}
          {isLoading && sortedItems.length === 0 && (
            <p className="p-3 text-xs text-gray-400">Loading...</p>
          )}

          {!isLoading && sortedItems.length === 0 && (
            <p className="p-3 text-xs text-gray-400">No pending notifications</p>
          )}

          {sortedItems.map((n) => {
            const typeConf = TYPE_CONFIG[n.notification_type] ?? TYPE_CONFIG.alert;
            const prioStyle = PRIORITY_STYLES[n.priority] ?? PRIORITY_STYLES.normal;
            const unread = n.status === "UNREAD";

            return (
              <div
                key={n.id}
                onClick={() => handleMarkRead(n)}
                className={`flex items-start gap-2 px-3 py-2.5 cursor-pointer border-b border-gray-100 last:border-b-0 ${
                  unread ? "bg-blue-50/40 hover:bg-blue-50" : "hover:bg-gray-50"
                }`}
              >
                {/* Unread dot */}
                <div className="w-2 flex-shrink-0 pt-2">
                  {unread && (
                    <span className={`inline-block w-2 h-2 rounded-full ${prioStyle.dot}`} />
                  )}
                </div>

                {/* Type icon */}
                <span className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center text-[10px] font-bold ${typeConf.style}`}>
                  {typeConf.icon}
                </span>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className={`text-xs line-clamp-2 ${unread ? "text-gray-900 font-medium" : "text-gray-600"}`}>
                    {n.title}
                  </p>
                  <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                    {/* Type badge */}
                    <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${typeConf.style}`}>
                      {typeConf.label}
                    </span>
                    {/* Priority badge */}
                    {n.priority !== "normal" && (
                      <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${prioStyle.badge}`}>
                        {n.priority}
                      </span>
                    )}
                    {/* Workflow ID */}
                    {n.workflow_id && (
                      <span className="text-[9px] text-gray-400">{n.workflow_id}</span>
                    )}
                    {/* Timestamp */}
                    <span className="text-[9px] text-gray-400">{relativeTime(n.created_at)}</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-1 flex-shrink-0">
                  {isBlocking(n) && n.status !== "RESOLVED" && (
                    <button
                      onClick={(e) => handleRespond(n, e)}
                      className="text-[10px] px-2 py-0.5 bg-blue-500 text-white rounded hover:bg-blue-600"
                      title="Respond"
                    >
                      Respond
                    </button>
                  )}
                  <button
                    onClick={(e) => handleDismiss(n, e)}
                    className="text-gray-300 hover:text-gray-500 text-xs"
                    title="Dismiss"
                  >
                    x
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
