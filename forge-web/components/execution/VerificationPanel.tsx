"use client";

import { useState, useCallback, useEffect } from "react";
import { gates as gatesApi } from "@/lib/api";
import { Badge } from "@/components/shared/Badge";
import { useAIElement } from "@/lib/ai-context";
import type { Gate } from "@/lib/types";

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

// ---------------------------------------------------------------------------
// Gate Runner
// ---------------------------------------------------------------------------

export interface GateResult {
  name: string;
  command: string;
  required: boolean;
  status: "pending" | "pass" | "fail" | "skipped";
  output?: string;
}

interface GateRunnerProps {
  slug: string;
  taskId: string;
  onResults?: (results: GateResult[]) => void;
}

export function GateRunner({ slug, taskId, onResults }: GateRunnerProps) {
  const [gates, setGates] = useState<GateResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedGate, setExpandedGate] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await gatesApi.check(slug, taskId);
        if (cancelled) return;
        const results: GateResult[] = (data.gates || []).map((g: Record<string, unknown>) => ({
          name: g.name as string,
          command: g.command as string,
          required: g.required !== false,
          status: "pending" as const,
        }));
        setGates(results);
        onResults?.(results);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [slug, taskId, onResults]);

  const allPassed = gates.length > 0 && gates.every((g) => g.status === "pass" || (!g.required && g.status !== "fail"));
  const requiredGates = gates.filter((g) => g.required);
  const advisoryGates = gates.filter((g) => !g.required);
  const passedCount = gates.filter((g) => g.status === "pass").length;
  const failedCount = gates.filter((g) => g.status === "fail").length;

  // AI annotation
  useAIElement({
    id: "gate-runner",
    type: "section",
    label: "Gate Runner",
    description: gates.length === 0
      ? "No gates configured"
      : `${passedCount}/${gates.length} passed, ${failedCount} failed`,
    data: {
      total: gates.length,
      passed: passedCount,
      failed: failedCount,
      required: requiredGates.length,
      advisory: advisoryGates.length,
      allPassed,
      gates: gates.map((g) => ({ name: g.name, required: g.required, status: g.status })),
    },
    actions: [
      {
        label: "Run gates via CLI",
        toolName: "runGates",
        toolParams: ["task_id*"],
        description: "Execute gate checks via python -m core.gates check",
      },
    ],
  });

  if (loading) {
    return (
      <div className="rounded-lg border bg-white px-4 py-6 text-center">
        <div className="animate-pulse text-sm text-gray-400">Loading gate configuration...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (gates.length === 0) {
    return (
      <div className="rounded-lg border bg-gray-50 px-4 py-6 text-center">
        <p className="text-sm text-gray-400">No gates configured for this project.</p>
        <p className="text-xs text-gray-300 mt-1">Configure gates via /gates or the settings page.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Gates</span>
          <Badge variant={allPassed ? "success" : failedCount > 0 ? "danger" : "default"}>
            {passedCount}/{gates.length}
          </Badge>
        </div>
        <span className="text-xs text-gray-400">
          {requiredGates.length} required, {advisoryGates.length} advisory
        </span>
      </div>

      {/* Gate list */}
      <div className="divide-y">
        {gates.map((gate) => {
          const isExpanded = expandedGate === gate.name;
          return (
            <div key={gate.name} className="px-4 py-3">
              <button
                onClick={() => setExpandedGate(isExpanded ? null : gate.name)}
                className="flex items-center justify-between w-full text-left"
              >
                <div className="flex items-center gap-2">
                  <GateStatusIcon status={gate.status} />
                  <span className="text-sm font-medium text-gray-800">{gate.name}</span>
                  <Badge variant={gate.required ? "danger" : "default"}>
                    {gate.required ? "required" : "advisory"}
                  </Badge>
                </div>
                <span className="text-xs text-gray-400">{isExpanded ? "\u25BC" : "\u25B6"}</span>
              </button>

              {isExpanded && (
                <div className="mt-2 ml-6 space-y-2">
                  <div className="text-xs text-gray-500">
                    <span className="text-gray-400">Command:</span>{" "}
                    <code className="bg-gray-100 px-1.5 py-0.5 rounded font-mono">{gate.command}</code>
                  </div>
                  {gate.output && (
                    <pre className="text-xs font-mono text-gray-600 bg-gray-50 rounded p-3 overflow-x-auto whitespace-pre-wrap max-h-48 overflow-y-auto">
                      {gate.output}
                    </pre>
                  )}
                  {gate.status === "pending" && (
                    <p className="text-xs text-gray-400 italic">
                      Run gates via CLI: py -m core.gates check {slug} --task {taskId}
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer warnings */}
      {failedCount > 0 && (
        <div className="px-4 py-2 border-t bg-red-50">
          <p className="text-xs text-red-600">
            {failedCount} gate{failedCount !== 1 ? "s" : ""} failed.
            {requiredGates.some((g) => g.status === "fail")
              ? " Required gates must pass before completion."
              : " Only advisory gates failed — completion is allowed."}
          </p>
        </div>
      )}
      {gates.every((g) => g.status === "pending") && (
        <div className="px-4 py-2 border-t bg-blue-50">
          <p className="text-xs text-blue-600">
            Gates have not been executed yet. They will be run during task completion.
          </p>
        </div>
      )}
    </div>
  );
}

function GateStatusIcon({ status }: { status: GateResult["status"] }) {
  switch (status) {
    case "pass":
      return <span className="text-green-500 text-sm">\u2713</span>;
    case "fail":
      return <span className="text-red-500 text-sm">\u2717</span>;
    case "skipped":
      return <span className="text-gray-400 text-sm">\u2014</span>;
    default:
      return <span className="text-gray-300 text-sm">\u25CB</span>;
  }
}
