"use client";

import type { WorkflowState } from "@/lib/types";

interface Props {
  workflow: WorkflowState;
}

const WORKFLOW_LABELS: Record<string, string> = {
  plan: "Planning",
  execute: "Execution",
  compound: "Compound Learning",
  verify: "Verification",
};

export default function WorkflowProgress({ workflow }: Props) {
  const label = WORKFLOW_LABELS[workflow.workflow_id] || workflow.workflow_id;
  const steps = workflow.steps;
  const currentIdx = workflow.current_step;
  const completed = new Set(workflow.completed_steps);

  return (
    <div className="border-b bg-white px-3 py-2">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-forge-600">
          {label}
        </span>
        <span className="text-[10px] text-gray-400">
          {Math.min(currentIdx, steps.length)}/{steps.length} steps
        </span>
      </div>
      <div className="flex items-center gap-1">
        {steps.map((step, i) => {
          const isDone = completed.has(step.name);
          const isCurrent = i === currentIdx && !isDone;
          const isPending = i > currentIdx && !isDone;

          return (
            <div key={step.name} className="flex items-center gap-1 flex-1 min-w-0">
              {/* Step indicator */}
              <div
                className={`flex items-center justify-center shrink-0 w-5 h-5 rounded-full text-[10px] font-bold
                  ${isDone ? "bg-green-100 text-green-700" : ""}
                  ${isCurrent ? "bg-forge-100 text-forge-700 ring-2 ring-forge-300" : ""}
                  ${isPending ? "bg-gray-100 text-gray-400" : ""}
                `}
                title={step.description}
              >
                {isDone ? (
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  i + 1
                )}
              </div>
              {/* Step label */}
              <span
                className={`text-[10px] truncate ${
                  isDone ? "text-green-700" : isCurrent ? "text-forge-700 font-medium" : "text-gray-400"
                }`}
                title={step.description}
              >
                {step.name}
              </span>
              {/* Connector line */}
              {i < steps.length - 1 && (
                <div className={`flex-1 h-px min-w-2 ${isDone ? "bg-green-300" : "bg-gray-200"}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
