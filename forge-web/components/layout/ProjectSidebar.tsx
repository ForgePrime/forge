"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTaskStore } from "@/stores/taskStore";
import { useDecisionStore } from "@/stores/decisionStore";
import { useObjectiveStore } from "@/stores/objectiveStore";
import { useIdeaStore } from "@/stores/ideaStore";
import { useChangeStore } from "@/stores/changeStore";
import { useGuidelineStore } from "@/stores/guidelineStore";
import { useKnowledgeStore } from "@/stores/knowledgeStore";
import { useLessonStore } from "@/stores/lessonStore";
import { useACTemplateStore } from "@/stores/acTemplateStore";

// ---------------------------------------------------------------------------
// Navigation structure
// ---------------------------------------------------------------------------

interface NavEntry {
  label: string;
  segment: string;
  icon: string;
  countKey?: string;
}

interface NavGroup {
  label: string;
  items: NavEntry[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { label: "Dashboard", segment: "", icon: "\u25EB" },
    ],
  },
  {
    label: "Planning",
    items: [
      { label: "Objectives", segment: "objectives", icon: "\u25CE", countKey: "objectives" },
      { label: "Ideas", segment: "ideas", icon: "\uD83D\uDCA1", countKey: "ideas" },
    ],
  },
  {
    label: "Execution",
    items: [
      { label: "Tasks", segment: "tasks", icon: "\u2611", countKey: "tasks" },
      { label: "Board", segment: "board", icon: "\u25A6" },
      { label: "Runner", segment: "execution", icon: "\u25B6" },
    ],
  },
  {
    label: "Quality",
    items: [
      { label: "Decisions", segment: "decisions", icon: "\u2696", countKey: "decisions" },
      { label: "Guidelines", segment: "guidelines", icon: "\uD83D\uDCCF", countKey: "guidelines" },
      { label: "AC Templates", segment: "ac-templates", icon: "\u2713", countKey: "acTemplates" },
    ],
  },
  {
    label: "Knowledge",
    items: [
      { label: "Knowledge", segment: "knowledge", icon: "\uD83D\uDCDA", countKey: "knowledge" },
      { label: "Lessons", segment: "lessons", icon: "\uD83C\uDF93", countKey: "lessons" },
      { label: "Changes", segment: "changes", icon: "\u0394", countKey: "changes" },
    ],
  },
  {
    label: "System",
    items: [
      { label: "Settings", segment: "settings", icon: "\u2699" },
      { label: "Debug", segment: "debug", icon: "\uD83D\uDD0D" },
    ],
  },
];

const STORAGE_KEY = "forge-project-sidebar-groups";

// ---------------------------------------------------------------------------
// Component — renders inside LeftPanel container
// ---------------------------------------------------------------------------

export function ProjectSidebar({ slug }: { slug: string }) {
  const pathname = usePathname();
  const basePath = `/projects/${slug}`;

  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) setCollapsedGroups(JSON.parse(stored));
    } catch { /* */ }
  }, []);

  const toggleGroup = (label: string) => {
    setCollapsedGroups((prev) => {
      const next = { ...prev, [label]: !prev[label] };
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch { /* */ }
      return next;
    });
  };

  // Entity counts from stores
  const counts: Record<string, number> = {
    tasks: useTaskStore((s) => s.count),
    decisions: useDecisionStore((s) => s.count),
    objectives: useObjectiveStore((s) => s.count),
    ideas: useIdeaStore((s) => s.count),
    changes: useChangeStore((s) => s.count),
    guidelines: useGuidelineStore((s) => s.count),
    knowledge: useKnowledgeStore((s) => s.count),
    lessons: useLessonStore((s) => s.count),
    acTemplates: useACTemplateStore((s) => s.count),
  };

  return (
    <nav className="w-56 overflow-y-auto px-1 py-2" aria-label="Project navigation">
      {NAV_GROUPS.map((group) => (
        <div key={group.label} className="mb-1">
          {/* Group header — skip for Overview (single item) */}
          {group.label !== "Overview" && (
            <button
              onClick={() => toggleGroup(group.label)}
              aria-expanded={!collapsedGroups[group.label]}
              className="flex items-center w-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400 hover:text-gray-600"
            >
              <span className="mr-1 text-[8px]" aria-hidden="true">
                {collapsedGroups[group.label] ? "\u25B6" : "\u25BC"}
              </span>
              {group.label}
            </button>
          )}

          {/* Items */}
          {!collapsedGroups[group.label] &&
            group.items.map((item) => {
              const href = item.segment
                ? `${basePath}/${item.segment}`
                : basePath;
              const isActive = item.segment
                ? pathname.startsWith(`${basePath}/${item.segment}`)
                : pathname === basePath;
              const count = item.countKey ? counts[item.countKey] : undefined;

              return (
                <Link
                  key={item.segment || "_dash"}
                  href={href}
                  aria-current={isActive ? "page" : undefined}
                  className={`flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors ${
                    isActive
                      ? "bg-forge-50 text-forge-700 font-medium"
                      : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  <span className="w-5 text-center flex-shrink-0 text-xs" aria-hidden="true">
                    {item.icon}
                  </span>
                  <span className="truncate">{item.label}</span>
                  {count !== undefined && count > 0 && (
                    <span className="ml-auto text-[10px] text-gray-400 tabular-nums">
                      {count}
                    </span>
                  )}
                </Link>
              );
            })}
        </div>
      ))}
    </nav>
  );
}
