"use client";

import { useEffect, useRef } from "react";
import { SLASH_ROUTES } from "@/lib/ai-context/slashCommandRouter";

export interface SlashCommand {
  name: string;
  label: string;
  description?: string;
  source: "built-in" | "skill";
}

// Built-in commands available in the chat
const BUILT_IN_COMMANDS: SlashCommand[] = [
  { name: "status", label: "status", description: "Show project status", source: "built-in" },
  { name: "next", label: "next", description: "Get and execute next task", source: "built-in" },
  { name: "plan", label: "plan", description: "Decompose goal into task graph", source: "built-in" },
  { name: "do", label: "do", description: "Quick execute a single task", source: "built-in" },
  { name: "run", label: "run", description: "Execute tasks continuously", source: "built-in" },
  { name: "idea", label: "idea", description: "Add idea to staging area", source: "built-in" },
  { name: "ideas", label: "ideas", description: "List/manage ideas", source: "built-in" },
  { name: "objective", label: "objective", description: "Define business objective", source: "built-in" },
  { name: "objectives", label: "objectives", description: "List/manage objectives", source: "built-in" },
  { name: "discover", label: "discover", description: "Explore options, assess risks", source: "built-in" },
  { name: "decide", label: "decide", description: "Review open decisions", source: "built-in" },
  { name: "risk", label: "risk", description: "Manage risk decisions", source: "built-in" },
  { name: "guideline", label: "guideline", description: "Add project guideline", source: "built-in" },
  { name: "guidelines", label: "guidelines", description: "List/manage guidelines", source: "built-in" },
  { name: "knowledge", label: "knowledge", description: "Manage knowledge objects", source: "built-in" },
  { name: "research", label: "research", description: "Manage research objects", source: "built-in" },
  { name: "review", label: "review", description: "Deep code review", source: "built-in" },
  { name: "compound", label: "compound", description: "Extract lessons learned", source: "built-in" },
  { name: "log", label: "log", description: "Show audit trail", source: "built-in" },
  { name: "task", label: "task", description: "Quick-add a task", source: "built-in" },
  { name: "help", label: "help", description: "Show all commands", source: "built-in" },
];

export { BUILT_IN_COMMANDS };

/**
 * Merge built-in + skill commands (dedup by name, built-in wins),
 * then filter by query. Single source of truth for the filtered list.
 */
export function getFilteredCommands(
  filter: string,
  skillCommands: SlashCommand[],
): SlashCommand[] {
  const allCommands: SlashCommand[] = [];
  const seen = new Set<string>();
  for (const cmd of BUILT_IN_COMMANDS) {
    seen.add(cmd.name);
    allCommands.push(cmd);
  }
  for (const cmd of skillCommands) {
    if (!seen.has(cmd.name)) {
      seen.add(cmd.name);
      allCommands.push(cmd);
    }
  }
  if (!filter) return allCommands;
  const lowerFilter = filter.toLowerCase();
  return allCommands.filter(
    (cmd) =>
      cmd.name.toLowerCase().includes(lowerFilter) ||
      cmd.label.toLowerCase().includes(lowerFilter) ||
      (cmd.description?.toLowerCase().includes(lowerFilter) ?? false),
  );
}

interface SlashCommandDropdownProps {
  /** Current text after the '/' (e.g., typing '/pl' → filter = 'pl'). */
  filter: string;
  /** Skill commands from the store. */
  skillCommands: SlashCommand[];
  /** Currently highlighted index. */
  selectedIndex: number;
  /** Called when user picks a command. */
  onSelect: (command: SlashCommand) => void;
}

export default function SlashCommandDropdown({
  filter,
  skillCommands,
  selectedIndex,
  onSelect,
}: SlashCommandDropdownProps) {
  const listRef = useRef<HTMLDivElement>(null);
  const filtered = getFilteredCommands(filter, skillCommands);

  // Scroll selected item into view
  useEffect(() => {
    if (!listRef.current) return;
    const items = listRef.current.querySelectorAll("[data-cmd-item]");
    const item = items[selectedIndex];
    if (item) {
      item.scrollIntoView({ block: "nearest" });
    }
  }, [selectedIndex]);

  if (filtered.length === 0) {
    return (
      <div className="absolute bottom-full left-0 right-0 mb-1 rounded-lg border border-gray-200 bg-white shadow-lg z-20 max-h-48 overflow-y-auto p-2">
        <span className="text-xs text-gray-400">No matching commands</span>
      </div>
    );
  }

  return (
    <div
      ref={listRef}
      className="absolute bottom-full left-0 right-0 mb-1 rounded-lg border border-gray-200 bg-white shadow-lg z-20 max-h-48 overflow-y-auto"
    >
      {filtered.map((cmd, idx) => (
        <button
          key={cmd.name}
          data-cmd-item
          onClick={() => onSelect(cmd)}
          className={`w-full text-left px-3 py-1.5 flex items-center gap-2 transition-colors ${
            idx === selectedIndex
              ? "bg-forge-50 text-forge-800"
              : "hover:bg-gray-50 text-gray-700"
          }`}
        >
          <span className="text-xs font-mono font-medium text-forge-600 shrink-0">
            /{cmd.name}
          </span>
          {cmd.description && (
            <span className="text-[11px] text-gray-500 truncate">{cmd.description}</span>
          )}
          {cmd.source === "skill" && (
            <span className="text-[9px] rounded bg-purple-100 text-purple-600 px-1 py-0.5 ml-auto shrink-0">
              skill
            </span>
          )}
          {cmd.source === "built-in" && SLASH_ROUTES[cmd.name]?.skillName && (
            <span className="text-[9px] rounded bg-forge-100 text-forge-600 px-1 py-0.5 ml-auto shrink-0">
              workflow
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
