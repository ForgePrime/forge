"use client";

import { useState, useMemo, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useEntityData } from "@/hooks/useEntityData";
import { updateTask as updateTaskAction } from "@/stores/taskStore";
import { Badge } from "@/components/shared/Badge";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import { EntityDAG } from "@/components/graph/EntityDAG";
import type { Task, TaskStatus } from "@/lib/types";

// ---------------------------------------------------------------------------
// Shared constants
// ---------------------------------------------------------------------------

const KANBAN_COLUMNS: TaskStatus[] = ["TODO", "IN_PROGRESS", "DONE", "FAILED"];

const STATUS_COLORS_CSS: Record<TaskStatus, string> = {
  TODO: "bg-yellow-400",
  IN_PROGRESS: "bg-blue-400",
  DONE: "bg-green-400",
  FAILED: "bg-red-400",
  SKIPPED: "bg-gray-300",
  CLAIMING: "bg-blue-200",
};

type ViewMode = "kanban" | "dag";

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function BoardPage() {
  const { slug } = useParams() as { slug: string };
  const { items: tasks, isLoading, error } = useEntityData<Task>(slug, "tasks");
  const [view, setView] = useState<ViewMode>("kanban");
  const [scopeFilter, setScopeFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Collect unique scopes and types for filters
  const { allScopes, allTypes } = useMemo(() => {
    const scopes = new Set<string>();
    const types = new Set<string>();
    for (const t of tasks) {
      types.add(t.type);
      for (const s of t.scopes) scopes.add(s);
    }
    return {
      allScopes: Array.from(scopes).sort(),
      allTypes: Array.from(types).sort(),
    };
  }, [tasks]);

  const filtered = useMemo(() => {
    let result = tasks;
    if (scopeFilter) result = result.filter((t) => t.scopes.includes(scopeFilter));
    if (typeFilter) result = result.filter((t) => t.type === typeFilter);
    if (statusFilter) result = result.filter((t) => t.status === statusFilter);
    return result;
  }, [tasks, scopeFilter, typeFilter, statusFilter]);

  // Status counts
  const statusCounts = useMemo(() => {
    const counts: Partial<Record<TaskStatus, number>> = {};
    for (const t of tasks) counts[t.status] = (counts[t.status] || 0) + 1;
    return counts;
  }, [tasks]);

  useAIPage({
    id: "board",
    title: `Task Board — ${slug}`,
    description: `${view} view of ${tasks.length} tasks`,
    route: `/projects/${slug}/board`,
  });

  useAIElement({
    id: "board-view",
    type: "display",
    label: `Task Board (${view})`,
    description: `${filtered.length} shown of ${tasks.length} total`,
    data: { view, total: tasks.length, filtered: filtered.length, ...statusCounts },
    actions: [
      { label: "Update task status", toolName: "updateTask", toolParams: ["task_id*", "status"] },
    ],
  });

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">Task Board</h2>
          <div className="flex border rounded-md overflow-hidden text-xs">
            <button
              onClick={() => setView("kanban")}
              className={`px-3 py-1 ${view === "kanban" ? "bg-forge-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
            >
              Kanban
            </button>
            <button
              onClick={() => setView("dag")}
              className={`px-3 py-1 ${view === "dag" ? "bg-forge-600 text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
            >
              DAG
            </button>
          </div>
        </div>

        {/* Filters + legend (kanban only — DAG has its own toolbar) */}
        {view === "kanban" && (
          <div className="flex items-center gap-2 flex-wrap">
            {allScopes.length > 0 && (
              <select
                value={scopeFilter}
                onChange={(e) => setScopeFilter(e.target.value)}
                className="text-xs border rounded px-2 py-1 bg-white"
              >
                <option value="">All scopes</option>
                {allScopes.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            )}
            {allTypes.length > 1 && (
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="text-xs border rounded px-2 py-1 bg-white"
              >
                <option value="">All types</option>
                {allTypes.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            )}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs border rounded px-2 py-1 bg-white"
            >
              <option value="">All statuses</option>
              {KANBAN_COLUMNS.map((s) => <option key={s} value={s}>{s}</option>)}
              <option value="SKIPPED">SKIPPED</option>
            </select>
            <div className="flex gap-2 text-[10px] text-gray-400 ml-2">
              {(Object.entries(statusCounts) as [TaskStatus, number][]).map(([s, c]) => (
                <span key={s} className="flex items-center gap-1">
                  <span className={`inline-block w-2 h-2 rounded-sm ${STATUS_COLORS_CSS[s]}`} />
                  {s}: {c}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {isLoading && <p className="text-sm text-gray-400">Loading tasks...</p>}
      {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
      {tasks.length === 0 && !isLoading && <p className="text-sm text-gray-400">No tasks to display.</p>}

      {tasks.length > 0 && (
        view === "kanban"
          ? <KanbanView tasks={filtered} slug={slug} />
          : <div className="flex-1 min-h-0"><EntityDAG slug={slug} /></div>
      )}
    </div>
  );
}

// ===========================================================================
// Kanban View
// ===========================================================================

function KanbanView({ tasks, slug }: { tasks: Task[]; slug: string }) {
  const [dragOverCol, setDragOverCol] = useState<string | null>(null);
  const dragItemRef = useRef<string | null>(null);

  const columns = useMemo(() => {
    const cols: Record<string, Task[]> = {};
    for (const col of KANBAN_COLUMNS) cols[col] = [];
    for (const t of tasks) {
      if (cols[t.status]) {
        cols[t.status].push(t);
      } else {
        // SKIPPED, CLAIMING → append to appropriate column
        if (t.status === "SKIPPED") cols.DONE?.push(t);
        else if (t.status === "CLAIMING") cols.IN_PROGRESS?.push(t);
      }
    }
    return cols;
  }, [tasks]);

  const handleDragStart = (e: React.DragEvent, taskId: string) => {
    e.dataTransfer.setData("text/plain", taskId);
    e.dataTransfer.effectAllowed = "move";
    dragItemRef.current = taskId;
  };

  const handleDragOver = (e: React.DragEvent, col: string) => {
    e.preventDefault();
    setDragOverCol(col);
  };

  const handleDragLeave = () => {
    setDragOverCol(null);
  };

  const handleDrop = (e: React.DragEvent, targetStatus: string) => {
    e.preventDefault();
    setDragOverCol(null);
    const taskId = dragItemRef.current;
    dragItemRef.current = null;
    if (!taskId) return;

    const task = tasks.find((t) => t.id === taskId);
    if (!task || task.status === targetStatus) return;

    updateTaskAction(slug, taskId, { status: targetStatus as TaskStatus }).catch(() => {
      // SWR will revalidate and restore correct state
    });
  };

  return (
    <div className="flex-1 overflow-x-auto">
      <div className="flex gap-3 min-h-[400px]" style={{ minWidth: KANBAN_COLUMNS.length * 260 }}>
        {KANBAN_COLUMNS.map((col) => {
          const colTasks = columns[col] ?? [];
          const isOver = dragOverCol === col;
          return (
            <div
              key={col}
              className={`flex-1 min-w-[240px] rounded-lg p-2 transition-colors ${
                isOver ? "bg-forge-50 border-2 border-dashed border-forge-300" : "bg-gray-50 border border-gray-200"
              }`}
              onDragOver={(e) => handleDragOver(e, col)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, col)}
            >
              {/* Column header */}
              <div className="flex items-center justify-between mb-2 px-1">
                <div className="flex items-center gap-1.5">
                  <span className={`w-2.5 h-2.5 rounded-sm ${STATUS_COLORS_CSS[col]}`} />
                  <span className="text-xs font-semibold text-gray-600">{col}</span>
                </div>
                <span className="text-[10px] text-gray-400 tabular-nums">{colTasks.length}</span>
              </div>

              {/* Cards */}
              <div className="space-y-2">
                {colTasks.map((task) => (
                  <KanbanCard key={task.id} task={task} slug={slug} onDragStart={handleDragStart} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function KanbanCard({
  task,
  slug,
  onDragStart,
}: {
  task: Task;
  slug: string;
  onDragStart: (e: React.DragEvent, id: string) => void;
}) {
  const isBlocked = (task.blocked_by_decisions ?? []).length > 0;

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, task.id)}
      className={`bg-white rounded-md border p-2.5 cursor-grab active:cursor-grabbing hover:border-forge-300 transition-colors ${
        isBlocked ? "border-red-300 border-l-4 border-l-red-400" : ""
      }`}
    >
      <Link href={`/projects/${slug}/tasks/${task.id}`} className="block">
        <div className="flex items-center gap-1.5 mb-1">
          <span className="text-[10px] font-mono text-gray-400">{task.id}</span>
          <Badge className="text-[9px]">{task.type}</Badge>
          {isBlocked && <span className="text-[9px] text-red-500 font-medium">BLOCKED</span>}
        </div>
        <p className="text-xs font-medium text-gray-700 line-clamp-2">{task.name}</p>
      </Link>
      {task.scopes.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1.5">
          {task.scopes.slice(0, 3).map((s) => (
            <span key={s} className="text-[9px] bg-gray-100 text-gray-500 px-1 py-0.5 rounded">{s}</span>
          ))}
          {task.scopes.length > 3 && (
            <span className="text-[9px] text-gray-400">+{task.scopes.length - 3}</span>
          )}
        </div>
      )}
    </div>
  );
}

