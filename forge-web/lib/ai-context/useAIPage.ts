"use client";

import { useEffect } from "react";
import type { AIPageConfig } from "./types";
import { useAIPageContextSafe } from "./AIPageProvider";
import { llm } from "@/lib/api";

/**
 * Declare page-level metadata for AI context.
 * Call once per page component.
 *
 * Also registers the page with the backend PageRegistry (fire-and-forget)
 * so the AI system prompt always has a complete page catalog.
 *
 * @example
 * ```tsx
 * function TasksPage() {
 *   useAIPage({ id: "tasks", title: "Tasks", description: "Task list for project" });
 *   return <div>...</div>;
 * }
 * ```
 */
export function useAIPage(config: AIPageConfig): void {
  const ctx = useAIPageContextSafe();

  useEffect(() => {
    if (!ctx) return;
    ctx.setPageConfig(config);
    // Register with backend PageRegistry (fire-and-forget)
    llm.registerPage({
      id: config.id,
      title: config.title,
      description: config.description ?? "",
      route: config.route ?? "",
    }).catch(() => {});
    return () => {
      ctx.setPageConfig(null);
    };
    // Re-register when config identity changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ctx, config.id, config.title, config.description, config.route]);
}
