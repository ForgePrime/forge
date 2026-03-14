"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { useEntityData } from "@/hooks/useEntityData";
import { useTaskStore, updateTask as updateTaskAction } from "@/stores/taskStore";
import { useExecutionStore } from "@/stores/executionStore";
import { tasks as tasksApi } from "@/lib/api";
import { TaskCard } from "@/components/entities/TaskCard";
import { StatusFilter } from "@/components/shared/StatusFilter";
import { SuggestionPanel } from "@/components/ai/SuggestionPanel";
import { TaskForm } from "@/components/forms/TaskForm";
import { DraftPlanView } from "@/components/planning/DraftPlanView";
import { ActiveTasksDashboard } from "@/components/execution/ActiveTasksDashboard";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import type { Task, DraftPlan } from "@/lib/types";

const STATUSES = ["TODO", "IN_PROGRESS", "DONE", "FAILED", "SKIPPED", "CLAIMING"];

export default function TasksPage() {
  const { slug } = useParams() as { slug: string };
  const router = useRouter();
  const searchParams = useSearchParams();
  const { items, count, isLoading, error, mutate } = useEntityData<Task>(slug, "tasks");
  const saving = useTaskStore((s) => s.saving);
  const [statusFilter, setStatusFilter] = useState(searchParams.get("status") ?? "");
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | undefined>();
  const [draft, setDraft] = useState<DraftPlan | null>(null);
  const [claimingTaskId, setClaimingTaskId] = useState<string | null>(null);
  const [claimError, setClaimError] = useState<string | null>(null);
  const [agentName, setAgentName] = useState("");

  const claimNext = useExecutionStore((s) => s.claimNext);
  const executionPhase = useExecutionStore((s) => s.phase);
  const executionError = useExecutionStore((s) => s.error);
  const resetExecution = useExecutionStore((s) => s.reset);
  const isClaiming = executionPhase === "claiming";

  // Load draft plan if one exists
  useEffect(() => {
    tasksApi.getDraft(slug).then(setDraft).catch(() => setDraft(null));
  }, [slug]);

  const tasks = items;
  const filtered = statusFilter
    ? tasks.filter((t) => t.status === statusFilter)
    : tasks;

  // ---------------------------------------------------------------------------
  // AI Annotations
  // ---------------------------------------------------------------------------

  useAIPage({
    id: "tasks",
    title: `Tasks (${count})`,
    description: `Task list for project ${slug}`,
    route: `/projects/${slug}/tasks`,
  });

  // Status distribution for AI context
  const statusDist = useMemo(() => {
    const dist: Record<string, number> = {};
    for (const t of tasks) {
      dist[t.status] = (dist[t.status] ?? 0) + 1;
    }
    return dist;
  }, [tasks]);

  useAIElement({
    id: "status-filter",
    type: "filter",
    label: "Status Filter",
    value: statusFilter || "All",
    actions: [{ label: "Filter", description: "Filter tasks by status" }],
  });

  useAIElement({
    id: "task-list",
    type: "list",
    label: "Tasks",
    description: `${filtered.length} shown of ${count} total`,
    data: {
      count,
      filtered: filtered.length,
      statuses: statusDist,
    },
    actions: [
      {
        label: "Start task",
        toolName: "updateTask",
        toolParams: ["task_id*", "status=IN_PROGRESS"],
        availableWhen: "status = TODO",
      },
      {
        label: "Skip task",
        toolName: "updateTask",
        toolParams: ["task_id*", "status=SKIPPED"],
        availableWhen: "status = TODO",
      },
      {
        label: "Complete task",
        toolName: "completeTask",
        toolParams: ["task_id*", "reasoning"],
        availableWhen: "status = IN_PROGRESS",
      },
      {
        label: "Create task",
        toolName: "createTask",
        toolParams: ["name*", "description", "type*", "scopes", "depends_on", "acceptance_criteria"],
      },
    ],
  });

  const todoCount = statusDist["TODO"] ?? 0;

  useAIElement({
    id: "claim-next-btn",
    type: "button",
    label: "Claim Next Task",
    description: `Claims the next available TODO task via /tasks/next. ${todoCount} TODO tasks available.`,
    data: { todoCount, isClaiming },
    actions: [
      {
        label: "Claim next task",
        toolName: "claimNextTask",
        toolParams: ["agent"],
        availableWhen: "todoCount > 0 and not claiming",
      },
    ],
  });

  useAIElement({
    id: "task-form",
    type: "form",
    label: "Task Form",
    value: formOpen,
    description: formOpen ? `open (${editingTask ? `editing ${editingTask.id}` : "creating"})` : "closed",
    data: {
      fields: ["name*", "description", "instruction", "type*", "scopes", "skill_id", "acceptance_criteria", "depends_on"],
    },
    actions: [
      {
        label: editingTask ? "Update" : "Create",
        toolName: editingTask ? "updateTask" : "createTask",
        toolParams: editingTask
          ? ["task_id*", "name", "description", "depends_on", "scopes"]
          : ["name*", "description", "type*", "scopes", "depends_on", "acceptance_criteria"],
      },
    ],
  });

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const handleClaimNext = useCallback(async () => {
    setClaimError(null);
    const task = await claimNext(slug, agentName || undefined);
    if (task) {
      router.push(`/projects/${slug}/execution/${task.id}`);
    } else {
      const state = useExecutionStore.getState();
      if (state.phase === "idle") {
        setClaimError("No tasks available to claim. All tasks are done, blocked by dependencies, or already in progress.");
      } else if (state.phase === "failed" && state.error) {
        setClaimError(state.error);
        resetExecution();
      }
    }
  }, [slug, claimNext, router, resetExecution]);

  const handleClaimSpecific = useCallback(async (task: Task) => {
    setClaimError(null);

    // Check for conflicts with active tasks
    const activeTasks = items.filter((t) => t.status === "IN_PROGRESS" || t.status === "CLAIMING");
    const conflicts: string[] = [];
    for (const conflictId of task.conflicts_with ?? []) {
      const activeConflict = activeTasks.find((t) => t.id === conflictId);
      if (activeConflict) {
        conflicts.push(`${conflictId}${activeConflict.agent ? ` (${activeConflict.agent})` : ""}: ${activeConflict.name}`);
      }
    }
    for (const active of activeTasks) {
      if ((active.conflicts_with ?? []).includes(task.id) && !conflicts.some((c) => c.startsWith(active.id))) {
        conflicts.push(`${active.id}${active.agent ? ` (${active.agent})` : ""}: ${active.name}`);
      }
    }
    if (conflicts.length > 0) {
      setClaimError(`Conflict warning: ${task.id} conflicts with active task(s): ${conflicts.join("; ")}`);
      return;
    }

    setClaimingTaskId(task.id);
    try {
      await updateTaskAction(slug, task.id, { status: "IN_PROGRESS" });
      mutate();
      router.push(`/projects/${slug}/execution/${task.id}`);
    } catch (e) {
      setClaimError((e as Error).message);
    } finally {
      setClaimingTaskId(null);
    }
  }, [slug, mutate, router, items]);

  const handleStatusChange = (id: string, status: string) => {
    updateTaskAction(slug, id, { status: status as Task["status"] });
  };

  const handleTaskSelect = (id: string) => {
    setSelectedTaskId((prev) => (prev === id ? null : id));
  };

  const handleEdit = (task: Task) => {
    setEditingTask(task);
    setFormOpen(true);
  };

  const handleCreate = () => {
    setEditingTask(undefined);
    setFormOpen(true);
  };

  const handleFormClose = () => {
    setFormOpen(false);
    setEditingTask(undefined);
  };

  const handleFormSuccess = useCallback(() => {
    mutate();
  }, [mutate]);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">
          Tasks ({count})
          {saving && <span className="ml-2 text-xs text-gray-400">Saving...</span>}
        </h2>
        <div className="flex items-center gap-3">
          <StatusFilter options={STATUSES} value={statusFilter} onChange={setStatusFilter} />
          <input
            type="text"
            value={agentName}
            onChange={(e) => setAgentName(e.target.value)}
            placeholder="Agent name"
            className="w-28 text-xs border rounded px-2 py-1.5 placeholder-gray-300 focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400"
          />
          <button
            onClick={handleClaimNext}
            disabled={isClaiming || todoCount === 0}
            className="px-3 py-1.5 text-sm text-white bg-emerald-600 rounded-md hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isClaiming ? "Claiming..." : "Claim Next Task"}
          </button>
          <button
            onClick={handleCreate}
            className="px-3 py-1.5 text-sm text-white bg-forge-600 rounded-md hover:bg-forge-700"
          >
            + New Task
          </button>
        </div>
      </div>
      {/* Active tasks dashboard */}
      <ActiveTasksDashboard slug={slug} />
      {/* Draft plan banner */}
      {draft && (
        <div className="mb-4">
          <DraftPlanView
            slug={slug}
            draft={draft}
            onApproved={() => { setDraft(null); mutate(); }}
            onDiscarded={() => setDraft(null)}
          />
        </div>
      )}
      {claimError && (
        <div className="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-md px-3 py-2 mb-4">
          <p className="text-sm text-amber-700">{claimError}</p>
          <button onClick={() => setClaimError(null)} className="text-xs text-amber-500 hover:text-amber-700">Dismiss</button>
        </div>
      )}
      {isLoading && <p className="text-sm text-gray-400">Loading...</p>}
      {error && (
        <p className="text-sm text-red-600 mb-2">{error}</p>
      )}
      <div className="space-y-3">
        {filtered.map((task) => (
          <div
            key={task.id}
            onClick={() => handleTaskSelect(task.id)}
            className={`cursor-pointer rounded-lg transition-shadow ${
              selectedTaskId === task.id
                ? "ring-2 ring-forge-500 shadow-md"
                : ""
            }`}
          >
            <TaskCard
              task={task}
              slug={slug}
              onStatusChange={handleStatusChange}
              onEdit={handleEdit}
              onClaim={handleClaimSpecific}
              claiming={claimingTaskId === task.id}
            />
          </div>
        ))}
        {!isLoading && filtered.length === 0 && (
          <p className="text-sm text-gray-400">No tasks{statusFilter ? ` with status ${statusFilter}` : ""}</p>
        )}
      </div>

      {selectedTaskId && (
        <SuggestionPanel
          entityType="task"
          entityId={selectedTaskId}
          suggestionTypes={["knowledge", "guidelines", "ac"]}
        />
      )}

      <TaskForm
        slug={slug}
        open={formOpen}
        onClose={handleFormClose}
        task={editingTask}
        onSuccess={handleFormSuccess}
      />
    </div>
  );
}
