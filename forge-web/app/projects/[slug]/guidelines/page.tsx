"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import { useEntityStore } from "@/stores/entityStore";
import { GuidelineCard } from "@/components/entities/GuidelineCard";
import { StatusFilter } from "@/components/shared/StatusFilter";
import Link from "next/link";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import { useMultiSelect } from "@/hooks/useMultiSelect";
import { BulkActionBar } from "@/components/shared/BulkActionBar";
import { guidelines as guidelinesApi } from "@/lib/api";
import type { Guideline, GuidelineWeight } from "@/lib/types";

const STATUSES = ["ACTIVE", "DEPRECATED"];
const WEIGHTS: GuidelineWeight[] = ["must", "should", "may"];

export default function GuidelinesPage() {
  const { slug } = useParams() as { slug: string };
  const { slices, fetchEntities } = useEntityStore();
  const [statusFilter, setStatusFilter] = useState("");
  const [weightFilter, setWeightFilter] = useState("");

  const { selectedIds, isSelected, toggle, deselectAll, count: selectionCount } = useMultiSelect();

  const handleBulkDelete = async () => {
    const ids = Array.from(selectedIds);
    await Promise.allSettled(ids.map((id) => guidelinesApi.remove(slug, id)));
    fetchEntities(slug, "guidelines");
  };

  useEffect(() => {
    fetchEntities(slug, "guidelines");
  }, [slug, fetchEntities]);

  const guidelines = slices.guidelines.items as Guideline[];
  const filtered = guidelines
    .filter((g) => !statusFilter || g.status === statusFilter)
    .filter((g) => !weightFilter || g.weight === weightFilter);

  const weightDist = useMemo(() => {
    const dist: Record<string, number> = {};
    for (const g of guidelines) dist[g.weight] = (dist[g.weight] ?? 0) + 1;
    return dist;
  }, [guidelines]);

  useAIPage({
    id: "guidelines",
    title: `Guidelines (${slices.guidelines.count})`,
    description: `Coding standards and conventions for project ${slug}`,
    route: `/projects/${slug}/guidelines`,
  });

  useAIElement({
    id: "status-filter",
    type: "filter",
    label: "Status Filter",
    value: statusFilter || "All",
    actions: [{ label: "Filter", description: "Filter guidelines by status" }],
  });

  useAIElement({
    id: "guideline-list",
    type: "list",
    label: "Guidelines",
    description: `${filtered.length} shown of ${slices.guidelines.count} total`,
    data: {
      count: slices.guidelines.count,
      filtered: filtered.length,
      weights: weightDist,
    },
    actions: [
      {
        label: "Create guideline",
        toolName: "createGuideline",
        toolParams: ["title*", "scope*", "content*", "weight", "rationale"],
      },
      {
        label: "Update guideline",
        toolName: "updateGuideline",
        toolParams: ["guideline_id*", "title", "content", "status", "weight", "scope"],
      },
    ],
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Guidelines ({slices.guidelines.count})</h2>
        <div className="flex gap-3 items-center">
          <StatusFilter options={STATUSES} value={statusFilter} onChange={setStatusFilter} />
          <StatusFilter options={WEIGHTS} value={weightFilter} onChange={setWeightFilter} label="Weight" />
          <Link
            href={`/projects/${slug}/guidelines/new`}
            className="rounded-md bg-forge-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-forge-700 transition-colors"
          >
            + New Guideline
          </Link>
        </div>
      </div>

      {slices.guidelines.loading && <p className="text-sm text-gray-400">Loading...</p>}
      {slices.guidelines.error && <p className="text-sm text-red-600 mb-2">{slices.guidelines.error}</p>}
      <BulkActionBar count={selectionCount} entityLabel="guidelines" onDelete={handleBulkDelete} onDeselectAll={deselectAll} />
      <div className="space-y-3">
        {filtered.map((g) => (
          <GuidelineCard
            key={g.id}
            guideline={g}
            slug={slug}
            selected={isSelected(g.id)}
            onSelect={() => toggle(g.id)}
          />
        ))}
        {!slices.guidelines.loading && filtered.length === 0 && (
          <p className="text-sm text-gray-400">No guidelines matching filters</p>
        )}
      </div>
    </div>
  );
}
