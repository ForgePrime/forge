"use client";

import { useState, useMemo, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { useActivityStore } from "@/stores/activityStore";
import type { ActivityEvent } from "@/components/shared/ActivityFeed";
import { ErrorDetail } from "./ErrorDetail";

// ---------------------------------------------------------------------------
// Event type colors
// ---------------------------------------------------------------------------

const EVENT_TYPE_COLORS: Record<string, string> = {
  task: "bg-blue-100 text-blue-700",
  decision: "bg-purple-100 text-purple-700",
  objective: "bg-indigo-100 text-indigo-700",
  idea: "bg-emerald-100 text-emerald-700",
  change: "bg-orange-100 text-orange-700",
  guideline: "bg-teal-100 text-teal-700",
  knowledge: "bg-cyan-100 text-cyan-700",
  lesson: "bg-amber-100 text-amber-700",
  gate: "bg-red-100 text-red-700",
  ac_template: "bg-pink-100 text-pink-700",
};

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
  gate: "settings",
};

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", fractionalSecondDigits: 3 });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function EventStream({ slug }: { slug: string | null }) {
  const allEvents = useActivityStore((s) => s.events);
  const lastError = useActivityStore((s) => s.lastError);
  const clearEvents = useActivityStore((s) => s.clear);

  const [typeFilters, setTypeFilters] = useState<Set<string>>(new Set());
  const [autoScroll, setAutoScroll] = useState(true);
  const listRef = useRef<HTMLDivElement>(null);
  const prevCountRef = useRef(0);

  // Filter to current project
  const projectEvents = useMemo(
    () => allEvents.filter((e) => e.project === slug),
    [allEvents, slug],
  );

  // Apply type filters
  const filtered = useMemo(() => {
    if (typeFilters.size === 0) return projectEvents;
    return projectEvents.filter((e) => e.entityType && typeFilters.has(e.entityType));
  }, [projectEvents, typeFilters]);

  // Collect unique event types for filter checkboxes
  const uniqueTypes = useMemo(() => {
    const types = new Set<string>();
    for (const e of projectEvents) {
      if (e.entityType) types.add(e.entityType);
    }
    return Array.from(types).sort();
  }, [projectEvents]);

  // Auto-scroll when new events arrive
  useEffect(() => {
    if (autoScroll && filtered.length > prevCountRef.current && listRef.current) {
      listRef.current.scrollTop = 0; // events are newest-first
    }
    prevCountRef.current = filtered.length;
  }, [filtered.length, autoScroll]);

  // Detect user scroll to pause auto-scroll
  const handleScroll = useCallback(() => {
    if (!listRef.current) return;
    const { scrollTop } = listRef.current;
    // If user scrolled away from top, pause auto-scroll
    setAutoScroll(scrollTop < 10);
  }, []);

  const toggleFilter = (type: string) => {
    setTypeFilters((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  if (!slug) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-xs text-gray-400 text-center">
          Navigate to a project to see real-time events
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-2 pb-2 border-b mb-2 flex-shrink-0 flex-wrap">
        <div className="flex items-center gap-1.5 text-[10px] text-gray-500">
          <span className={`h-2 w-2 rounded-full ${projectEvents.length > 0 ? "bg-green-500" : "bg-gray-300"}`} />
          <span>{filtered.length} events</span>
          {!autoScroll && (
            <>
              <span className="text-gray-300">|</span>
              <button
                onClick={() => setAutoScroll(true)}
                className="text-forge-600 hover:text-forge-700"
              >
                Resume auto-scroll
              </button>
            </>
          )}
        </div>

        {/* Type filter chips */}
        {uniqueTypes.length > 0 && (
          <div className="flex gap-1 ml-2">
            {uniqueTypes.map((type) => {
              const active = typeFilters.size === 0 || typeFilters.has(type);
              const colorClass = EVENT_TYPE_COLORS[type] ?? "bg-gray-100 text-gray-600";
              return (
                <button
                  key={type}
                  onClick={() => toggleFilter(type)}
                  className={`px-1.5 py-0.5 text-[9px] rounded font-medium transition-opacity ${colorClass} ${
                    active ? "opacity-100" : "opacity-30"
                  }`}
                >
                  {type}
                </button>
              );
            })}
          </div>
        )}

        <button
          onClick={clearEvents}
          className="ml-auto text-[10px] text-red-500 hover:text-red-700 px-1.5 py-0.5 border rounded"
        >
          Clear
        </button>
      </div>

      {/* WS error */}
      {lastError != null ? (
        <div className="mb-2">
          <ErrorDetail error={lastError} id="event-stream-ws-error" />
        </div>
      ) : null}

      {/* Event list */}
      <div
        ref={listRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto"
      >
        {filtered.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">
            No events yet — events appear as WebSocket messages arrive
          </p>
        )}

        <div className="space-y-px">
          {filtered.map((event) => (
            <EventRow key={event.id} event={event} slug={slug} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Event Row
// ---------------------------------------------------------------------------

function EventRow({ event, slug }: { event: ActivityEvent; slug: string }) {
  const typeColor = EVENT_TYPE_COLORS[event.entityType ?? ""] ?? "bg-gray-100 text-gray-600";
  const route = event.entityType ? ENTITY_ROUTES[event.entityType] : null;
  const href = route && event.entityId
    ? `/projects/${slug}/${route}/${event.entityId}`
    : null;

  return (
    <div className="flex items-center gap-2 px-2 py-1 hover:bg-gray-50 text-[10px]">
      <span className="text-gray-300 tabular-nums w-20 flex-shrink-0">{formatTime(event.timestamp)}</span>
      <span className={`inline-flex items-center justify-center rounded px-1.5 py-0.5 font-medium w-16 text-center flex-shrink-0 ${typeColor}`}>
        {event.entityType ?? "?"}
      </span>
      <span className="text-gray-500 w-14 flex-shrink-0 font-medium">{event.action}</span>
      {href ? (
        <Link href={href} className="text-gray-700 hover:text-forge-600 truncate flex-1">
          {event.message}
        </Link>
      ) : (
        <span className="text-gray-700 truncate flex-1">{event.message}</span>
      )}
      {event.entityId && (
        <span className="text-gray-400 font-mono flex-shrink-0">{event.entityId}</span>
      )}
    </div>
  );
}
