"use client";

import { useEffect, useMemo, useState } from "react";
import { useAIElement } from "@/lib/ai-context";
import { useSkillStore, fetchSkills } from "@/stores/skillStore";
import { useSidebarStore } from "@/stores/sidebarStore";
import type { Skill } from "@/lib/types";
import { SkillCategorySection } from "./SkillCategorySection";

export function ToolsTabEnhanced() {
  const { items: skills } = useSkillStore();
  const attachedSkills = useSidebarStore((s) => s.attachedSkills);
  const attachSkill = useSidebarStore((s) => s.attachSkill);
  const setActiveTab = useSidebarStore((s) => s.setActiveTab);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (skills.length === 0) {
      fetchSkills();
    }
  }, [skills.length]);

  const attachedNames = useMemo(
    () => new Set(attachedSkills.map((s) => s.name)),
    [attachedSkills],
  );

  const filtered = useMemo(() => {
    if (!search.trim()) return skills;
    const q = search.toLowerCase();
    return skills.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        (s.display_name && s.display_name.toLowerCase().includes(q)),
    );
  }, [skills, search]);

  const categoryMap = useMemo(() => {
    const map = new Map<string, Skill[]>();
    for (const skill of filtered) {
      const cats = skill.categories && skill.categories.length > 0
        ? skill.categories
        : ["Uncategorized"];
      for (const cat of cats) {
        const list = map.get(cat) || [];
        list.push(skill);
        map.set(cat, list);
      }
    }
    // Sort categories alphabetically, but Uncategorized last
    return new Map(
      Array.from(map.entries()).sort(([a], [b]) => {
        if (a === "Uncategorized") return 1;
        if (b === "Uncategorized") return -1;
        return a.localeCompare(b);
      }),
    );
  }, [filtered]);

  useAIElement({
    id: "tools-tab-search",
    type: "input",
    label: "Skill Search",
    value: search,
  });

  useAIElement({
    id: "tools-tab-categories",
    type: "section",
    label: "Skill Categories",
    value: Array.from(categoryMap.keys()).join(", "),
  });

  const handleAttach = (name: string, displayName: string) => {
    attachSkill(name, displayName);
    setActiveTab("chat");
  };

  if (skills.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-gray-400">
        No skills available
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 pt-2 pb-1">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search skills..."
          className="w-full rounded border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-800 placeholder-gray-400 focus:border-blue-300 focus:outline-none focus:ring-1 focus:ring-blue-200"
        />
      </div>

      <div className="flex-1 overflow-y-auto">
        {categoryMap.size === 0 ? (
          <div className="flex items-center justify-center h-20 text-xs text-gray-400">
            No skills match &ldquo;{search}&rdquo;
          </div>
        ) : (
          Array.from(categoryMap.entries()).map(([category, catSkills]) => (
            <SkillCategorySection
              key={category}
              category={category}
              skills={catSkills}
              attachedSkillNames={attachedNames}
              onAttachSkill={handleAttach}
            />
          ))
        )}
      </div>
    </div>
  );
}
