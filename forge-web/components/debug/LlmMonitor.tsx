"use client";

import { useState, useMemo, useCallback } from "react";
import useSWR from "swr";
import { debug as debugApi } from "@/lib/api";
import type { DebugSessionSummary, DebugSession, DebugStatus } from "@/lib/types";
import { ErrorDetail } from "./ErrorDetail";
import { JsonView } from "./JsonView";

// ---------------------------------------------------------------------------
// Status colors
// ---------------------------------------------------------------------------

const STATUS_COLORS: Record<string, string> = {
  success: "bg-green-100 text-green-700",
  error: "bg-red-100 text-red-700",
  validation_failed: "bg-yellow-100 text-yellow-700",
  pending: "bg-gray-100 text-gray-500",
};

function formatTokens(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function LlmMonitor({ slug }: { slug: string | null }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [taskFilter, setTaskFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Debug status (SWR key is null when slug is null — no fetch)
  const { data: statusData, mutate: refreshStatus } = useSWR<DebugStatus>(
    slug ? `debug-status-${slug}` : null,
    () => debugApi.status(slug!),
    { refreshInterval: 10000 },
  );

  // Session list
  const params: Record<string, string> = {};
  if (taskFilter) params.task_id = taskFilter;
  if (statusFilter) params.status = statusFilter;

  const { data: sessionsData, mutate: refreshSessions } = useSWR(
    slug ? `debug-sessions-${slug}-${taskFilter}-${statusFilter}` : null,
    () => debugApi.sessions(slug!, { ...params, limit: 100 }),
    { refreshInterval: 5000 },
  );

  const sessions = sessionsData?.sessions ?? [];

  const [actionError, setActionError] = useState<unknown>(null);

  const handleToggle = async () => {
    if (!statusData || !slug) return;
    setActionError(null);
    try {
      if (statusData.enabled) {
        await debugApi.disable(slug);
      } else {
        await debugApi.enable(slug);
      }
      refreshStatus();
    } catch (e) {
      setActionError(e);
    }
  };

  const handleClear = async () => {
    if (!slug) return;
    setActionError(null);
    try {
      await debugApi.clear(slug);
      refreshSessions();
      refreshStatus();
    } catch (e) {
      setActionError(e);
    }
  };

  // Collect unique task IDs for filter
  const uniqueTaskIds = useMemo(() => {
    const ids = new Set<string>();
    for (const s of sessions) {
      if (s.task_id) ids.add(s.task_id);
    }
    return Array.from(ids).sort();
  }, [sessions]);

  if (!slug) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-xs text-gray-400 text-center">
          Navigate to a project to see LLM debug sessions
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-2 pb-2 border-b mb-2 flex-shrink-0 flex-wrap">
        <div className="flex items-center gap-1.5 text-[10px] text-gray-500">
          <span className={`h-2 w-2 rounded-full ${statusData?.enabled ? "bg-green-500" : "bg-gray-300"}`} />
          <span>{statusData?.enabled ? "Capturing" : "Disabled"}</span>
          <span className="text-gray-300">|</span>
          <span>{statusData?.session_count ?? 0} sessions</span>
        </div>

        <div className="ml-auto flex items-center gap-2">
          {uniqueTaskIds.length > 0 && (
            <select
              value={taskFilter}
              onChange={(e) => setTaskFilter(e.target.value)}
              className="text-[10px] border rounded px-1.5 py-0.5 bg-white"
            >
              <option value="">All tasks</option>
              {uniqueTaskIds.map((id) => <option key={id} value={id}>{id}</option>)}
            </select>
          )}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-[10px] border rounded px-1.5 py-0.5 bg-white"
          >
            <option value="">All statuses</option>
            <option value="success">Success</option>
            <option value="error">Error</option>
            <option value="validation_failed">Validation Failed</option>
          </select>

          <button
            onClick={handleToggle}
            className={`text-[10px] px-1.5 py-0.5 border rounded ${
              statusData?.enabled ? "text-red-500 hover:text-red-700" : "text-green-600 hover:text-green-700"
            }`}
          >
            {statusData?.enabled ? "Disable" : "Enable"}
          </button>
          <button
            onClick={handleClear}
            className="text-[10px] text-red-500 hover:text-red-700 px-1.5 py-0.5 border rounded"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Action error */}
      {actionError != null ? (
        <div className="mb-2">
          <ErrorDetail error={actionError} />
        </div>
      ) : null}

      {/* Session list */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">
            {statusData?.enabled
              ? "No LLM sessions captured yet"
              : "Debug capture is disabled — click Enable to start"}
          </p>
        )}

        <div className="space-y-px">
          {sessions.map((session) => (
            <SessionRow
              key={session.session_id}
              session={session}
              slug={slug}
              expanded={expandedId === session.session_id}
              onToggle={() => setExpandedId(
                expandedId === session.session_id ? null : session.session_id,
              )}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Session Row (summary + expandable detail)
// ---------------------------------------------------------------------------

function SessionRow({
  session,
  slug,
  expanded,
  onToggle,
}: {
  session: DebugSessionSummary;
  slug: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  const statusClass = STATUS_COLORS[session.status] ?? "bg-gray-100 text-gray-500";
  const totalTokens = (session.token_usage?.total_tokens ?? 0);

  return (
    <div className={expanded ? "bg-gray-50" : "hover:bg-gray-50"}>
      <button onClick={onToggle} className="w-full flex items-center gap-2 px-2 py-1.5 text-left">
        <span className={`inline-flex items-center justify-center rounded px-1.5 py-0.5 text-[10px] font-medium ${statusClass}`}>
          {session.status}
        </span>
        {session.task_id && (
          <span className="text-[10px] font-mono text-gray-500">{session.task_id}</span>
        )}
        <span className="text-xs text-gray-600 truncate flex-1">{session.model}</span>
        <span className="text-[10px] text-gray-400 tabular-nums w-14 text-right">
          {formatTokens(totalTokens)} tok
        </span>
        <span className="text-[10px] text-gray-400 tabular-nums w-14 text-right">
          {formatDuration(session.latency_ms)}
        </span>
        <span className="text-[10px] text-gray-300 w-16 text-right">{formatTime(session.timestamp)}</span>
        <span className="text-[10px] text-gray-300 w-4">{expanded ? "▼" : "▶"}</span>
      </button>

      {expanded && <SessionDetail slug={slug} sessionId={session.session_id} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Session Detail (lazy-loaded)
// ---------------------------------------------------------------------------

function SessionDetail({ slug, sessionId }: { slug: string; sessionId: string }) {
  const { data: session, isLoading } = useSWR<DebugSession>(
    `debug-session-${slug}-${sessionId}`,
    () => debugApi.session(slug, sessionId),
  );

  if (isLoading || !session) {
    return <p className="text-[10px] text-gray-400 px-2 pb-2">Loading session details...</p>;
  }

  return (
    <div className="px-2 pb-3 space-y-3">
      {/* Costs */}
      <div className="flex flex-wrap gap-4 text-[10px] text-gray-500">
        <span>Provider: <b>{session.provider}</b></span>
        <span>Model: <b>{session.model}</b></span>
        <span>Input: <b>{formatTokens(session.token_usage?.input_tokens ?? 0)}</b></span>
        <span>Output: <b>{formatTokens(session.token_usage?.output_tokens ?? 0)}</b></span>
        <span>Latency: <b>{formatDuration(session.latency_ms)}</b></span>
        {session.temperature !== undefined && <span>Temp: <b>{session.temperature}</b></span>}
        {session.stop_reason && <span>Stop: <b>{session.stop_reason}</b></span>}
      </div>

      {/* Error */}
      {session.error_type && (
        <div className="text-[10px] bg-red-50 text-red-700 rounded p-2 font-mono">
          {session.error_type}: {session.raw_response?.slice(0, 500)}
        </div>
      )}

      {/* Context sections */}
      {session.context_sections && session.context_sections.length > 0 && (
        <CollapsibleSection title={`Context Sections (${session.context_sections.length})`}>
          <div className="space-y-1">
            {session.context_sections.map((sec, i) => (
              <div key={i} className="flex items-center gap-2 text-[10px]">
                <span className="text-gray-600 font-medium">{sec.name}</span>
                <span className="text-gray-400 tabular-nums">{formatTokens(sec.token_estimate)} tok</span>
                {sec.was_truncated && <span className="text-yellow-600 text-[9px]">truncated</span>}
              </div>
            ))}
            <div className="text-[10px] text-gray-400 pt-1 border-t">
              Total context: {formatTokens(session.total_context_tokens)} tokens
            </div>
          </div>
        </CollapsibleSection>
      )}

      {/* System prompt */}
      {session.system_prompt && (
        <CollapsibleSection title="System Prompt">
          <pre className="text-[10px] bg-white border rounded p-2 overflow-x-auto max-h-40 overflow-y-auto font-mono whitespace-pre-wrap">
            {session.system_prompt}
          </pre>
        </CollapsibleSection>
      )}

      {/* User prompt */}
      {session.user_prompt && (
        <CollapsibleSection title="User Prompt">
          <pre className="text-[10px] bg-white border rounded p-2 overflow-x-auto max-h-40 overflow-y-auto font-mono whitespace-pre-wrap">
            {session.user_prompt}
          </pre>
        </CollapsibleSection>
      )}

      {/* Response */}
      {session.raw_response && (
        <CollapsibleSection title="LLM Response">
          <pre className="text-[10px] bg-white border rounded p-2 overflow-x-auto max-h-40 overflow-y-auto font-mono whitespace-pre-wrap">
            {session.raw_response}
          </pre>
        </CollapsibleSection>
      )}

      {/* Parsed output */}
      {session.parsed_output && (
        <CollapsibleSection title="Parsed Output">
          <JsonView data={session.parsed_output} maxHeight="10rem" lineNumbers />
        </CollapsibleSection>
      )}

      {/* Validation results */}
      {session.validation_results && session.validation_results.length > 0 && (
        <CollapsibleSection
          title={`Validation (${session.validation_passed ? "PASSED" : "FAILED"})`}
        >
          <div className="space-y-1">
            {session.validation_results.map((v, i) => (
              <div key={i} className="flex items-center gap-2 text-[10px]">
                <span className={`font-medium ${v.passed ? "text-green-600" : "text-red-600"}`}>
                  {v.passed ? "PASS" : "FAIL"}
                </span>
                <span className="text-gray-600">{v.description}</span>
                {v.error && <span className="text-red-500 text-[9px]">{v.error}</span>}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Collapsible Section helper
// ---------------------------------------------------------------------------

function CollapsibleSection({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-[10px] font-medium text-gray-500 hover:text-gray-700"
      >
        <span className="text-[8px]">{open ? "▼" : "▶"}</span>
        {title}
      </button>
      {open && <div className="mt-1">{children}</div>}
    </div>
  );
}
