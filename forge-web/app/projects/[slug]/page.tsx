"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { useProjectStore } from "@/stores/projectStore";
import { useEntityStore } from "@/stores/entityStore";
import { Card, CardTitle } from "@/components/shared/Card";
import { Badge, statusVariant } from "@/components/shared/Badge";

export default function ProjectDashboardPage() {
  const params = useParams();
  const slug = params.slug as string;

  const { statuses, fetchStatus } = useProjectStore();
  const { slices, fetchEntities } = useEntityStore();
  const status = statuses[slug];

  useEffect(() => {
    if (slug) {
      fetchStatus(slug);
      fetchEntities(slug, "tasks");
      fetchEntities(slug, "decisions", { status: "OPEN" });
      fetchEntities(slug, "changes");
    }
  }, [slug, fetchStatus, fetchEntities]);

  const tasks = slices.tasks.items as import("@/lib/types").Task[];
  const openDecisions = slices.decisions.items as import("@/lib/types").Decision[];
  const recentChanges = (slices.changes.items as import("@/lib/types").ChangeRecord[]).slice(-5).reverse();

  // Task status distribution
  const statusCounts: Record<string, number> = {};
  tasks.forEach((t) => {
    statusCounts[t.status] = (statusCounts[t.status] || 0) + 1;
  });

  const statusColors: Record<string, string> = {
    TODO: "bg-yellow-400",
    IN_PROGRESS: "bg-blue-400",
    DONE: "bg-green-400",
    FAILED: "bg-red-400",
    SKIPPED: "bg-gray-300",
    CLAIMING: "bg-blue-200",
  };

  const totalTasks = tasks.length;

  return (
    <div className="space-y-6">
      {/* Status summary */}
      {status && (
        <Card>
          <div className="flex items-center justify-between mb-3">
            <CardTitle>Project Status</CardTitle>
            <span className="text-2xl font-bold text-forge-600">
              {Math.round(status.progress_pct ?? 0)}%
            </span>
          </div>
          <p className="text-sm text-gray-500 mb-4">{status.goal}</p>

          {/* Progress bar */}
          <div className="h-3 bg-gray-100 rounded-full overflow-hidden flex">
            {Object.entries(statusCounts).map(([key, count]) => (
              <div
                key={key}
                className={`${statusColors[key] || "bg-gray-300"} transition-all`}
                style={{ width: `${totalTasks ? (count / totalTasks) * 100 : 0}%` }}
                title={`${key}: ${count}`}
              />
            ))}
          </div>
          <div className="flex gap-4 mt-2 text-xs text-gray-500">
            {Object.entries(statusCounts).map(([key, count]) => (
              <span key={key} className="flex items-center gap-1">
                <span className={`inline-block w-2 h-2 rounded-full ${statusColors[key] || "bg-gray-300"}`} />
                {key}: {count}
              </span>
            ))}
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Open decisions */}
        <Card>
          <CardTitle>Open Decisions ({openDecisions.length})</CardTitle>
          {openDecisions.length === 0 ? (
            <p className="text-sm text-gray-400 mt-2">No open decisions</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {openDecisions.slice(0, 5).map((d) => (
                <li key={d.id} className="text-sm">
                  <div className="flex items-center gap-2">
                    <Badge variant={statusVariant(d.status)} className="text-[10px]">
                      {d.status}
                    </Badge>
                    <span className="text-gray-400 text-xs">{d.id}</span>
                  </div>
                  <p className="text-gray-700 mt-0.5">{d.issue}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Recent changes */}
        <Card>
          <CardTitle>Recent Changes</CardTitle>
          {recentChanges.length === 0 ? (
            <p className="text-sm text-gray-400 mt-2">No changes recorded</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {recentChanges.map((c) => (
                <li key={c.id} className="text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400 text-xs">{c.id}</span>
                    <code className="text-xs bg-gray-100 px-1 rounded">{c.file}</code>
                  </div>
                  <p className="text-gray-600 mt-0.5">{c.summary}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {/* Entity counts */}
      <Card>
        <CardTitle>Entity Overview</CardTitle>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3">
          {([
            ["Tasks", slices.tasks.count],
            ["Decisions", slices.decisions.count],
            ["Changes", slices.changes.count],
            ["Knowledge", slices.knowledge.count],
            ["Guidelines", slices.guidelines.count],
            ["Objectives", slices.objectives.count],
            ["Ideas", slices.ideas.count],
            ["Lessons", slices.lessons.count],
          ] as [string, number][]).map(([label, count]) => (
            <div key={label} className="text-center">
              <div className="text-2xl font-bold text-gray-700">{count || 0}</div>
              <div className="text-xs text-gray-400">{label}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
