"use client";

import { useState } from "react";
import type { NotificationRendererProps } from "../registry";

/**
 * Question notification renderer (LLM questions).
 * Shows question text, text input for answer, send/skip buttons.
 */
export function QuestionRenderer({ notification, onRespond, onDismiss, loading }: NotificationRendererProps) {
  const [answer, setAnswer] = useState("");

  return (
    <div className="space-y-3">
      {/* Question */}
      {notification.message && (
        <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
          <p className="text-sm text-amber-800">{notification.message}</p>
        </div>
      )}

      {/* AI suggested answers */}
      {notification.ai_options.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500">Suggested answers:</p>
          {notification.ai_options.map((opt, i) => (
            <button
              key={i}
              onClick={() => onRespond(opt.label, opt.action)}
              disabled={loading}
              className="w-full text-left p-2 rounded border border-gray-200 hover:border-blue-300 hover:bg-blue-50 text-sm disabled:opacity-50"
            >
              <span className="text-gray-800">{opt.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Text input */}
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">
          Your answer
        </label>
        <textarea
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Type your answer..."
          rows={3}
          className="w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between pt-2 border-t">
        <button
          onClick={() => onRespond("Skipped", "skip")}
          disabled={loading}
          className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700 disabled:opacity-50"
        >
          Skip
        </button>
        <button
          onClick={() => onRespond(answer.trim(), "answer")}
          disabled={loading || !answer.trim()}
          className="px-4 py-1.5 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
        >
          {loading ? "Sending..." : "Send Answer"}
        </button>
      </div>
    </div>
  );
}
