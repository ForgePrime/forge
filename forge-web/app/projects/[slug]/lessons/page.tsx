"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import { useEntityStore } from "@/stores/entityStore";
import { LessonCard } from "@/components/entities/LessonCard";
import { StatusFilter } from "@/components/shared/StatusFilter";
import Link from "next/link";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import { useMultiSelect } from "@/hooks/useMultiSelect";
import { BulkActionBar } from "@/components/shared/BulkActionBar";
import { lessons as lessonsApi } from "@/lib/api";
import type { Lesson } from "@/lib/types";

const CATEGORIES = [
  "pattern-discovered", "mistake-avoided", "decision-validated",
  "decision-reversed", "tool-insight", "architecture-lesson",
  "process-improvement", "market-insight",
];

export default function LessonsPage() {
  const { slug } = useParams() as { slug: string };
  const { slices, fetchEntities } = useEntityStore();
  const [categoryFilter, setCategoryFilter] = useState("");

  const { selectedIds, isSelected, toggle, deselectAll, count: selectionCount } = useMultiSelect();

  const handleBulkDelete = async () => {
    const ids = Array.from(selectedIds);
    await Promise.allSettled(ids.map((id) => lessonsApi.remove(slug, id)));
    fetchEntities(slug, "lessons");
  };

  useEffect(() => {
    fetchEntities(slug, "lessons");
  }, [slug, fetchEntities]);

  const handleRefresh = useCallback(() => {
    fetchEntities(slug, "lessons");
  }, [slug, fetchEntities]);

  const lessons = slices.lessons.items as Lesson[];
  const filtered = categoryFilter
    ? lessons.filter((l) => l.category === categoryFilter)
    : lessons;

  const categoryDist = useMemo(() => {
    const dist: Record<string, number> = {};
    for (const l of lessons) dist[l.category] = (dist[l.category] ?? 0) + 1;
    return dist;
  }, [lessons]);

  useAIPage({
    id: "lessons",
    title: `Lessons (${slices.lessons.count})`,
    description: `Compound learning and lessons from project ${slug}`,
    route: `/projects/${slug}/lessons`,
  });

  useAIElement({
    id: "category-filter",
    type: "filter",
    label: "Category Filter",
    value: categoryFilter || "All",
    actions: [{ label: "Filter", description: "Filter lessons by category" }],
  });

  useAIElement({
    id: "lesson-list",
    type: "list",
    label: "Lessons",
    description: `${filtered.length} shown of ${slices.lessons.count} total`,
    data: {
      count: slices.lessons.count,
      filtered: filtered.length,
      categories: categoryDist,
    },
    actions: [
      {
        label: "Record lesson",
        toolName: "createLesson",
        toolParams: ["title*", "category*", "description*", "severity", "tags"],
      },
    ],
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Lessons ({slices.lessons.count})</h2>
        <div className="flex items-center gap-3">
          <StatusFilter options={CATEGORIES} value={categoryFilter} onChange={setCategoryFilter} label="Category" />
          <Link
            href={`/projects/${slug}/lessons/new`}
            className="px-3 py-1.5 text-sm text-white bg-forge-600 rounded-md hover:bg-forge-700"
          >
            + Record Lesson
          </Link>
        </div>
      </div>
      {slices.lessons.loading && <p className="text-sm text-gray-400">Loading...</p>}
      {slices.lessons.error && <p className="text-sm text-red-600 mb-2">{slices.lessons.error}</p>}
      <BulkActionBar count={selectionCount} entityLabel="lessons" onDelete={handleBulkDelete} onDeselectAll={deselectAll} />
      <div className="space-y-3">
        {filtered.map((l) => (
          <LessonCard key={l.id} lesson={l} slug={slug} onPromoted={handleRefresh} selected={isSelected(l.id)} onSelect={() => toggle(l.id)} />
        ))}
        {!slices.lessons.loading && filtered.length === 0 && (
          <p className="text-sm text-gray-400">No lessons{categoryFilter ? ` in category ${categoryFilter}` : ""}</p>
        )}
      </div>

    </div>
  );
}
