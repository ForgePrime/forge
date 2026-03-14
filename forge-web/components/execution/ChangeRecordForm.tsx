"use client";

import { useState, useEffect, useCallback } from "react";
import { changes as changesApi, decisions as decisionsApi } from "@/lib/api";
import { Badge } from "@/components/shared/Badge";
import { useAIElement } from "@/lib/ai-context";
import type { ChangeRecord, ChangeAction, Decision } from "@/lib/types";

const CHANGE_ACTIONS: ChangeAction[] = ["create", "edit", "delete", "rename"];

interface ChangeRecordFormProps {
  slug: string;
  taskId: string;
}

export function ChangeRecordForm({ slug, taskId }: ChangeRecordFormProps) {
  const [expanded, setExpanded] = useState(false);
  const [changeList, setChangeList] = useState<ChangeRecord[]>([]);
  const [taskDecisions, setTaskDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form fields
  const [filePath, setFilePath] = useState("");
  const [action, setAction] = useState<ChangeAction>("edit");
  const [summary, setSummary] = useState("");
  const [selectedDecisionIds, setSelectedDecisionIds] = useState<string[]>([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [chRes, decRes] = await Promise.all([
        changesApi.list(slug, { task_id: taskId }),
        decisionsApi.list(slug, { task_id: taskId }),
      ]);
      setChangeList(
        (chRes.changes || []).filter((c: ChangeRecord) => c.task_id === taskId)
      );
      setTaskDecisions(
        (decRes.decisions || []).filter((d: Decision) => d.task_id === taskId)
      );
    } catch {
      // Non-critical
    } finally {
      setLoading(false);
    }
  }, [slug, taskId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const toggleDecisionId = (id: string) => {
    setSelectedDecisionIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  };

  const handleSubmit = useCallback(async () => {
    if (!filePath.trim() || !summary.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await changesApi.create(slug, [{
        task_id: taskId,
        file: filePath.trim(),
        action,
        summary: summary.trim(),
        decision_ids: selectedDecisionIds.length > 0 ? selectedDecisionIds : undefined,
      }]);
      setFilePath("");
      setSummary("");
      setSelectedDecisionIds([]);
      setAction("edit");
      await loadData();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }, [slug, taskId, filePath, action, summary, selectedDecisionIds, loadData]);

  // AI annotation
  useAIElement({
    id: "change-record",
    type: "section",
    label: "Change Recording",
    description: `${changeList.length} changes for task ${taskId}`,
    data: {
      task_id: taskId,
      change_count: changeList.length,
      expanded,
    },
    actions: [
      {
        label: "Record change",
        toolName: "recordChange",
        toolParams: ["file*", "action*", "summary*", "decision_ids"],
        description: "Record a file change for this task",
      },
    ],
  });

  const actionColor: Record<string, string> = {
    create: "text-green-600",
    edit: "text-blue-600",
    delete: "text-red-600",
    rename: "text-yellow-600",
  };

  return (
    <div className="rounded-lg border bg-white">
      {/* Header - collapsible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full px-4 py-3 hover:bg-gray-50 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400 select-none">{expanded ? "\u25BC" : "\u25B6"}</span>
          <span className="text-sm font-medium text-gray-700">Changes</span>
          <Badge variant="default">{changeList.length}</Badge>
        </div>
        <span className="text-xs text-gray-400">for {taskId}</span>
      </button>

      {expanded && (
        <div className="border-t">
          {/* Change list */}
          {changeList.length > 0 && (
            <div className="divide-y border-b">
              {changeList.map((ch) => (
                <div key={ch.id} className="px-4 py-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-medium ${actionColor[ch.action] ?? "text-gray-600"}`}>
                      {ch.action}
                    </span>
                    <span className="text-xs font-mono text-gray-600 truncate">{ch.file}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{ch.summary}</p>
                  {ch.decision_ids && ch.decision_ids.length > 0 && (
                    <div className="flex gap-1 mt-1">
                      {ch.decision_ids.map((d) => (
                        <span key={d} className="text-[10px] bg-gray-100 text-gray-400 px-1 rounded">{d}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          {loading && (
            <p className="text-xs text-gray-400 px-4 py-2">Loading...</p>
          )}

          {/* Add change form */}
          <div className="px-4 py-3 space-y-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={filePath}
                onChange={(e) => setFilePath(e.target.value)}
                placeholder="File path *"
                className="flex-1 text-xs border rounded px-2 py-1.5 placeholder-gray-300 focus:border-forge-400 focus:ring-1 focus:ring-forge-400 font-mono"
              />
              <select
                value={action}
                onChange={(e) => setAction(e.target.value as ChangeAction)}
                className="text-xs border rounded px-2 py-1.5 bg-white text-gray-700"
              >
                {CHANGE_ACTIONS.map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>

            <input
              type="text"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Summary of change *"
              className="w-full text-xs border rounded px-2 py-1.5 placeholder-gray-300 focus:border-forge-400 focus:ring-1 focus:ring-forge-400"
            />

            {/* Decision linking */}
            {taskDecisions.length > 0 && (
              <div>
                <span className="text-[10px] text-gray-500">Link to decisions:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {taskDecisions.map((d) => (
                    <button
                      key={d.id}
                      type="button"
                      onClick={() => toggleDecisionId(d.id)}
                      className={`text-[10px] px-1.5 py-0.5 rounded border ${
                        selectedDecisionIds.includes(d.id)
                          ? "bg-forge-100 border-forge-400 text-forge-700"
                          : "bg-white border-gray-200 text-gray-400 hover:border-gray-300"
                      }`}
                    >
                      {d.id}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {error && <p className="text-xs text-red-600">{error}</p>}

            <div className="flex justify-end">
              <button
                onClick={handleSubmit}
                disabled={submitting || !filePath.trim() || !summary.trim()}
                className="px-3 py-1.5 text-xs text-white bg-forge-600 rounded hover:bg-forge-700 disabled:opacity-50"
              >
                {submitting ? "Recording..." : "Record Change"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
