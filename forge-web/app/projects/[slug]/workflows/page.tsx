"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useWorkflowStore } from "@/stores/workflowStore";
import { Badge } from "@/components/shared/Badge";
import { StatusFilter } from "@/components/shared/StatusFilter";
import type { WorkflowExecution, WorkflowExecutionStatus } from "@/lib/types";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STATUSES: WorkflowExecutionStatus[] = [
  "pending", "running", "paused", "completed", "failed", "cancelled",
];

const DEFINITIONS = [
  {
    id: "full-lifecycle",
    name: "Full Lifecycle",
    description: "Complete: objective \u2192 discover \u2192 plan \u2192 execute \u2192 compound",
  },
  {
    id: "simplified-next",
    name: "Simplified Next",
    description: "Single task: begin \u2192 execute \u2192 complete",
  },
  {
    id: "discovery-only",
    name: "Discovery Only",
    description: "Explore: discover \u2192 review",
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function statusBadgeVariant(status: WorkflowExecutionStatus) {
  switch (status) {
    case "completed": return "success" as const;
    case "running": return "info" as const;
    case "failed": return "danger" as const;
    case "cancelled": return "danger" as const;
    case "paused": return "warning" as const;
    case "pending": default: return "default" as const;
  }
}

function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// ---------------------------------------------------------------------------
// Workflow card
// ---------------------------------------------------------------------------

function WorkflowCard({ ex, slug }: { ex: WorkflowExecution; slug: string }) {
  const completedSteps = Object.values(ex.step_results).filter(
    (sr) => sr.status === "completed",
  ).length;
  const totalSteps = Object.keys(ex.step_results).length;
  const isRunning = ex.status === "running";

  return (
    <Link
      href={`/projects/${slug}/workflows/${ex.ext_id}`}
      className="block rounded-lg border bg-white p-4 hover:border-forge-300 transition-colors"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {isRunning && (
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500" />
            </span>
          )}
          <span className="text-sm font-mono text-gray-500">{ex.ext_id}</span>
          <Badge variant={statusBadgeVariant(ex.status)}>{ex.status}</Badge>
        </div>
        <span className="text-xs text-gray-400">{timeAgo(ex.created_at)}</span>
      </div>

      <div className="text-sm font-medium text-gray-700 mb-1">
        {ex.workflow_def_id}
      </div>

      {ex.objective_id && (
        <div className="text-xs text-gray-400 mb-2">
          Objective: {ex.objective_id}
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {ex.current_step && (
            <span className="text-xs text-gray-500">
              Step: <span className="font-medium">{ex.current_step}</span>
            </span>
          )}
          {totalSteps > 0 && (
            <span className="text-xs text-gray-400">
              ({completedSteps}/{totalSteps} done)
            </span>
          )}
        </div>

        {ex.pause_reason && (
          <span className="text-xs text-amber-600 font-medium">
            {ex.pause_reason === "awaiting_user_decision"
              ? "Needs your decision"
              : ex.pause_reason}
          </span>
        )}

        {ex.error && (
          <span className="text-xs text-red-500 truncate max-w-[200px]">
            {ex.error}
          </span>
        )}
      </div>
    </Link>
  );
}

// ---------------------------------------------------------------------------
// Start dialog
// ---------------------------------------------------------------------------

function StartWorkflowDialog({
  slug,
  onClose,
}: {
  slug: string;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState(DEFINITIONS[0].id);
  const [objectiveId, setObjectiveId] = useState("");
  const [starting, setStarting] = useState(false);
  const startWorkflow = useWorkflowStore((s) => s.startWorkflow);
  const router = useRouter();

  const handleStart = async () => {
    setStarting(true);
    const ex = await startWorkflow(
      slug,
      selected,
      objectiveId || undefined,
    );
    setStarting(false);
    if (ex) {
      router.push(`/projects/${slug}/workflows/${ex.ext_id}`);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold mb-4">Start Workflow</h3>

        <div className="space-y-3 mb-4">
          {DEFINITIONS.map((d) => (
            <label
              key={d.id}
              className={`flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                selected === d.id
                  ? "border-forge-500 bg-forge-50"
                  : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <input
                type="radio"
                name="definition"
                value={d.id}
                checked={selected === d.id}
                onChange={() => setSelected(d.id)}
                className="mt-0.5"
              />
              <div>
                <div className="text-sm font-medium">{d.name}</div>
                <div className="text-xs text-gray-500">{d.description}</div>
              </div>
            </label>
          ))}
        </div>

        <div className="mb-4">
          <label className="block text-sm text-gray-600 mb-1">
            Objective ID (optional)
          </label>
          <input
            type="text"
            value={objectiveId}
            onChange={(e) => setObjectiveId(e.target.value)}
            placeholder="O-001"
            className="w-full rounded-md border px-3 py-2 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
          />
        </div>

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={handleStart}
            disabled={starting}
            className="px-4 py-2 text-sm text-white bg-forge-600 rounded-md hover:bg-forge-700 disabled:opacity-50"
          >
            {starting ? "Starting..." : "Start"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function WorkflowsPage() {
  const { slug } = useParams() as { slug: string };
  const { executions, loading, fetchList } = useWorkflowStore();
  const [statusFilter, setStatusFilter] = useState("");
  const [showStart, setShowStart] = useState(false);

  useEffect(() => {
    fetchList(slug);
  }, [slug, fetchList]);

  const list = useMemo(() => {
    let items = Object.values(executions);
    if (statusFilter) {
      items = items.filter((ex) => ex.status === statusFilter);
    }
    // Sort: running/paused first, then by created_at desc
    items.sort((a, b) => {
      const aActive = a.status === "running" || a.status === "paused" ? 0 : 1;
      const bActive = b.status === "running" || b.status === "paused" ? 0 : 1;
      if (aActive !== bActive) return aActive - bActive;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
    return items;
  }, [executions, statusFilter]);

  const total = Object.keys(executions).length;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Workflows ({total})</h2>
        <div className="flex gap-3 items-center">
          <StatusFilter options={STATUSES} value={statusFilter} onChange={setStatusFilter} />
          <button
            onClick={() => setShowStart(true)}
            className="px-3 py-1.5 text-sm text-white bg-forge-600 rounded-md hover:bg-forge-700"
          >
            + Start Workflow
          </button>
        </div>
      </div>

      {loading && total === 0 && (
        <p className="text-sm text-gray-400">Loading workflows...</p>
      )}

      {!loading && list.length === 0 && (
        <p className="text-sm text-gray-400">
          {total === 0
            ? "No workflows yet. Start one to orchestrate AI-driven processes."
            : "No matching workflows."}
        </p>
      )}

      {list.length > 0 && (
        <div className="space-y-3">
          {list.map((ex) => (
            <WorkflowCard key={ex.ext_id} ex={ex} slug={slug} />
          ))}
        </div>
      )}

      {showStart && (
        <StartWorkflowDialog slug={slug} onClose={() => setShowStart(false)} />
      )}
    </div>
  );
}
