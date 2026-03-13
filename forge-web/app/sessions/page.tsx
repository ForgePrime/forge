"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import useSWR, { mutate } from "swr";
import { useChatStore } from "@/stores/chatStore";
import type { ChatSessionSummary } from "@/stores/chatStore";
import { StatusFilter } from "@/components/shared/StatusFilter";

const SESSION_TYPES = ["chat", "plan", "execute", "verify", "compound"];
const SESSION_STATUSES = ["active", "paused", "completed", "failed"];

/** SWR cache key for sessions list. Exported for WS revalidation. */
export const SESSIONS_SWR_KEY = "/llm/sessions?limit=200";

/** Format token count (e.g., 12345 → "12.3k"). */
function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

/** Relative time label (e.g., "5m ago", "2h ago"). */
function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

/** Badge color per session type. */
function typeBadgeColor(type?: string): string {
  switch (type) {
    case "plan": return "bg-blue-100 text-blue-700";
    case "execute": return "bg-green-100 text-green-700";
    case "verify": return "bg-amber-100 text-amber-700";
    case "compound": return "bg-purple-100 text-purple-700";
    default: return "bg-gray-100 text-gray-600";
  }
}

/** Status dot color. */
function statusDotColor(status?: string): string {
  switch (status) {
    case "active": return "bg-green-500";
    case "paused": return "bg-amber-400";
    case "completed": return "bg-blue-400";
    case "failed": return "bg-red-500";
    default: return "bg-gray-400";
  }
}

export default function SessionsPage() {
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [projectFilter, setProjectFilter] = useState("");
  const [search, setSearch] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const router = useRouter();
  const { deleteSession } = useChatStore();

  // SWR-managed data fetching — auto-revalidates on WS events
  const { data, error, isLoading } = useSWR<{ sessions: ChatSessionSummary[]; count: number }>(SESSIONS_SWR_KEY);
  const sessions: ChatSessionSummary[] = (data?.sessions as ChatSessionSummary[]) ?? [];

  // Unique projects for filter dropdown
  const projects = useMemo(() => {
    const set = new Set<string>();
    for (const s of sessions) {
      if (s.project) set.add(s.project);
    }
    return Array.from(set).sort();
  }, [sessions]);

  // Filtered sessions
  const filtered = useMemo(() => {
    return sessions.filter((s) => {
      if (typeFilter && s.session_type !== typeFilter) return false;
      if (statusFilter && s.session_status !== statusFilter) return false;
      if (projectFilter && s.project !== projectFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        const haystack = [
          s.session_id,
          s.context_type,
          s.context_id,
          s.project,
          s.model_used,
          s.target_entity_type,
          s.target_entity_id,
        ].join(" ").toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [sessions, typeFilter, statusFilter, projectFilter, search]);

  // Stats
  const stats = useMemo(() => {
    const totalTokens = sessions.reduce((a, s) => a + s.total_tokens_in + s.total_tokens_out, 0);
    const totalCost = sessions.reduce((a, s) => a + s.estimated_cost, 0);
    const active = sessions.filter((s) => s.session_status === "active").length;
    return { total: sessions.length, active, totalTokens, totalCost };
  }, [sessions]);

  const handleDelete = async (sessionId: string) => {
    if (!confirm("Delete this session?")) return;
    try {
      await deleteSession(sessionId);
      // Revalidate SWR cache after deletion
      mutate(SESSIONS_SWR_KEY);
    } catch (e) {
      setDeleteError((e as Error).message);
    }
  };

  const displayError = error ? (error as Error).message : deleteError;

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">
          Sessions
          <span className="text-base font-normal text-gray-400 ml-2">({stats.total})</span>
        </h1>
        <div className="flex items-center gap-4 text-sm text-gray-500">
          <span>{stats.active} active</span>
          <span>{fmtTokens(stats.totalTokens)} tokens</span>
          <span>${stats.totalCost.toFixed(4)}</span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search sessions..."
          className="flex-1 rounded-md border px-3 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
        />
        <StatusFilter options={SESSION_TYPES} value={typeFilter} onChange={setTypeFilter} label="Type" />
        <StatusFilter options={SESSION_STATUSES} value={statusFilter} onChange={setStatusFilter} />
        {projects.length > 1 && (
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-500">Project:</label>
            <select
              value={projectFilter}
              onChange={(e) => setProjectFilter(e.target.value)}
              className="rounded-md border px-2 py-1 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
            >
              <option value="">All</option>
              {projects.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
        )}
        <button
          onClick={() => mutate(SESSIONS_SWR_KEY)}
          className="px-3 py-1.5 text-sm text-gray-600 border rounded-md hover:bg-gray-50"
        >
          Refresh
        </button>
      </div>

      {/* Error */}
      {displayError && (
        <div className="flex items-center justify-between bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-4">
          <p className="text-sm text-red-600">{displayError}</p>
          <button onClick={() => setDeleteError(null)} className="text-xs text-red-400 hover:text-red-600">Dismiss</button>
        </div>
      )}

      {isLoading && <p className="text-sm text-gray-400">Loading sessions...</p>}

      {/* Session cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {filtered.map((session) => (
          <div
            key={session.session_id}
            onClick={() => router.push(`/sessions/${session.session_id}`)}
            className="border rounded-lg p-4 hover:shadow-md transition-shadow bg-white cursor-pointer"
          >
            {/* Top row: type badge + status dot + time */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${typeBadgeColor(session.session_type)}`}>
                  {session.session_type || "chat"}
                </span>
                <span className={`w-2 h-2 rounded-full ${statusDotColor(session.session_status)}`} title={session.session_status || "active"} />
                {session.target_entity_id && (
                  <span className="text-xs text-gray-500 font-mono">{session.target_entity_id}</span>
                )}
              </div>
              <span className="text-xs text-gray-400" title={session.updated_at}>
                {relativeTime(session.updated_at)}
              </span>
            </div>

            {/* Context info */}
            <div className="mb-2">
              <p className="text-sm font-medium text-gray-800 truncate">
                {session.context_type}{session.context_id ? `: ${session.context_id}` : ""}
              </p>
              {session.project && (
                <p className="text-xs text-gray-500">{session.project}</p>
              )}
            </div>

            {/* Paused: awaiting decision indicator */}
            {session.session_status === "paused" && session.blocked_by_decision_id && (
              <div className="flex items-center gap-1.5 mb-2 px-2 py-1 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                Awaiting decision <span className="font-mono">{session.blocked_by_decision_id}</span>
              </div>
            )}

            {/* Snippet (search results) */}
            {session.snippet && (
              <p className="text-xs text-gray-500 italic mb-2 truncate">{session.snippet}</p>
            )}

            {/* Stats row */}
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <span title="Messages">{session.message_count} msgs</span>
              <span title="Input tokens">{fmtTokens(session.total_tokens_in)} in</span>
              <span title="Output tokens">{fmtTokens(session.total_tokens_out)} out</span>
              {session.model_used && (
                <span className="text-gray-400 truncate max-w-[120px]" title={session.model_used}>
                  {session.model_used.split("/").pop()}
                </span>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end mt-3 gap-2">
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(session.session_id); }}
                className="text-xs text-red-400 hover:text-red-600"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {!isLoading && filtered.length === 0 && (
        <p className="text-sm text-gray-400 mt-4">
          {sessions.length === 0
            ? "No sessions yet. Start a conversation with the AI to create one."
            : "No sessions matching filters."}
        </p>
      )}
    </div>
  );
}
