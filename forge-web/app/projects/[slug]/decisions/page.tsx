"use client";

import { useState, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import { useEntityData } from "@/hooks/useEntityData";
import { useDecisionStore, updateDecision as updateDecisionAction } from "@/stores/decisionStore";
import { DecisionCard } from "@/components/entities/DecisionCard";
import { StatusFilter } from "@/components/shared/StatusFilter";
import { DecisionForm } from "@/components/forms/DecisionForm";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import type { Decision } from "@/lib/types";

const STATUSES = ["OPEN", "CLOSED", "DEFERRED", "ANALYZING", "MITIGATED", "ACCEPTED"];

export default function DecisionsPage() {
  const { slug } = useParams() as { slug: string };
  const { items, count, isLoading, error, mutate } = useEntityData<Decision>(slug, "decisions");
  const saving = useDecisionStore((s) => s.saving);
  const [statusFilter, setStatusFilter] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editingDecision, setEditingDecision] = useState<Decision | undefined>();

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
      { label: "Close", endpoint: `/projects/{slug}/decisions/{id}`, method: "PATCH", availableWhen: "status = OPEN" },
      { label: "Defer", endpoint: `/projects/{slug}/decisions/{id}`, method: "PATCH", availableWhen: "status = OPEN" },
      { label: "Mitigate", endpoint: `/projects/{slug}/decisions/{id}`, method: "PATCH", availableWhen: "status = ANALYZING" },
      { label: "Accept", endpoint: `/projects/{slug}/decisions/{id}`, method: "PATCH", availableWhen: "status = ANALYZING" },
      { label: "Create", endpoint: `/projects/{slug}/decisions`, method: "POST" },
    ],
  });

  useAIElement({
    id: "decision-form",
    type: "form",
    label: "Decision Form",
    value: formOpen,
    description: formOpen ? `open (${editingDecision ? `editing ${editingDecision.id}` : "creating"})` : "closed",
    data: {
      fields: ["title*", "description", "type*", "status", "reasoning_trace*", "severity", "likelihood", "linked_entity_type", "linked_entity_id"],
    },
    actions: [
      {
        label: editingDecision ? "Update" : "Create",
        endpoint: editingDecision ? `/projects/{slug}/decisions/${editingDecision.id}` : `/projects/{slug}/decisions`,
        method: editingDecision ? "PATCH" : "POST",
      },
    ],
  });

  const handleStatusChange = (id: string, status: string) => {
    updateDecisionAction(slug, id, { status: status as Decision["status"] });
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
    mutate();
  }, [mutate]);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">
          Decisions ({count})
          {saving && <span className="ml-2 text-xs text-gray-400">Saving...</span>}
        </h2>
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
      {isLoading && <p className="text-sm text-gray-400">Loading...</p>}
      {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
      <div className="space-y-3">
        {filtered.map((d) => (
          <DecisionCard key={d.id} decision={d} slug={slug} onStatusChange={handleStatusChange} onEdit={handleEdit} />
        ))}
        {!isLoading && filtered.length === 0 && (
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
