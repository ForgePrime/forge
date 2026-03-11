"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { useEntityStore } from "@/stores/entityStore";
import { ObjectiveCard } from "@/components/entities/ObjectiveCard";
import { StatusFilter } from "@/components/shared/StatusFilter";
import { ObjectiveForm } from "@/components/forms/ObjectiveForm";
import type { Objective } from "@/lib/types";

const STATUSES = ["ACTIVE", "ACHIEVED", "ABANDONED", "PAUSED"];

export default function ObjectivesPage() {
  const { slug } = useParams() as { slug: string };
  const { slices, fetchEntities } = useEntityStore();
  const [statusFilter, setStatusFilter] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editingObj, setEditingObj] = useState<Objective | undefined>();

  useEffect(() => {
    fetchEntities(slug, "objectives");
  }, [slug, fetchEntities]);

  const objectives = slices.objectives.items as Objective[];
  const filtered = statusFilter
    ? objectives.filter((o) => o.status === statusFilter)
    : objectives;

  const handleFormSuccess = useCallback(() => {
    fetchEntities(slug, "objectives");
  }, [slug, fetchEntities]);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Objectives ({slices.objectives.count})</h2>
        <div className="flex items-center gap-3">
          <StatusFilter options={STATUSES} value={statusFilter} onChange={setStatusFilter} />
          <button
            onClick={() => { setEditingObj(undefined); setFormOpen(true); }}
            className="px-3 py-1.5 text-sm text-white bg-forge-600 rounded-md hover:bg-forge-700"
          >
            + New Objective
          </button>
        </div>
      </div>
      {slices.objectives.loading && <p className="text-sm text-gray-400">Loading...</p>}
      {slices.objectives.error && <p className="text-sm text-red-600 mb-2">{slices.objectives.error}</p>}
      <div className="space-y-3">
        {filtered.map((o) => (
          <ObjectiveCard key={o.id} objective={o} onEdit={(obj) => { setEditingObj(obj); setFormOpen(true); }} />
        ))}
        {!slices.objectives.loading && filtered.length === 0 && (
          <p className="text-sm text-gray-400">No objectives{statusFilter ? ` with status ${statusFilter}` : ""}</p>
        )}
      </div>

      <ObjectiveForm
        slug={slug}
        open={formOpen}
        onClose={() => { setFormOpen(false); setEditingObj(undefined); }}
        objective={editingObj}
        onSuccess={handleFormSuccess}
      />
    </div>
  );
}
