"use client";

import { useState, useCallback } from "react";
import { Badge } from "@/components/shared/Badge";
import { useAIElement } from "@/lib/ai-context";

interface ACItem {
  text: string;
  from_template?: string;
  params?: Record<string, string>;
}

export interface ACVerification {
  criterion: string;
  checked: boolean;
  reasoning: string;
}

interface VerificationPanelProps {
  acceptanceCriteria: (string | ACItem)[];
  onChange?: (verifications: ACVerification[]) => void;
}

function normalizeAC(ac: string | ACItem): { text: string; template?: string } {
  if (typeof ac === "string") return { text: ac };
  return { text: ac.text, template: ac.from_template };
}

export function VerificationPanel({ acceptanceCriteria, onChange }: VerificationPanelProps) {
  const [verifications, setVerifications] = useState<ACVerification[]>(() =>
    acceptanceCriteria.map((ac) => ({
      criterion: normalizeAC(ac).text,
      checked: false,
      reasoning: "",
    }))
  );

  const allChecked = verifications.length > 0 && verifications.every((v) => v.checked);
  const checkedCount = verifications.filter((v) => v.checked).length;

  const updateVerification = useCallback(
    (index: number, update: Partial<ACVerification>) => {
      setVerifications((prev) => {
        const next = prev.map((v, i) => (i === index ? { ...v, ...update } : v));
        onChange?.(next);
        return next;
      });
    },
    [onChange]
  );

  // AI annotation
  useAIElement({
    id: "verification-panel",
    type: "section",
    label: "Acceptance Criteria Verification",
    description: `${checkedCount}/${verifications.length} criteria verified`,
    data: {
      total: verifications.length,
      checked: checkedCount,
      allChecked,
      criteria: verifications.map((v) => ({
        text: v.criterion.slice(0, 80),
        checked: v.checked,
        hasReasoning: v.reasoning.length > 0,
      })),
    },
    actions: [
      {
        label: "Verify criterion",
        toolName: "verifyAC",
        toolParams: ["index*", "reasoning"],
        description: "Mark an acceptance criterion as verified with reasoning",
      },
    ],
  });

  if (acceptanceCriteria.length === 0) {
    return (
      <div className="rounded-lg border bg-gray-50 px-4 py-6 text-center">
        <p className="text-sm text-gray-400">No acceptance criteria defined for this task.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Acceptance Criteria</span>
          <Badge variant={allChecked ? "success" : "default"}>
            {checkedCount}/{verifications.length}
          </Badge>
        </div>
        {allChecked && (
          <span className="text-xs text-green-600 font-medium">All verified</span>
        )}
      </div>

      {/* Checklist */}
      <div className="divide-y">
        {acceptanceCriteria.map((ac, i) => {
          const { text, template } = normalizeAC(ac);
          const v = verifications[i];

          return (
            <div key={i} className="px-4 py-3 space-y-2">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={v.checked}
                  onChange={(e) => updateVerification(i, { checked: e.target.checked })}
                  className="mt-0.5 h-4 w-4 rounded border-gray-300 text-forge-600 focus:ring-forge-500"
                />
                <div className="flex-1 min-w-0">
                  <span className={`text-sm ${v.checked ? "text-gray-500 line-through" : "text-gray-800"}`}>
                    {text}
                  </span>
                  {template && (
                    <span className="ml-2 text-[10px] bg-purple-50 text-purple-600 px-1.5 py-0.5 rounded">
                      from {template}
                    </span>
                  )}
                </div>
              </label>

              {/* Reasoning input — shown when checked or has content */}
              {(v.checked || v.reasoning) && (
                <div className="ml-7">
                  <input
                    type="text"
                    value={v.reasoning}
                    onChange={(e) => updateVerification(i, { reasoning: e.target.value })}
                    placeholder="Reasoning (how was this verified?)..."
                    className="w-full text-xs border rounded px-2 py-1.5 text-gray-600 placeholder-gray-300 focus:border-forge-400 focus:ring-1 focus:ring-forge-400"
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      {!allChecked && (
        <div className="px-4 py-2 border-t bg-amber-50">
          <p className="text-xs text-amber-600">
            All criteria must be verified before task completion.
          </p>
        </div>
      )}
    </div>
  );
}

/** Export helper to get structured verification data for completion dialog. */
export function getVerificationSummary(verifications: ACVerification[]): string {
  return verifications
    .map((v, i) => `${i + 1}. [${v.checked ? "x" : " "}] ${v.criterion}${v.reasoning ? ` — ${v.reasoning}` : ""}`)
    .join("\n");
}
