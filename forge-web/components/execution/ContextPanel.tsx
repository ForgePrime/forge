"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { tasks as tasksApi, objectives as objectivesApi } from "@/lib/api";
import { Badge, statusVariant } from "@/components/shared/Badge";
import { useAIElement } from "@/lib/ai-context";
import type { TaskContext, ContextSection, Objective } from "@/lib/types";

interface ContextPanelProps {
  slug: string;
  taskId: string;
}

const SECTION_ICONS: Record<string, string> = {
  task: "\u{1F4CB}",
  dependencies: "\u{1F517}",
  decisions: "\u2696\uFE0F",
  guidelines: "\u{1F4CF}",
  knowledge: "\u{1F4DA}",
  skill: "\u{1F6E0}\uFE0F",
  changes: "\u{1F4DD}",
  business: "\u{1F3AF}",
};

function tokenColor(count: number): string {
  if (count > 8000) return "text-red-600";
  if (count > 4000) return "text-yellow-600";
  return "text-green-600";
}

function formatTokens(count: number): string {
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
  return String(count);
}

/** Parse guideline weight from content line like "[MUST] Title (scope: backend)" */
function parseGuidelineWeight(line: string): "must" | "should" | "may" | null {
  const m = line.match(/^\[(\w+)\]/);
  if (!m) return null;
  const w = m[1].toLowerCase();
  if (w === "must" || w === "should" || w === "may") return w;
  return null;
}

function GuidelinesContent({ content }: { content: string }) {
  const lines = content.split("\n");
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        const weight = parseGuidelineWeight(line);
        if (weight === "must") {
          return (
            <div key={i} className="text-xs font-mono bg-red-50 border-l-2 border-red-400 pl-2 py-0.5 text-gray-800">
              {line}
            </div>
          );
        }
        if (weight === "should") {
          return (
            <div key={i} className="text-xs font-mono bg-blue-50 border-l-2 border-blue-300 pl-2 py-0.5 text-gray-700">
              {line}
            </div>
          );
        }
        if (weight === "may") {
          return (
            <div key={i} className="text-xs font-mono bg-gray-50 border-l-2 border-gray-200 pl-2 py-0.5 text-gray-500">
              {line}
            </div>
          );
        }
        if (line.trim() === "") return <div key={i} className="h-1" />;
        return (
          <div key={i} className="text-xs font-mono text-gray-600 pl-2">
            {line}
          </div>
        );
      })}
    </div>
  );
}

function BusinessContextSection({ objective }: { objective: Objective }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-400">{objective.id}</span>
        <Badge variant={statusVariant(objective.status)}>{objective.status}</Badge>
        {objective.appetite && (
          <span className="text-xs text-gray-400">appetite: {objective.appetite}</span>
        )}
      </div>
      <h4 className="text-sm font-medium">{objective.title}</h4>
      {objective.description && (
        <p className="text-xs text-gray-500">{objective.description}</p>
      )}
      {objective.key_results && objective.key_results.length > 0 && (
        <div className="space-y-2">
          <span className="text-xs font-medium text-gray-600">Key Results:</span>
          {objective.key_results.map((kr) => {
            const pct = kr.target ? Math.round(((kr.current ?? kr.baseline ?? 0) / kr.target) * 100) : 0;
            return (
              <div key={kr.id} className="flex items-center gap-2 text-xs">
                <span className="text-gray-400 w-12">{kr.id}</span>
                <span className="flex-1">{kr.metric}</span>
                <div className="w-24 bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${pct >= 100 ? "bg-green-500" : pct >= 50 ? "bg-yellow-500" : "bg-red-500"}`}
                    style={{ width: `${Math.min(100, pct)}%` }}
                  />
                </div>
                <span className="font-mono w-16 text-right">
                  {kr.current ?? kr.baseline}/{kr.target}
                </span>
                <span className={`w-10 text-right font-medium ${pct >= 100 ? "text-green-600" : "text-gray-500"}`}>
                  {pct}%
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function ContextPanel({ slug, taskId }: ContextPanelProps) {
  const [context, setContext] = useState<TaskContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [objective, setObjective] = useState<Objective | null>(null);

  // Progressive disclosure: only "task" expanded by default (D-099)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({ task: true });

  const fetchContext = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await tasksApi.context(slug, taskId);
      setContext(data);

      // Try to load business context from task origin
      const origin = data.task?.origin;
      if (origin && origin.startsWith("O-")) {
        try {
          const obj = await objectivesApi.get(slug, origin);
          setObjective(obj);
        } catch {
          // Objective not found — that's OK
        }
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [slug, taskId]);

  useEffect(() => {
    fetchContext();
  }, [fetchContext]);

  const toggle = (name: string) => {
    setExpanded((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  // Build final sections list including business context
  const allSections = useMemo(() => {
    if (!context) return [];
    const sections = [...context.sections];
    if (objective) {
      sections.push({
        name: "business",
        header: `Business Context — ${objective.title}`,
        content: "",
        token_estimate: 200,
        was_truncated: false,
      });
    }
    return sections;
  }, [context, objective]);

  const totalTokens = useMemo(() => {
    return allSections.reduce((sum, s) => sum + s.token_estimate, 0);
  }, [allSections]);

  const expandAll = () => {
    const next: Record<string, boolean> = {};
    for (const s of allSections) next[s.name] = true;
    setExpanded(next);
  };

  const collapseAll = () => {
    const next: Record<string, boolean> = {};
    for (const s of allSections) next[s.name] = false;
    setExpanded(next);
  };

  // AI annotations
  useAIElement({
    id: "context-panel",
    type: "section",
    label: "Context Panel",
    description: context
      ? `${allSections.length} sections, ${formatTokens(totalTokens)} tokens`
      : loading ? "loading" : "error",
    data: context ? {
      sections: allSections.map((s) => s.name),
      total_tokens: totalTokens,
      task_id: taskId,
      has_business_context: !!objective,
    } : undefined,
    actions: [
      { label: "Refresh context", description: "Reload context from API" },
    ],
  });

  if (loading) {
    return (
      <div className="rounded-lg border bg-white px-4 py-8 text-center">
        <div className="animate-pulse text-sm text-gray-400">Loading context...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
        <p className="text-sm text-red-600">{error}</p>
        <button onClick={fetchContext} className="mt-2 text-xs text-red-500 hover:text-red-700 underline">
          Retry
        </button>
      </div>
    );
  }

  if (!context) return null;

  return (
    <div>
      {/* Summary bar */}
      <div className="flex items-center justify-between rounded-lg border bg-white px-4 py-3 mb-4">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-700">Execution Context</span>
          <span className="text-xs text-gray-400">
            {allSections.length} section{allSections.length !== 1 ? "s" : ""}
          </span>
          {context.scopes.length > 0 && (
            <div className="flex gap-1">
              {context.scopes.map((s) => (
                <span key={s} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-sm font-mono font-semibold ${tokenColor(totalTokens)}`}>
            {formatTokens(totalTokens)} tokens
          </span>
          <div className="flex gap-1">
            <button onClick={expandAll} className="text-xs text-gray-400 hover:text-gray-600 px-1">
              Expand all
            </button>
            <span className="text-gray-300">|</span>
            <button onClick={collapseAll} className="text-xs text-gray-400 hover:text-gray-600 px-1">
              Collapse all
            </button>
          </div>
        </div>
      </div>

      {/* Sections */}
      <div className="space-y-3">
        {allSections.map((section) => {
          const isOpen = expanded[section.name] ?? false;
          const icon = SECTION_ICONS[section.name] ?? "\u{1F4C4}";

          return (
            <div key={section.name} className="rounded-lg border bg-white overflow-hidden">
              <button
                onClick={() => toggle(section.name)}
                className="flex items-center justify-between w-full px-4 py-3 hover:bg-gray-50 transition-colors text-left"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs select-none">{isOpen ? "\u25BC" : "\u25B6"}</span>
                  <span className="text-sm">{icon}</span>
                  <span className="text-sm font-medium text-gray-800">{section.header}</span>
                  {section.was_truncated && <Badge variant="warning">truncated</Badge>}
                </div>
                <span className={`text-xs font-mono ${tokenColor(section.token_estimate)}`}>
                  {formatTokens(section.token_estimate)}
                </span>
              </button>

              {isOpen && (
                <div className="border-t px-4 py-3">
                  {section.was_truncated && (
                    <div className="flex items-center gap-2 mb-3 rounded-md bg-yellow-50 border border-yellow-200 px-3 py-2">
                      <span className="text-xs text-yellow-700">
                        Section truncated to fit token limits.
                      </span>
                    </div>
                  )}

                  {/* Special renderers for certain sections */}
                  {section.name === "guidelines" ? (
                    <GuidelinesContent content={section.content} />
                  ) : section.name === "business" && objective ? (
                    <BusinessContextSection objective={objective} />
                  ) : (
                    <pre className="text-xs font-mono text-gray-700 bg-gray-50 rounded-md p-4 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                      {section.content}
                    </pre>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {allSections.length === 0 && (
        <div className="rounded-lg border bg-gray-50 px-4 py-8 text-center">
          <p className="text-sm text-gray-400">No context sections assembled for this task.</p>
        </div>
      )}
    </div>
  );
}
