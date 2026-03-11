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
      { label: "Dashboard", segment: "", icon: "◫" },
    ],
  },
  {
    label: "Planning",
    items: [
      { label: "Objectives", segment: "objectives", icon: "◎", countKey: "objectives" },
      { label: "Ideas", segment: "ideas", icon: "💡", countKey: "ideas" },
    ],
  },
  {
    label: "Execution",
    items: [
      { label: "Tasks", segment: "tasks", icon: "☑", countKey: "tasks" },
      { label: "Board", segment: "board", icon: "▦" },
      { label: "Runner", segment: "execution", icon: "▶" },
    ],
  },
  {
    label: "Quality",
    items: [
      { label: "Decisions", segment: "decisions", icon: "⚖", countKey: "decisions" },
      { label: "Guidelines", segment: "guidelines", icon: "📏", countKey: "guidelines" },
      { label: "AC Templates", segment: "ac-templates", icon: "✓", countKey: "acTemplates" },
    ],
  },
  {
    label: "Knowledge",
    items: [
      { label: "Knowledge", segment: "knowledge", icon: "📚", countKey: "knowledge" },
      { label: "Lessons", segment: "lessons", icon: "🎓", countKey: "lessons" },
      { label: "Changes", segment: "changes", icon: "Δ", countKey: "changes" },
    ],
  },
  {
    label: "System",
    items: [
      { label: "Settings", segment: "settings", icon: "⚙" },
      { label: "Debug", segment: "debug", icon: "🔍" },
    ],
  },
];

const STORAGE_KEY = "forge-project-sidebar-collapsed";

function readStoredCollapse(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : false;
  } catch { return false; }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ProjectSidebar({ slug }: { slug: string }) {
  const pathname = usePathname();
  const basePath = `/projects/${slug}`;

  const [collapsed, setCollapsed] = useState(readStoredCollapse);
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
  const [mobileOpen, setMobileOpen] = useState(false);

  // Close mobile drawer on navigation
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const toggleCollapse = () => {
    const next = !collapsed;
    setCollapsed(next);
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch { /* */ }
  };

  const toggleGroup = (label: string) => {
    setCollapsedGroups((prev) => ({ ...prev, [label]: !prev[label] }));
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

  const sidebarContent = (
    <nav className="flex-1 overflow-y-auto px-1 pb-2" aria-label="Project navigation">
      {NAV_GROUPS.map((group) => (
        <div key={group.label} className="mb-1">
          {/* Group header — skip for Overview (single item) */}
          {group.label !== "Overview" && !collapsed && (
            <button
              onClick={() => toggleGroup(group.label)}
              aria-expanded={!collapsedGroups[group.label]}
              className="flex items-center w-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400 hover:text-gray-600"
            >
              <span className="mr-1 text-[8px]" aria-hidden="true">
                {collapsedGroups[group.label] ? "▶" : "▼"}
              </span>
              {group.label}
            </button>
          )}

          {/* Items */}
          {(!collapsedGroups[group.label] || collapsed) &&
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
                  title={collapsed ? item.label : undefined}
                  aria-current={isActive ? "page" : undefined}
                  className={`flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors ${
                    isActive
                      ? "bg-forge-50 text-forge-700 font-medium"
                      : "text-gray-600 hover:bg-gray-100"
                  } ${collapsed ? "justify-center" : ""}`}
                >
                  <span className="w-5 text-center flex-shrink-0 text-xs" aria-hidden="true">
                    {item.icon}
                  </span>
                  {!collapsed && (
                    <>
                      <span className="truncate">{item.label}</span>
                      {count !== undefined && count > 0 && (
                        <span className="ml-auto text-[10px] text-gray-400 tabular-nums">
                          {count}
                        </span>
                      )}
                    </>
                  )}
                </Link>
              );
            })}
        </div>
      ))}
    </nav>
  );

  return (
    <>
      {/* Mobile toggle button — visible only on small screens */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="md:hidden fixed top-2 left-2 z-50 p-2 bg-white border rounded-md shadow-sm text-gray-600"
        aria-label="Toggle project navigation"
      >
        ☰
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/30 z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile drawer */}
      <aside
        className={`md:hidden fixed inset-y-0 left-0 z-40 w-56 bg-white border-r flex flex-col transform transition-transform duration-200 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-label="Project navigation"
      >
        <div className="p-2 flex justify-end">
          <button
            onClick={() => setMobileOpen(false)}
            className="p-1 text-gray-400 hover:text-gray-600"
            aria-label="Close navigation"
          >
            ✕
          </button>
        </div>
        {sidebarContent}
      </aside>

      {/* Desktop sidebar */}
      <aside
        className={`hidden md:flex flex-shrink-0 border-r bg-white flex-col transition-all duration-200 ${
          collapsed ? "w-12" : "w-56"
        }`}
        aria-label="Project navigation"
      >
        {/* Collapse toggle */}
        <button
          onClick={toggleCollapse}
          className="p-2 text-gray-400 hover:text-gray-600 self-end"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
        >
          {collapsed ? "»" : "«"}
        </button>

        {sidebarContent}
      </aside>
    </>
  );
}
