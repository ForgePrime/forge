"use client";

import { useId } from "react";
import { type FieldValues, type Path, type Control, Controller } from "react-hook-form";

interface TextFieldProps<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  label: string;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
}

export function TextField<T extends FieldValues>({
  name,
  control,
  label,
  placeholder,
  required,
  disabled,
}: TextFieldProps<T>) {
  const id = useId();
  const errorId = `${id}-error`;

  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState: { error } }) => (
        <div className="mb-4">
          <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
            {label}
            {required && <span className="text-red-500 ml-0.5">*</span>}
          </label>
          <input
            {...field}
            id={id}
            type="text"
            placeholder={placeholder}
            disabled={disabled}
            aria-required={required}
            aria-invalid={!!error}
            aria-describedby={error ? errorId : undefined}
            className={`w-full px-3 py-2 text-sm border rounded-md outline-none transition-colors ${
              error
                ? "border-red-300 focus:border-red-500 focus:ring-1 focus:ring-red-500"
                : "border-gray-300 focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
            } disabled:bg-gray-50 disabled:text-gray-500`}
          />
          {error && (
            <p id={errorId} className="mt-1 text-xs text-red-600" role="alert">{error.message}</p>
          )}
        </div>
      )}
    />
  );
}
