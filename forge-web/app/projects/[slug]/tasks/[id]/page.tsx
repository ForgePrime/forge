"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { tasks as tasksApi, decisions as decisionsApi, changes as changesApi, guidelines as guidelinesApi, knowledge as knowledgeApi } from "@/lib/api";
import { Badge, statusVariant } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import { ConfirmDeleteDialog } from "@/components/shared/ConfirmDeleteDialog";
import { EntityLink } from "@/components/shared/EntityLink";
import { useChatStore } from "@/stores/chatStore";
import { useSidebarStore } from "@/stores/sidebarStore";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import type { Task, TaskUpdate, Decision, ChangeRecord, TaskContext, ContextSection, Guideline, Knowledge } from "@/lib/types";

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
  const [scopedGuidelines, setScopedGuidelines] = useState<{ must: Guideline[]; should: Guideline[]; may: Guideline[] } | null>(null);
  const [linkedKnowledge, setLinkedKnowledge] = useState<Knowledge[]>([]);
  const [relatedLoading, setRelatedLoading] = useState(false);

  // Edit mode state
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editInstruction, setEditInstruction] = useState("");
  const [editScopes, setEditScopes] = useState<string[]>([]);
  const [editAC, setEditAC] = useState<string[]>([]);
  const [editDependsOn, setEditDependsOn] = useState<string[]>([]);
  const [editBlockedByDecisions, setEditBlockedByDecisions] = useState<string[]>([]);

  // Delete state
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

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
        if (tab === "overview" && !scopedGuidelines) {
          const scopes = [...task.scopes, "general"].join(",");
          const glRes = await guidelinesApi.context(slug, scopes);
          setScopedGuidelines(glRes);

          const kIds = task.knowledge_ids ?? [];
          if (kIds.length > 0) {
            const kRes = await knowledgeApi.list(slug);
            const kSet = new Set(kIds);
            setLinkedKnowledge(kRes.knowledge.filter((k) => kSet.has(k.id)));
          }
        }
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
  }, [task, tab, slug, id, depTasks.length, linkedDecisions.length, taskChanges.length, taskContext, scopedGuidelines]);

  const launchSession = (sessionType: string) => {
    useChatStore.getState().startConversation("task", id, slug);
    useChatStore.getState().setPendingSessionMeta({
      sessionType,
      targetEntityType: "task",
      targetEntityId: id,
    });
    useSidebarStore.getState().setActiveTab("chat");
  };

  const canEdit = task?.status === "TODO" || task?.status === "FAILED";
  const canDelete = task?.status === "TODO";

  const startEdit = () => {
    if (!task) return;
    setEditName(task.name);
    setEditDescription(task.description || "");
    setEditInstruction(task.instruction || "");
    setEditScopes([...task.scopes]);
    setEditAC([...task.acceptance_criteria]);
    setEditDependsOn([...task.depends_on]);
    setEditBlockedByDecisions([...task.blocked_by_decisions]);
    setEditing(true);
  };

  const handleSave = async () => {
    if (!task) return;
    setSaving(true);
    setError(null);
    try {
      const update: TaskUpdate = {};
      if (editName !== task.name) update.name = editName;
      if (editDescription !== (task.description || "")) update.description = editDescription;
      if (editInstruction !== (task.instruction || "")) update.instruction = editInstruction;
      if (JSON.stringify(editScopes) !== JSON.stringify(task.scopes)) update.scopes = editScopes;
      if (JSON.stringify(editAC) !== JSON.stringify(task.acceptance_criteria)) update.acceptance_criteria = editAC;
      if (JSON.stringify(editDependsOn) !== JSON.stringify(task.depends_on)) update.depends_on = editDependsOn;
      if (JSON.stringify(editBlockedByDecisions) !== JSON.stringify(task.blocked_by_decisions)) update.blocked_by_decisions = editBlockedByDecisions;
      if (Object.keys(update).length > 0) {
        const updated = await tasksApi.update(slug, task.id, update);
        setTask(updated);
      }
      setEditing(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!task) return;
    setDeleting(true);
    try {
      await tasksApi.remove(slug, task.id);
      router.push(`/projects/${slug}/tasks`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  // --- AI Annotations (must be before early returns) ---
  useAIPage({
    id: "task-detail",
    title: task ? `Task ${task.id} — ${task.name}` : "Task Detail (loading)",
    description: task ? `${task.status} ${task.type} task` : "Loading...",
    route: `/projects/${slug}/tasks/${id}`,
  });

  useAIElement({
    id: "task-entity",
    type: "display",
    label: task ? `Task ${task.id}` : "Task",
    description: task ? `${task.status} ${task.type}` : undefined,
    data: task ? {
      status: task.status,
      type: task.type,
      scopes: task.scopes,
      depends_on: task.depends_on,
      acceptance_criteria_count: task.acceptance_criteria.length,
      origin: task.origin || "none",
    } : undefined,
    actions: [
      {
        label: "Update task",
        toolName: "updateTask",
        toolParams: ["task_id*", "name", "description", "depends_on", "scopes"],
        availableWhen: "status = TODO or FAILED",
      },
      {
        label: "Complete task",
        toolName: "completeTask",
        toolParams: ["task_id*", "reasoning"],
        availableWhen: "status = IN_PROGRESS",
      },
      {
        label: "Get task context",
        toolName: "getTaskContext",
        toolParams: ["task_id*"],
      },
    ],
  });

  if (loading) return <p className="text-sm text-gray-400">Loading task...</p>;
  if (error && !task) return <p className="text-sm text-red-600">{error}</p>;
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
          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-2">
              {!editing && canEdit && (
                <Button variant="secondary" size="sm" onClick={startEdit}>Edit</Button>
              )}
              {!editing && canDelete && (
                <Button variant="danger" size="sm" onClick={() => setDeleteOpen(true)}>Delete</Button>
              )}
              <button
                onClick={() => launchSession("execute")}
                className="px-3 py-1.5 text-xs font-medium text-white bg-green-600 rounded-md hover:bg-green-700"
              >
                Execute with AI
              </button>
              <button
                onClick={() => launchSession("verify")}
                className="px-3 py-1.5 text-xs font-medium text-white bg-amber-600 rounded-md hover:bg-amber-700"
              >
                Verify with AI
              </button>
            </div>
            <div className="text-xs text-gray-400 text-right">
              {task.started_at && <div>Started: {new Date(task.started_at).toLocaleDateString()}</div>}
              {task.completed_at && <div>Completed: {new Date(task.completed_at).toLocaleDateString()}</div>}
              {task.agent && <div>Agent: {task.agent}</div>}
            </div>
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

      {/* Error banner */}
      {error && (
        <div className="flex items-center justify-between bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-4">
          <p className="text-sm text-red-600">{error}</p>
          <button onClick={() => setError(null)} className="text-xs text-red-400 hover:text-red-600">Dismiss</button>
        </div>
      )}

      {/* Tab Content */}
      {tab === "overview" && editing ? (
        <div className="space-y-4 border rounded-lg p-5 bg-gray-50">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Name *</label>
            <input
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="w-full rounded-md border px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
            <textarea
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              rows={4}
              className="w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Instruction</label>
            <textarea
              value={editInstruction}
              onChange={(e) => setEditInstruction(e.target.value)}
              rows={6}
              className="w-full rounded-md border px-3 py-2 text-sm font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Scopes ({editScopes.length})</label>
            {editScopes.map((s, i) => (
              <div key={i} className="flex items-center gap-2 mb-1">
                <input value={s} onChange={(e) => { const next = [...editScopes]; next[i] = e.target.value; setEditScopes(next); }} className="flex-1 rounded-md border px-2 py-1 text-xs" />
                <button onClick={() => setEditScopes(editScopes.filter((_, j) => j !== i))} className="text-xs text-red-400 hover:text-red-600">Remove</button>
              </div>
            ))}
            <button onClick={() => setEditScopes([...editScopes, ""])} className="text-xs text-forge-600 hover:underline mt-1">+ Add scope</button>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Acceptance Criteria ({editAC.length})</label>
            {editAC.map((ac, i) => (
              <div key={i} className="flex items-start gap-2 mb-1">
                <textarea value={ac} onChange={(e) => { const next = [...editAC]; next[i] = e.target.value; setEditAC(next); }} rows={2} className="flex-1 rounded-md border px-2 py-1 text-xs" />
                <button onClick={() => setEditAC(editAC.filter((_, j) => j !== i))} className="text-xs text-red-400 hover:text-red-600 mt-1">Remove</button>
              </div>
            ))}
            <button onClick={() => setEditAC([...editAC, ""])} className="text-xs text-forge-600 hover:underline mt-1">+ Add criterion</button>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Depends On ({editDependsOn.length})</label>
            {editDependsOn.map((dep, i) => (
              <div key={i} className="flex items-center gap-2 mb-1">
                <input value={dep} onChange={(e) => { const next = [...editDependsOn]; next[i] = e.target.value; setEditDependsOn(next); }} placeholder="T-001" className="flex-1 rounded-md border px-2 py-1 text-xs" />
                <button onClick={() => setEditDependsOn(editDependsOn.filter((_, j) => j !== i))} className="text-xs text-red-400 hover:text-red-600">Remove</button>
              </div>
            ))}
            <button onClick={() => setEditDependsOn([...editDependsOn, ""])} className="text-xs text-forge-600 hover:underline mt-1">+ Add dependency</button>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Blocked by Decisions ({editBlockedByDecisions.length})</label>
            {editBlockedByDecisions.map((d, i) => (
              <div key={i} className="flex items-center gap-2 mb-1">
                <input value={d} onChange={(e) => { const next = [...editBlockedByDecisions]; next[i] = e.target.value; setEditBlockedByDecisions(next); }} placeholder="D-001" className="flex-1 rounded-md border px-2 py-1 text-xs" />
                <button onClick={() => setEditBlockedByDecisions(editBlockedByDecisions.filter((_, j) => j !== i))} className="text-xs text-red-400 hover:text-red-600">Remove</button>
              </div>
            ))}
            <button onClick={() => setEditBlockedByDecisions([...editBlockedByDecisions, ""])} className="text-xs text-forge-600 hover:underline mt-1">+ Add decision</button>
          </div>
          <div className="flex items-center gap-2 pt-2">
            <Button onClick={handleSave} disabled={saving} size="sm">
              {saving ? "Saving..." : "Save"}
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setEditing(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : tab === "overview" ? (
        <OverviewTab task={task} slug={slug} guidelines={scopedGuidelines} knowledge={linkedKnowledge} />
      ) : null}
      {tab === "dependencies" && <DependenciesTab task={task} depTasks={depTasks} slug={slug} />}
      {tab === "decisions" && <DecisionsTab decisions={linkedDecisions} slug={slug} />}
      {tab === "changes" && <ChangesTab changes={taskChanges} />}
      {tab === "context" && <ContextTab context={taskContext} />}

      <ConfirmDeleteDialog
        open={deleteOpen}
        title={`Delete ${task.id}?`}
        description="This action cannot be undone. Only TODO tasks with no dependents can be deleted."
        onConfirm={handleDelete}
        onCancel={() => setDeleteOpen(false)}
        loading={deleting}
      />
    </div>
  );
}

function OverviewTab({ task, slug, guidelines, knowledge }: {
  task: Task; slug: string;
  guidelines: { must: Guideline[]; should: Guideline[]; may: Guideline[] } | null;
  knowledge: Knowledge[];
}) {
  const totalGuidelines = guidelines ? guidelines.must.length + guidelines.should.length + guidelines.may.length : 0;

  return (
    <div className="space-y-6">
      {/* Origin */}
      {task.origin && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Origin</h3>
          <EntityLink id={task.origin} />
        </section>
      )}

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

      {/* Applicable Guidelines */}
      {totalGuidelines > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Applicable Guidelines ({totalGuidelines})
          </h3>
          <div className="space-y-1">
            {[
              ...guidelines!.must.map((g) => ({ ...g, _weight: "must" as const })),
              ...guidelines!.should.map((g) => ({ ...g, _weight: "should" as const })),
              ...guidelines!.may.map((g) => ({ ...g, _weight: "may" as const })),
            ].map((g) => (
              <Link
                key={g.id}
                href={`/projects/${slug}/guidelines`}
                className="flex items-center gap-2 p-2 rounded border bg-white text-xs hover:border-forge-300 transition-colors"
              >
                <span className="font-mono text-forge-600">{g.id}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                  g._weight === "must" ? "bg-red-100 text-red-700" :
                  g._weight === "should" ? "bg-yellow-100 text-yellow-700" :
                  "bg-gray-100 text-gray-600"
                }`}>{g._weight}</span>
                <span className="text-gray-500 truncate">[{g.scope}]</span>
                <span className="text-gray-700 truncate">{g.title || g.content?.slice(0, 50)}</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Knowledge */}
      {knowledge.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Knowledge ({knowledge.length})
          </h3>
          <div className="space-y-2">
            {knowledge.map((k) => (
              <Link
                key={k.id}
                href={`/projects/${slug}/knowledge/${k.id}`}
                className="block rounded-lg border bg-white p-3 hover:border-forge-300 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 font-mono">{k.id}</span>
                  <Badge variant={statusVariant(k.status)}>{k.status}</Badge>
                  <Badge>{k.category}</Badge>
                  <span className="text-sm text-gray-700">{k.title}</span>
                </div>
                {k.content && (
                  <p className="text-xs text-gray-500 mt-1 line-clamp-2">{k.content.slice(0, 120)}</p>
                )}
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Failed Reason */}
      {task.failed_reason && (
        <section>
          <h3 className="text-sm font-semibold text-red-600 mb-2">Failed Reason</h3>
          <p className="text-sm text-red-500 bg-red-50 border border-red-200 rounded-md p-3">{task.failed_reason}</p>
        </section>
      )}

      {/* Linked Skill */}
      {task.skill_id && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Linked Skill</h3>
          <Link
            href={`/skills/${task.skill_id}`}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md border bg-white hover:border-forge-300 transition-colors text-sm"
          >
            <span className="text-xs text-gray-400 font-mono">{task.skill_id}</span>
            <span className="text-forge-600">View Skill &rarr;</span>
          </Link>
        </section>
      )}

      {/* Legacy Skill Path */}
      {task.skill && !task.skill_id && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Skill Path</h3>
          <code className="text-xs bg-gray-50 px-2 py-1 rounded">{task.skill}</code>
        </section>
      )}

      {/* Blocked by Decisions */}
      {task.blocked_by_decisions.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Blocked by Decisions</h3>
          <div className="flex flex-wrap gap-2">
            {task.blocked_by_decisions.map((dId) => (
              <EntityLink key={dId} id={dId} />
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
              <EntityLink key={tId} id={tId} />
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
                <EntityLink key={dId} id={dId} showPreview={false} />
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
