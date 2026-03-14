"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useEntityData } from "@/hooks/useEntityData";
import { Badge, statusVariant } from "@/components/shared/Badge";
import { useAIElement } from "@/lib/ai-context";
import type { Task } from "@/lib/types";

interface ActiveTasksDashboardProps {
  slug: string;
}

export function ActiveTasksDashboard({ slug }: ActiveTasksDashboardProps) {
  const { items: tasks } = useEntityData<Task>(slug, "tasks");

  const activeTasks = useMemo(
    () => tasks.filter((t) => t.status === "IN_PROGRESS" || t.status === "CLAIMING"),
    [tasks]
  );

  const agents = useMemo(() => {
    const map = new Map<string, Task[]>();
    for (const t of activeTasks) {
      const agent = t.agent || "unassigned";
      const list = map.get(agent) || [];
      list.push(t);
      map.set(agent, list);
    }
    return map;
  }, [activeTasks]);

  useAIElement({
    id: "active-tasks-dashboard",
    type: "section",
    label: "Active Tasks",
    description: `${activeTasks.length} active tasks, ${agents.size} agents`,
    data: {
      active: activeTasks.length,
      agents: Array.from(agents.keys()),
      tasks: activeTasks.map((t) => ({ id: t.id, name: t.name, agent: t.agent })),
    },
    actions: [],
  });

  if (activeTasks.length === 0) {
    return (
      <div className="rounded-lg border bg-gray-50 px-4 py-6 text-center">
        <p className="text-sm text-gray-400">No tasks currently in progress.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-white">
      <div className="px-4 py-3 border-b flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">Active Tasks</span>
          <Badge variant="default">{activeTasks.length}</Badge>
        </div>
        <span className="text-xs text-gray-400">{agents.size} agent{agents.size !== 1 ? "s" : ""}</span>
      </div>

      <div className="divide-y">
        {activeTasks.map((task) => (
          <Link
            key={task.id}
            href={`/projects/${slug}/execution/${task.id}`}
            className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition-colors"
          >
            <span className="text-xs text-gray-400 w-12">{task.id}</span>
            <Badge variant={statusVariant(task.status)}>{task.status}</Badge>
            <span className="text-sm text-gray-700 flex-1 truncate">{task.name}</span>
            {task.agent && (
              <span className="text-[10px] bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded font-medium">
                {task.agent}
              </span>
            )}
            {task.conflicts_with.length > 0 && (
              <span className="text-[10px] text-amber-500" title={`Conflicts: ${task.conflicts_with.join(", ")}`}>
                conflicts: {task.conflicts_with.join(", ")}
              </span>
            )}
          </Link>
        ))}
      </div>
    </div>
  );
}
