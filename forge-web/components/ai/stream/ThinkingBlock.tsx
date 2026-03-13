"use client";

import { useState } from "react";
import type { ContentBlock } from "@/lib/hooks/useStreamDebug";

export function ThinkingBlock({ block }: { block: ContentBlock }) {
  const [expanded, setExpanded] = useState(false);
  const preview = block.content.slice(0, 80).replace(/\n/g, " ");

  return (
    <div className="rounded border border-purple-200 bg-purple-50/50">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-purple-100/50 transition-colors rounded"
      >
        <span className="text-purple-400">{expanded ? "▼" : "▶"}</span>
        <span className="font-medium text-purple-600">Thinking</span>
        <span className="text-purple-400 truncate flex-1 italic text-[10px]">{preview}</span>
        <span className="text-[10px] text-purple-400 tabular-nums">{block.content.length} chars</span>
      </button>
      {expanded && (
        <div className="border-t border-purple-200 px-3 py-2">
          <pre className="text-[11px] text-purple-800 italic whitespace-pre-wrap font-mono max-h-48 overflow-y-auto select-text">
            {block.content}
          </pre>
        </div>
      )}
    </div>
  );
}
