"use client";

import { useAIElement } from "@/lib/ai-context/useAIElement";
import type { ContentBlock } from "@/lib/hooks/useStreamDebug";
import { ThinkingBlock } from "./ThinkingBlock";
import { StreamToolCallBlock } from "./ToolCallBlock";
import { ResponseBlock } from "./ResponseBlock";
import { ErrorBlock } from "./ErrorBlock";

interface StreamViewProps {
  blocks: ContentBlock[];
  streaming: boolean;
}

function renderBlock(block: ContentBlock, streaming: boolean, isLast: boolean) {
  switch (block.type) {
    case "thinking":
      return <ThinkingBlock key={block.id} block={block} />;
    case "tool_use":
      return <StreamToolCallBlock key={block.id} block={block} />;
    case "tool_result":
      // tool_result blocks are informational; the tool_use block already shows status
      return null;
    case "text":
      return <ResponseBlock key={block.id} block={block} streaming={streaming && isLast} />;
    case "error":
      return <ErrorBlock key={block.id} block={block} />;
    default:
      return null;
  }
}

export function StreamView({ blocks, streaming }: StreamViewProps) {
  useAIElement({
    id: "stream-view",
    type: "display",
    label: "Stream View",
    description: `${blocks.length} blocks, ${streaming ? "streaming" : "idle"}`,
    value: streaming ? "streaming" : "idle",
    actions: [],
  });

  if (blocks.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-xs text-gray-400">
        {streaming ? (
          <span className="flex items-center gap-1">
            <span className="animate-pulse">●</span> Waiting for stream data...
          </span>
        ) : (
          "No stream data — start a chat to see structured debug output"
        )}
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {blocks.map((block, i) => renderBlock(block, streaming, i === blocks.length - 1))}
    </div>
  );
}
