"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { ForgeEvent } from "@/lib/ws";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ContentBlock {
  id: string;
  type: "thinking" | "text" | "tool_use" | "tool_result" | "error";
  content: string;
  metadata?: Record<string, unknown>;
  /** Tool call status: pending = waiting for result, done/error = finished. */
  status?: "pending" | "done" | "error";
}

export interface StreamMetadata {
  sessionId: string | null;
  model: string;
  tokensIn: number;
  tokensOut: number;
  startTime: number | null;
}

interface StreamDebugState {
  blocks: ContentBlock[];
  metadata: StreamMetadata;
  streaming: boolean;
}

// ---------------------------------------------------------------------------
// Debug event subscription (bypasses React state for raw WS events)
// ---------------------------------------------------------------------------

type StreamEventCallback = (event: ForgeEvent) => void;
const _debugListeners = new Set<StreamEventCallback>();

/**
 * Subscribe to raw chat WS events for debug purposes.
 * Returns unsubscribe function.
 */
export function subscribeToStreamEvents(cb: StreamEventCallback): () => void {
  _debugListeners.add(cb);
  return () => _debugListeners.delete(cb);
}

/** Called by chatStore.handleWsEvent to forward events to debug subscribers. */
export function _notifyDebugListeners(event: ForgeEvent): void {
  Array.from(_debugListeners).forEach((cb) => {
    try {
      cb(event);
    } catch {
      // Never crash the main event loop
    }
  });
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

let _blockSeq = 0;
function nextBlockId(): string {
  return `blk-${++_blockSeq}`;
}

const EMPTY_METADATA: StreamMetadata = {
  sessionId: null,
  model: "",
  tokensIn: 0,
  tokensOut: 0,
  startTime: null,
};

const THROTTLE_MS = 100;

/**
 * useStreamDebug — subscribes to WS chat events and parses them into
 * structured content blocks for the Debug tab stream view.
 *
 * Uses ref+subscription pattern (L-018, D-063) to avoid infinite re-renders:
 * - Raw events accumulate in useRef
 * - React state is updated at most every 100ms via setTimeout
 */
export function useStreamDebug() {
  // --- Ref-based accumulation (no re-renders per token) ---
  const blocksRef = useRef<ContentBlock[]>([]);
  const metadataRef = useRef<StreamMetadata>({ ...EMPTY_METADATA });
  const streamingRef = useRef(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastFlushRef = useRef(0);

  // --- React state (updated at throttled intervals) ---
  const [state, setState] = useState<StreamDebugState>({
    blocks: [],
    metadata: { ...EMPTY_METADATA },
    streaming: false,
  });

  // Flush ref state to React state (shallow-clone each block for React.memo safety)
  const flush = useCallback(() => {
    timerRef.current = null;
    setState({
      blocks: blocksRef.current.map((b) => ({ ...b })),
      metadata: { ...metadataRef.current },
      streaming: streamingRef.current,
    });
    lastFlushRef.current = Date.now();
  }, []);

  // Schedule a throttled flush — at most once per THROTTLE_MS
  const scheduleFlush = useCallback(() => {
    if (timerRef.current !== null) return; // Already scheduled
    const elapsed = Date.now() - lastFlushRef.current;
    if (elapsed >= THROTTLE_MS) {
      // Enough time passed, flush immediately
      flush();
    } else {
      // Wait until THROTTLE_MS since last flush
      timerRef.current = setTimeout(flush, THROTTLE_MS - elapsed);
    }
  }, [flush]);

  // --- Event handler (runs in ref-land, no React state) ---
  const handleEvent = useCallback((event: ForgeEvent) => {
    const { event: eventType, payload } = event;
    const p = payload as Record<string, unknown>;

    switch (eventType) {
      case "chat.token": {
        const content = (p.content as string) || "";
        const blockType = (p.block_type as string) || "token";

        if (!streamingRef.current) {
          streamingRef.current = true;
          metadataRef.current.startTime = Date.now();
          metadataRef.current.sessionId = (p.session_id as string) || null;
        }

        const type = blockType === "thinking" ? "thinking" : "text";
        const blocks = blocksRef.current;
        const last = blocks[blocks.length - 1];

        // Append to existing block of same type, or create new
        if (last && last.type === type) {
          last.content += content;
        } else {
          blocks.push({ id: nextBlockId(), type, content });
        }
        break;
      }

      case "chat.tool_call": {
        blocksRef.current.push({
          id: nextBlockId(),
          type: "tool_use",
          content: (p.name as string) || "unknown",
          metadata: {
            toolId: p.id,
            name: p.name,
            input: p.input,
          },
          status: "pending",
        });
        break;
      }

      case "chat.tool_result": {
        const toolId = p.id as string | undefined;
        const name = p.name as string | undefined;
        // Find matching tool_use block and replace with updated copy
        const blocks = blocksRef.current;
        for (let i = blocks.length - 1; i >= 0; i--) {
          const b = blocks[i];
          if (b.type === "tool_use" && b.status === "pending") {
            const meta = b.metadata as Record<string, unknown>;
            if ((toolId && meta?.toolId === toolId) || (name && meta?.name === name)) {
              blocks[i] = { ...b, status: "done", metadata: { ...meta, result: p.result } };
              break;
            }
          }
        }
        // Also add as a separate block for visibility
        blocksRef.current.push({
          id: nextBlockId(),
          type: "tool_result",
          content: (p.name as string) || "tool_result",
          metadata: { toolId: p.id, name: p.name, result: p.result },
        });
        break;
      }

      case "chat.complete": {
        streamingRef.current = false;
        metadataRef.current.tokensIn = (p.total_input_tokens as number) || 0;
        metadataRef.current.tokensOut = (p.total_output_tokens as number) || 0;
        metadataRef.current.model = (p.model as string) || metadataRef.current.model;
        break;
      }

      case "chat.error": {
        streamingRef.current = false;
        const message = ((p.message ?? p.reason ?? "Unknown error") as string) || "Unknown error";
        blocksRef.current.push({
          id: nextBlockId(),
          type: "error",
          content: message,
          metadata: { reason: p.reason, message: p.message },
        });
        break;
      }
    }

    scheduleFlush();
  }, [scheduleFlush]);

  // --- Subscribe to debug events ---
  useEffect(() => {
    const unsub = subscribeToStreamEvents(handleEvent);
    return () => {
      unsub();
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [handleEvent]);

  // --- Clear function ---
  const clear = useCallback(() => {
    blocksRef.current = [];
    metadataRef.current = { ...EMPTY_METADATA };
    streamingRef.current = false;
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    setState({
      blocks: [],
      metadata: { ...EMPTY_METADATA },
      streaming: false,
    });
  }, []);

  return {
    blocks: state.blocks,
    metadata: state.metadata,
    streaming: state.streaming,
    clear,
  };
}
