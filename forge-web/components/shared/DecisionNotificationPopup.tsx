"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useNotificationStore, type DecisionNotification } from "@/stores/notificationStore";
import { decisions as decisionsApi } from "@/lib/api";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high: "bg-orange-100 text-orange-700 border-orange-200",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
  low: "bg-gray-100 text-gray-600 border-gray-200",
};

const TYPE_LABELS: Record<string, string> = {
  exploration: "Exploration",
  risk: "Risk",
  architecture: "Architecture",
  implementation: "Implementation",
  standard: "Decision",
};

export function DecisionNotificationPopup() {
  const { decisions, removeDecision, clearAll } = useNotificationStore();
  const router = useRouter();
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  if (decisions.length === 0) return null;

  // Show only the first decision; display count badge for others
  const current = decisions[0];
  const remaining = decisions.length - 1;

  const handleView = (n: DecisionNotification) => {
    if (n.project) {
      router.push(`/projects/${n.project}/decisions/${n.decisionId}`);
    }
    removeDecision(n.id);
  };

  const handleClose = async (n: DecisionNotification) => {
    if (!n.project) return;
    setActionLoading(n.id);
    try {
      await decisionsApi.update(n.project, n.decisionId, { status: "CLOSED" });
      removeDecision(n.id);
    } catch {
      // Fallback: still remove from notifications
      removeDecision(n.id);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDefer = async (n: DecisionNotification) => {
    if (!n.project) return;
    setActionLoading(n.id);
    try {
      await decisionsApi.update(n.project, n.decisionId, { status: "DEFERRED" });
      removeDecision(n.id);
    } catch {
      removeDecision(n.id);
    } finally {
      setActionLoading(null);
    }
  };

  const isLoading = actionLoading === current.id;

  return (
    <div className="fixed top-16 right-4 z-[90] w-80">
      <div className="bg-white border border-purple-200 rounded-lg shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between bg-purple-50 px-3 py-2 border-b border-purple-200">
          <div className="flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-purple-600 text-white text-[10px] font-bold flex items-center justify-center">
              D
            </span>
            <span className="text-xs font-semibold text-purple-800">Decision Created</span>
          </div>
          <div className="flex items-center gap-2">
            {remaining > 0 && (
              <span className="px-1.5 py-0.5 rounded-full bg-purple-600 text-white text-[10px] font-bold">
                +{remaining}
              </span>
            )}
            {decisions.length > 1 && (
              <button
                onClick={clearAll}
                className="text-[10px] text-purple-400 hover:text-purple-600"
              >
                Clear all
              </button>
            )}
            <button
              onClick={() => removeDecision(current.id)}
              className="text-purple-400 hover:text-purple-600 text-sm leading-none"
            >
              x
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-mono text-purple-600">{current.decisionId}</span>
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
              current.type === "risk"
                ? SEVERITY_COLORS[current.severity || "medium"]
                : "bg-purple-100 text-purple-700 border-purple-200"
            }`}>
              {TYPE_LABELS[current.type] || current.type}
            </span>
            {current.type === "risk" && current.severity && (
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                SEVERITY_COLORS[current.severity]
              }`}>
                {current.severity}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-800 line-clamp-3 mb-2">{current.issue}</p>
          {current.taskId && (
            <p className="text-[10px] text-gray-400">Task: <span className="font-mono">{current.taskId}</span></p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 px-3 pb-3">
          <button
            onClick={() => handleView(current)}
            disabled={isLoading}
            className="flex-1 px-2 py-1.5 text-xs font-medium text-purple-700 border border-purple-300 rounded hover:bg-purple-50 disabled:opacity-50"
          >
            View
          </button>
          <button
            onClick={() => handleClose(current)}
            disabled={isLoading || !current.project}
            className="flex-1 px-2 py-1.5 text-xs font-medium text-green-700 border border-green-300 rounded hover:bg-green-50 disabled:opacity-50"
          >
            Close
          </button>
          <button
            onClick={() => handleDefer(current)}
            disabled={isLoading || !current.project}
            className="flex-1 px-2 py-1.5 text-xs font-medium text-gray-600 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
          >
            Defer
          </button>
        </div>
      </div>
    </div>
  );
}
