"use client";

import { useState, useEffect, useCallback } from "react";
import { decisions as decisionsApi } from "@/lib/api";
import { Badge, statusVariant } from "@/components/shared/Badge";
import { useAIElement } from "@/lib/ai-context";
import type { Decision, DecisionType, Confidence } from "@/lib/types";

const DECISION_TYPES: DecisionType[] = [
  "architecture", "implementation", "dependency", "security",
  "performance", "testing", "naming", "convention",
  "constraint", "business", "strategy", "other",
];

const CONFIDENCE_LEVELS: Confidence[] = ["HIGH", "MEDIUM", "LOW"];

interface DecisionRecordFormProps {
  slug: string;
  taskId: string;
}

export function DecisionRecordForm({ slug, taskId }: DecisionRecordFormProps) {
  const [expanded, setExpanded] = useState(false);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loadingDecisions, setLoadingDecisions] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form fields
  const [type, setType] = useState<DecisionType>("implementation");
  const [issue, setIssue] = useState("");
  const [recommendation, setRecommendation] = useState("");
  const [reasoning, setReasoning] = useState("");
  const [confidence, setConfidence] = useState<Confidence>("MEDIUM");

  const loadDecisions = useCallback(async () => {
    setLoadingDecisions(true);
    try {
      const res = await decisionsApi.list(slug, { task_id: taskId });
      setDecisions(
        (res.decisions || []).filter((d: Decision) => d.task_id === taskId)
      );
    } catch {
      // Silently handle — not critical
    } finally {
      setLoadingDecisions(false);
    }
  }, [slug, taskId]);

  useEffect(() => {
    loadDecisions();
  }, [loadDecisions]);

  const handleSubmit = useCallback(async () => {
    if (!issue.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await decisionsApi.create(slug, [{
        task_id: taskId,
        type,
        issue: issue.trim(),
        recommendation: recommendation.trim(),
        reasoning: reasoning.trim() || undefined,
        confidence,
        status: "OPEN",
        decided_by: "user",
      }]);
      // Reset form
      setIssue("");
      setRecommendation("");
      setReasoning("");
      setType("implementation");
      setConfidence("MEDIUM");
      // Reload decisions
      await loadDecisions();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }, [slug, taskId, type, issue, recommendation, reasoning, confidence, loadDecisions]);

  // AI annotation
  useAIElement({
    id: "decision-record",
    type: "section",
    label: "Decision Recording",
    description: `${decisions.length} decisions for task ${taskId}`,
    data: {
      task_id: taskId,
      decision_count: decisions.length,
      expanded,
    },
    actions: [
      {
        label: "Record decision",
        toolName: "recordDecision",
        toolParams: ["type*", "issue*", "recommendation*", "reasoning", "confidence"],
        description: "Record a new decision for this task",
      },
    ],
  });

  return (
    <div className="rounded-lg border bg-white">
      {/* Header - collapsible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full px-4 py-3 hover:bg-gray-50 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400 select-none">{expanded ? "\u25BC" : "\u25B6"}</span>
          <span className="text-sm font-medium text-gray-700">Decisions</span>
          <Badge variant="default">{decisions.length}</Badge>
        </div>
        <span className="text-xs text-gray-400">for {taskId}</span>
      </button>

      {expanded && (
        <div className="border-t">
          {/* Decision list */}
          {decisions.length > 0 && (
            <div className="divide-y border-b">
              {decisions.map((d) => (
                <div key={d.id} className="px-4 py-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">{d.id}</span>
                    <Badge variant={statusVariant(d.status)}>{d.status}</Badge>
                    <Badge variant="default">{d.type}</Badge>
                    {d.confidence && (
                      <span className="text-[10px] text-gray-400">{d.confidence}</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-700 mt-0.5">{d.issue}</p>
                  {d.recommendation && (
                    <p className="text-xs text-gray-500 mt-0.5">{d.recommendation}</p>
                  )}
                </div>
              ))}
            </div>
          )}
          {loadingDecisions && (
            <p className="text-xs text-gray-400 px-4 py-2">Loading decisions...</p>
          )}

          {/* Add decision form */}
          <div className="px-4 py-3 space-y-3">
            <div className="flex gap-2">
              <select
                value={type}
                onChange={(e) => setType(e.target.value as DecisionType)}
                className="text-xs border rounded px-2 py-1.5 bg-white text-gray-700"
              >
                {DECISION_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <select
                value={confidence}
                onChange={(e) => setConfidence(e.target.value as Confidence)}
                className="text-xs border rounded px-2 py-1.5 bg-white text-gray-700"
              >
                {CONFIDENCE_LEVELS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <input
              type="text"
              value={issue}
              onChange={(e) => setIssue(e.target.value)}
              placeholder="Issue / decision to record *"
              className="w-full text-xs border rounded px-2 py-1.5 placeholder-gray-300 focus:border-forge-400 focus:ring-1 focus:ring-forge-400"
            />

            <input
              type="text"
              value={recommendation}
              onChange={(e) => setRecommendation(e.target.value)}
              placeholder="Recommendation / chosen approach *"
              className="w-full text-xs border rounded px-2 py-1.5 placeholder-gray-300 focus:border-forge-400 focus:ring-1 focus:ring-forge-400"
            />

            <textarea
              value={reasoning}
              onChange={(e) => setReasoning(e.target.value)}
              placeholder="Reasoning (why this choice?)..."
              rows={2}
              className="w-full text-xs border rounded px-2 py-1.5 placeholder-gray-300 focus:border-forge-400 focus:ring-1 focus:ring-forge-400 resize-none"
            />

            {error && (
              <p className="text-xs text-red-600">{error}</p>
            )}

            <div className="flex justify-end">
              <button
                onClick={handleSubmit}
                disabled={submitting || !issue.trim() || !recommendation.trim()}
                className="px-3 py-1.5 text-xs text-white bg-forge-600 rounded hover:bg-forge-700 disabled:opacity-50"
              >
                {submitting ? "Recording..." : "Record Decision"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
