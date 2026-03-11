"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { ToastItem } from "@/stores/toastStore";
import { useToastStore } from "@/stores/toastStore";

const AUTO_DISMISS_MS = 5_000;

const ACTION_ICONS: Record<string, string> = {
  created: "+",
  updated: "~",
  deleted: "x",
  completed: "v",
  failed: "!",
  info: "i",
};

const ACTION_COLORS: Record<string, string> = {
  created: "bg-green-500",
  updated: "bg-blue-500",
  deleted: "bg-red-500",
  completed: "bg-green-600",
  failed: "bg-red-600",
  info: "bg-gray-500",
};

const ENTITY_ROUTES: Record<string, string> = {
  task: "tasks",
  decision: "decisions",
  objective: "objectives",
  idea: "ideas",
  change: "changes",
  guideline: "guidelines",
  knowledge: "knowledge",
  lesson: "lessons",
  ac_template: "ac-templates",
  gate: "gates",
};

export function Toast({ toast }: { toast: ToastItem }) {
  const router = useRouter();
  const removeToast = useToastStore((s) => s.removeToast);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Slide in
    requestAnimationFrame(() => setVisible(true));

    // Auto-dismiss
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(() => removeToast(toast.id), 300);
    }, AUTO_DISMISS_MS);

    return () => clearTimeout(timer);
  }, [toast.id, removeToast]);

  const handleClick = () => {
    if (toast.entityId && toast.entityType && toast.project) {
      const route = ENTITY_ROUTES[toast.entityType];
      if (route) {
        router.push(`/projects/${toast.project}/${route}/${toast.entityId}`);
      }
    }
    setVisible(false);
    setTimeout(() => removeToast(toast.id), 300);
  };

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    setVisible(false);
    setTimeout(() => removeToast(toast.id), 300);
  };

  const icon = ACTION_ICONS[toast.action] ?? "i";
  const iconColor = ACTION_COLORS[toast.action] ?? "bg-gray-500";
  const isClickable = toast.entityId && toast.entityType && toast.project;

  return (
    <div
      onClick={isClickable ? handleClick : undefined}
      className={`flex items-start gap-3 bg-white border rounded-lg shadow-lg p-3 max-w-sm transition-all duration-300 ${
        visible ? "translate-x-0 opacity-100" : "translate-x-full opacity-0"
      } ${isClickable ? "cursor-pointer hover:border-forge-300" : ""}`}
    >
      <span
        className={`flex-shrink-0 w-6 h-6 rounded-full ${iconColor} text-white text-xs font-bold flex items-center justify-center`}
      >
        {icon}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-800 line-clamp-2">{toast.message}</p>
        {toast.entityId && (
          <span className="text-[10px] text-gray-400 font-mono">{toast.entityId}</span>
        )}
      </div>
      <button
        onClick={handleDismiss}
        aria-label="Dismiss notification"
        className="flex-shrink-0 text-gray-400 hover:text-gray-600 text-sm leading-none"
      >
        x
      </button>
    </div>
  );
}
