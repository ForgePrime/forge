"use client";

import type { ContentBlock } from "@/lib/hooks/useStreamDebug";

export function ResponseBlock({ block, streaming }: { block: ContentBlock; streaming?: boolean }) {
  return (
    <div className="rounded border border-gray-200 bg-white">
      <div className="px-3 py-1.5 flex items-center gap-2 border-b border-gray-100">
        <span className="text-xs font-medium text-gray-600">Response</span>
        {streaming && (
          <span className="text-[10px] text-forge-600 flex items-center gap-1">
            <span className="animate-pulse">●</span> streaming
          </span>
        )}
        <span className="ml-auto text-[10px] text-gray-400 tabular-nums">{block.content.length} chars</span>
      </div>
      <pre className="px-3 py-2 text-xs text-gray-800 whitespace-pre-wrap font-mono max-h-64 overflow-y-auto select-text">
        {block.content}
        {streaming && <span className="inline-block animate-pulse text-forge-500 ml-0.5">▊</span>}
      </pre>
    </div>
  );
}
