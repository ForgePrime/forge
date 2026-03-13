"use client";

import { useState, useMemo, useRef, useEffect, useCallback } from "react";
import { useDebugStore, type ApiEntry } from "@/stores/debugStore";
import { RequestDetailPanel } from "./RequestDetailPanel";

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-green-100 text-green-700",
  POST: "bg-blue-100 text-blue-700",
  PATCH: "bg-yellow-100 text-yellow-700",
  PUT: "bg-orange-100 text-orange-700",
  DELETE: "bg-red-100 text-red-700",
};

function statusColor(status: number | null): string {
  if (status === null) return "text-gray-400";
  if (status < 300) return "text-green-400";
  if (status < 400) return "text-yellow-400";
  return "text-red-400";
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatTime(timestamp: number): string {
  const d = new Date(timestamp);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

type MethodFilter = "" | "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

type StatusFilter = "" | "2xx" | "4xx" | "5xx" | "err";

export function ApiInspector({ slug: _slug }: { slug: string | null }) {
  const entries = useDebugStore((s) => s.entries);
  const totalRequests = useDebugStore((s) => s.totalRequests);
  const errorCount = useDebugStore((s) => s.errorCount);
  const clear = useDebugStore((s) => s.clear);

  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [methodFilter, setMethodFilter] = useState<MethodFilter>("");
  const [statusFilterVal, setStatusFilterVal] = useState<StatusFilter>("");
  const [urlFilter, setUrlFilter] = useState("");

  const filtered = useMemo(() => {
    let result = entries;

    if (methodFilter) {
      result = result.filter((e) => e.method === methodFilter);
    }

    if (statusFilterVal) {
      result = result.filter((e) => {
        if (statusFilterVal === "err") return e.status === null || (e.status !== null && e.status >= 400);
        if (statusFilterVal === "2xx") return e.status !== null && e.status >= 200 && e.status < 300;
        if (statusFilterVal === "4xx") return e.status !== null && e.status >= 400 && e.status < 500;
        if (statusFilterVal === "5xx") return e.status !== null && e.status >= 500;
        return true;
      });
    }

    if (urlFilter) {
      const lower = urlFilter.toLowerCase();
      result = result.filter((e) => e.url.toLowerCase().includes(lower));
    }

    return [...result].reverse();
  }, [entries, methodFilter, statusFilterVal, urlFilter]);

  // Auto-scroll state
  const listRef = useRef<HTMLDivElement>(null);
  const prevCountRef = useRef(0);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto-scroll to top when new entries arrive (newest are at top)
  useEffect(() => {
    if (autoScroll && filtered.length > prevCountRef.current && listRef.current) {
      listRef.current.scrollTop = 0;
    }
    prevCountRef.current = filtered.length;
  }, [filtered.length, autoScroll]);

  // Detect manual scroll to pause auto-scroll
  const handleScroll = useCallback(() => {
    if (!listRef.current) return;
    setAutoScroll(listRef.current.scrollTop < 10);
  }, []);

  const avgTime = useMemo(() => {
    if (entries.length === 0) return 0;
    const total = entries.reduce((sum, e) => sum + e.duration, 0);
    return Math.round(total / entries.length);
  }, [entries]);

  const handleExport = () => {
    const data = JSON.stringify(filtered, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `api-inspector-${new Date().toISOString().slice(0, 19)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-2 pb-2 mb-2 flex-shrink-0 flex-wrap" style={{ borderBottom: "1px solid var(--debug-border)" }}>
        <div className="flex items-center gap-1.5 text-[10px]" style={{ color: "var(--debug-text-muted)" }}>
          <span>{totalRequests} total</span>
          <span className="text-gray-300">|</span>
          {errorCount > 0 && (
            <span className="text-red-600 font-medium">{errorCount} errors</span>
          )}
          {errorCount > 0 && <span className="text-gray-300">|</span>}
          <span>avg {formatDuration(avgTime)}</span>
          {!autoScroll && (
            <>
              <span className="text-gray-300">|</span>
              <button
                onClick={() => {
                  if (listRef.current) listRef.current.scrollTop = 0;
                  setAutoScroll(true);
                }}
                className="text-forge-600 hover:text-forge-700"
              >
                Resume auto-scroll
              </button>
            </>
          )}
        </div>

        <div className="ml-auto flex items-center gap-2">
          {/* Method filter */}
          <select
            value={methodFilter}
            onChange={(e) => setMethodFilter(e.target.value as MethodFilter)}
            className="text-[10px] border rounded px-1.5 py-0.5 bg-white"
          >
            <option value="">All methods</option>
            <option value="GET">GET</option>
            <option value="POST">POST</option>
            <option value="PATCH">PATCH</option>
            <option value="PUT">PUT</option>
            <option value="DELETE">DELETE</option>
          </select>

          {/* Status filter */}
          <select
            value={statusFilterVal}
            onChange={(e) => setStatusFilterVal(e.target.value as StatusFilter)}
            className="text-[10px] border rounded px-1.5 py-0.5 bg-white"
          >
            <option value="">All statuses</option>
            <option value="2xx">2xx</option>
            <option value="4xx">4xx</option>
            <option value="5xx">5xx</option>
            <option value="err">Errors</option>
          </select>

          {/* URL filter */}
          <input
            type="text"
            placeholder="Filter URL..."
            value={urlFilter}
            onChange={(e) => setUrlFilter(e.target.value)}
            className="text-[10px] border rounded px-2 py-0.5 w-32"
          />

          <button
            onClick={handleExport}
            className="text-[10px] text-gray-500 hover:text-gray-700 px-1.5 py-0.5 border rounded"
          >
            Export
          </button>
          <button
            onClick={clear}
            className="text-[10px] text-red-500 hover:text-red-700 px-1.5 py-0.5 border rounded"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Entries list */}
      <div
        ref={listRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto relative"
      >
        {filtered.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">
            {entries.length === 0 ? "No API calls captured yet" : "No matching entries"}
          </p>
        )}

        <div className="space-y-px">
          {filtered.map((entry) => (
            <EntryRow
              key={entry.id}
              entry={entry}
              expanded={expandedId === entry.id}
              onToggle={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
            />
          ))}
        </div>

        {/* Scroll to top button */}
        {!autoScroll && filtered.length > 0 && (
          <button
            onClick={() => {
              if (listRef.current) listRef.current.scrollTop = 0;
              setAutoScroll(true);
            }}
            className="sticky bottom-2 left-1/2 -translate-x-1/2 bg-forge-600 text-white text-[10px] px-3 py-1 rounded-full shadow-md hover:bg-forge-700 transition-colors"
          >
            ↑ Scroll to latest
          </button>
        )}
      </div>
    </div>
  );
}

function EntryRow({
  entry,
  expanded,
  onToggle,
}: {
  entry: ApiEntry;
  expanded: boolean;
  onToggle: () => void;
}) {
  const methodClass = METHOD_COLORS[entry.method] ?? "bg-gray-100 text-gray-700";
  const statusClass = statusColor(entry.status);

  return (
    <div style={{ backgroundColor: expanded ? "var(--debug-bg-secondary)" : undefined }}>
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-2 py-1 text-left transition-colors"
        style={{ color: "var(--debug-text-primary)" }}
      >
        <span className={`inline-flex items-center justify-center rounded px-1.5 py-0.5 text-[10px] font-medium w-12 ${methodClass}`}>
          {entry.method}
        </span>
        <span className="text-xs font-mono truncate flex-1">{entry.url}</span>
        <span className={`text-[10px] font-medium w-8 text-right ${statusClass}`}>
          {entry.status ?? "ERR"}
        </span>
        <span className="text-[10px] w-14 text-right tabular-nums" style={{ color: "var(--debug-text-muted)" }}>
          {formatDuration(entry.duration)}
        </span>
        <span className="text-[10px] w-16 text-right" style={{ color: "var(--debug-text-muted)" }}>{formatTime(entry.timestamp)}</span>
        <span className="text-[10px] w-4" style={{ color: "var(--debug-text-muted)" }}>{expanded ? "▼" : "▶"}</span>
      </button>

      {expanded && <RequestDetailPanel entry={entry} />}
    </div>
  );
}
