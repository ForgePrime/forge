"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { useEntityStore } from "@/stores/entityStore";
import { IdeaCard } from "@/components/entities/IdeaCard";
import { StatusFilter } from "@/components/shared/StatusFilter";
import { IdeaForm } from "@/components/forms/IdeaForm";
import type { Idea } from "@/lib/types";

const STATUSES = ["DRAFT", "EXPLORING", "APPROVED", "REJECTED", "COMMITTED"];

export default function IdeasPage() {
  const { slug } = useParams() as { slug: string };
  const { slices, fetchEntities } = useEntityStore();
  const [statusFilter, setStatusFilter] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editingIdea, setEditingIdea] = useState<Idea | undefined>();

  useEffect(() => {
    fetchEntities(slug, "ideas");
  }, [slug, fetchEntities]);

  const ideas = slices.ideas.items as Idea[];
  const filtered = statusFilter
    ? ideas.filter((i) => i.status === statusFilter)
    : ideas;

  const handleFormSuccess = useCallback(() => {
    fetchEntities(slug, "ideas");
  }, [slug, fetchEntities]);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Ideas ({slices.ideas.count})</h2>
        <div className="flex items-center gap-3">
          <StatusFilter options={STATUSES} value={statusFilter} onChange={setStatusFilter} />
          <button
            onClick={() => { setEditingIdea(undefined); setFormOpen(true); }}
            className="px-3 py-1.5 text-sm text-white bg-forge-600 rounded-md hover:bg-forge-700"
          >
            + New Idea
          </button>
        </div>
      </div>
      {slices.ideas.loading && <p className="text-sm text-gray-400">Loading...</p>}
      {slices.ideas.error && <p className="text-sm text-red-600 mb-2">{slices.ideas.error}</p>}
      <div className="space-y-3">
        {filtered.map((idea) => (
          <IdeaCard key={idea.id} idea={idea} onEdit={(i) => { setEditingIdea(i); setFormOpen(true); }} />
        ))}
        {!slices.ideas.loading && filtered.length === 0 && (
          <p className="text-sm text-gray-400">No ideas{statusFilter ? ` with status ${statusFilter}` : ""}</p>
        )}
      </div>

      <IdeaForm
        slug={slug}
        open={formOpen}
        onClose={() => { setFormOpen(false); setEditingIdea(undefined); }}
        idea={editingIdea}
        onSuccess={handleFormSuccess}
      />
    </div>
  );
}
