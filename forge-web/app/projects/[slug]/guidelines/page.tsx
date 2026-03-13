"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import { useEntityStore } from "@/stores/entityStore";
import { GuidelineCard } from "@/components/entities/GuidelineCard";
import { StatusFilter } from "@/components/shared/StatusFilter";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import type { Guideline, GuidelineWeight, GuidelineCreate } from "@/lib/types";

const STATUSES = ["ACTIVE", "DEPRECATED"];
const WEIGHTS: GuidelineWeight[] = ["must", "should", "may"];
const SCOPES = ["global", "backend", "frontend", "api", "database", "testing", "devops"];

const emptyForm: GuidelineCreate = {
  title: "",
  scope: "global",
  content: "",
  rationale: "",
  examples: [],
  tags: [],
  weight: "should",
};

export default function GuidelinesPage() {
  const { slug } = useParams() as { slug: string };
  const { slices, fetchEntities, createGuideline, updateGuideline } = useEntityStore();
  const [statusFilter, setStatusFilter] = useState("");
  const [weightFilter, setWeightFilter] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [form, setForm] = useState<GuidelineCreate>({ ...emptyForm });
  const [tagInput, setTagInput] = useState("");
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  useEffect(() => {
    fetchEntities(slug, "guidelines");
  }, [slug, fetchEntities]);

  const guidelines = slices.guidelines.items as Guideline[];
  const filtered = guidelines
    .filter((g) => !statusFilter || g.status === statusFilter)
    .filter((g) => !weightFilter || g.weight === weightFilter);

  const weightDist = useMemo(() => {
    const dist: Record<string, number> = {};
    for (const g of guidelines) dist[g.weight] = (dist[g.weight] ?? 0) + 1;
    return dist;
  }, [guidelines]);

  useAIPage({
    id: "guidelines",
    title: `Guidelines (${slices.guidelines.count})`,
    description: `Coding standards and conventions for project ${slug}`,
    route: `/projects/${slug}/guidelines`,
  });

  useAIElement({
    id: "status-filter",
    type: "filter",
    label: "Status Filter",
    value: statusFilter || "All",
    actions: [{ label: "Filter", description: "Filter guidelines by status" }],
  });

  useAIElement({
    id: "guideline-list",
    type: "list",
    label: "Guidelines",
    description: `${filtered.length} shown of ${slices.guidelines.count} total`,
    data: {
      count: slices.guidelines.count,
      filtered: filtered.length,
      weights: weightDist,
    },
    actions: [
      {
        label: "Create guideline",
        toolName: "createGuideline",
        toolParams: ["title*", "scope*", "content*", "weight", "rationale"],
      },
      {
        label: "Update guideline",
        toolName: "updateGuideline",
        toolParams: ["guideline_id*", "title", "content", "status", "weight", "scope"],
      },
    ],
  });

  useAIElement({
    id: "guideline-form",
    type: "form",
    label: "Guideline Form",
    value: showCreateForm,
    description: showCreateForm ? `open (${editingId ? `editing ${editingId}` : "creating"})` : "closed",
    data: { fields: ["title*", "scope*", "content*", "weight", "rationale", "examples", "tags"] },
    actions: [
      {
        label: editingId ? "Update" : "Create",
        toolName: editingId ? "updateGuideline" : "createGuideline",
        toolParams: editingId
          ? ["guideline_id*", "title", "content", "weight", "scope"]
          : ["title*", "scope*", "content*", "weight", "rationale"],
      },
    ],
  });

  const handleAddTag = () => {
    const tag = tagInput.trim();
    if (tag && !form.tags?.includes(tag)) {
      setForm({ ...form, tags: [...(form.tags ?? []), tag] });
    }
    setTagInput("");
  };

  const handleRemoveTag = (tag: string) => {
    setForm({ ...form, tags: (form.tags ?? []).filter((t) => t !== tag) });
  };

  const handleCreate = async () => {
    if (!form.title.trim() || !form.content.trim()) return;
    setCreating(true);
    try {
      await createGuideline(slug, [form]);
      setForm({ ...emptyForm });
      setShowCreateForm(false);
      await fetchEntities(slug, "guidelines");
    } finally {
      setCreating(false);
    }
  };

  const handleCancelCreate = () => {
    setForm({ ...emptyForm });
    setTagInput("");
    setShowCreateForm(false);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Guidelines ({slices.guidelines.count})</h2>
        <div className="flex gap-3 items-center">
          <StatusFilter options={STATUSES} value={statusFilter} onChange={setStatusFilter} />
          <StatusFilter options={WEIGHTS} value={weightFilter} onChange={setWeightFilter} label="Weight" />
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="rounded-md bg-forge-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-forge-700 transition-colors"
          >
            {showCreateForm ? "Cancel" : "+ New Guideline"}
          </button>
        </div>
      </div>

      {/* Inline create form */}
      {showCreateForm && (
        <div className="rounded-lg border-2 border-dashed border-forge-300 bg-forge-50 p-4 mb-4">
          <h3 className="text-sm font-semibold mb-3">Create New Guideline</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Title *</label>
              <input
                type="text"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Guideline title..."
                className="w-full rounded-md border px-3 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
              />
            </div>
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="block text-xs text-gray-500 mb-1">Scope</label>
                <select
                  value={form.scope}
                  onChange={(e) => setForm({ ...form, scope: e.target.value })}
                  className="w-full rounded-md border px-3 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
                >
                  {SCOPES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div className="flex-1">
                <label className="block text-xs text-gray-500 mb-1">Weight</label>
                <select
                  value={form.weight}
                  onChange={(e) => setForm({ ...form, weight: e.target.value as GuidelineWeight })}
                  className="w-full rounded-md border px-3 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
                >
                  {WEIGHTS.map((w) => (
                    <option key={w} value={w}>{w}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
          <div className="mt-3">
            <label className="block text-xs text-gray-500 mb-1">Content *</label>
            <textarea
              value={form.content}
              onChange={(e) => setForm({ ...form, content: e.target.value })}
              placeholder="Guideline content / description..."
              rows={3}
              className="w-full rounded-md border px-3 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
            />
          </div>
          <div className="mt-3">
            <label className="block text-xs text-gray-500 mb-1">Rationale</label>
            <input
              type="text"
              value={form.rationale ?? ""}
              onChange={(e) => setForm({ ...form, rationale: e.target.value })}
              placeholder="Why this guideline exists..."
              className="w-full rounded-md border px-3 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
            />
          </div>
          <div className="mt-3">
            <label className="block text-xs text-gray-500 mb-1">Tags</label>
            <div className="flex gap-2 items-center">
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleAddTag(); } }}
                placeholder="Add tag and press Enter..."
                className="flex-1 rounded-md border px-3 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
              />
              <button
                type="button"
                onClick={handleAddTag}
                className="rounded-md border px-2 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
              >
                Add
              </button>
            </div>
            {(form.tags ?? []).length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {(form.tags ?? []).map((t) => (
                  <span key={t} className="inline-flex items-center gap-1 text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                    {t}
                    <button onClick={() => handleRemoveTag(t)} className="text-gray-400 hover:text-red-500">&times;</button>
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="flex gap-2 mt-4">
            <button
              onClick={handleCreate}
              disabled={creating || !form.title.trim() || !form.content.trim()}
              className="rounded-md bg-forge-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-forge-700 disabled:opacity-50 transition-colors"
            >
              {creating ? "Creating..." : "Create Guideline"}
            </button>
            <button
              onClick={handleCancelCreate}
              className="rounded-md border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {slices.guidelines.loading && <p className="text-sm text-gray-400">Loading...</p>}
      {slices.guidelines.error && <p className="text-sm text-red-600 mb-2">{slices.guidelines.error}</p>}
      <div className="space-y-3">
        {filtered.map((g) => (
          <GuidelineCard
            key={g.id}
            guideline={g}
            editing={editingId === g.id}
            onEditToggle={() => setEditingId(editingId === g.id ? null : g.id)}
            onSave={async (data) => {
              await updateGuideline(slug, g.id, data);
              setEditingId(null);
              await fetchEntities(slug, "guidelines");
            }}
          />
        ))}
        {!slices.guidelines.loading && filtered.length === 0 && (
          <p className="text-sm text-gray-400">No guidelines matching filters</p>
        )}
      </div>
    </div>
  );
}
