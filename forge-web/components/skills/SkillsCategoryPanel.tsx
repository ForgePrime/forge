"use client";

import { getCategoryColor, categoryLabel } from "@/lib/utils/categoryColors";

interface SkillsCategoryPanelProps {
  categoryFilter: string;
  setCategoryFilter: (cat: string) => void;
  allCategoryKeys: string[];
  categoryCounts: Record<string, number>;
  totalCount: number;
}

export function SkillsCategoryPanel({
  categoryFilter,
  setCategoryFilter,
  allCategoryKeys,
  categoryCounts,
  totalCount,
}: SkillsCategoryPanelProps) {
  return (
    <div className="w-48 py-2 px-1">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 px-2">
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
          <span className="float-right text-xs text-gray-400">{totalCount}</span>
        </button>
        {allCategoryKeys.map((key) => {
          const cat = getCategoryColor(key);
          return (
            <button
              key={key}
              onClick={() => setCategoryFilter(key === categoryFilter ? "" : key)}
              className={`w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors flex items-center gap-2 ${
                categoryFilter === key
                  ? "bg-forge-50 text-forge-700 font-medium"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${cat.dot} flex-shrink-0`} />
              <span className="flex-1">{categoryLabel(key)}</span>
              <span className="text-xs text-gray-400">
                {categoryCounts[key] || 0}
              </span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
