"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { useEntityStore } from "@/stores/entityStore";
import { ACTemplateCard } from "@/components/entities/ACTemplateCard";
import { StatusFilter } from "@/components/shared/StatusFilter";
import { acTemplates as acTemplatesApi } from "@/lib/api";
import Link from "next/link";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import { useMultiSelect } from "@/hooks/useMultiSelect";
import { BulkActionBar } from "@/components/shared/BulkActionBar";
import type { ACTemplate, ACTemplateCategory } from "@/lib/types";

const STATUSES = ["ACTIVE", "DEPRECATED"];
const CATEGORIES: ACTemplateCategory[] = [
  "performance", "security", "quality", "functionality",
  "accessibility", "reliability", "data-integrity", "ux",
];

export default function ACTemplatesPage() {
  const { slug } = useParams() as { slug: string };
  const { slices, fetchEntities } = useEntityStore();
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  const { selectedIds, isSelected, toggle, deselectAll, count: selectionCount } = useMultiSelect();

  const handleBulkDelete = async () => {
    const ids = Array.from(selectedIds);
    await Promise.allSettled(ids.map((id) => acTemplatesApi.remove(slug, id)));
    fetchEntities(slug, "acTemplates");
  };

  // Instantiate state
  const [instantiateId, setInstantiateId] = useState<string | null>(null);
  const [instantiateParams, setInstantiateParams] = useState<Record<string, string>>({});
  const [instantiateResult, setInstantiateResult] = useState<string | null>(null);
  const [instantiating, setInstantiating] = useState(false);
  const [instantiateError, setInstantiateError] = useState<string | null>(null);

  useEffect(() => {
    fetchEntities(slug, "acTemplates");
  }, [slug, fetchEntities]);

  const templates = slices.acTemplates.items as ACTemplate[];
  const filtered = templates
    .filter((t) => !statusFilter || t.status === statusFilter)
    .filter((t) => !categoryFilter || t.category === categoryFilter);

  useAIPage({
    id: "ac-templates",
    title: `AC Templates (${slices.acTemplates.count})`,
    description: `Reusable acceptance criteria templates for project ${slug}`,
    route: `/projects/${slug}/ac-templates`,
  });

  useAIElement({
    id: "template-list",
    type: "list",
    label: "AC Templates",
    description: `${filtered.length} shown of ${slices.acTemplates.count} total`,
    data: { count: slices.acTemplates.count, filtered: filtered.length },
    actions: [
      { label: "Create template", toolName: "createACTemplate", toolParams: ["title*", "template*", "category*", "description", "parameters", "scopes"] },
      { label: "Instantiate", toolName: "instantiateACTemplate", toolParams: ["template_id*", "params*"] },
    ],
  });

  // Instantiate flow
  const instantiateTemplate = templates.find((t) => t.id === instantiateId);

  const handleOpenInstantiate = useCallback((templateId: string) => {
    const tmpl = templates.find((t) => t.id === templateId);
    if (!tmpl) return;
    const defaults: Record<string, string> = {};
    for (const p of tmpl.parameters ?? []) {
      defaults[p.name] = p.default != null ? String(p.default) : "";
    }
    setInstantiateParams(defaults);
    setInstantiateResult(null);
    setInstantiateError(null);
    setInstantiateId(templateId);
  }, [templates]);

  const handleInstantiate = async () => {
    if (!instantiateId) return;
    setInstantiating(true);
    setInstantiateError(null);
    try {
      const res = await acTemplatesApi.instantiate(slug, instantiateId, instantiateParams);
      setInstantiateResult(res.criterion);
      await fetchEntities(slug, "acTemplates");
    } catch (e) {
      setInstantiateError((e as Error).message);
    } finally {
      setInstantiating(false);
    }
  };

  const handleCloseInstantiate = () => {
    setInstantiateId(null);
    setInstantiateParams({});
    setInstantiateResult(null);
    setInstantiateError(null);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">AC Templates ({slices.acTemplates.count})</h2>
        <div className="flex gap-3 items-center">
          <StatusFilter options={STATUSES} value={statusFilter} onChange={setStatusFilter} />
          <StatusFilter options={CATEGORIES} value={categoryFilter} onChange={setCategoryFilter} label="Category" />
          <Link
            href={`/projects/${slug}/ac-templates/new`}
            className="rounded-md bg-forge-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-forge-700 transition-colors"
          >
            + New Template
          </Link>
        </div>
      </div>

      {/* Instantiate modal */}
      {instantiateId && instantiateTemplate && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 p-6">
            <h3 className="text-sm font-semibold mb-1">Instantiate Template</h3>
            <p className="text-xs text-gray-500 mb-4">{instantiateTemplate.title}</p>

            <div className="mb-4 p-3 bg-gray-50 rounded text-xs font-mono text-gray-600">
              {instantiateTemplate.template}
            </div>

            {(instantiateTemplate.parameters ?? []).length > 0 && (
              <div className="space-y-3 mb-4">
                <p className="text-xs text-gray-500 font-medium">Fill in parameters:</p>
                {(instantiateTemplate.parameters ?? []).map((p) => (
                  <div key={p.name}>
                    <label className="block text-xs text-gray-500 mb-1">
                      {p.name}
                      {p.type && <span className="text-gray-400 ml-1">({p.type})</span>}
                      {p.description && <span className="text-gray-400 ml-1">- {p.description}</span>}
                    </label>
                    <input
                      type="text"
                      value={instantiateParams[p.name] ?? ""}
                      onChange={(e) => setInstantiateParams({ ...instantiateParams, [p.name]: e.target.value })}
                      placeholder={p.default != null ? `default: ${p.default}` : `Enter ${p.name}...`}
                      className="w-full rounded-md border px-3 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
                    />
                  </div>
                ))}
              </div>
            )}

            {instantiateResult && (
              <div className="mb-4">
                <p className="text-xs text-gray-500 font-medium mb-1">Generated AC:</p>
                <div className="p-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
                  {instantiateResult}
                </div>
              </div>
            )}

            {instantiateError && (
              <p className="text-sm text-red-600 mb-4">{instantiateError}</p>
            )}

            <div className="flex gap-2 justify-end">
              <button
                onClick={handleCloseInstantiate}
                className="rounded-md border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              >
                Close
              </button>
              {!instantiateResult && (
                <button
                  onClick={handleInstantiate}
                  disabled={instantiating}
                  className="rounded-md bg-forge-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-forge-700 disabled:opacity-50 transition-colors"
                >
                  {instantiating ? "Generating..." : "Generate AC"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {slices.acTemplates.loading && <p className="text-sm text-gray-400">Loading...</p>}
      {slices.acTemplates.error && <p className="text-sm text-red-600 mb-2">{slices.acTemplates.error}</p>}
      <BulkActionBar count={selectionCount} entityLabel="templates" onDelete={handleBulkDelete} onDeselectAll={deselectAll} />
      <div className="space-y-3">
        {filtered.map((t) => (
          <ACTemplateCard
            key={t.id}
            template={t}
            slug={slug}
            onInstantiate={handleOpenInstantiate}
            selected={isSelected(t.id)}
            onSelect={() => toggle(t.id)}
          />
        ))}
        {!slices.acTemplates.loading && filtered.length === 0 && (
          <p className="text-sm text-gray-400">No templates matching filters</p>
        )}
      </div>
    </div>
  );
}
