"use client";

import { useEffect, useRef } from "react";

export interface SkillMentionItem {
  name: string;
  display_name: string;
  description?: string;
}

interface MentionDropdownProps {
  filter: string;
  skills: SkillMentionItem[];
  selectedIndex: number;
  onSelect: (skill: SkillMentionItem) => void;
  position: { top: number; left: number };
}

export function MentionDropdown({
  filter,
  skills,
  selectedIndex,
  onSelect,
  position,
}: MentionDropdownProps) {
  const listRef = useRef<HTMLDivElement>(null);

  const filtered = filter
    ? skills.filter(
        (s) =>
          s.name.toLowerCase().includes(filter.toLowerCase()) ||
          s.display_name.toLowerCase().includes(filter.toLowerCase()),
      )
    : skills;

  // Scroll selected item into view
  useEffect(() => {
    if (!listRef.current) return;
    const items = listRef.current.querySelectorAll("[data-mention-item]");
    const item = items[selectedIndex];
    if (item) {
      item.scrollIntoView({ block: "nearest" });
    }
  }, [selectedIndex]);

  if (filtered.length === 0) {
    return (
      <div
        className="absolute rounded-lg border border-gray-200 bg-white shadow-lg z-20 max-h-48 overflow-y-auto p-2"
        style={{ bottom: `calc(100% - ${position.top}px)`, left: position.left }}
      >
        <span className="text-xs text-gray-400">No matching skills</span>
      </div>
    );
  }

  return (
    <div
      ref={listRef}
      className="absolute rounded-lg border border-gray-200 bg-white shadow-lg z-20 max-h-48 overflow-y-auto"
      style={{ bottom: `calc(100% - ${position.top}px)`, left: position.left }}
    >
      {filtered.map((skill, idx) => (
        <button
          key={skill.name}
          data-mention-item
          onClick={() => onSelect(skill)}
          className={`w-full text-left px-3 py-1.5 flex items-center gap-2 transition-colors ${
            idx === selectedIndex
              ? "bg-forge-50 text-forge-800"
              : "hover:bg-gray-50 text-gray-700"
          }`}
        >
          <span className="text-xs font-medium text-gray-800 truncate">
            {skill.display_name}
          </span>
          {skill.description && (
            <span className="text-[11px] text-gray-500 truncate">{skill.description}</span>
          )}
          <span className="text-[9px] rounded bg-purple-100 text-purple-600 px-1 py-0.5 ml-auto shrink-0">
            skill
          </span>
        </button>
      ))}
    </div>
  );
}
