"use client";

import { useState } from "react";
import { useAIElement } from "@/lib/ai-context/useAIElement";
import type { ContentBlock } from "@/lib/hooks/useStreamDebug";

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  pending: { label: "running", className: "bg-yellow-100 text-yellow-700 animate-pulse" },
  done: { label: "done", className: "bg-green-100 text-green-700" },
  error: { label: "error", className: "bg-red-100 text-red-700" },
};

export function StreamToolCallBlock({ block }: { block: ContentBlock }) {
  const [expanded, setExpanded] = useState(false);
  const meta = block.metadata as Record<string, unknown> | undefined;
  const toolName = (meta?.name as string) || block.content;
  const input = meta?.input;
  const result = meta?.result;
  const badge = STATUS_BADGE[block.status ?? "pending"] ?? STATUS_BADGE.pending;

  useAIElement({
    id: `tool-call-${block.id}`,
    type: "display",
    label: `Tool Call: ${toolName}`,
    description: `Tool ${toolName} — ${block.status ?? "pending"}`,
    value: block.status ?? "pending",
    actions: [],
  });

  return (
    <div className={`rounded border text-xs ${
      block.status === "error" ? "border-red-200 bg-red-50" : "border-blue-200 bg-blue-50/50"
    }`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-blue-100/50 transition-colors rounded"
      >
        <span className="text-blue-400">{expanded ? "▼" : "▶"}</span>
        <span className="font-mono font-medium text-blue-700">{toolName}</span>
        <span className={`ml-auto rounded px-1.5 py-0.5 text-[10px] ${badge.className}`}>
          {badge.label}
        </span>
      </button>
      {expanded && (
        <div className="border-t border-blue-200 px-3 py-2 space-y-2">
          {input !== undefined && (
            <div>
              <span className="font-semibold text-[10px] text-gray-500">Input:</span>
              <pre className="mt-0.5 overflow-x-auto rounded bg-white p-2 text-[10px] text-gray-700 border border-gray-100 font-mono max-h-32 overflow-y-auto select-text">
                {typeof input === "string" ? input : JSON.stringify(input, null, 2)}
              </pre>
            </div>
          )}
          {result !== undefined && (
            <div>
              <span className={`font-semibold text-[10px] ${block.status === "error" ? "text-red-500" : "text-gray-500"}`}>
                Result:
              </span>
              <pre className={`mt-0.5 overflow-x-auto rounded p-2 text-[10px] border max-h-32 overflow-y-auto font-mono select-text ${
                block.status === "error"
                  ? "bg-red-50 text-red-800 border-red-100"
                  : "bg-white text-gray-700 border-gray-100"
              }`}>
                {typeof result === "string" ? result : JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
