"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { useEntityStore } from "@/stores/entityStore";
import { DecisionCard } from "@/components/entities/DecisionCard";
import { StatusFilter } from "@/components/shared/StatusFilter";
import { DecisionForm } from "@/components/forms/DecisionForm";
import type { Decision } from "@/lib/types";

const STATUSES = ["OPEN", "CLOSED", "DEFERRED", "ANALYZING", "MITIGATED", "ACCEPTED"];

export default function DecisionsPage() {
  const { slug } = useParams() as { slug: string };
  const { slices, fetchEntities, updateDecision } = useEntityStore();
  const [statusFilter, setStatusFilter] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editingDecision, setEditingDecision] = useState<Decision | undefined>();

  useEffect(() => {
    fetchEntities(slug, "decisions");
  }, [slug, fetchEntities]);

  const decisions = slices.decisions.items as Decision[];
  const filtered = statusFilter
    ? decisions.filter((d) => d.status === statusFilter)
    : decisions;

  const handleStatusChange = (id: string, status: string) => {
    updateDecision(slug, id, { status: status as Decision["status"] });
  };

  const handleEdit = (decision: Decision) => {
    setEditingDecision(decision);
    setFormOpen(true);
  };

  const handleCreate = () => {
    setEditingDecision(undefined);
    setFormOpen(true);
  };

  const handleFormClose = () => {
    setFormOpen(false);
    setEditingDecision(undefined);
  };

  const handleFormSuccess = useCallback(() => {
    fetchEntities(slug, "decisions");
  }, [slug, fetchEntities]);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Decisions ({slices.decisions.count})</h2>
        <div className="flex items-center gap-3">
          <StatusFilter options={STATUSES} value={statusFilter} onChange={setStatusFilter} />
          <button
            onClick={handleCreate}
            className="px-3 py-1.5 text-sm text-white bg-forge-600 rounded-md hover:bg-forge-700"
          >
            + New Decision
          </button>
        </div>
      </div>
      {slices.decisions.loading && <p className="text-sm text-gray-400">Loading...</p>}
      {slices.decisions.error && <p className="text-sm text-red-600 mb-2">{slices.decisions.error}</p>}
      <div className="space-y-3">
        {filtered.map((d) => (
          <DecisionCard key={d.id} decision={d} slug={slug} onStatusChange={handleStatusChange} onEdit={handleEdit} />
        ))}
        {!slices.decisions.loading && filtered.length === 0 && (
          <p className="text-sm text-gray-400">No decisions{statusFilter ? ` with status ${statusFilter}` : ""}</p>
        )}
      </div>

      <DecisionForm
        slug={slug}
        open={formOpen}
        onClose={handleFormClose}
        decision={editingDecision}
        onSuccess={handleFormSuccess}
      />
    </div>
  );
}
