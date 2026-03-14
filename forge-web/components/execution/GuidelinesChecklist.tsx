"use client";

import { useState, useCallback } from "react";
import { Badge } from "@/components/shared/Badge";
import { useAIElement } from "@/lib/ai-context";

interface GuidelineItem {
  id: string;
  title: string;
  content: string;
  weight: "must" | "should" | "may";
  scope: string;
}

export interface GuidelineVerification {
  id: string;
  title: string;
  weight: string;
  checked: boolean;
}

interface GuidelinesChecklistProps {
  guidelines: GuidelineItem[];
  onChange?: (verifications: GuidelineVerification[]) => void;
}

function parseGuidelines(contextContent: string): GuidelineItem[] {
  const items: GuidelineItem[] = [];
  const lines = contextContent.split("\n");
  let current: Partial<GuidelineItem> | null = null;

  for (const line of lines) {
    const headerMatch = line.match(/^\[(\w+)\]\s+(.+?)\s+\(scope:\s*(.+?)\)/);
    if (headerMatch) {
      if (current?.title) items.push(current as GuidelineItem);
      const weight = headerMatch[1].toLowerCase();
      current = {
        id: `gl-${items.length}`,
        title: headerMatch[2],
        weight: weight === "must" ? "must" : weight === "should" ? "should" : "may",
        scope: headerMatch[3],
        content: "",
      };
    } else if (current && line.trim().startsWith("  ")) {
      current.content = (current.content ?? "") + line.trim() + "\n";
    }
  }
  if (current?.title) items.push(current as GuidelineItem);
  return items;
}

export { parseGuidelines };

export function GuidelinesChecklist({ guidelines, onChange }: GuidelinesChecklistProps) {
  const [verifications, setVerifications] = useState<GuidelineVerification[]>(() =>
    guidelines.map((g) => ({
      id: g.id,
      title: g.title,
      weight: g.weight,
      checked: false,
    }))
  );
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const mustItems = guidelines.filter((g) => g.weight === "must");
  const shouldItems = guidelines.filter((g) => g.weight === "should");
  const mayItems = guidelines.filter((g) => g.weight === "may");

  const mustChecked = verifications.filter((v) => v.weight === "must" && v.checked).length;
  const shouldChecked = verifications.filter((v) => v.weight === "should" && v.checked).length;
  const allMustChecked = mustItems.length === 0 || mustChecked === mustItems.length;

  const toggleCheck = useCallback(
    (id: string) => {
      setVerifications((prev) => {
        const next = prev.map((v) => (v.id === id ? { ...v, checked: !v.checked } : v));
        onChange?.(next);
        return next;
      });
    },
    [onChange]
  );

  // AI annotation
  useAIElement({
    id: "guidelines-checklist",
    type: "section",
    label: "Guidelines Compliance",
    description: `MUST: ${mustChecked}/${mustItems.length}, SHOULD: ${shouldChecked}/${shouldItems.length}`,
    data: {
      must_total: mustItems.length,
      must_checked: mustChecked,
      should_total: shouldItems.length,
      should_checked: shouldChecked,
      all_must_checked: allMustChecked,
    },
    actions: [
      {
        label: "Check guideline",
        toolName: "checkGuideline",
        toolParams: ["guideline_id*"],
        description: "Mark a guideline as compliant",
      },
    ],
  });

  if (guidelines.length === 0) {
    return (
      <div className="rounded-lg border bg-gray-50 px-4 py-6 text-center">
        <p className="text-sm text-gray-400">No guidelines applicable for this task&apos;s scopes.</p>
      </div>
    );
  }

  const renderGroup = (items: GuidelineItem[], label: string, required: boolean) => {
    if (items.length === 0) return null;
    return (
      <div className="space-y-1">
        <div className="flex items-center gap-2 px-4 py-2">
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</span>
          {required && (
            <span className="text-[10px] text-red-500 font-medium">Required</span>
          )}
        </div>
        {items.map((g) => {
          const v = verifications.find((v) => v.id === g.id);
          const isExpanded = expandedId === g.id;
          const checked = v?.checked ?? false;
          const borderColor = !checked
            ? required ? "border-l-red-400" : "border-l-yellow-400"
            : "border-l-green-400";

          return (
            <div
              key={g.id}
              className={`border-l-2 ${borderColor} mx-4 rounded-r-md ${
                !checked && required ? "bg-red-50" : !checked ? "bg-yellow-50" : "bg-green-50"
              }`}
            >
              <div className="flex items-center justify-between px-3 py-2">
                <label className="flex items-center gap-2 cursor-pointer flex-1 min-w-0">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleCheck(g.id)}
                    className="h-4 w-4 rounded border-gray-300 text-forge-600 focus:ring-forge-500"
                  />
                  <span className={`text-xs ${checked ? "text-gray-400 line-through" : "text-gray-700"}`}>
                    {g.title}
                  </span>
                  <Badge variant={g.weight === "must" ? "danger" : g.weight === "should" ? "warning" : "default"}>
                    {g.weight.toUpperCase()}
                  </Badge>
                  <span className="text-[10px] text-gray-400">{g.scope}</span>
                </label>
                <button
                  onClick={() => setExpandedId(isExpanded ? null : g.id)}
                  className="text-[10px] text-gray-400 hover:text-gray-600 ml-2"
                >
                  {isExpanded ? "Hide" : "Show"}
                </button>
              </div>
              {isExpanded && (
                <div className="px-3 pb-2 ml-6">
                  <p className="text-xs text-gray-500 whitespace-pre-wrap">{g.content.trim()}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="rounded-lg border bg-white">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Guidelines Compliance</span>
          <Badge variant={allMustChecked ? "success" : "danger"}>
            {mustChecked}/{mustItems.length} MUST
          </Badge>
          <Badge variant="default">
            {shouldChecked}/{shouldItems.length} SHOULD
          </Badge>
        </div>
        {!allMustChecked && (
          <span className="text-xs text-red-500 font-medium">MUST guidelines required</span>
        )}
      </div>

      <div className="py-2 space-y-3">
        {renderGroup(mustItems, "Must", true)}
        {renderGroup(shouldItems, "Should", false)}
        {renderGroup(mayItems, "May", false)}
      </div>

      {!allMustChecked && (
        <div className="px-4 py-2 border-t bg-red-50">
          <p className="text-xs text-red-600">
            All MUST guidelines must be verified before task completion.
          </p>
        </div>
      )}
    </div>
  );
}
