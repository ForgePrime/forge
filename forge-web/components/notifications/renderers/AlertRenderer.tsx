"use client";

import type { NotificationRendererProps } from "../registry";

/**
 * Alert notification renderer.
 * Shows alert message and acknowledge button.
 */
export function AlertRenderer({ notification, onRespond, loading }: NotificationRendererProps) {
  return (
    <div className="space-y-3">
      {/* Alert message */}
      {notification.message && (
        <div className="p-3 bg-red-50 rounded-lg border border-red-200">
          <p className="text-sm text-red-800">{notification.message}</p>
        </div>
      )}

      {/* Source info */}
      {notification.source_entity_id && (
        <p className="text-xs text-gray-500">
          Source: {notification.source_entity_type} {notification.source_entity_id}
        </p>
      )}

      {/* Actions */}
      <div className="flex items-center justify-end pt-2 border-t">
        <button
          onClick={() => onRespond("Acknowledged", "acknowledge")}
          disabled={loading}
          className="px-4 py-1.5 text-xs bg-gray-700 text-white rounded hover:bg-gray-800 disabled:opacity-50"
        >
          {loading ? "..." : "Acknowledge"}
        </button>
      </div>
    </div>
  );
}
