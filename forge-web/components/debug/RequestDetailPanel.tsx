"use client";

import { useState, useCallback } from "react";
import { useAIElement } from "@/lib/ai-context/useAIElement";
import type { ApiEntry } from "@/stores/debugStore";
import { ErrorDetail } from "./ErrorDetail";
import { ApiError } from "@/lib/api";

// ---------------------------------------------------------------------------
// Collapsible section
// ---------------------------------------------------------------------------

function Section({
  title,
  defaultOpen,
  badge,
  children,
  copyText,
}: {
  title: string;
  defaultOpen?: boolean;
  badge?: string;
  children: React.ReactNode;
  copyText?: string;
}) {
  const [open, setOpen] = useState(defaultOpen ?? false);
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    if (!copyText) return;
    navigator.clipboard.writeText(copyText);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [copyText]);

  return (
    <div className="border rounded bg-white">
      <div
        role="button"
        tabIndex={0}
        onClick={() => setOpen(!open)}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setOpen(!open); } }}
        className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left hover:bg-gray-50 transition-colors cursor-pointer"
      >
        <span className="text-[10px] text-gray-400">{open ? "▼" : "▶"}</span>
        <span className="text-[11px] font-medium text-gray-700">{title}</span>
        {badge && (
          <span className="text-[10px] text-gray-400 tabular-nums">{badge}</span>
        )}
        {copyText && (
          <button
            onClick={(e) => { e.stopPropagation(); handleCopy(); }}
            className="ml-auto text-[10px] text-gray-400 hover:text-gray-600 px-1.5 py-0.5 border rounded"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        )}
      </div>
      {open && (
        <div className="border-t px-2.5 py-2">
          {children}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Timing bar
// ---------------------------------------------------------------------------

function TimingBar({ duration }: { duration: number }) {
  // Scale: 0-100ms=green, 100-500ms=yellow, 500ms+=red
  const pct = Math.min(duration / 2000, 1) * 100;
  const color =
    duration < 100 ? "bg-green-400" :
    duration < 500 ? "bg-yellow-400" :
    "bg-red-400";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[10px] text-gray-500">
        <span>Duration</span>
        <span className="font-medium tabular-nums">
          {duration < 1000 ? `${duration}ms` : `${(duration / 1000).toFixed(2)}s`}
        </span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Key-value table
// ---------------------------------------------------------------------------

function KVTable({ data }: { data: Record<string, string> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) {
    return <span className="text-[10px] text-gray-400 italic">None</span>;
  }
  return (
    <table className="w-full text-[10px]">
      <tbody>
        {entries.map(([k, v]) => (
          <tr key={k} className="border-b border-gray-50 last:border-b-0">
            <td className="py-0.5 pr-3 font-medium text-gray-600 whitespace-nowrap align-top select-text">{k}</td>
            <td className="py-0.5 text-gray-700 font-mono break-all select-text">{v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ---------------------------------------------------------------------------
// Parse query params from URL
// ---------------------------------------------------------------------------

function parseQueryParams(url: string): Record<string, string> {
  const qIdx = url.indexOf("?");
  if (qIdx === -1) return {};
  const params: Record<string, string> = {};
  let search = url.slice(qIdx + 1);
  // Strip fragment if present
  const hashIdx = search.indexOf("#");
  if (hashIdx !== -1) search = search.slice(0, hashIdx);
  for (const pair of search.split("&")) {
    const eqIdx = pair.indexOf("=");
    if (eqIdx === -1) {
      params[decodeURIComponent(pair)] = "";
    } else {
      params[decodeURIComponent(pair.slice(0, eqIdx))] = decodeURIComponent(pair.slice(eqIdx + 1));
    }
  }
  return params;
}

function urlWithoutQuery(url: string): string {
  const qIdx = url.indexOf("?");
  return qIdx === -1 ? url : url.slice(0, qIdx);
}

// ---------------------------------------------------------------------------
// Body renderer
// ---------------------------------------------------------------------------

function BodyView({ body, id }: { body: unknown; id: string }) {
  const text = typeof body === "string" ? body : JSON.stringify(body, null, 2);

  useAIElement({
    id,
    type: "display",
    label: "Request/Response Body",
    description: `Body: ${(text ?? "").slice(0, 80)}...`,
    value: `${(text ?? "").length} chars`,
    actions: [],
  });

  return (
    <pre className="text-[10px] text-gray-700 font-mono whitespace-pre-wrap break-all max-h-48 overflow-y-auto select-text">
      {text}
    </pre>
  );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export function RequestDetailPanel({ entry }: { entry: ApiEntry }) {
  const queryParams = parseQueryParams(entry.url);
  const cleanUrl = urlWithoutQuery(entry.url);
  const hasQuery = Object.keys(queryParams).length > 0;
  const headers = entry.requestHeaders ?? {};
  const hasHeaders = Object.keys(headers).length > 0;
  const hasRequestBody = entry.requestBody !== undefined;
  const hasResponseBody = entry.responseBody !== undefined;

  const headersText = Object.entries(headers).map(([k, v]) => `${k}: ${v}`).join("\n");
  const queryText = Object.entries(queryParams).map(([k, v]) => `${k}=${v}`).join("\n");
  const requestBodyText = hasRequestBody
    ? (typeof entry.requestBody === "string" ? entry.requestBody : JSON.stringify(entry.requestBody, null, 2))
    : "";
  const responseBodyText = hasResponseBody
    ? (typeof entry.responseBody === "string" ? entry.responseBody : JSON.stringify(entry.responseBody, null, 2))
    : "";

  useAIElement({
    id: `request-detail-${entry.id}`,
    type: "display",
    label: `Request Detail: ${entry.method} ${cleanUrl}`,
    description: `${entry.method} ${cleanUrl} — ${entry.status ?? "ERR"} in ${entry.duration}ms`,
    value: `${entry.status ?? "error"}`,
    actions: [],
  });

  return (
    <div className="space-y-1.5 px-2 pb-2">
      {/* Error (if any) */}
      {entry.error && (
        <ErrorDetail
          error={
            entry.status
              ? new ApiError(entry.status, entry.error, { method: entry.method, url: entry.url })
              : new Error(entry.error)
          }
          id={`api-entry-error-${entry.id}`}
        />
      )}

      {/* Timing */}
      <Section title="Timing" defaultOpen badge={`${entry.duration}ms`}>
        <TimingBar duration={entry.duration} />
        <div className="mt-1.5 text-[10px] text-gray-500">
          Started: {new Date(entry.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", fractionalSecondDigits: 3 } as Intl.DateTimeFormatOptions)}
        </div>
      </Section>

      {/* Request Headers */}
      {hasHeaders && (
        <Section
          title="Request Headers"
          badge={`${Object.keys(headers).length}`}
          copyText={headersText}
        >
          <KVTable data={headers} />
        </Section>
      )}

      {/* Query Params */}
      {hasQuery && (
        <Section
          title="Query Parameters"
          badge={`${Object.keys(queryParams).length}`}
          copyText={queryText}
        >
          <KVTable data={queryParams} />
        </Section>
      )}

      {/* Request Body */}
      {hasRequestBody && (
        <Section title="Request Body" copyText={requestBodyText}>
          <BodyView body={entry.requestBody} id={`req-body-${entry.id}`} />
        </Section>
      )}

      {/* Response Body */}
      {hasResponseBody && (
        <Section title="Response Body" copyText={responseBodyText}>
          <BodyView body={entry.responseBody} id={`res-body-${entry.id}`} />
        </Section>
      )}
    </div>
  );
}
