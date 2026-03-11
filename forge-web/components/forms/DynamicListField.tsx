"use client";

import { type FieldValues, type Path, type Control, Controller } from "react-hook-form";

interface DynamicListFieldProps<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  label: string;
  placeholder?: string;
  addLabel?: string;
  required?: boolean;
  disabled?: boolean;
}

export function DynamicListField<T extends FieldValues>({
  name,
  control,
  label,
  placeholder = "Enter item...",
  addLabel = "Add item",
  required,
  disabled,
}: DynamicListFieldProps<T>) {
  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState: { error } }) => {
        const items: string[] = Array.isArray(field.value) ? field.value : [];

        const addItem = () => {
          field.onChange([...items, ""]);
        };

        const updateItem = (index: number, value: string) => {
          const next = [...items];
          next[index] = value;
          field.onChange(next);
        };

        const removeItem = (index: number) => {
          field.onChange(items.filter((_, i) => i !== index));
        };

        return (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {label}
              {required && <span className="text-red-500 ml-0.5">*</span>}
            </label>

            <div className="space-y-2">
              {items.map((item, idx) => (
                <div key={idx} className="flex gap-2 items-start">
                  <span className="text-xs text-gray-400 mt-2.5 w-5 text-right flex-shrink-0">
                    {idx + 1}.
                  </span>
                  <input
                    type="text"
                    value={item}
                    onChange={(e) => updateItem(idx, e.target.value)}
                    placeholder={placeholder}
                    disabled={disabled}
                    className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-md outline-none focus:border-forge-500 focus:ring-1 focus:ring-forge-500 disabled:bg-gray-50"
                  />
                  <button
                    type="button"
                    onClick={() => removeItem(idx)}
                    disabled={disabled}
                    className="p-2 text-gray-400 hover:text-red-500 disabled:opacity-50 flex-shrink-0"
                    aria-label={`Remove item ${idx + 1}`}
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={addItem}
              disabled={disabled}
              className="mt-2 inline-flex items-center gap-1 px-3 py-1.5 text-xs text-forge-600 border border-dashed border-forge-300 rounded-md hover:bg-forge-50 disabled:opacity-50"
            >
              + {addLabel}
            </button>

            {error && (
              <p className="mt-1 text-xs text-red-600" role="alert">
                {typeof error.message === "string" ? error.message : "Invalid list items"}
              </p>
            )}
          </div>
        );
      }}
    />
  );
}
