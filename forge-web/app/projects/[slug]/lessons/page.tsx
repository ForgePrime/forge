"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import { useEntityStore } from "@/stores/entityStore";
import { LessonCard } from "@/components/entities/LessonCard";
import { StatusFilter } from "@/components/shared/StatusFilter";
import { LessonForm } from "@/components/forms/LessonForm";
import { useAIPage, useAIElement } from "@/lib/ai-context";
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
  const [formOpen, setFormOpen] = useState(false);

  useEffect(() => {
    fetchEntities(slug, "lessons");
  }, [slug, fetchEntities]);

  const handleFormSuccess = useCallback(() => {
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

  useAIElement({
    id: "lesson-form",
    type: "form",
    label: "Lesson Form",
    value: formOpen,
    description: formOpen ? "open (creating)" : "closed",
    data: { fields: ["title*", "category*", "description*", "severity", "tags"] },
    actions: [
      {
        label: "Create",
        toolName: "createLesson",
        toolParams: ["title*", "category*", "description*", "severity"],
      },
    ],
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Lessons ({slices.lessons.count})</h2>
        <div className="flex items-center gap-3">
          <StatusFilter options={CATEGORIES} value={categoryFilter} onChange={setCategoryFilter} label="Category" />
          <button
            onClick={() => setFormOpen(true)}
            className="px-3 py-1.5 text-sm text-white bg-forge-600 rounded-md hover:bg-forge-700"
          >
            + Record Lesson
          </button>
        </div>
      </div>
      {slices.lessons.loading && <p className="text-sm text-gray-400">Loading...</p>}
      {slices.lessons.error && <p className="text-sm text-red-600 mb-2">{slices.lessons.error}</p>}
      <div className="space-y-3">
        {filtered.map((l) => (
          <LessonCard key={l.id} lesson={l} />
        ))}
        {!slices.lessons.loading && filtered.length === 0 && (
          <p className="text-sm text-gray-400">No lessons{categoryFilter ? ` in category ${categoryFilter}` : ""}</p>
        )}
      </div>

      <LessonForm
        slug={slug}
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSuccess={handleFormSuccess}
      />
    </div>
  );
}
