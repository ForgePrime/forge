"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { tasks as tasksApi } from "@/lib/api";
import { useToastStore } from "@/stores/toastStore";
import { Badge } from "@/components/shared/Badge";
import { useAIElement } from "@/lib/ai-context";
import type { ACVerification } from "./VerificationPanel";
import type { GuidelineVerification } from "./GuidelinesChecklist";
import type { GateRunnerState } from "./GateRunner";

interface CompletionDialogProps {
  slug: string;
  taskId: string;
  taskName: string;
  open: boolean;
  onClose: () => void;
  acVerifications: ACVerification[];
  guidelineVerifications: GuidelineVerification[];
  gateState: GateRunnerState;
}

export function CompletionDialog({
  slug,
  taskId,
  taskName,
  open,
  onClose,
  acVerifications,
  guidelineVerifications,
  gateState,
}: CompletionDialogProps) {
  const router = useRouter();
  const [reasoning, setReasoning] = useState("");
  const [completing, setCompleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check blocking conditions
  const uncheckedMustAC = acVerifications.filter((v) => !v.checked);
  const uncheckedMustGuidelines = guidelineVerifications.filter(
    (v) => v.weight === "must" && !v.checked
  );
  const uncheckedShouldGuidelines = guidelineVerifications.filter(
    (v) => v.weight === "should" && !v.checked
  );
  const gatesFailed = !gateState.allRequiredPassed;
  const gatesNotRun = !gateState.ran;

  const isBlocked =
    uncheckedMustAC.length > 0 ||
    uncheckedMustGuidelines.length > 0 ||
    gatesFailed ||
    !reasoning.trim();

  const hasWarnings = uncheckedShouldGuidelines.length > 0 || gatesNotRun;

  const handleComplete = useCallback(async () => {
    if (isBlocked) return;
    setCompleting(true);
    setError(null);
    try {
      await tasksApi.complete(slug, taskId, reasoning.trim());
      useToastStore.getState().addToast({
        message: `Task ${taskId} completed successfully`,
        action: "completed",
      });
      onClose();
      router.push(`/projects/${slug}/tasks`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCompleting(false);
    }
  }, [slug, taskId, reasoning, isBlocked, onClose, router]);

  // AI annotation
  useAIElement({
    id: "completion-dialog",
    type: "form",
    label: "Task Completion",
    value: open,
    description: open
      ? `${isBlocked ? "BLOCKED" : "ready"} — AC: ${acVerifications.filter((v) => v.checked).length}/${acVerifications.length}, Guidelines: ${guidelineVerifications.filter((v) => v.checked).length}/${guidelineVerifications.length}`
      : "closed",
    data: {
      blocked: isBlocked,
      blockers: {
        unchecked_must_ac: uncheckedMustAC.length,
        unchecked_must_guidelines: uncheckedMustGuidelines.length,
        gates_failed: gatesFailed,
        no_reasoning: !reasoning.trim(),
      },
      warnings: {
        unchecked_should: uncheckedShouldGuidelines.length,
        gates_not_run: gatesNotRun,
      },
    },
    actions: [
      {
        label: "Complete task",
        toolName: "completeTask",
        toolParams: ["task_id*", "reasoning*"],
        availableWhen: "not blocked",
      },
    ],
  });

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">Complete Task</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {taskId} — {taskName}
          </p>
        </div>

        {/* Verification summary */}
        <div className="px-6 py-4 space-y-3">
          {/* AC Summary */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-700">Acceptance Criteria</span>
            <Badge variant={uncheckedMustAC.length === 0 ? "success" : "danger"}>
              {acVerifications.filter((v) => v.checked).length}/{acVerifications.length}
            </Badge>
          </div>
          {uncheckedMustAC.length > 0 && (
            <div className="bg-red-50 rounded px-3 py-2">
              <p className="text-xs text-red-600 font-medium">
                {uncheckedMustAC.length} unchecked acceptance criteria — must verify before completion
              </p>
            </div>
          )}

          {/* Guidelines Summary */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-700">Guidelines</span>
            <div className="flex gap-1">
              <Badge variant={uncheckedMustGuidelines.length === 0 ? "success" : "danger"}>
                {guidelineVerifications.filter((v) => v.weight === "must" && v.checked).length}/
                {guidelineVerifications.filter((v) => v.weight === "must").length} MUST
              </Badge>
              <Badge variant={uncheckedShouldGuidelines.length === 0 ? "success" : "warning"}>
                {guidelineVerifications.filter((v) => v.weight === "should" && v.checked).length}/
                {guidelineVerifications.filter((v) => v.weight === "should").length} SHOULD
              </Badge>
            </div>
          </div>
          {uncheckedMustGuidelines.length > 0 && (
            <div className="bg-red-50 rounded px-3 py-2">
              <p className="text-xs text-red-600 font-medium">
                {uncheckedMustGuidelines.length} unchecked MUST guidelines
              </p>
            </div>
          )}
          {uncheckedShouldGuidelines.length > 0 && (
            <div className="bg-yellow-50 rounded px-3 py-2">
              <p className="text-xs text-yellow-600">
                {uncheckedShouldGuidelines.length} unchecked SHOULD guidelines (non-blocking)
              </p>
            </div>
          )}

          {/* Gates Summary */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-700">Gates</span>
            {gateState.ran ? (
              <Badge variant={gateState.allRequiredPassed ? "success" : "danger"}>
                {gateState.allRequiredPassed ? "PASSED" : "FAILED"}
              </Badge>
            ) : (
              <Badge variant="warning">NOT RUN</Badge>
            )}
          </div>
          {gatesFailed && (
            <div className="bg-red-50 rounded px-3 py-2">
              <p className="text-xs text-red-600 font-medium">
                Required gates failed — fix issues before completion
              </p>
            </div>
          )}
          {gatesNotRun && !gatesFailed && (
            <div className="bg-yellow-50 rounded px-3 py-2">
              <p className="text-xs text-yellow-600">
                Gates have not been run (non-blocking warning)
              </p>
            </div>
          )}
        </div>

        {/* Reasoning */}
        <div className="px-6 py-3 border-t">
          <label className="text-sm font-medium text-gray-700">Completion Reasoning *</label>
          <textarea
            value={reasoning}
            onChange={(e) => setReasoning(e.target.value)}
            placeholder="Explain what was done and why the task is complete..."
            rows={3}
            className="w-full mt-1 text-sm border rounded-md px-3 py-2 placeholder-gray-300 focus:border-forge-400 focus:ring-1 focus:ring-forge-400 resize-none"
          />
        </div>

        {/* Error */}
        {error && (
          <div className="px-6 py-2">
            <p className="text-xs text-red-600">{error}</p>
          </div>
        )}

        {/* Footer */}
        <div className="px-6 py-4 border-t flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 border rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleComplete}
            disabled={isBlocked || completing}
            className="px-4 py-2 text-sm text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {completing ? "Completing..." : "Complete Task"}
          </button>
        </div>
      </div>
    </div>
  );
}
