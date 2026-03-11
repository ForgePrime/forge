"use client";

import { useState, useRef, useEffect } from "react";
import { type FieldValues, type Path, type Control, Controller } from "react-hook-form";
import type { SelectOption } from "./SelectField";

interface MultiSelectFieldProps<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  label: string;
  options: SelectOption[];
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
}

export function MultiSelectField<T extends FieldValues>({
  name,
  control,
  label,
  options,
  placeholder = "Select items...",
  required,
  disabled,
}: MultiSelectFieldProps<T>) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
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

  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState: { error } }) => {
        const selected: string[] = Array.isArray(field.value) ? field.value : [];

        const toggle = (value: string) => {
          const next = selected.includes(value)
            ? selected.filter((v) => v !== value)
            : [...selected, value];
          field.onChange(next);
        };

        const remove = (value: string) => {
          field.onChange(selected.filter((v) => v !== value));
        };

        return (
          <div className="mb-4" ref={containerRef}>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {label}
              {required && <span className="text-red-500 ml-0.5">*</span>}
            </label>

            {/* Selected chips + trigger */}
            <div
              className={`min-h-[38px] w-full px-2 py-1.5 border rounded-md flex flex-wrap gap-1 items-center cursor-pointer ${
                disabled ? "bg-gray-50 cursor-not-allowed" : "bg-white"
              } ${
                error
                  ? "border-red-300"
                  : dropdownOpen ? "border-forge-500 ring-1 ring-forge-500" : "border-gray-300"
              }`}
              onClick={() => { if (!disabled) setDropdownOpen((o) => !o); }}
              role="combobox"
              aria-expanded={dropdownOpen}
              aria-haspopup="listbox"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  if (!disabled) setDropdownOpen((o) => !o);
                }
              }}
            >
              {selected.length === 0 && (
                <span className="text-sm text-gray-400">{placeholder}</span>
              )}
              {selected.map((val) => {
                const opt = options.find((o) => o.value === val);
                return (
                  <span
                    key={val}
                    className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-forge-100 text-forge-700 rounded"
                  >
                    {opt?.label ?? val}
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); remove(val); }}
                      className="hover:text-forge-900"
                      aria-label={`Remove ${opt?.label ?? val}`}
                    >
                      x
                    </button>
                  </span>
                );
              })}
            </div>

            {/* Dropdown */}
            {dropdownOpen && (
              <div
                className="mt-1 w-full border rounded-md bg-white shadow-lg max-h-48 overflow-y-auto z-10 relative"
                role="listbox"
                aria-multiselectable="true"
              >
                {options.map((opt) => {
                  const isSelected = selected.includes(opt.value);
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      role="option"
                      aria-selected={isSelected}
                      onClick={() => toggle(opt.value)}
                      className={`w-full px-3 py-2 text-sm text-left flex items-center gap-2 hover:bg-gray-50 ${
                        isSelected ? "bg-forge-50 text-forge-700" : "text-gray-700"
                      }`}
                    >
                      <span className={`w-4 h-4 flex items-center justify-center border rounded text-xs ${
                        isSelected ? "bg-forge-600 border-forge-600 text-white" : "border-gray-300"
                      }`}>
                        {isSelected && "\u2713"}
                      </span>
                      {opt.label}
                    </button>
                  );
                })}
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
