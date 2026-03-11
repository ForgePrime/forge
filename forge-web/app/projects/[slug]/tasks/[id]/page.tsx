"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { tasks as tasksApi, decisions as decisionsApi, changes as changesApi } from "@/lib/api";
import { Badge, statusVariant } from "@/components/shared/Badge";
import type { Task, Decision, ChangeRecord, TaskContext, ContextSection } from "@/lib/types";

type Tab = "overview" | "dependencies" | "decisions" | "changes" | "context";

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "dependencies", label: "Dependencies" },
  { key: "decisions", label: "Decisions" },
  { key: "changes", label: "Changes" },
  { key: "context", label: "Context" },
];

export default function TaskDetailPage() {
  const { slug, id } = useParams() as { slug: string; id: string };
  const router = useRouter();
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("overview");

  // Related data
  const [depTasks, setDepTasks] = useState<Task[]>([]);
  const [linkedDecisions, setLinkedDecisions] = useState<Decision[]>([]);
  const [taskChanges, setTaskChanges] = useState<ChangeRecord[]>([]);
  const [taskContext, setTaskContext] = useState<TaskContext | null>(null);
  const [relatedLoading, setRelatedLoading] = useState(false);

  const fetchTask = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await tasksApi.get(slug, id);
      setTask(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [slug, id]);

  useEffect(() => {
    fetchTask();
  }, [fetchTask]);

  // Fetch related data when task loads or tab changes
  useEffect(() => {
    if (!task) return;

    const fetchRelated = async () => {
      setRelatedLoading(true);
      try {
        if (tab === "dependencies" && depTasks.length === 0 && task.depends_on.length > 0) {
          const deps = await Promise.all(
            task.depends_on.map((depId) => tasksApi.get(slug, depId).catch(() => null))
          );
          setDepTasks(deps.filter((d): d is Task => d !== null));
        }
        if (tab === "decisions" && linkedDecisions.length === 0) {
          const res = await decisionsApi.list(slug, { task_id: id });
          setLinkedDecisions(res.decisions);
        }
        if (tab === "changes" && taskChanges.length === 0) {
          const res = await changesApi.list(slug, { task_id: id });
          setTaskChanges(res.changes);
        }
        if (tab === "context" && !taskContext) {
          const ctx = await tasksApi.context(slug, id);
          setTaskContext(ctx);
        }
      } catch {
        // Silently fail for related data
      } finally {
        setRelatedLoading(false);
      }
    };
    fetchRelated();
  }, [task, tab, slug, id, depTasks.length, linkedDecisions.length, taskChanges.length, taskContext]);

  if (loading) return <p className="text-sm text-gray-400">Loading task...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!task) return <p className="text-sm text-gray-400">Task not found</p>;

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <button onClick={() => router.back()} className="text-xs text-gray-400 hover:text-gray-600 mb-2">
          &larr; Back
        </button>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm text-gray-400 font-mono">{task.id}</span>
              <Badge variant={statusVariant(task.status)}>{task.status}</Badge>
              <Badge>{task.type}</Badge>
              {task.parallel && <Badge variant="info">parallel</Badge>}
            </div>
            <h1 className="text-xl font-bold">{task.name}</h1>
          </div>
          <div className="text-xs text-gray-400 text-right">
            {task.started_at && <div>Started: {new Date(task.started_at).toLocaleDateString()}</div>}
            {task.completed_at && <div>Completed: {new Date(task.completed_at).toLocaleDateString()}</div>}
            {task.agent && <div>Agent: {task.agent}</div>}
          </div>
        </div>
        {task.scopes.length > 0 && (
          <div className="flex gap-1 mt-2">
            {task.scopes.map((s) => (
              <span key={s} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{s}</span>
            ))}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b mb-4">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm border-b-2 transition-colors ${
              tab === t.key
                ? "border-forge-600 text-forge-600 font-medium"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {relatedLoading && <p className="text-xs text-gray-400 mb-2">Loading...</p>}

      {/* Tab Content */}
      {tab === "overview" && <OverviewTab task={task} slug={slug} />}
      {tab === "dependencies" && <DependenciesTab task={task} depTasks={depTasks} slug={slug} />}
      {tab === "decisions" && <DecisionsTab decisions={linkedDecisions} slug={slug} />}
      {tab === "changes" && <ChangesTab changes={taskChanges} />}
      {tab === "context" && <ContextTab context={taskContext} />}
    </div>
  );
}

function OverviewTab({ task, slug }: { task: Task; slug: string }) {
  return (
    <div className="space-y-6">
      {/* Description */}
      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Description</h3>
        <p className="text-sm text-gray-600 whitespace-pre-wrap">{task.description || "No description"}</p>
      </section>

      {/* Instruction */}
      {task.instruction && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Instruction</h3>
          <pre className="text-xs bg-gray-50 border rounded-md p-3 whitespace-pre-wrap overflow-x-auto">
            {task.instruction}
          </pre>
        </section>
      )}

      {/* Acceptance Criteria */}
      {task.acceptance_criteria.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Acceptance Criteria ({task.acceptance_criteria.length})
          </h3>
          <ul className="space-y-1">
            {task.acceptance_criteria.map((ac, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className={`mt-0.5 w-4 h-4 rounded border flex items-center justify-center text-[10px] ${
                  task.status === "DONE" ? "bg-green-100 border-green-300 text-green-600" : "border-gray-300"
                }`}>
                  {task.status === "DONE" ? "✓" : ""}
                </span>
                <span className="text-gray-600">{ac}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Failed Reason */}
      {task.failed_reason && (
        <section>
          <h3 className="text-sm font-semibold text-red-600 mb-2">Failed Reason</h3>
          <p className="text-sm text-red-500 bg-red-50 border border-red-200 rounded-md p-3">{task.failed_reason}</p>
        </section>
      )}

      {/* Blocked by Decisions */}
      {task.blocked_by_decisions.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Blocked by Decisions</h3>
          <div className="flex flex-wrap gap-2">
            {task.blocked_by_decisions.map((dId) => (
              <Link
                key={dId}
                href={`/projects/${slug}/decisions/${dId}`}
                className="text-xs bg-amber-50 text-amber-700 border border-amber-200 px-2 py-1 rounded hover:bg-amber-100"
              >
                {dId}
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Conflicts With */}
      {task.conflicts_with.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Conflicts With</h3>
          <div className="flex flex-wrap gap-2">
            {task.conflicts_with.map((tId) => (
              <Link
                key={tId}
                href={`/projects/${slug}/tasks/${tId}`}
                className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded hover:bg-gray-200"
              >
                {tId}
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function DependenciesTab({ task, depTasks, slug }: { task: Task; depTasks: Task[]; slug: string }) {
  if (task.depends_on.length === 0) {
    return <p className="text-sm text-gray-400">No dependencies</p>;
  }

  return (
    <div className="space-y-2">
      {task.depends_on.map((depId) => {
        const dep = depTasks.find((d) => d.id === depId);
        return (
          <Link
            key={depId}
            href={`/projects/${slug}/tasks/${depId}`}
            className="block rounded-lg border bg-white p-3 hover:border-forge-300 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400 font-mono">{depId}</span>
              {dep && (
                <>
                  <Badge variant={statusVariant(dep.status)}>{dep.status}</Badge>
                  <span className="text-sm text-gray-700">{dep.name}</span>
                </>
              )}
              {!dep && <span className="text-sm text-gray-400">Loading...</span>}
            </div>
          </Link>
        );
      })}
    </div>
  );
}

function DecisionsTab({ decisions, slug }: { decisions: Decision[]; slug: string }) {
  if (decisions.length === 0) {
    return <p className="text-sm text-gray-400">No linked decisions</p>;
  }

  return (
    <div className="space-y-2">
      {decisions.map((d) => (
        <Link
          key={d.id}
          href={`/projects/${slug}/decisions/${d.id}`}
          className="block rounded-lg border bg-white p-3 hover:border-forge-300 transition-colors"
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-gray-400 font-mono">{d.id}</span>
            <Badge variant={statusVariant(d.status)}>{d.status}</Badge>
            <Badge>{d.type}</Badge>
          </div>
          <p className="text-sm text-gray-700">{d.issue}</p>
          {d.recommendation && (
            <p className="text-xs text-gray-500 mt-1 line-clamp-2">{d.recommendation}</p>
          )}
        </Link>
      ))}
    </div>
  );
}

function ChangesTab({ changes }: { changes: ChangeRecord[] }) {
  if (changes.length === 0) {
    return <p className="text-sm text-gray-400">No recorded changes</p>;
  }

  return (
    <div className="space-y-2">
      {changes.map((c) => (
        <div key={c.id} className="rounded-lg border bg-white p-3">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant={c.action === "create" ? "success" : c.action === "delete" ? "danger" : "warning"}>
              {c.action}
            </Badge>
            <span className="text-sm font-mono text-gray-700">{c.file}</span>
            {c.lines_added != null && (
              <span className="text-[10px] text-green-600">+{c.lines_added}</span>
            )}
            {c.lines_removed != null && (
              <span className="text-[10px] text-red-500">-{c.lines_removed}</span>
            )}
          </div>
          <p className="text-xs text-gray-500">{c.summary}</p>
          {c.decision_ids && c.decision_ids.length > 0 && (
            <div className="flex gap-1 mt-1">
              {c.decision_ids.map((dId) => (
                <span key={dId} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{dId}</span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ContextTab({ context }: { context: TaskContext | null }) {
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  if (!context) {
    return <p className="text-sm text-gray-400">Loading context...</p>;
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4 text-xs text-gray-500">
        <span>Sections: {context.sections.length}</span>
        <span>Tokens: ~{context.total_token_estimate.toLocaleString()}</span>
        <span>Scopes: {context.scopes.join(", ") || "none"}</span>
      </div>
      <div className="space-y-2">
        {context.sections.map((section) => (
          <div key={section.name} className="border rounded-lg overflow-hidden">
            <button
              onClick={() => setExpandedSection(expandedSection === section.name ? null : section.name)}
              className="w-full flex items-center justify-between px-4 py-2 bg-gray-50 text-left hover:bg-gray-100"
            >
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-700">{section.header || section.name}</span>
                {section.was_truncated && <Badge variant="warning">truncated</Badge>}
              </div>
              <span className="text-xs text-gray-400">~{section.token_estimate} tokens</span>
            </button>
            {expandedSection === section.name && (
              <pre className="text-xs bg-white p-4 whitespace-pre-wrap overflow-x-auto border-t max-h-96 overflow-y-auto">
                {section.content || "(empty)"}
              </pre>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
