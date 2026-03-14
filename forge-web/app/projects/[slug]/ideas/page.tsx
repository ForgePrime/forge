"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import { useEntityStore } from "@/stores/entityStore";
import { IdeaCard } from "@/components/entities/IdeaCard";
import { StatusFilter } from "@/components/shared/StatusFilter";
import Link from "next/link";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import { useMultiSelect } from "@/hooks/useMultiSelect";
import { BulkActionBar } from "@/components/shared/BulkActionBar";
import { ideas as ideasApi } from "@/lib/api";
import type { Idea } from "@/lib/types";

const STATUSES = ["DRAFT", "EXPLORING", "APPROVED", "REJECTED", "COMMITTED"];

export default function IdeasPage() {
  const { slug } = useParams() as { slug: string };
  const { slices, fetchEntities } = useEntityStore();
  const [statusFilter, setStatusFilter] = useState("");
  useEffect(() => {
    fetchEntities(slug, "ideas");
  }, [slug, fetchEntities]);

  const { selectedIds, isSelected, toggle, deselectAll, count: selectionCount } = useMultiSelect();

  const handleBulkDelete = async () => {
    const ids = Array.from(selectedIds);
    await Promise.allSettled(ids.map((id) => ideasApi.remove(slug, id)));
    fetchEntities(slug, "ideas");
  };

  const ideas = slices.ideas.items as Idea[];
  const filtered = statusFilter
    ? ideas.filter((i) => i.status === statusFilter)
    : ideas;

  // ---------------------------------------------------------------------------
  // AI Annotations
  // ---------------------------------------------------------------------------

  useAIPage({
    id: "ideas",
    title: `Ideas (${slices.ideas.count})`,
    description: `Idea staging area for project ${slug}`,
    route: `/projects/${slug}/ideas`,
  });

  const statusDist = useMemo(() => {
    const dist: Record<string, number> = {};
    for (const i of ideas) {
      dist[i.status] = (dist[i.status] ?? 0) + 1;
    }
    return dist;
  }, [ideas]);

  useAIElement({
    id: "status-filter",
    type: "filter",
    label: "Status Filter",
    value: statusFilter || "All",
    actions: [{ label: "Filter", description: "Filter ideas by status" }],
  });

  useAIElement({
    id: "idea-list",
    type: "list",
    label: "Ideas",
    description: `${filtered.length} shown of ${slices.ideas.count} total`,
    data: {
      count: slices.ideas.count,
      filtered: filtered.length,
      statuses: statusDist,
    },
    actions: [
      { label: "Approve idea", toolName: "updateIdea", toolParams: ["id*", "status=APPROVED"], availableWhen: "status = EXPLORING" },
      { label: "Reject idea", toolName: "updateIdea", toolParams: ["id*", "status=REJECTED", "rejection_reason"], availableWhen: "status = EXPLORING" },
      { label: "Commit idea", toolName: "updateIdea", toolParams: ["id*", "status=COMMITTED"], availableWhen: "status = APPROVED" },
      { label: "Create idea", toolName: "createIdea", toolParams: ["title*", "description*", "category", "priority", "parent_id", "advances_key_results"] },
    ],
  });


  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Ideas ({slices.ideas.count})</h2>
        <div className="flex items-center gap-3">
          <StatusFilter options={STATUSES} value={statusFilter} onChange={setStatusFilter} />
          <Link
            href={`/projects/${slug}/ideas/new`}
            className="px-3 py-1.5 text-sm text-white bg-forge-600 rounded-md hover:bg-forge-700"
          >
            + New Idea
          </Link>
        </div>
      </div>
      {slices.ideas.loading && <p className="text-sm text-gray-400">Loading...</p>}
      {slices.ideas.error && <p className="text-sm text-red-600 mb-2">{slices.ideas.error}</p>}
      <BulkActionBar count={selectionCount} entityLabel="ideas" onDelete={handleBulkDelete} onDeselectAll={deselectAll} />
      <div className="space-y-3">
        {filtered.map((idea) => (
          <IdeaCard key={idea.id} idea={idea} slug={slug} selected={isSelected(idea.id)} onSelect={() => toggle(idea.id)} />
        ))}
        {!slices.ideas.loading && filtered.length === 0 && (
          <p className="text-sm text-gray-400">No ideas{statusFilter ? ` with status ${statusFilter}` : ""}</p>
        )}
      </div>

    </div>
  );
}
