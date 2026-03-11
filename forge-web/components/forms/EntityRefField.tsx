"use client";

import { useState, useRef, useEffect, useMemo, useId } from "react";
import { type FieldValues, type Path, type Control, Controller } from "react-hook-form";
import { useTaskStore } from "@/stores/taskStore";
import { useDecisionStore } from "@/stores/decisionStore";
import { useObjectiveStore } from "@/stores/objectiveStore";
import { useIdeaStore } from "@/stores/ideaStore";

export type EntityRefType = "task" | "decision" | "objective" | "idea";

interface EntityRefOption {
  id: string;
  title: string;
  type: EntityRefType;
}

const DEFAULT_ENTITY_TYPES: EntityRefType[] = ["task"];

interface EntityRefFieldProps<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  label: string;
  entityTypes?: EntityRefType[];
  multiple?: boolean;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function EntityRefField<T extends FieldValues>({
  name,
  control,
  label,
  entityTypes = DEFAULT_ENTITY_TYPES,
  multiple = true,
  required,
  disabled,
  placeholder = "Search by ID or name...",
}: EntityRefFieldProps<T>) {
  const [query, setQuery] = useState("");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fieldId = useId();
  const listboxId = `${fieldId}-listbox`;

  const tasks = useTaskStore((s) => s.items);
  const decisions = useDecisionStore((s) => s.items);
  const objectives = useObjectiveStore((s) => s.items);
  const ideas = useIdeaStore((s) => s.items);

  // Build searchable list from enabled entity types
  const allOptions = useMemo(() => {
    const opts: EntityRefOption[] = [];
    if (entityTypes.includes("task")) {
      for (const t of tasks) opts.push({ id: t.id, title: t.name || t.id, type: "task" });
    }
    if (entityTypes.includes("decision")) {
      for (const d of decisions) opts.push({ id: d.id, title: d.issue || d.id, type: "decision" });
    }
    if (entityTypes.includes("objective")) {
      for (const o of objectives) opts.push({ id: o.id, title: o.title || o.id, type: "objective" });
    }
    if (entityTypes.includes("idea")) {
      for (const i of ideas) opts.push({ id: i.id, title: i.title || i.id, type: "idea" });
    }
    return opts;
  }, [entityTypes, tasks, decisions, objectives, ideas]);

  // Filter by query
  const filtered = useMemo(() => {
    if (!query.trim()) return allOptions.slice(0, 20);
    const q = query.toLowerCase().trim();
    return allOptions
      .filter((o) => o.id.toLowerCase().includes(q) || o.title.toLowerCase().includes(q))
      .slice(0, 20);
  }, [query, allOptions]);

  // Close on outside click
  useEffect(() => {
    if (!dropdownOpen) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [dropdownOpen]);

  const TYPE_PREFIXES: Record<EntityRefType, string> = {
    task: "T", decision: "D", objective: "O", idea: "I",
  };

  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState: { error } }) => {
        const selected: string[] = multiple
          ? (Array.isArray(field.value) ? field.value : [])
          : (field.value ? [field.value as string] : []);

        const addRef = (id: string) => {
          if (multiple) {
            if (!selected.includes(id)) field.onChange([...selected, id]);
          } else {
            field.onChange(id);
          }
          setQuery("");
          setDropdownOpen(false);
        };

        const removeRef = (id: string) => {
          if (multiple) {
            field.onChange(selected.filter((v) => v !== id));
          } else {
            field.onChange("");
          }
        };

        return (
          <div className="mb-4 relative" ref={containerRef}>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {label}
              {required && <span className="text-red-500 ml-0.5">*</span>}
            </label>

            {/* Selected chips */}
            {selected.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-1.5">
                {selected.map((id) => {
                  const opt = allOptions.find((o) => o.id === id);
                  return (
                    <span
                      key={id}
                      className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-forge-100 text-forge-700 rounded"
                    >
                      <span className="font-mono">{id}</span>
                      {opt && <span className="text-forge-500 truncate max-w-[120px]">{opt.title}</span>}
                      <button
                        type="button"
                        onClick={() => removeRef(id)}
                        disabled={disabled}
                        className="hover:text-forge-900 ml-0.5"
                        aria-label={`Remove ${id}`}
                      >
                        x
                      </button>
                    </span>
                  );
                })}
              </div>
            )}

            {/* Search input */}
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setDropdownOpen(true); }}
              onFocus={() => setDropdownOpen(true)}
              onKeyDown={(e) => {
                if (e.key === "Escape" && dropdownOpen) {
                  e.stopPropagation();
                  setDropdownOpen(false);
                }
              }}
              placeholder={placeholder}
              disabled={disabled}
              className={`w-full px-3 py-2 text-sm border rounded-md outline-none transition-colors ${
                error
                  ? "border-red-300 focus:border-red-500 focus:ring-1 focus:ring-red-500"
                  : "border-gray-300 focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
              } disabled:bg-gray-50`}
              role="combobox"
              aria-expanded={dropdownOpen}
              aria-haspopup="listbox"
              aria-controls={dropdownOpen ? listboxId : undefined}
              autoComplete="off"
            />

            {/* Dropdown */}
            {dropdownOpen && (
              <div
                id={listboxId}
                className="absolute mt-1 w-full border rounded-md bg-white shadow-lg max-h-48 overflow-y-auto z-10"
                role="listbox"
              >
                {filtered.length > 0 ? (
                  filtered.map((opt) => {
                    const isSelected = selected.includes(opt.id);
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        role="option"
                        aria-selected={isSelected}
                        onClick={() => addRef(opt.id)}
                        disabled={isSelected}
                        className={`w-full px-3 py-2 text-sm text-left flex items-center gap-2 hover:bg-gray-50 ${
                          isSelected ? "opacity-50" : "text-gray-700"
                        }`}
                      >
                        <span className="text-[10px] font-medium text-gray-400 bg-gray-100 px-1 rounded">
                          {TYPE_PREFIXES[opt.type]}
                        </span>
                        <span className="font-mono text-xs text-gray-500">{opt.id}</span>
                        <span className="truncate">{opt.title}</span>
                      </button>
                    );
                  })
                ) : (
                  <div className="px-3 py-4 text-center text-sm text-gray-400">
                    No matching entities
                  </div>
                )}
              </div>
            )}

            {error && (
              <p className="mt-1 text-xs text-red-600" role="alert">{error.message}</p>
            )}
          </div>
        );
      }}
    />
  );
}
