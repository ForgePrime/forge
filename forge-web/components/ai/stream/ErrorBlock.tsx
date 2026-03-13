"use client";

import { useAIElement } from "@/lib/ai-context/useAIElement";
import type { ContentBlock } from "@/lib/hooks/useStreamDebug";

export function ErrorBlock({ block }: { block: ContentBlock }) {
  const meta = block.metadata as Record<string, unknown> | undefined;
  const reason = (meta?.reason as string) || "";

  useAIElement({
    id: `error-${block.id}`,
    type: "display",
    label: "Stream Error",
    description: `Error: ${block.content}`,
    value: "error",
    actions: [],
  });

  return (
    <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-xs">
      <div className="flex items-center gap-2 mb-1">
        <span className="inline-flex items-center rounded px-1.5 py-0.5 bg-red-100 text-red-700 font-bold text-[10px]">
          ERROR
        </span>
        {reason && (
          <span className="text-red-500 font-medium">{reason}</span>
        )}
      </div>
      <p className="text-red-700 font-mono select-text">{block.content}</p>
    </div>
  );
}
