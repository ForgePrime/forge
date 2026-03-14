"use client";

import { useEffect, useState, useRef } from "react";
import { Badge } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import type {
  WorkflowExecution,
  WorkflowExecutionStatus,
  WorkflowStepStatus,
  WorkflowStepDefinition,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function statusVariant(status: WorkflowExecutionStatus | WorkflowStepStatus) {
  switch (status) {
    case "completed":
      return "success" as const;
    case "running":
      return "info" as const;
    case "failed":
      return "danger" as const;
    case "cancelled":
      return "warning" as const;
    case "paused":
      return "warning" as const;
    case "skipped":
      return "default" as const;
    case "pending":
    default:
      return "default" as const;
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

// ---------------------------------------------------------------------------
// Step indicator
// ---------------------------------------------------------------------------

function StepIndicator({
  step,
  status,
  isCurrent,
}: {
  step: WorkflowStepDefinition;
  status: WorkflowStepStatus;
  isCurrent: boolean;
}) {
  const isRunning = status === "running";

  return (
    <div className={`flex items-center gap-2 rounded px-3 py-2 text-sm ${
      isCurrent ? "bg-blue-50 border border-blue-200" : "bg-gray-50"
    }`}>
      {/* Status icon */}
      <span className="flex h-5 w-5 shrink-0 items-center justify-center">
        {status === "completed" && (
          <svg className="h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
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
          <svg className="h-4 w-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        )}
        {status === "pending" && (
          <span className="h-2.5 w-2.5 rounded-full border-2 border-gray-300" />
        )}
        {status === "skipped" && (
          <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
          </svg>
        )}
      </span>

      {/* Step name + type */}
      <div className="flex flex-col min-w-0">
        <span className={`truncate font-medium ${isCurrent ? "text-blue-700" : "text-gray-700"}`}>
          {step.name}
        </span>
        <span className="truncate text-xs text-gray-400">
          {step.type.replace("_", " ")}
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface WorkflowStatusProps {
  execution: WorkflowExecution;
  steps: WorkflowStepDefinition[];
  onResume?: (userResponse: unknown) => void;
  onCancel?: () => void;
  cancelling?: boolean;
}

export function WorkflowStatus({
  execution,
  steps,
  onResume,
  onCancel,
  cancelling = false,
}: WorkflowStatusProps) {
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (execution.status === "running" && execution.created_at) {
      const start = new Date(execution.created_at).getTime();
      const tick = () => setElapsed((Date.now() - start) / 1000);
      tick();
      intervalRef.current = setInterval(tick, 1000);
    } else if (execution.created_at && execution.completed_at) {
      const start = new Date(execution.created_at).getTime();
      const end = new Date(execution.completed_at).getTime();
      setElapsed((end - start) / 1000);
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [execution.status, execution.created_at, execution.completed_at]);

  const isActive = execution.status === "running" || execution.status === "paused";
  const isPaused = execution.status === "paused";
  const isTerminal = execution.status === "completed" || execution.status === "failed" || execution.status === "cancelled";

  // Count completed steps
  const completedSteps = Object.values(execution.step_results).filter(
    (sr) => sr.status === "completed",
  ).length;

  return (
    <div className="rounded-lg border bg-white">
      {/* Header bar */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-3">
          {/* Animated dot for running */}
          {execution.status === "running" && (
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-blue-500" />
            </span>
          )}
          <Badge variant={statusVariant(execution.status)}>
            {execution.status}
          </Badge>
          <span className="text-sm text-gray-500">
            {execution.ext_id} &middot; {execution.workflow_def_id}
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Duration */}
          {(isActive || isTerminal) && (
            <span className="font-mono text-xs text-gray-500">
              {formatDuration(elapsed)}
            </span>
          )}

          {/* Progress fraction */}
          <span className="text-xs text-gray-400">
            {completedSteps}/{steps.length} steps
          </span>

          {/* Cancel button */}
          {isActive && onCancel && (
            <Button variant="danger" size="sm" onClick={onCancel} disabled={cancelling}>
              {cancelling ? "Cancelling..." : "Cancel"}
            </Button>
          )}
        </div>
      </div>

      {/* Pause banner */}
      {isPaused && (
        <div className="flex items-center justify-between border-b bg-amber-50 px-4 py-2">
          <div className="text-sm text-amber-800">
            {execution.pause_reason === "awaiting_user_decision"
              ? "Waiting for your decision to continue."
              : `Paused: ${execution.pause_reason ?? "unknown reason"}`}
          </div>
          {onResume && execution.pause_reason === "awaiting_user_decision" && (
            <Button size="sm" onClick={() => onResume("proceed")}>
              Resume
            </Button>
          )}
        </div>
      )}

      {/* Error banner */}
      {execution.error && (
        <div className="border-b bg-red-50 px-4 py-2 text-sm text-red-700">
          {execution.error}
        </div>
      )}

      {/* Step list */}
      <div className="flex flex-col gap-1 p-3">
        {steps.map((step) => {
          const sr = execution.step_results[step.id];
          const stepStatus: WorkflowStepStatus = sr?.status ?? "pending";
          const isCurrent = execution.current_step === step.id;
          return (
            <StepIndicator
              key={step.id}
              step={step}
              status={stepStatus}
              isCurrent={isCurrent}
            />
          );
        })}
      </div>
    </div>
  );
}
