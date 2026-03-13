"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { projects as projectsApi, decisions as decisionsApi, llm } from "@/lib/api";
import type { Decision } from "@/lib/types";
import type { ChatSessionSummary } from "@/stores/chatStore";

const DISMISSED_KEY = "forge:dismissed-notifications";

interface NotificationItem {
  id: string;          // unique key for dedup + dismiss
  type: "decision" | "session";
  icon: string;
  title: string;
  project?: string;
  href: string;
  createdAt: string;
}

function loadDismissed(): Set<string> {
  try {
    const raw = localStorage.getItem(DISMISSED_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

function saveDismissed(set: Set<string>): void {
  try {
    // Keep only last 500 dismissed IDs to prevent unbounded growth
    const arr = Array.from(set).slice(-500);
    localStorage.setItem(DISMISSED_KEY, JSON.stringify(arr));
  } catch { /* localStorage full — ignore */ }
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}

export function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Load dismissed set on mount
  useEffect(() => {
    setDismissed(loadDismissed());
  }, []);

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

  // Fetch notifications
  const fetchItems = useCallback(async () => {
    setLoading(true);
    const all: NotificationItem[] = [];

    try {
      // 1. Fetch open decisions across all projects
      const { projects: slugs } = await projectsApi.list();
      const decisionPromises = slugs.map(async (slug) => {
        try {
          const { decisions } = await decisionsApi.list(slug, { status: "OPEN" });
          return decisions.map((d: Decision) => ({
            id: `decision:${slug}:${d.id}`,
            type: "decision" as const,
            icon: d.type === "risk" ? "!" : "D",
            title: d.issue,
            project: slug,
            href: `/projects/${slug}/decisions/${d.id}`,
            createdAt: d.created_at,
          }));
        } catch {
          return [];
        }
      });
      const decisionResults = await Promise.all(decisionPromises);
      for (const batch of decisionResults) {
        all.push(...batch);
      }

      // 2. Fetch paused sessions
      try {
        const { sessions } = await llm.listSessions(200);
        for (const s of sessions as ChatSessionSummary[]) {
          if (s.session_status === "paused") {
            all.push({
              id: `session:${s.session_id}`,
              type: "session",
              icon: "P",
              title: s.blocked_by_decision_id
                ? `Paused: awaiting ${s.blocked_by_decision_id}`
                : "Session paused",
              project: s.project || undefined,
              href: `/sessions/${s.session_id}`,
              createdAt: s.updated_at,
            });
          }
        }
      } catch { /* ignore session fetch failures */ }

    } catch { /* ignore project fetch failures */ }

    // Sort by date descending
    all.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
    setItems(all);
    setLoading(false);
  }, []);

  // Fetch when opened
  useEffect(() => {
    if (open) fetchItems();
  }, [open, fetchItems]);

  // Periodic background refresh for badge count (every 30s)
  useEffect(() => {
    fetchItems();
    const interval = setInterval(fetchItems, 30_000);
    return () => clearInterval(interval);
  }, [fetchItems]);

  const visibleItems = items.filter((item) => !dismissed.has(item.id));
  const unreadCount = visibleItems.length;

  const handleDismiss = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const next = new Set(dismissed);
    next.add(id);
    setDismissed(next);
    saveDismissed(next);
  };

  const handleClick = (item: NotificationItem) => {
    router.push(item.href);
    setOpen(false);
  };

  const handleDismissAll = () => {
    const next = new Set(dismissed);
    for (const item of visibleItems) next.add(item.id);
    setDismissed(next);
    saveDismissed(next);
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
        <div className="absolute right-0 top-full mt-1 w-80 max-h-96 overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-xl z-[100]">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 border-b bg-gray-50">
            <span className="text-xs font-semibold text-gray-600">
              Notifications {unreadCount > 0 && `(${unreadCount})`}
            </span>
            {unreadCount > 0 && (
              <button
                onClick={handleDismissAll}
                className="text-[10px] text-gray-400 hover:text-gray-600"
              >
                Dismiss all
              </button>
            )}
          </div>

          {/* Items */}
          {loading && visibleItems.length === 0 && (
            <p className="p-3 text-xs text-gray-400">Loading...</p>
          )}

          {!loading && visibleItems.length === 0 && (
            <p className="p-3 text-xs text-gray-400">No pending notifications</p>
          )}

          {visibleItems.map((item) => (
            <div
              key={item.id}
              onClick={() => handleClick(item)}
              className="flex items-start gap-2 px-3 py-2.5 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0"
            >
              {/* Type icon */}
              <span className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center text-[10px] font-bold ${
                item.type === "decision"
                  ? item.icon === "!" ? "bg-red-100 text-red-600" : "bg-purple-100 text-purple-600"
                  : "bg-amber-100 text-amber-600"
              }`}>
                {item.icon}
              </span>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-800 line-clamp-2">{item.title}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  {item.project && (
                    <span className="text-[10px] text-gray-400">{item.project}</span>
                  )}
                  <span className="text-[10px] text-gray-400">{relativeTime(item.createdAt)}</span>
                </div>
              </div>

              {/* Dismiss */}
              <button
                onClick={(e) => handleDismiss(item.id, e)}
                className="text-gray-300 hover:text-gray-500 text-xs flex-shrink-0"
                title="Dismiss"
              >
                x
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
