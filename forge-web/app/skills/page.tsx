"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { skills as skillsApi } from "@/lib/api";
import { SkillRow } from "@/components/entities/SkillRow";
import { LintResultsMatrix } from "@/components/skills/LintResultsMatrix";
import { StatusFilter } from "@/components/shared/StatusFilter";
import { Button } from "@/components/shared/Button";
import { SkillsCategoryPanel } from "@/components/skills/SkillsCategoryPanel";
import { useLeftPanel } from "@/components/layout/LeftPanelProvider";
import type { Skill, BulkLintResult, SkillCategoryDef } from "@/lib/types";

const STATUSES = ["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"];

export default function SkillsPage() {
  const router = useRouter();
  const [items, setItems] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [categories, setCategories] = useState<SkillCategoryDef[]>([]);

  // Lint state
  const [lintResult, setLintResult] = useState<BulkLintResult | null>(null);
  const [lintRunning, setLintRunning] = useState(false);

  // Import state
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const fetchCategories = useCallback(async () => {
    try {
      const res = await skillsApi.categories();
      setCategories(res.categories);
    } catch {
      // Non-critical — fallback to built-in labels
    }
  }, []);

  useEffect(() => {
    fetchSkills();
    fetchCategories();
  }, [fetchSkills, fetchCategories]);

  // Category counts (multi-category: each skill can be in multiple)
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const s of items) {
      for (const cat of (s.categories ?? [])) {
        counts[cat] = (counts[cat] || 0) + 1;
      }
    }
    return counts;
  }, [items]);

  // Unique category keys from both fetched categories + item data
  const allCategoryKeys = useMemo(() => {
    const keys = new Set<string>();
    categories.forEach((c) => keys.add(c.key));
    items.forEach((s) => {
      for (const cat of (s.categories ?? [])) keys.add(cat);
    });
    return Array.from(keys);
  }, [categories, items]);

  // Register category panel in left panel
  useLeftPanel(
    <SkillsCategoryPanel
      categoryFilter={categoryFilter}
      setCategoryFilter={setCategoryFilter}
      allCategoryKeys={allCategoryKeys}
      categoryCounts={categoryCounts}
      totalCount={items.length}
    />
  );

  const filtered = useMemo(() => {
    return items
      .filter((s) => !statusFilter || s.status === statusFilter)
      .filter((s) => !categoryFilter || (s.categories ?? []).includes(categoryFilter))
      .filter((s) => {
        if (!search) return true;
        const q = search.toLowerCase();
        return (
          s.name.toLowerCase().includes(q) ||
          (s.description ?? "").toLowerCase().includes(q) ||
          (s.tags ?? []).some((t) => t.toLowerCase().includes(q))
        );
      });
  }, [items, statusFilter, categoryFilter, search]);

  // Selection handlers
  const toggleSelect = (name: string, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(name);
      else next.delete(name);
      return next;
    });
  };

  const selectAll = () => {
    setSelected(new Set(filtered.map((s) => s.name)));
  };

  const deselectAll = () => {
    setSelected(new Set());
  };

  // Actions
  const runLintAll = async () => {
    setLintRunning(true);
    try {
      const res = await skillsApi.lintAll();
      setLintResult(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLintRunning(false);
    }
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const content = await file.text();
      const res = await skillsApi.importSkill({ content, filename: file.name });
      router.push(`/skills/${res.name}`);
    } catch (err) {
      setError((err as Error).message);
    }
    // Reset input
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleExportSelected = async () => {
    if (selected.size === 0) return;
    try {
      const blob = await skillsApi.exportBulk(Array.from(selected));
      // If blob, trigger download
      if (blob instanceof Blob) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "skills-export.zip";
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold">
            Skills
            <span className="text-base font-normal text-gray-400 ml-2">({items.length})</span>
          </h1>
          <div className="flex items-center gap-2">
            <StatusFilter options={STATUSES} value={statusFilter} onChange={setStatusFilter} />
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-2 mb-3">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search skills..."
            className="flex-1 rounded-md border px-3 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
          />
          <Button size="sm" variant="secondary" onClick={() => fileInputRef.current?.click()}>
            Import
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".md"
            className="hidden"
            onChange={handleImportFile}
          />
          <Button
            size="sm"
            variant="secondary"
            onClick={runLintAll}
            disabled={lintRunning || items.length === 0}
          >
            {lintRunning ? "Linting..." : "Lint All"}
          </Button>
          <Button size="sm" onClick={() => router.push("/skills/new")}>
            + New Skill
          </Button>
        </div>

        {/* Bulk selection bar */}
        {selected.size > 0 && (
          <div className="flex items-center gap-3 mb-3 px-3 py-2 rounded-md bg-forge-50 border border-forge-200 text-sm">
            <span className="text-forge-700 font-medium">
              {selected.size} selected
            </span>
            <button onClick={selectAll} className="text-xs text-forge-600 hover:underline">
              Select all ({filtered.length})
            </button>
            <button onClick={deselectAll} className="text-xs text-gray-500 hover:underline">
              Clear
            </button>
            <div className="flex-1" />
            <Button size="sm" variant="secondary" onClick={handleExportSelected}>
              Export selected
            </Button>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="flex items-center justify-between bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-3">
            <p className="text-sm text-red-600">{error}</p>
            <button onClick={() => setError(null)} className="text-xs text-red-400 hover:text-red-600">Dismiss</button>
          </div>
        )}

        {loading && <p className="text-sm text-gray-400">Loading skills...</p>}

        {/* Skills list */}
        <div className="space-y-1">
          {filtered.map((skill) => (
            <SkillRow
              key={skill.name}
              skill={skill}
              selected={selected.has(skill.name)}
              onSelect={toggleSelect}
            />
          ))}
        </div>

        {!loading && filtered.length === 0 && (
          <p className="text-sm text-gray-400 mt-4">
            {items.length === 0
              ? "No skills yet. Create your first skill or import an existing SKILL.md file."
              : "No skills matching filters."}
          </p>
        )}

      {/* Lint results modal */}
      {lintResult && (
        <LintResultsMatrix data={lintResult} onClose={() => setLintResult(null)} />
      )}
    </div>
  );
}
