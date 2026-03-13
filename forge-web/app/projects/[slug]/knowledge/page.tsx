"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import { useEntityStore } from "@/stores/entityStore";
import { KnowledgeCard } from "@/components/entities/KnowledgeCard";
import { StatusFilter } from "@/components/shared/StatusFilter";
import { KnowledgeForm } from "@/components/forms/KnowledgeForm";
import { Badge } from "@/components/shared/Badge";
import { knowledgeMaintenance } from "@/lib/api";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import type { Knowledge, MaintenanceReport, StaleKnowledge } from "@/lib/types";

const STATUSES = ["DRAFT", "ACTIVE", "REVIEW_NEEDED", "DEPRECATED", "ARCHIVED"];
const CATEGORIES = [
  "domain-rules", "api-reference", "architecture", "business-context",
  "technical-context", "code-patterns", "integration", "infrastructure",
];

export default function KnowledgePage() {
  const { slug } = useParams() as { slug: string };
  const { slices, fetchEntities } = useEntityStore();
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editingKnowledge, setEditingKnowledge] = useState<Knowledge | undefined>();
  const [maintenance, setMaintenance] = useState<MaintenanceReport | null>(null);
  const [maintenanceLoading, setMaintenanceLoading] = useState(false);
  const [maintenanceError, setMaintenanceError] = useState<string | null>(null);
  const [showMaintenance, setShowMaintenance] = useState(false);

  useEffect(() => {
    fetchEntities(slug, "knowledge");
  }, [slug, fetchEntities]);

  const handleFormSuccess = useCallback(() => {
    fetchEntities(slug, "knowledge");
  }, [slug, fetchEntities]);

  const fetchMaintenance = useCallback(async () => {
    setMaintenanceLoading(true);
    setMaintenanceError(null);
    try {
      const report = await knowledgeMaintenance.overview(slug);
      setMaintenance(report);
    } catch (e) {
      setMaintenanceError((e as Error).message);
    } finally {
      setMaintenanceLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    if (showMaintenance && !maintenance && !maintenanceLoading) {
      fetchMaintenance();
    }
  }, [showMaintenance, maintenance, maintenanceLoading, fetchMaintenance]);

  const items = slices.knowledge.items as Knowledge[];

  const categoryDist = useMemo(() => {
    const dist: Record<string, number> = {};
    for (const k of items) dist[k.category] = (dist[k.category] ?? 0) + 1;
    return dist;
  }, [items]);

  useAIPage({
    id: "knowledge",
    title: `Knowledge (${slices.knowledge.count})`,
    description: `Domain knowledge objects for project ${slug}`,
    route: `/projects/${slug}/knowledge`,
  });

  useAIElement({
    id: "status-filter",
    type: "filter",
    label: "Status Filter",
    value: statusFilter || "All",
    actions: [{ label: "Filter", description: "Filter knowledge by status" }],
  });

  useAIElement({
    id: "knowledge-list",
    type: "list",
    label: "Knowledge",
    description: `${slices.knowledge.count} total knowledge objects`,
    data: {
      count: slices.knowledge.count,
      categories: categoryDist,
    },
    actions: [
      {
        label: "Create knowledge",
        toolName: "createKnowledge",
        toolParams: ["title*", "category*", "content*", "scope", "tags"],
      },
      {
        label: "Update knowledge",
        toolName: "updateKnowledge",
        toolParams: ["knowledge_id*", "title", "content", "status", "category"],
      },
    ],
  });

  useAIElement({
    id: "knowledge-form",
    type: "form",
    label: "Knowledge Form",
    value: formOpen,
    description: formOpen ? `open (${editingKnowledge ? `editing ${editingKnowledge.id}` : "creating"})` : "closed",
    data: { fields: ["title*", "category*", "content*", "scope", "tags", "links"] },
    actions: [
      {
        label: editingKnowledge ? "Update" : "Create",
        toolName: editingKnowledge ? "updateKnowledge" : "createKnowledge",
        toolParams: editingKnowledge
          ? ["knowledge_id*", "title", "content", "status"]
          : ["title*", "category*", "content*", "scope"],
      },
    ],
  });

  const filtered = items
    .filter((k) => !statusFilter || k.status === statusFilter)
    .filter((k) => !categoryFilter || k.category === categoryFilter)
    .filter((k) => {
      if (!search) return true;
      const q = search.toLowerCase();
      return (
        k.title.toLowerCase().includes(q) ||
        k.content.toLowerCase().includes(q) ||
        k.tags?.some((t) => t.toLowerCase().includes(q))
      );
    });

  // Build a map of stale knowledge IDs for quick lookup
  const staleMap = new Map<string, StaleKnowledge>();
  if (maintenance) {
    for (const s of maintenance.stale) {
      staleMap.set(s.id, s);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Knowledge ({slices.knowledge.count})</h2>
        <div className="flex gap-3 items-center">
          <button
            onClick={() => setShowMaintenance((v) => !v)}
            className={`text-xs px-3 py-1.5 rounded-md border transition-colors ${
              showMaintenance
                ? "bg-amber-50 border-amber-300 text-amber-700"
                : "bg-white border-gray-200 text-gray-500 hover:border-gray-300"
            }`}
          >
            {showMaintenance ? "Hide Maintenance" : "Maintenance"}
          </button>
          <StatusFilter options={STATUSES} value={statusFilter} onChange={setStatusFilter} />
          <StatusFilter options={CATEGORIES} value={categoryFilter} onChange={setCategoryFilter} label="Category" />
          <button
            onClick={() => { setEditingKnowledge(undefined); setFormOpen(true); }}
            className="px-3 py-1.5 text-sm text-white bg-forge-600 rounded-md hover:bg-forge-700"
          >
            + New Knowledge
          </button>
        </div>
      </div>

      {/* Maintenance Panel */}
      {showMaintenance && (
        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-amber-800">Knowledge Maintenance</h3>
            <button
              onClick={fetchMaintenance}
              disabled={maintenanceLoading}
              className="text-xs text-amber-600 hover:text-amber-800 disabled:opacity-50"
            >
              {maintenanceLoading ? "Loading..." : "Refresh"}
            </button>
          </div>

          {maintenanceError && (
            <p className="text-xs text-red-600 mb-2">{maintenanceError}</p>
          )}

          {maintenance && (
            <>
              {/* Summary Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 mb-4">
                <div className="bg-white rounded px-3 py-2 text-center">
                  <div className="text-lg font-bold text-gray-800">{maintenance.summary.total_knowledge}</div>
                  <div className="text-[10px] text-gray-500">Total</div>
                </div>
                <div className="bg-white rounded px-3 py-2 text-center">
                  <div className="text-lg font-bold text-green-600">{maintenance.summary.active}</div>
                  <div className="text-[10px] text-gray-500">Active</div>
                </div>
                <div className="bg-white rounded px-3 py-2 text-center">
                  <div className="text-lg font-bold text-yellow-600">{maintenance.summary.draft}</div>
                  <div className="text-[10px] text-gray-500">Draft</div>
                </div>
                <div className="bg-white rounded px-3 py-2 text-center">
                  <div className="text-lg font-bold text-amber-600">{maintenance.summary.review_needed}</div>
                  <div className="text-[10px] text-gray-500">Review Needed</div>
                </div>
                <div className="bg-white rounded px-3 py-2 text-center">
                  <div className="text-lg font-bold text-red-600">{maintenance.summary.deprecated}</div>
                  <div className="text-[10px] text-gray-500">Deprecated</div>
                </div>
                <div className="bg-white rounded px-3 py-2 text-center">
                  <div className="text-lg font-bold text-gray-400">{maintenance.summary.archived}</div>
                  <div className="text-[10px] text-gray-500">Archived</div>
                </div>
                <div className="bg-white rounded px-3 py-2 text-center">
                  <div className="text-lg font-bold text-amber-700">{maintenance.summary.stale_count}</div>
                  <div className="text-[10px] text-gray-500">Stale ({maintenance.summary.stale_days_threshold}d)</div>
                </div>
              </div>

              {/* Review Suggestions */}
              {maintenance.review_suggestions.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-xs font-semibold text-amber-700 mb-2">
                    Review Suggestions ({maintenance.review_suggestions.length})
                  </h4>
                  <div className="space-y-1.5">
                    {maintenance.review_suggestions.map((rs) => (
                      <div key={rs.id} className="flex items-start gap-2 bg-white rounded px-3 py-2">
                        <Badge variant={rs.priority === "high" ? "danger" : "warning"}>
                          {rs.priority}
                        </Badge>
                        <div className="flex-1 min-w-0">
                          <span className="text-xs text-gray-400 mr-1">{rs.id}</span>
                          <span className="text-xs text-gray-700">{rs.suggestion}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Usage Stats — top unused knowledge */}
              {maintenance.usage_stats.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-amber-700 mb-2">
                    Usage Overview (lowest usage first)
                  </h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-left text-gray-500 border-b border-amber-200">
                          <th className="py-1 pr-3">ID</th>
                          <th className="py-1 pr-3">Title</th>
                          <th className="py-1 pr-3">Status</th>
                          <th className="py-1 pr-3 text-right">Links</th>
                          <th className="py-1 pr-3 text-right">Tasks</th>
                          <th className="py-1 pr-3 text-right">Ideas</th>
                          <th className="py-1 text-right">Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...maintenance.usage_stats]
                          .sort((a, b) => a.total_references - b.total_references)
                          .slice(0, 10)
                          .map((us) => (
                            <tr key={us.id} className="border-b border-amber-100">
                              <td className="py-1 pr-3 text-gray-400">{us.id}</td>
                              <td className="py-1 pr-3 text-gray-700 truncate max-w-[200px]">{us.title}</td>
                              <td className="py-1 pr-3">
                                <Badge variant={
                                  us.status === "ACTIVE" ? "success" :
                                  us.status === "REVIEW_NEEDED" ? "warning" :
                                  us.status === "DEPRECATED" ? "danger" : "default"
                                }>{us.status}</Badge>
                              </td>
                              <td className="py-1 pr-3 text-right text-gray-600">{us.linked_entities}</td>
                              <td className="py-1 pr-3 text-right text-gray-600">{us.referencing_tasks}</td>
                              <td className="py-1 pr-3 text-right text-gray-600">{us.referencing_ideas}</td>
                              <td className="py-1 text-right font-medium text-gray-800">{us.total_references}</td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}

          {!maintenance && !maintenanceLoading && !maintenanceError && (
            <p className="text-xs text-amber-600">Click &quot;Refresh&quot; to load maintenance data.</p>
          )}
        </div>
      )}

      <div className="mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search title, content, or tags..."
          className="w-full rounded-md border px-3 py-2 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
        />
      </div>
      {slices.knowledge.loading && <p className="text-sm text-gray-400">Loading...</p>}
      {slices.knowledge.error && <p className="text-sm text-red-600 mb-2">{slices.knowledge.error}</p>}
      <div className="space-y-3">
        {filtered.map((k) => (
          <KnowledgeCard
            key={k.id}
            knowledge={k}
            slug={slug}
            onEdit={(knowledge) => { setEditingKnowledge(knowledge); setFormOpen(true); }}
            staleInfo={staleMap.get(k.id)}
          />
        ))}
        {!slices.knowledge.loading && filtered.length === 0 && (
          <p className="text-sm text-gray-400">
            No knowledge entries{statusFilter || categoryFilter || search ? " matching filters" : ""}
          </p>
        )}
      </div>

      <KnowledgeForm
        slug={slug}
        open={formOpen}
        onClose={() => { setFormOpen(false); setEditingKnowledge(undefined); }}
        knowledge={editingKnowledge}
        onSuccess={handleFormSuccess}
      />
    </div>
  );
}
