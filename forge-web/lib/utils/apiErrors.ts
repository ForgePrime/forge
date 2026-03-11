import { ApiError } from "@/lib/api";

/** Field-level error from a 422 validation response. */
export interface FieldError {
  field: string;
  message: string;
}

/**
 * Parse a FastAPI 422 validation error into field-level messages.
 * FastAPI returns: { detail: [{ loc: ["body", "field"], msg: "...", type: "..." }] }
 */
export function parseValidationErrors(error: unknown): FieldError[] {
  if (!(error instanceof ApiError) || error.status !== 422) return [];

  const detail = error.detail;
  if (!detail || typeof detail !== "object") return [];

  const errors = (detail as { detail?: unknown[] }).detail;
  if (!Array.isArray(errors)) return [];

  return errors.map((err) => {
    const e = err as { loc?: string[]; msg?: string };
    // loc is typically ["body", "fieldName"] or ["body", "index", "fieldName"]
    const loc = e.loc ?? [];
    const field = loc.filter((s) => s !== "body" && typeof s === "string").join(".");
    return { field: field || "unknown", message: e.msg ?? "Validation error" };
  });
}

/**
 * Convert field errors to a record keyed by field name, for use with react-hook-form setError.
 */
export function fieldErrorsToRecord(errors: FieldError[]): Record<string, string> {
  const result: Record<string, string> = {};
  for (const { field, message } of errors) {
    if (!result[field]) result[field] = message;
  }
  return result;
}
