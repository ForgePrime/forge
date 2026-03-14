"use client";

import { useState, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import { useEntityData } from "@/hooks/useEntityData";
import { useDecisionStore, updateDecision as updateDecisionAction } from "@/stores/decisionStore";
import { DecisionCard } from "@/components/entities/DecisionCard";
import { StatusFilter } from "@/components/shared/StatusFilter";
import Link from "next/link";
import { useMultiSelect } from "@/hooks/useMultiSelect";
import { BulkActionBar } from "@/components/shared/BulkActionBar";
import { decisions as decisionsApi } from "@/lib/api";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import type { Decision } from "@/lib/types";

const STATUSES = ["OPEN", "CLOSED", "DEFERRED", "ANALYZING", "MITIGATED", "ACCEPTED"];

export default function DecisionsPage() {
  const { slug } = useParams() as { slug: string };
  const { items, count, isLoading, error, mutate } = useEntityData<Decision>(slug, "decisions");
  const saving = useDecisionStore((s) => s.saving);
  const [statusFilter, setStatusFilter] = useState("");
  const { selectedIds, isSelected, toggle, deselectAll, count: selectionCount } = useMultiSelect();

  const handleBulkDelete = async () => {
    const ids = Array.from(selectedIds);
    await Promise.allSettled(ids.map((id) => decisionsApi.remove(slug, id)));
    mutate();
  };

  const decisions = items;
  const filtered = statusFilter
    ? decisions.filter((d) => d.status === statusFilter)
    : decisions;

  // ---------------------------------------------------------------------------
  // AI Annotations
  // ---------------------------------------------------------------------------

  useAIPage({
    id: "decisions",
    title: `Decisions (${count})`,
    description: `Decision log for project ${slug}`,
    route: `/projects/${slug}/decisions`,
  });

  const statusDist = useMemo(() => {
    const dist: Record<string, number> = {};
    for (const d of decisions) {
      dist[d.status] = (dist[d.status] ?? 0) + 1;
    }
    return dist;
  }, [decisions]);

  useAIElement({
    id: "status-filter",
    type: "filter",
    label: "Status Filter",
    value: statusFilter || "All",
    actions: [{ label: "Filter", description: "Filter decisions by status" }],
  });

  useAIElement({
    id: "decision-list",
    type: "list",
    label: "Decisions",
    description: `${filtered.length} shown of ${count} total`,
    data: {
      count,
      filtered: filtered.length,
      statuses: statusDist,
    },
    actions: [
      { label: "Close decision", toolName: "updateDecision", toolParams: ["id*", "status=CLOSED", "resolution_notes"], availableWhen: "status = OPEN" },
      { label: "Defer decision", toolName: "updateDecision", toolParams: ["id*", "status=DEFERRED"], availableWhen: "status = OPEN" },
      { label: "Mitigate risk", toolName: "updateDecision", toolParams: ["id*", "status=MITIGATED", "mitigation_plan"], availableWhen: "status = ANALYZING" },
      { label: "Accept risk", toolName: "updateDecision", toolParams: ["id*", "status=ACCEPTED"], availableWhen: "status = ANALYZING" },
      { label: "Create decision", toolName: "createDecision", toolParams: ["task_id*", "type*", "issue*", "recommendation*", "reasoning", "alternatives", "confidence"] },
    ],
  });

  const handleStatusChange = (id: string, status: string) => {
    updateDecisionAction(slug, id, { status: status as Decision["status"] });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">
          Decisions ({count})
          {saving && <span className="ml-2 text-xs text-gray-400">Saving...</span>}
        </h2>
        <div className="flex items-center gap-3">
          <StatusFilter options={STATUSES} value={statusFilter} onChange={setStatusFilter} />
          <Link
            href={`/projects/${slug}/decisions/new`}
            className="px-3 py-1.5 text-sm text-white bg-forge-600 rounded-md hover:bg-forge-700"
          >
            + New Decision
          </Link>
        </div>
      </div>
      {isLoading && <p className="text-sm text-gray-400">Loading...</p>}
      {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
      <BulkActionBar count={selectionCount} entityLabel="decisions" onDelete={handleBulkDelete} onDeselectAll={deselectAll} />
      <div className="space-y-3">
        {filtered.map((d) => (
          <DecisionCard key={d.id} decision={d} slug={slug} onStatusChange={handleStatusChange} selected={isSelected(d.id)} onSelect={() => toggle(d.id)} />
        ))}
        {!isLoading && filtered.length === 0 && (
          <p className="text-sm text-gray-400">No decisions{statusFilter ? ` with status ${statusFilter}` : ""}</p>
        )}
      </div>

    </div>
  );
}
