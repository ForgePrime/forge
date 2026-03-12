"use client";

import { useState, useEffect } from "react";
import { useLeftPanelContent } from "./LeftPanelProvider";

const STORAGE_KEY = "forge-left-panel-collapsed";

export function LeftPanel() {
  const content = useLeftPanelContent();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored !== null) setCollapsed(stored === "true");
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  };

  if (!content) return null;

  return (
    <aside
      className={`flex-shrink-0 border-r bg-white flex transition-all duration-200 overflow-hidden ${
        collapsed ? "w-0" : ""
      }`}
      style={collapsed ? { width: 0 } : undefined}
    >
      {!collapsed && (
        <div className="flex-1 overflow-y-auto">{content}</div>
      )}
      <button
        onClick={toggleCollapsed}
        className="w-5 flex-shrink-0 flex items-center justify-center border-l bg-gray-50 hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
        title={collapsed ? "Expand panel" : "Collapse panel"}
      >
        <span className="text-xs">{collapsed ? "\u25B6" : "\u25C0"}</span>
      </button>
    </aside>
  );
}
