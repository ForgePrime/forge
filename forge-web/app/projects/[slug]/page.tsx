"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEntityData } from "@/hooks/useEntityData";
import { useProjectStore } from "@/stores/projectStore";
import { useActivityStore } from "@/stores/activityStore";
import { Card, CardTitle } from "@/components/shared/Card";
import { Badge, statusVariant } from "@/components/shared/Badge";
import { ActivityFeed } from "@/components/shared/ActivityFeed";
import type {
  Task,
  Decision,
  Objective,
  KeyResult,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Status colors shared by pipeline bar and legend
// ---------------------------------------------------------------------------

const STATUS_COLORS: Record<string, string> = {
  TODO: "bg-yellow-400",
  IN_PROGRESS: "bg-blue-400",
  DONE: "bg-green-400",
  FAILED: "bg-red-400",
  SKIPPED: "bg-gray-300",
  CLAIMING: "bg-blue-200",
};

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function ProjectDashboardPage() {
  const params = useParams();
  const slug = params.slug as string;

  return (
    <div className="space-y-6">
      <ObjectivesSection slug={slug} />
      <PipelineSection slug={slug} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <OpenDecisionsSection slug={slug} />
        <ActivitySection slug={slug} />
      </div>

      <QuickActionsSection slug={slug} />
      <BlockingAlertsSection slug={slug} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section 1: Active Objectives with KR Progress
// ---------------------------------------------------------------------------

function ObjectivesSection({ slug }: { slug: string }) {
  const { items: objectives, isLoading } = useEntityData<Objective>(slug, "objectives");

  const active = useMemo(
    () => objectives.filter((o) => o.status === "ACTIVE"),
    [objectives],
  );

  if (isLoading) return null;
  if (active.length === 0) return null;

  return (
    <Card>
      <CardTitle>Active Objectives</CardTitle>
      <div className="mt-3 space-y-4">
        {active.map((obj) => (
          <div key={obj.id}>
            <Link
              href={`/projects/${slug}/objectives/${obj.id}`}
              className="text-sm font-medium text-gray-700 hover:text-forge-600"
            >
              {obj.id}: {obj.title}
            </Link>
            <div className="mt-1.5 space-y-1.5">
              {obj.key_results.map((kr, i) => (
                <KRProgressBar key={i} kr={kr} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function KRProgressBar({ kr }: { kr: KeyResult }) {
  const target = kr.target || 1;
  const current = kr.current ?? 0;
  const pct = Math.min(100, Math.round((current / target) * 100));

  let barColor = "bg-forge-500";
  if (pct >= 100) barColor = "bg-green-500";
  else if (pct < 30) barColor = "bg-red-400";
  else if (pct < 60) barColor = "bg-yellow-400";

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1">
        <div className="flex items-center justify-between text-[10px] text-gray-500 mb-0.5">
          <span className="truncate max-w-[200px]">{kr.metric}</span>
          <span className="tabular-nums">{current}/{target} ({pct}%)</span>
        </div>
        <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${barColor}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section 2: Task Pipeline Proportions Bar
// ---------------------------------------------------------------------------

function PipelineSection({ slug }: { slug: string }) {
  const { items: tasks, isLoading } = useEntityData<Task>(slug, "tasks");
  const { statuses } = useProjectStore();
  const status = statuses[slug];

  const { statusCounts, totalTasks } = useMemo(() => {
    const counts: Record<string, number> = {};
    tasks.forEach((t) => {
      counts[t.status] = (counts[t.status] || 0) + 1;
    });
    return { statusCounts: counts, totalTasks: tasks.length };
  }, [tasks]);

  if (isLoading) return null;

  return (
    <Card>
      <div className="flex items-center justify-between mb-3">
        <CardTitle>Task Pipeline</CardTitle>
        <span className="text-2xl font-bold text-forge-600">
          {status ? `${Math.round(status.progress_pct ?? 0)}%` : `${totalTasks}`}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-4 bg-gray-100 rounded-full overflow-hidden flex">
        {Object.entries(statusCounts).map(([key, count]) => (
          <Link
            key={key}
            href={`/projects/${slug}/tasks?status=${key}`}
            className={`${STATUS_COLORS[key] || "bg-gray-300"} transition-all hover:opacity-80`}
            style={{ width: `${totalTasks ? (count / totalTasks) * 100 : 0}%` }}
            title={`${key}: ${count}`}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mt-2 text-xs text-gray-500">
        {Object.entries(statusCounts).map(([key, count]) => (
          <Link
            key={key}
            href={`/projects/${slug}/tasks?status=${key}`}
            className="flex items-center gap-1 hover:text-gray-700"
          >
            <span className={`inline-block w-2 h-2 rounded-full ${STATUS_COLORS[key] || "bg-gray-300"}`} />
            {key}: {count}
          </Link>
        ))}
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Section 3: Open Decisions
// ---------------------------------------------------------------------------

function OpenDecisionsSection({ slug }: { slug: string }) {
  const { items: decisions } = useEntityData<Decision>(slug, "decisions");

  const openDecisions = useMemo(
    () => decisions.filter((d) => d.status === "OPEN" || d.status === "ANALYZING"),
    [decisions],
  );

  return (
    <Card>
      <div className="flex items-center justify-between mb-2">
        <CardTitle>Open Decisions ({openDecisions.length})</CardTitle>
        <Link href={`/projects/${slug}/decisions`} className="text-xs text-forge-600 hover:underline">
          View all
        </Link>
      </div>
      {openDecisions.length === 0 ? (
        <p className="text-sm text-gray-400 mt-2">No open decisions</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {openDecisions.slice(0, 5).map((d) => (
            <li key={d.id}>
              <Link
                href={`/projects/${slug}/decisions/${d.id}`}
                className="block hover:bg-gray-50 rounded-md p-1.5 -mx-1.5"
              >
                <div className="flex items-center gap-2">
                  <Badge variant={statusVariant(d.status)} className="text-[10px]">
                    {d.status}
                  </Badge>
                  <span className="text-gray-400 text-xs font-mono">{d.id}</span>
                  {d.type === "risk" && (
                    <span className="text-[10px] text-red-500 font-medium">RISK</span>
                  )}
                </div>
                <p className="text-sm text-gray-700 mt-0.5 line-clamp-1">{d.issue}</p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Section 4: Activity Feed
// ---------------------------------------------------------------------------

function ActivitySection({ slug }: { slug: string }) {
  const events = useActivityStore((s) => s.events);
  const projectEvents = useMemo(
    () => events.filter((e) => e.project === slug),
    [events, slug],
  );

  return (
    <Card>
      <CardTitle>Recent Activity</CardTitle>
      <div className="mt-2">
        {projectEvents.length === 0 ? (
          <p className="text-sm text-gray-400">No activity yet — events appear as changes happen</p>
        ) : (
          <ActivityFeed events={projectEvents} compact limit={10} />
        )}
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Section 5: Quick Actions
// ---------------------------------------------------------------------------

function QuickActionsSection({ slug }: { slug: string }) {
  const actions = [
    { label: "Tasks", href: `/projects/${slug}/tasks`, icon: "+" },
    { label: "Ideas", href: `/projects/${slug}/ideas`, icon: "+" },
    { label: "Decisions", href: `/projects/${slug}/decisions`, icon: "+" },
    { label: "Knowledge", href: `/projects/${slug}/knowledge`, icon: "+" },
    { label: "Board", href: `/projects/${slug}/board`, icon: "▦" },
    { label: "Settings", href: `/projects/${slug}/settings`, icon: "⚙" },
  ];

  return (
    <div className="flex flex-wrap gap-2">
      {actions.map((a) => (
        <Link
          key={a.label}
          href={a.href}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50 text-gray-600 hover:text-gray-800 transition-colors"
        >
          <span className="text-xs">{a.icon}</span>
          {a.label}
        </Link>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section 6: Blocking Alerts
// ---------------------------------------------------------------------------

function BlockingAlertsSection({ slug }: { slug: string }) {
  const { items: tasks } = useEntityData<Task>(slug, "tasks");
  const { items: decisions } = useEntityData<Decision>(slug, "decisions");

  const blockers = useMemo(() => {
    const closedDecisions = new Set(
      decisions.filter((d) => d.status === "CLOSED" || d.status === "DEFERRED").map((d) => d.id),
    );
    const doneTasks = new Set(
      tasks.filter((t) => t.status === "DONE" || t.status === "SKIPPED").map((t) => t.id),
    );

    const blocked: Array<{
      task: Task;
      reasons: string[];
    }> = [];

    for (const t of tasks) {
      if (t.status !== "TODO") continue;
      const reasons: string[] = [];

      // Check unmet dependencies
      if (t.depends_on) {
        for (const dep of t.depends_on) {
          if (!doneTasks.has(dep)) {
            reasons.push(`Depends on ${dep}`);
          }
        }
      }

      // Check unresolved decisions
      if (t.blocked_by_decisions) {
        for (const decId of t.blocked_by_decisions) {
          if (!closedDecisions.has(decId)) {
            reasons.push(`Blocked by decision ${decId}`);
          }
        }
      }

      if (reasons.length > 0) {
        blocked.push({ task: t, reasons });
      }
    }

    return blocked;
  }, [tasks, decisions]);

  // Also show FAILED tasks
  const failedTasks = useMemo(
    () => tasks.filter((t) => t.status === "FAILED"),
    [tasks],
  );

  if (blockers.length === 0 && failedTasks.length === 0) return null;

  return (
    <Card>
      <CardTitle>
        Blocking Alerts ({blockers.length + failedTasks.length})
      </CardTitle>
      <div className="mt-2 space-y-2">
        {failedTasks.map((t) => (
          <Link
            key={t.id}
            href={`/projects/${slug}/tasks/${t.id}`}
            className="flex items-start gap-2 p-2 bg-red-50 rounded-lg border border-red-100 hover:border-red-200"
          >
            <span className="text-red-500 text-xs font-bold mt-0.5">!</span>
            <div>
              <span className="text-sm font-medium text-red-700">{t.id}: {t.name}</span>
              <p className="text-xs text-red-600">
                FAILED{t.failed_reason ? `: ${t.failed_reason}` : ""}
              </p>
            </div>
          </Link>
        ))}
        {blockers.map(({ task: t, reasons }) => (
          <Link
            key={t.id}
            href={`/projects/${slug}/tasks/${t.id}`}
            className="flex items-start gap-2 p-2 bg-amber-50 rounded-lg border border-amber-100 hover:border-amber-200"
          >
            <span className="text-amber-500 text-xs font-bold mt-0.5">!</span>
            <div>
              <span className="text-sm font-medium text-amber-700">{t.id}: {t.name}</span>
              <div className="flex flex-wrap gap-1 mt-0.5">
                {reasons.map((r) => (
                  <span key={r} className="text-[10px] text-amber-600 bg-amber-100 rounded px-1.5 py-0.5">
                    {r}
                  </span>
                ))}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </Card>
  );
}
