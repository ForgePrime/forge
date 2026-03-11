"use client";

import type { FieldError } from "@/lib/utils/apiErrors";

interface FormErrorSummaryProps {
  errors: FieldError[];
}

export function FormErrorSummary({ errors }: FormErrorSummaryProps) {
  if (errors.length === 0) return null;

  return (
    <div
      className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md"
      role="alert"
    >
      <p className="text-sm font-medium text-red-800 mb-1">
        {errors.length} validation error{errors.length !== 1 ? "s" : ""}
      </p>
      <ul className="list-disc list-inside space-y-0.5">
        {errors.map((err, idx) => (
          <li key={idx} className="text-xs text-red-700">
            <span className="font-mono font-medium">{err.field}</span>: {err.message}
          </li>
        ))}
      </ul>
    </div>
  );
}
