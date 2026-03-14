"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { useWorkflowStore } from "@/stores/workflowStore";
import { Badge } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import type {
  WorkflowExecution,
  WorkflowExecutionStatus,
  WorkflowStepStatus,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function statusBadgeVariant(status: WorkflowExecutionStatus | WorkflowStepStatus) {
  switch (status) {
    case "completed": return "success" as const;
    case "running": return "info" as const;
    case "failed": return "danger" as const;
    case "cancelled": return "danger" as const;
    case "paused": return "warning" as const;
    case "skipped": return "default" as const;
    case "pending": default: return "default" as const;
  }
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (mins < 60) return `${mins}m ${secs}s`;
  const hrs = Math.floor(mins / 60);
  const remainMins = mins % 60;
  return `${hrs}h ${remainMins}m`;
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString();
}

// ---------------------------------------------------------------------------
// Step row
// ---------------------------------------------------------------------------

function StepRow({
  stepId,
  execution,
  isCurrent,
}: {
  stepId: string;
  execution: WorkflowExecution;
  isCurrent: boolean;
}) {
  const sr = execution.step_results[stepId];
  const status: WorkflowStepStatus = sr?.status ?? "pending";
  const isRunning = status === "running";

  return (
    <div
      className={`flex items-center gap-3 rounded-lg px-4 py-3 ${
        isCurrent
          ? "bg-blue-50 border border-blue-200"
          : status === "completed"
            ? "bg-green-50/50 border border-green-100"
            : status === "failed"
              ? "bg-red-50/50 border border-red-100"
              : "bg-gray-50 border border-gray-100"
      }`}
    >
      {/* Status icon */}
      <span className="flex h-6 w-6 shrink-0 items-center justify-center">
        {status === "completed" && (
          <svg className="h-5 w-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )}
        {isRunning && (
          <span className="relative flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-blue-500" />
          </span>
        )}
        {status === "failed" && (
          <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        )}
        {status === "pending" && (
          <span className="h-3 w-3 rounded-full border-2 border-gray-300" />
        )}
        {status === "skipped" && (
          <span className="text-gray-400 text-xs">skip</span>
        )}
      </span>

      {/* Step info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-medium ${isCurrent ? "text-blue-700" : "text-gray-700"}`}>
            {stepId}
          </span>
          <Badge variant={statusBadgeVariant(status)}>{status}</Badge>
        </div>

        {/* Timing */}
        {sr?.started_at && (
          <div className="flex gap-3 text-xs text-gray-400 mt-0.5">
            <span>Started: {formatTimestamp(sr.started_at)}</span>
            {sr.completed_at && (
              <span>
                Duration:{" "}
                {formatDuration(
                  (new Date(sr.completed_at).getTime() - new Date(sr.started_at).getTime()) / 1000,
                )}
              </span>
            )}
          </div>
        )}

        {/* Error */}
        {sr?.error && !sr.error.startsWith("awaiting_") && !sr.error.startsWith("blocked_by_") && (
          <div className="text-xs text-red-500 mt-1">{sr.error}</div>
        )}

        {/* Output summary */}
        {sr?.output && (
          <div className="text-xs text-gray-500 mt-1">
            {sr.output.content
              ? String(sr.output.content).slice(0, 150) + (String(sr.output.content).length > 150 ? "..." : "")
              : sr.output.success !== undefined
                ? `Success: ${sr.output.success}`
                : null}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function WorkflowDetailPage() {
  const { slug, extId } = useParams() as { slug: string; extId: string };
  const router = useRouter();
  const { executions, fetchOne, resumeWorkflow, cancelWorkflow, error } = useWorkflowStore();
  const [cancelling, setCancelling] = useState(false);
  const [resumeInput, setResumeInput] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const execution = executions[extId];

  // Fetch on mount and poll while active
  useEffect(() => {
    fetchOne(slug, extId);
    const poll = setInterval(() => {
      fetchOne(slug, extId);
    }, 3000);
    return () => clearInterval(poll);
  }, [slug, extId, fetchOne]);

  // Elapsed timer
  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (!execution) return;

    if (execution.status === "running" || execution.status === "paused") {
      const start = new Date(execution.created_at).getTime();
      const tick = () => setElapsed((Date.now() - start) / 1000);
      tick();
      intervalRef.current = setInterval(tick, 1000);
    } else if (execution.completed_at) {
      setElapsed(
        (new Date(execution.completed_at).getTime() -
          new Date(execution.created_at).getTime()) /
          1000,
      );
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [execution?.status, execution?.created_at, execution?.completed_at]);

  const handleCancel = async () => {
    setCancelling(true);
    await cancelWorkflow(slug, extId);
    setCancelling(false);
  };

  const handleResume = async () => {
    await resumeWorkflow(slug, extId, resumeInput || "proceed");
    setResumeInput("");
  };

  if (!execution) {
    return (
      <div>
        <button
          onClick={() => router.back()}
          className="text-xs text-gray-400 hover:text-gray-600 mb-4"
        >
          &larr; Back to workflows
        </button>
        <p className="text-sm text-gray-400">Loading workflow {extId}...</p>
      </div>
    );
  }

  const isActive = execution.status === "running" || execution.status === "paused";
  const isPaused = execution.status === "paused";

  // Build ordered step list from step_results + current_step
  const stepIds = Object.keys(execution.step_results);
  if (execution.current_step && !stepIds.includes(execution.current_step)) {
    stepIds.push(execution.current_step);
  }

  return (
    <div>
      {/* Back button */}
      <button
        onClick={() => router.push(`/projects/${slug}/workflows`)}
        className="text-xs text-gray-400 hover:text-gray-600 mb-3"
      >
        &larr; Back to workflows
      </button>

      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm text-gray-400 font-mono">{execution.ext_id}</span>
            <Badge variant={statusBadgeVariant(execution.status)}>
              {execution.status}
            </Badge>
          </div>
          <h1 className="text-xl font-bold">{execution.workflow_def_id}</h1>
          {execution.objective_id && (
            <span className="text-sm text-gray-500">
              Objective: {execution.objective_id}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          <span className="font-mono text-sm text-gray-500">
            {formatDuration(elapsed)}
          </span>
          {isActive && (
            <Button
              variant="danger"
              size="sm"
              onClick={handleCancel}
              disabled={cancelling}
            >
              {cancelling ? "Cancelling..." : "Cancel"}
            </Button>
          )}
        </div>
      </div>

      {/* Error banner */}
      {execution.error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 mb-4 text-sm text-red-700">
          {execution.error}
        </div>
      )}

      {/* Pause banner with resume */}
      {isPaused && (
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 mb-4">
          <div className="text-sm text-amber-800 mb-2">
            {execution.pause_reason === "awaiting_user_decision"
              ? "This workflow is waiting for your decision to continue."
              : `Paused: ${execution.pause_reason ?? "unknown"}`}
          </div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={resumeInput}
              onChange={(e) => setResumeInput(e.target.value)}
              placeholder="Your response (or leave empty to proceed)..."
              className="flex-1 rounded-md border px-3 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
            />
            <Button size="sm" onClick={handleResume}>
              Resume
            </Button>
          </div>
        </div>
      )}

      {/* Info bar */}
      <div className="flex gap-4 text-xs text-gray-400 mb-4">
        <span>Created: {formatTimestamp(execution.created_at)}</span>
        {execution.completed_at && (
          <span>Completed: {formatTimestamp(execution.completed_at)}</span>
        )}
        {execution.current_step && (
          <span>Current step: <span className="font-medium text-gray-600">{execution.current_step}</span></span>
        )}
      </div>

      {/* Step list */}
      <h3 className="text-sm font-semibold text-gray-600 mb-2">Steps</h3>
      {stepIds.length === 0 ? (
        <p className="text-sm text-gray-400">No steps executed yet.</p>
      ) : (
        <div className="space-y-2">
          {stepIds.map((stepId) => (
            <StepRow
              key={stepId}
              stepId={stepId}
              execution={execution}
              isCurrent={execution.current_step === stepId}
            />
          ))}
        </div>
      )}

      {/* Variables */}
      {Object.keys(execution.variables).length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-semibold text-gray-600 mb-2">Variables</h3>
          <pre className="rounded-lg bg-gray-50 border p-3 text-xs text-gray-600 overflow-x-auto">
            {JSON.stringify(execution.variables, null, 2)}
          </pre>
        </div>
      )}

      {error && (
        <div className="mt-4 text-sm text-red-500">{error}</div>
      )}
    </div>
  );
}
