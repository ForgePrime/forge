"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { skills as skillsApi } from "@/lib/api";
import { SkillCard } from "@/components/entities/SkillCard";
import { SkillForm } from "@/components/forms/SkillForm";
import { StatusFilter } from "@/components/shared/StatusFilter";
import { Button } from "@/components/shared/Button";
import type { Skill, SkillCategory } from "@/lib/types";

const STATUSES = ["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"];
const CATEGORIES: { key: SkillCategory; label: string }[] = [
  { key: "workflow", label: "Workflow" },
  { key: "analysis", label: "Analysis" },
  { key: "generation", label: "Generation" },
  { key: "validation", label: "Validation" },
  { key: "integration", label: "Integration" },
  { key: "refactoring", label: "Refactoring" },
  { key: "testing", label: "Testing" },
  { key: "deployment", label: "Deployment" },
  { key: "documentation", label: "Documentation" },
  { key: "custom", label: "Custom" },
];

export default function SkillsPage() {
  const [items, setItems] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [search, setSearch] = useState("");
  const [view, setView] = useState<"list" | "grid">("list");
  const [formOpen, setFormOpen] = useState(false);
  const [editingSkill, setEditingSkill] = useState<Skill | undefined>();

  const fetchSkills = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await skillsApi.list();
      setItems(res.skills);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  // Compute category counts from all items (unfiltered)
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const s of items) {
      counts[s.category] = (counts[s.category] || 0) + 1;
    }
    return counts;
  }, [items]);

  const filtered = useMemo(() => {
    return items
      .filter((s) => !statusFilter || s.status === statusFilter)
      .filter((s) => !categoryFilter || s.category === categoryFilter)
      .filter((s) => {
        if (!search) return true;
        const q = search.toLowerCase();
        return (
          s.name.toLowerCase().includes(q) ||
          s.description.toLowerCase().includes(q) ||
          s.tags.some((t) => t.toLowerCase().includes(q))
        );
      });
  }, [items, statusFilter, categoryFilter, search]);

  return (
    <div className="flex gap-6">
      {/* Category sidebar */}
      <aside className="w-48 flex-shrink-0 hidden lg:block">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
          Categories
        </h3>
        <nav className="space-y-0.5">
          <button
            onClick={() => setCategoryFilter("")}
            className={`w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors ${
              !categoryFilter
                ? "bg-forge-50 text-forge-700 font-medium"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            All
            <span className="float-right text-xs text-gray-400">{items.length}</span>
          </button>
          {CATEGORIES.map((cat) => (
            <button
              key={cat.key}
              onClick={() => setCategoryFilter(cat.key === categoryFilter ? "" : cat.key)}
              className={`w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors ${
                categoryFilter === cat.key
                  ? "bg-forge-50 text-forge-700 font-medium"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              {cat.label}
              <span className="float-right text-xs text-gray-400">
                {categoryCounts[cat.key] || 0}
              </span>
            </button>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold">
            Skills
            <span className="text-base font-normal text-gray-400 ml-2">({items.length})</span>
          </h1>
          <div className="flex items-center gap-3">
            <StatusFilter options={STATUSES} value={statusFilter} onChange={setStatusFilter} />
            {/* Category filter for small screens */}
            <div className="lg:hidden">
              <StatusFilter
                options={CATEGORIES.map((c) => c.key)}
                value={categoryFilter}
                onChange={setCategoryFilter}
                label="Category"
              />
            </div>
            {/* View toggle */}
            <div className="flex rounded-md border overflow-hidden">
              <button
                onClick={() => setView("list")}
                className={`px-2 py-1 text-xs ${
                  view === "list"
                    ? "bg-forge-600 text-white"
                    : "bg-white text-gray-500 hover:bg-gray-50"
                }`}
                title="List view"
              >
                =
              </button>
              <button
                onClick={() => setView("grid")}
                className={`px-2 py-1 text-xs ${
                  view === "grid"
                    ? "bg-forge-600 text-white"
                    : "bg-white text-gray-500 hover:bg-gray-50"
                }`}
                title="Grid view"
              >
                #
              </button>
            </div>
            <Button size="sm" onClick={() => { setEditingSkill(undefined); setFormOpen(true); }}>
              + New Skill
            </Button>
          </div>
        </div>

        {/* Search */}
        <div className="mb-4">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name, description, or tags..."
            className="w-full rounded-md border px-3 py-2 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
          />
        </div>

        {loading && <p className="text-sm text-gray-400">Loading skills...</p>}
        {error && <p className="text-sm text-red-600 mb-2">{error}</p>}

        {/* Skills list/grid */}
        <div className={
          view === "grid"
            ? "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3"
            : "space-y-3"
        }>
          {filtered.map((skill) => (
            <SkillCard
              key={skill.id}
              skill={skill}
              view={view}
              onEdit={(s) => { setEditingSkill(s); setFormOpen(true); }}
            />
          ))}
        </div>

        {!loading && filtered.length === 0 && (
          <p className="text-sm text-gray-400 mt-4">
            {items.length === 0
              ? "No skills yet. Create your first skill to get started."
              : "No skills matching filters."}
          </p>
        )}
      </div>

      <SkillForm
        open={formOpen}
        onClose={() => { setFormOpen(false); setEditingSkill(undefined); }}
        skill={editingSkill}
        onSuccess={fetchSkills}
      />
    </div>
  );
}
