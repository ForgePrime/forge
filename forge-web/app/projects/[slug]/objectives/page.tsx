"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import { useEntityStore } from "@/stores/entityStore";
import { ObjectiveCard } from "@/components/entities/ObjectiveCard";
import { StatusFilter } from "@/components/shared/StatusFilter";
import { CoverageDashboard } from "@/components/objectives/CoverageDashboard";
import Link from "next/link";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import { useMultiSelect } from "@/hooks/useMultiSelect";
import { BulkActionBar } from "@/components/shared/BulkActionBar";
import { objectives as objectivesApi } from "@/lib/api";
import type { Objective } from "@/lib/types";

const STATUSES = ["ACTIVE", "ACHIEVED", "ABANDONED", "PAUSED"];

export default function ObjectivesPage() {
  const { slug } = useParams() as { slug: string };
  const { slices, fetchEntities } = useEntityStore();
  const [statusFilter, setStatusFilter] = useState("");
  const [showCoverage, setShowCoverage] = useState(false);

  useEffect(() => {
    fetchEntities(slug, "objectives");
  }, [slug, fetchEntities]);

  const { selectedIds, isSelected, toggle, deselectAll, count: selectionCount } = useMultiSelect();

  const handleBulkDelete = async () => {
    const ids = Array.from(selectedIds);
    await Promise.allSettled(ids.map((id) => objectivesApi.remove(slug, id)));
    fetchEntities(slug, "objectives");
  };

  const objectives = slices.objectives.items as Objective[];
  const filtered = statusFilter
    ? objectives.filter((o) => o.status === statusFilter)
    : objectives;

  // ---------------------------------------------------------------------------
  // AI Annotations
  // ---------------------------------------------------------------------------

  useAIPage({
    id: "objectives",
    title: `Objectives (${slices.objectives.count})`,
    description: `Business objectives for project ${slug}`,
    route: `/projects/${slug}/objectives`,
  });

  const statusDist = useMemo(() => {
    const dist: Record<string, number> = {};
    for (const o of objectives) {
      dist[o.status] = (dist[o.status] ?? 0) + 1;
    }
    return dist;
  }, [objectives]);

  useAIElement({
    id: "status-filter",
    type: "filter",
    label: "Status Filter",
    value: statusFilter || "All",
    actions: [{ label: "Filter", description: "Filter objectives by status" }],
  });

  useAIElement({
    id: "objective-list",
    type: "list",
    label: "Objectives",
    description: `${filtered.length} shown of ${slices.objectives.count} total`,
    data: {
      count: slices.objectives.count,
      filtered: filtered.length,
      statuses: statusDist,
    },
    actions: [
      { label: "Update KR progress", toolName: "updateObjective", toolParams: ["id*", "key_results[{id, current, status}]"], availableWhen: "status = ACTIVE" },
      { label: "Mark achieved", toolName: "updateObjective", toolParams: ["id*", "status=ACHIEVED"], availableWhen: "status = ACTIVE" },
      { label: "Abandon", toolName: "updateObjective", toolParams: ["id*", "status=ABANDONED"], availableWhen: "status = ACTIVE" },
      { label: "Pause", toolName: "updateObjective", toolParams: ["id*", "status=PAUSED"], availableWhen: "status = ACTIVE" },
      { label: "Create objective", toolName: "createObjective", toolParams: ["title*", "description*", "key_results*", "appetite", "scopes"] },
    ],
  });


  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Objectives ({slices.objectives.count})</h2>
        <div className="flex items-center gap-3">
          <StatusFilter options={STATUSES} value={statusFilter} onChange={setStatusFilter} />
          <button
            onClick={() => setShowCoverage((v) => !v)}
            className={`px-3 py-1.5 text-sm rounded-md border ${showCoverage ? "bg-forge-50 border-forge-300 text-forge-700" : "border-gray-200 text-gray-600 hover:bg-gray-50"}`}
          >
            Coverage
          </button>
          <Link
            href={`/projects/${slug}/objectives/new`}
            className="px-3 py-1.5 text-sm text-white bg-forge-600 rounded-md hover:bg-forge-700"
          >
            + New Objective
          </Link>
        </div>
      </div>
      {showCoverage && (
        <div className="mb-4">
          <CoverageDashboard slug={slug} />
        </div>
      )}
      {slices.objectives.loading && <p className="text-sm text-gray-400">Loading...</p>}
      {slices.objectives.error && <p className="text-sm text-red-600 mb-2">{slices.objectives.error}</p>}
      <BulkActionBar count={selectionCount} entityLabel="objectives" onDelete={handleBulkDelete} onDeselectAll={deselectAll} />
      <div className="space-y-3">
        {filtered.map((o) => (
          <ObjectiveCard key={o.id} objective={o} slug={slug} selected={isSelected(o.id)} onSelect={() => toggle(o.id)} />
        ))}
        {!slices.objectives.loading && filtered.length === 0 && (
          <p className="text-sm text-gray-400">No objectives{statusFilter ? ` with status ${statusFilter}` : ""}</p>
        )}
      </div>

    </div>
  );
}
