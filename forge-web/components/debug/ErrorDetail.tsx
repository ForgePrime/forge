"use client";

import { ApiError } from "@/lib/api";

function statusBadgeColor(status: number): string {
  if (status >= 500) return "bg-red-100 text-red-700";
  if (status >= 400) return "bg-orange-100 text-orange-700";
  return "bg-gray-100 text-gray-600";
}

/**
 * Renders error details with status badge, endpoint, and response excerpt.
 * For ApiError: shows status code, HTTP method + URL, and response body excerpt.
 * For other errors: shows a plain error message.
 */
export function ErrorDetail({ error }: { error: unknown }) {
  const isApiError = error instanceof ApiError;

  if (!error) return null;

  if (!isApiError) {
    const message = error instanceof Error ? error.message : String(error);
    return (
      <div className="text-[10px] bg-red-50 text-red-700 rounded p-2 font-mono select-text">
        {message}
      </div>
    );
  }

  const apiErr = error as ApiError;

  return (
    <div className="text-[10px] bg-red-50 rounded p-2 space-y-1.5">
      {/* Status + endpoint */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`inline-flex items-center rounded px-1.5 py-0.5 font-bold tabular-nums ${statusBadgeColor(apiErr.status)}`}>
          {apiErr.status}
        </span>
        {apiErr.method && (
          <span className="font-medium text-gray-600 uppercase">{apiErr.method}</span>
        )}
        {apiErr.url && (
          <span className="font-mono text-gray-500 truncate">{apiErr.url}</span>
        )}
      </div>

      {/* Response body excerpt */}
      {apiErr.responseExcerpt && (
        <pre className="text-[10px] bg-white border border-red-200 rounded p-2 overflow-x-auto max-h-32 overflow-y-auto font-mono whitespace-pre-wrap text-red-700 select-text">
          {apiErr.responseExcerpt}
        </pre>
      )}
    </div>
  );
}
