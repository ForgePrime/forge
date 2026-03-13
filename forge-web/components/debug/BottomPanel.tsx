"use client";

import { useEffect, useCallback, useMemo } from "react";
import { usePathname } from "next/navigation";
import {
  useDebugPanelStore,
  type PanelState,
  type DebugTab,
} from "@/stores/debugPanelStore";
import { useDebugStore } from "@/stores/debugStore";
import { ApiInspector } from "./ApiInspector";
import { LlmMonitor } from "./LlmMonitor";
import { EventStream } from "./EventStream";

// ---------------------------------------------------------------------------
// Height mappings
// ---------------------------------------------------------------------------

const PANEL_HEIGHTS: Record<PanelState, string> = {
  collapsed: "h-10",
  expanded: "h-[33vh]",
  fullscreen: "h-[calc(100vh-var(--topnav-height))]",
};

const TABS: Array<{ id: DebugTab; label: string }> = [
  { id: "api", label: "API Inspector" },
  { id: "llm", label: "LLM Monitor" },
  { id: "events", label: "Event Stream" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function BottomPanel() {
  const { panelState, activeTab, eventCount, toggle, setPanelState, setActiveTab } =
    useDebugPanelStore();
  const apiErrorCount = useDebugStore((s) => s.errorCount);
  const apiTotalRequests = useDebugStore((s) => s.totalRequests);

  // Extract project slug from URL pathname (works in root layout, unlike useParams)
  const pathname = usePathname();
  const slug = useMemo(() => {
    const match = pathname?.match(/\/projects\/([^/]+)/);
    return match ? decodeURIComponent(match[1]) : null;
  }, [pathname]);

  // Keyboard shortcut: Ctrl+` to toggle
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "`") {
        e.preventDefault();
        toggle();
      }
    },
    [toggle],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const isCollapsed = panelState === "collapsed";

  const cycleState = () => {
    const order: PanelState[] = ["collapsed", "expanded", "fullscreen"];
    const idx = order.indexOf(panelState);
    setPanelState(order[(idx + 1) % order.length]);
  };

  return (
    <div
      data-debug-panel
      className={`flex-shrink-0 flex flex-col transition-all duration-200 ${PANEL_HEIGHTS[panelState]}`}
      style={{ borderTop: "1px solid var(--debug-border)", backgroundColor: "var(--debug-bg-primary)" }}
    >
      {/* Status bar / drag handle */}
      <div
        className="flex items-center gap-2 px-3 h-10 flex-shrink-0 cursor-pointer select-none"
        style={{
          backgroundColor: "var(--debug-bg-secondary)",
          borderBottom: "1px solid var(--debug-border)",
          color: "var(--debug-text-secondary)",
        }}
        onClick={() => {
          if (isCollapsed) setPanelState("expanded");
        }}
        onDoubleClick={() => {
          if (!isCollapsed) {
            setPanelState(panelState === "expanded" ? "fullscreen" : "expanded");
          }
        }}
      >
        {/* Tab buttons (only when not collapsed) */}
        {!isCollapsed && (
          <div className="flex gap-1" role="tablist" aria-label="Debug console tabs">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-controls={`debug-panel-${tab.id}`}
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveTab(tab.id);
                }}
                className="px-2 py-0.5 text-xs rounded transition-colors font-medium"
                style={{
                  backgroundColor: activeTab === tab.id ? "var(--debug-bg-surface)" : "transparent",
                  color: activeTab === tab.id ? "var(--debug-text-primary)" : "var(--debug-text-muted)",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        )}

        {/* Status indicators */}
        <div className="ml-auto flex items-center gap-3 text-xs" style={{ color: "var(--debug-text-muted)" }}>
          {isCollapsed && <span className="font-medium" style={{ color: "var(--debug-text-secondary)" }}>Debug Console</span>}
          {apiErrorCount > 0 && (
            <span className="inline-flex items-center gap-1 font-medium" style={{ color: "var(--debug-status-error)" }}>
              <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: "var(--debug-status-error)" }} />
              {apiErrorCount} error{apiErrorCount !== 1 ? "s" : ""}
            </span>
          )}
          {apiTotalRequests > 0 && (
            <span className="tabular-nums">{apiTotalRequests} req</span>
          )}
          <span className="tabular-nums">{eventCount} events</span>

          {/* Panel state controls */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              cycleState();
            }}
            className="p-0.5 rounded transition-colors"
            style={{ color: "var(--debug-text-muted)" }}
            title="Cycle panel size"
            aria-label="Cycle panel size"
          >
            {panelState === "fullscreen" ? "↓" : panelState === "expanded" ? "↑" : "□"}
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              toggle();
            }}
            className="p-0.5 rounded transition-colors"
            style={{ color: "var(--debug-text-muted)" }}
            title={isCollapsed ? "Open debug console (Ctrl+`)" : "Close debug console (Ctrl+`)"}
            aria-label={isCollapsed ? "Open debug console" : "Close debug console"}
          >
            {isCollapsed ? "▲" : "▼"}
          </button>
        </div>
      </div>

      {/* Tab content */}
      {!isCollapsed && (
        <div className="flex-1 overflow-y-auto p-3 text-sm" style={{
          backgroundColor: "var(--debug-bg-primary)",
          color: "var(--debug-text-primary)",
        }}>
          <div role="tabpanel" id="debug-panel-api" hidden={activeTab !== "api"} className="h-full">
            <ApiInspector slug={slug} />
          </div>
          <div role="tabpanel" id="debug-panel-llm" hidden={activeTab !== "llm"} className="h-full">
            <LlmMonitor slug={slug} />
          </div>
          <div role="tabpanel" id="debug-panel-events" hidden={activeTab !== "events"} className="h-full">
            <EventStream slug={slug} />
          </div>
        </div>
      )}
    </div>
  );
}
