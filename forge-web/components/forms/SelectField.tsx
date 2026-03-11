"use client";

import { type FieldValues, type Path, type Control, Controller } from "react-hook-form";

export interface SelectOption {
  value: string;
  label: string;
}

interface SelectFieldProps<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  label: string;
  options: SelectOption[];
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
}

export function SelectField<T extends FieldValues>({
  name,
  control,
  label,
  options,
  placeholder = "Select...",
  required,
  disabled,
}: SelectFieldProps<T>) {
  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState: { error } }) => (
        <div className="mb-4">
          <label htmlFor={`field-${name}`} className="block text-sm font-medium text-gray-700 mb-1">
            {label}
            {required && <span className="text-red-500 ml-0.5">*</span>}
          </label>
          <select
            {...field}
            id={`field-${name}`}
            disabled={disabled}
            className={`w-full px-3 py-2 text-sm border rounded-md outline-none transition-colors bg-white ${
              error
                ? "border-red-300 focus:border-red-500 focus:ring-1 focus:ring-red-500"
                : "border-gray-300 focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
            } disabled:bg-gray-50 disabled:text-gray-500`}
          >
            <option value="">{placeholder}</option>
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {error && (
            <p className="mt-1 text-xs text-red-600" role="alert">{error.message}</p>
          )}
        </div>
      )}
    />
  );
}
