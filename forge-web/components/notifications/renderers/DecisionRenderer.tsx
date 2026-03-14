"use client";

import { useState } from "react";
import type { NotificationRendererProps } from "../registry";

const SEVERITY_BADGE: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-gray-100 text-gray-500",
};

/**
 * Decision notification renderer.
 * Shows severity badge, issue/recommendation, AI options,
 * and Accept/Mitigate/Defer action buttons.
 */
export function DecisionRenderer({ notification, onRespond, onDismiss, loading }: NotificationRendererProps) {
  const [mode, setMode] = useState<"options" | "mitigate">("options");
  const [mitigationText, setMitigationText] = useState("");

  const severity = notification.ai_options.find(o => o.action === "severity")?.label ?? "";
  const sevStyle = SEVERITY_BADGE[severity.toLowerCase()] ?? SEVERITY_BADGE.medium;

  return (
    <div className="space-y-3">
      {/* Severity + source */}
      <div className="flex items-center gap-2">
        {severity && (
          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${sevStyle}`}>
            {severity}
          </span>
        )}
        {notification.source_entity_id && (
          <span className="text-[10px] text-gray-400">
            {notification.source_entity_id}
          </span>
        )}
      </div>

      {/* Message / issue */}
      {notification.message && (
        <p className="text-sm text-gray-700">{notification.message}</p>
      )}

      {/* AI-proposed options */}
      {notification.ai_options.length > 0 && notification.ai_options.some(o => o.action !== "severity") && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500">Recommended:</p>
          {notification.ai_options
            .filter(o => o.action !== "severity")
            .map((opt, i) => (
              <button
                key={i}
                onClick={() => onRespond(opt.label, opt.action)}
                disabled={loading}
                className="w-full text-left p-2 rounded border border-gray-200 hover:border-blue-300 hover:bg-blue-50 text-sm disabled:opacity-50"
              >
                <span className="font-medium text-gray-800">{opt.label}</span>
                {opt.reasoning && (
                  <p className="text-xs text-gray-500 mt-0.5">{opt.reasoning}</p>
                )}
              </button>
            ))}
        </div>
      )}

      {/* Mitigate text input */}
      {mode === "mitigate" && (
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Mitigation plan
          </label>
          <textarea
            value={mitigationText}
            onChange={(e) => setMitigationText(e.target.value)}
            placeholder="Describe the mitigation plan..."
            rows={3}
            className="w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-2 border-t">
        <button
          onClick={onDismiss}
          disabled={loading}
          className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700 disabled:opacity-50"
        >
          Dismiss
        </button>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onRespond("Deferred", "defer")}
            disabled={loading}
            className="px-3 py-1.5 text-xs text-gray-600 border rounded hover:bg-gray-50 disabled:opacity-50"
          >
            Defer
          </button>
          {mode === "options" ? (
            <button
              onClick={() => setMode("mitigate")}
              disabled={loading}
              className="px-3 py-1.5 text-xs text-orange-600 border border-orange-200 rounded hover:bg-orange-50 disabled:opacity-50"
            >
              Mitigate
            </button>
          ) : (
            <button
              onClick={() => onRespond(mitigationText, "mitigate")}
              disabled={loading || !mitigationText.trim()}
              className="px-3 py-1.5 text-xs text-orange-600 border border-orange-200 rounded hover:bg-orange-50 disabled:opacity-50"
            >
              Submit Mitigation
            </button>
          )}
          <button
            onClick={() => onRespond("Accepted", "accept")}
            disabled={loading}
            className="px-4 py-1.5 text-xs bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
          >
            Accept
          </button>
        </div>
      </div>
    </div>
  );
}
