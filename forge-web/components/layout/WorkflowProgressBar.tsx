"use client";

import Link from "next/link";
import { useEntityData } from "@/hooks/useEntityData";
import type { Task, Objective, Idea, Research } from "@/lib/types";

interface WorkflowProgressBarProps {
  slug: string;
}

interface Stage {
  key: string;
  label: string;
  icon: string;
  route: string;
  status: "done" | "active" | "pending";
  count: number;
}

const STATUS_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  done: { bg: "bg-green-50", text: "text-green-700", dot: "bg-green-500" },
  active: { bg: "bg-forge-50", text: "text-forge-700", dot: "bg-forge-500" },
  pending: { bg: "bg-gray-50", text: "text-gray-400", dot: "bg-gray-300" },
};

export function WorkflowProgressBar({ slug }: WorkflowProgressBarProps) {
  const { items: objectives } = useEntityData<Objective>(slug, "objectives");
  const { items: ideas } = useEntityData<Idea>(slug, "ideas");
  const { items: tasks } = useEntityData<Task>(slug, "tasks");
  const { items: research } = useEntityData<Research>(slug, "research");

  // Heuristic counts
  const objCount = objectives.length;
  const approvedIdeas = ideas.filter((i) => i.status === "APPROVED" || i.status === "COMMITTED");
  const researchCount = research.length;
  const todoTasks = tasks.filter((t) => t.status === "TODO");
  const inProgressTasks = tasks.filter((t) => t.status === "IN_PROGRESS");
  const doneTasks = tasks.filter((t) => t.status === "DONE");

  // We don't import lessons store here to keep it light — use task count as proxy
  const totalTasks = tasks.length;

  // Build stages with heuristic status
  const stages: Stage[] = [
    {
      key: "objective",
      label: "Objectives",
      icon: "\u{1F3AF}",
      route: `/projects/${slug}/objectives`,
      status: objCount > 0 ? "done" : "pending",
      count: objCount,
    },
    {
      key: "ideas",
      label: "Ideas",
      icon: "\u{1F4A1}",
      route: `/projects/${slug}/ideas`,
      status: approvedIdeas.length > 0 ? "done" : ideas.length > 0 ? "active" : "pending",
      count: ideas.length,
    },
    {
      key: "discovery",
      label: "Discovery",
      icon: "\u{1F50D}",
      route: `/projects/${slug}/research`,
      status: researchCount > 0 ? "done" : "pending",
      count: researchCount,
    },
    {
      key: "plan",
      label: "Plan",
      icon: "\u{1F4CB}",
      route: `/projects/${slug}/tasks`,
      status: totalTasks > 0 ? "done" : "pending",
      count: totalTasks,
    },
    {
      key: "execute",
      label: "Execute",
      icon: "\u26A1",
      route: `/projects/${slug}/tasks?status=IN_PROGRESS`,
      status: doneTasks.length === totalTasks && totalTasks > 0
        ? "done"
        : inProgressTasks.length > 0 || doneTasks.length > 0
          ? "active"
          : "pending",
      count: doneTasks.length,
    },
    {
      key: "learn",
      label: "Learn",
      icon: "\u{1F4DA}",
      route: `/projects/${slug}/lessons`,
      status: doneTasks.length === totalTasks && totalTasks > 0 ? "active" : "pending",
      count: 0, // Would need lessonStore; keep it lightweight
    },
  ];

  return (
    <div className="flex items-center gap-1 px-6 py-1.5 bg-gray-50 border-b overflow-x-auto">
      {stages.map((stage, i) => {
        const colors = STATUS_COLORS[stage.status];
        return (
          <div key={stage.key} className="flex items-center">
            {i > 0 && (
              <div className={`w-4 h-px mx-0.5 ${
                stage.status !== "pending" ? "bg-forge-300" : "bg-gray-200"
              }`} />
            )}
            <Link
              href={stage.route}
              className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs transition-colors hover:bg-gray-100 ${colors.text}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
              <span>{stage.icon}</span>
              <span className="font-medium whitespace-nowrap">{stage.label}</span>
              {stage.count > 0 && (
                <span className="text-[10px] opacity-60">{stage.count}</span>
              )}
            </Link>
          </div>
        );
      })}
    </div>
  );
}
