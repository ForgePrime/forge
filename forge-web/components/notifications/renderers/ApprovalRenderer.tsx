"use client";

import { useState } from "react";
import type { NotificationRendererProps } from "../registry";

/**
 * Approval notification renderer.
 * Shows plan summary, approve/reject/modify buttons.
 */
export function ApprovalRenderer({ notification, onRespond, onDismiss, loading }: NotificationRendererProps) {
  const [mode, setMode] = useState<"actions" | "modify">("actions");
  const [modifyText, setModifyText] = useState("");

  return (
    <div className="space-y-3">
      {/* Message */}
      {notification.message && (
        <p className="text-sm text-gray-700">{notification.message}</p>
      )}

      {/* AI options */}
      {notification.ai_options.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500">Options:</p>
          {notification.ai_options.map((opt, i) => (
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

      {/* Modify text input */}
      {mode === "modify" && (
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Modification notes
          </label>
          <textarea
            value={modifyText}
            onChange={(e) => setModifyText(e.target.value)}
            placeholder="Describe the changes needed..."
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
            onClick={() => onRespond("Rejected", "reject")}
            disabled={loading}
            className="px-3 py-1.5 text-xs text-red-600 border border-red-200 rounded hover:bg-red-50 disabled:opacity-50"
          >
            Reject
          </button>
          {mode === "actions" ? (
            <button
              onClick={() => setMode("modify")}
              disabled={loading}
              className="px-3 py-1.5 text-xs text-amber-600 border border-amber-200 rounded hover:bg-amber-50 disabled:opacity-50"
            >
              Modify
            </button>
          ) : (
            <button
              onClick={() => onRespond(modifyText, "modify")}
              disabled={loading || !modifyText.trim()}
              className="px-3 py-1.5 text-xs text-amber-600 border border-amber-200 rounded hover:bg-amber-50 disabled:opacity-50"
            >
              Submit Changes
            </button>
          )}
          <button
            onClick={() => onRespond("Approved", "approve")}
            disabled={loading}
            className="px-4 py-1.5 text-xs bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
          >
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}
