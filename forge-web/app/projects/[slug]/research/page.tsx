"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import { useResearchStore } from "@/stores/researchStore";
import { ResearchCard } from "@/components/entities/ResearchCard";
import { StatusFilter } from "@/components/shared/StatusFilter";
import Link from "next/link";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import { useMultiSelect } from "@/hooks/useMultiSelect";
import { BulkActionBar } from "@/components/shared/BulkActionBar";
import { research as researchApi } from "@/lib/api";
import type { Research } from "@/lib/types";

const STATUSES = ["DRAFT", "ACTIVE", "SUPERSEDED", "ARCHIVED"];
const CATEGORIES = [
  "architecture", "domain", "feasibility", "risk", "business", "technical",
];

export default function ResearchPage() {
  const { slug } = useParams() as { slug: string };
  const { items, count, fetchAll } = useResearchStore();
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [search, setSearch] = useState("");

  const { selectedIds, isSelected, toggle, deselectAll, count: selectionCount } = useMultiSelect();

  const handleBulkDelete = async () => {
    const ids = Array.from(selectedIds);
    await Promise.allSettled(ids.map((id) => researchApi.remove(slug, id)));
    fetchAll(slug);
  };

  useEffect(() => {
    fetchAll(slug);
  }, [slug, fetchAll]);

  const research = items as Research[];

  const filtered = useMemo(() => {
    let result = research;
    if (statusFilter) {
      result = result.filter((r) => r.status === statusFilter);
    }
    if (categoryFilter) {
      result = result.filter((r) => r.category === categoryFilter);
    }
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (r) =>
          r.title.toLowerCase().includes(q) ||
          r.summary.toLowerCase().includes(q) ||
          r.topic.toLowerCase().includes(q) ||
          r.tags.some((t) => t.toLowerCase().includes(q))
      );
    }
    return result;
  }, [research, statusFilter, categoryFilter, search]);

  const categoryDist = useMemo(() => {
    const dist: Record<string, number> = {};
    for (const r of research) dist[r.category] = (dist[r.category] ?? 0) + 1;
    return dist;
  }, [research]);

  // --- AI Annotations ---
  useAIPage({
    id: "research",
    title: `Research (${count})`,
    description: `Research objects for project ${slug}`,
    route: `/projects/${slug}/research`,
  });

  useAIElement({
    id: "status-filter",
    type: "filter",
    label: "Status Filter",
    value: statusFilter || "All",
    actions: [{ label: "Filter", description: "Filter research by status" }],
  });

  useAIElement({
    id: "research-list",
    type: "list",
    label: "Research Objects",
    description: `${filtered.length} shown of ${count} total`,
    data: { count, filtered: filtered.length, categories: categoryDist },
    actions: [
      {
        label: "Create research",
        toolName: "createResearch",
        toolParams: ["title*", "topic*", "category*", "summary*"],
      },
      {
        label: "Update research",
        toolName: "updateResearch",
        toolParams: ["research_id*", "title", "status", "key_findings"],
      },
    ],
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Research ({count})</h2>
        <div className="flex gap-3 items-center">
          <StatusFilter options={STATUSES} value={statusFilter} onChange={setStatusFilter} />
          <StatusFilter options={CATEGORIES} value={categoryFilter} onChange={setCategoryFilter} label="Category" />
          <Link
            href={`/projects/${slug}/research/new`}
            className="px-3 py-1.5 text-sm text-white bg-forge-600 rounded-md hover:bg-forge-700"
          >
            + New Research
          </Link>
        </div>
      </div>

      <div className="mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search title, topic, summary, or tags..."
          className="w-full rounded-md border px-3 py-2 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
        />
      </div>

      <BulkActionBar count={selectionCount} entityLabel="research items" onDelete={handleBulkDelete} onDeselectAll={deselectAll} />
      {filtered.length === 0 ? (
        <p className="text-sm text-gray-400">
          {count === 0
            ? "No research objects yet. Use /discover to create research."
            : "No matching research objects."}
        </p>
      ) : (
        <div className="space-y-3">
          {filtered.map((r) => (
            <ResearchCard
              key={r.id}
              research={r}
              slug={slug}
              selected={isSelected(r.id)}
              onSelect={() => toggle(r.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
