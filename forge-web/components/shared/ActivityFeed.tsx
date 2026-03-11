"use client";

import { useState } from "react";
import Link from "next/link";

export interface ActivityEvent {
  id: string;
  event: string;
  entityId?: string;
  entityType?: string;
  project: string;
  timestamp: string;
  message: string;
  action: string;
}

interface ActivityFeedProps {
  events: ActivityEvent[];
  /** Compact mode — smaller text, no borders */
  compact?: boolean;
  /** Max events to show (default: 20) */
  limit?: number;
  /** Filter by entity type */
  entityTypeFilter?: string;
  /** Show project name in each entry */
  showProject?: boolean;
}

const ENTITY_ROUTES: Record<string, string> = {
  task: "tasks",
  decision: "decisions",
  objective: "objectives",
  idea: "ideas",
  change: "changes",
  guideline: "guidelines",
  knowledge: "knowledge",
  lesson: "lessons",
  ac_template: "ac-templates",
  gate: "gates",
};

const ACTION_ICONS: Record<string, { icon: string; color: string }> = {
  created: { icon: "+", color: "text-green-500 bg-green-50" },
  updated: { icon: "~", color: "text-blue-500 bg-blue-50" },
  deleted: { icon: "x", color: "text-red-500 bg-red-50" },
  completed: { icon: "v", color: "text-green-600 bg-green-50" },
  failed: { icon: "!", color: "text-red-600 bg-red-50" },
  status_changed: { icon: "->", color: "text-amber-500 bg-amber-50" },
  closed: { icon: "v", color: "text-green-500 bg-green-50" },
};

function formatRelativeTime(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function ActivityFeed({
  events,
  compact = false,
  limit = 20,
  entityTypeFilter,
  showProject = false,
}: ActivityFeedProps) {
  const [expanded, setExpanded] = useState(false);

  let filtered = entityTypeFilter
    ? events.filter((e) => e.entityType === entityTypeFilter)
    : events;

  const total = filtered.length;
  const displayLimit = expanded ? total : limit;
  filtered = filtered.slice(0, displayLimit);

  if (filtered.length === 0) {
    return <p className="text-sm text-gray-400">No activity</p>;
  }

  return (
    <div className={compact ? "space-y-1" : "space-y-2"}>
      {filtered.map((event) => {
        const actionInfo = ACTION_ICONS[event.action] ?? { icon: "?", color: "text-gray-500 bg-gray-50" };
        const route = event.entityType ? ENTITY_ROUTES[event.entityType] : null;
        const href = route && event.entityId
          ? `/projects/${event.project}/${route}/${event.entityId}`
          : null;

        return (
          <div
            key={event.id}
            className={`flex items-start gap-2 ${
              compact ? "py-1" : "p-2 rounded-lg border bg-white"
            }`}
          >
            <span
              className={`flex-shrink-0 w-5 h-5 rounded-full ${actionInfo.color} text-[10px] font-bold flex items-center justify-center mt-0.5`}
            >
              {actionInfo.icon}
            </span>
            <div className="flex-1 min-w-0">
              <p className={`${compact ? "text-xs" : "text-sm"} text-gray-700 line-clamp-1`}>
                {href ? (
                  <Link href={href} className="hover:text-forge-600 hover:underline">
                    {event.message}
                  </Link>
                ) : (
                  event.message
                )}
              </p>
              <div className="flex items-center gap-2">
                {event.entityId && (
                  <span className="text-[10px] text-gray-400 font-mono">{event.entityId}</span>
                )}
                {showProject && (
                  <span className="text-[10px] text-gray-400">{event.project}</span>
                )}
                <span className="text-[10px] text-gray-400">{formatRelativeTime(event.timestamp)}</span>
              </div>
            </div>
          </div>
        );
      })}

      {total > limit && !expanded && (
        <button
          onClick={() => setExpanded(true)}
          className="text-xs text-forge-600 hover:text-forge-700"
        >
          Show {total - limit} more...
        </button>
      )}
    </div>
  );
}
