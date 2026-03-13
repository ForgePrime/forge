"use client";

import { useState, useMemo, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useEntityData } from "@/hooks/useEntityData";
import { updateTask as updateTaskAction } from "@/stores/taskStore";
import { Badge } from "@/components/shared/Badge";
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

const STATUS_COLORS_HEX: Record<TaskStatus, string> = {
  TODO: "#9ca3af",
  IN_PROGRESS: "#3b82f6",
  DONE: "#22c55e",
  FAILED: "#ef4444",
  SKIPPED: "#d1d5db",
  CLAIMING: "#93c5fd",
};

const STATUS_TEXT_HEX: Record<TaskStatus, string> = {
  TODO: "#ffffff",
  IN_PROGRESS: "#ffffff",
  DONE: "#ffffff",
  FAILED: "#ffffff",
  SKIPPED: "#374151",
  CLAIMING: "#1e3a5f",
};

// ---------------------------------------------------------------------------
// Filter types
// ---------------------------------------------------------------------------

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

        {/* Filters + legend */}
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
      </div>

      {isLoading && <p className="text-sm text-gray-400">Loading tasks...</p>}
      {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
      {tasks.length === 0 && !isLoading && <p className="text-sm text-gray-400">No tasks to display.</p>}

      {tasks.length > 0 && (
        view === "kanban"
          ? <KanbanView tasks={filtered} slug={slug} />
          : <DagView tasks={filtered} slug={slug} />
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

// ===========================================================================
// DAG View (preserved from original, enhanced with colors + tooltips)
// ===========================================================================

const NODE_W = 180;
const NODE_H = 56;
const H_GAP = 60;
const V_GAP = 32;
const PAD_X = 40;
const PAD_Y = 40;
const ARROW_SIZE = 6;

interface NodePos {
  id: string;
  x: number;
  y: number;
  layer: number;
}

function computeLayout(tasks: Task[]): { nodes: Map<string, NodePos>; width: number; height: number; cycleNodes: Set<string> } {
  const taskMap = new Map<string, Task>();
  for (const t of tasks) taskMap.set(t.id, t);

  const children = new Map<string, string[]>();
  const parents = new Map<string, string[]>();
  for (const t of tasks) {
    if (!children.has(t.id)) children.set(t.id, []);
    if (!parents.has(t.id)) parents.set(t.id, []);
    for (const dep of t.depends_on) {
      if (!taskMap.has(dep)) continue;
      if (!children.has(dep)) children.set(dep, []);
      children.get(dep)!.push(t.id);
      parents.get(t.id)!.push(dep);
    }
  }

  const layerOf = new Map<string, number>();
  const inDegree = new Map<string, number>();
  for (const t of tasks) {
    inDegree.set(t.id, (parents.get(t.id) ?? []).filter((p) => taskMap.has(p)).length);
  }
  const queue: string[] = [];
  inDegree.forEach((deg, id) => {
    if (deg === 0) { queue.push(id); layerOf.set(id, 0); }
  });

  let qi = 0;
  while (qi < queue.length) {
    const cur = queue[qi++];
    const curLayer = layerOf.get(cur)!;
    for (const child of children.get(cur) ?? []) {
      const newLayer = curLayer + 1;
      if (!layerOf.has(child) || layerOf.get(child)! < newLayer) layerOf.set(child, newLayer);
      inDegree.set(child, inDegree.get(child)! - 1);
      if (inDegree.get(child) === 0) queue.push(child);
    }
  }

  const assignedMax = Math.max(0, ...Array.from(layerOf.values()));
  const cycleNodes = new Set<string>();
  for (const t of tasks) {
    if (!layerOf.has(t.id)) { layerOf.set(t.id, assignedMax + 1); cycleNodes.add(t.id); }
  }

  const layers = new Map<number, string[]>();
  layerOf.forEach((layer, id) => {
    if (!layers.has(layer)) layers.set(layer, []);
    layers.get(layer)!.push(id);
  });
  layers.forEach((ids) => ids.sort());

  const layerKeys = Array.from(layers.keys());
  const maxLayer = layerKeys.length > 0 ? Math.max(...layerKeys) : 0;

  const nodes = new Map<string, NodePos>();
  let maxY = 0;
  for (let l = 0; l <= maxLayer; l++) {
    const ids = layers.get(l) ?? [];
    const x = PAD_X + l * (NODE_W + H_GAP);
    for (let i = 0; i < ids.length; i++) {
      const y = PAD_Y + i * (NODE_H + V_GAP);
      nodes.set(ids[i], { id: ids[i], x, y, layer: l });
      if (y + NODE_H > maxY) maxY = y + NODE_H;
    }
  }

  return {
    nodes,
    width: PAD_X * 2 + (maxLayer + 1) * NODE_W + maxLayer * H_GAP,
    height: maxY + PAD_Y,
    cycleNodes,
  };
}

function DagView({ tasks, slug }: { tasks: Task[]; slug: string }) {
  const router = useRouter();
  const [tooltip, setTooltip] = useState<{ task: Task; x: number; y: number } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const isPanning = useRef(false);
  const panStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });

  const taskMap = useMemo(() => {
    const m = new Map<string, Task>();
    for (const t of tasks) m.set(t.id, t);
    return m;
  }, [tasks]);

  const { nodes, width, height, cycleNodes } = useMemo(() => computeLayout(tasks), [tasks]);

  const edges = useMemo(() => {
    const result: { from: string; to: string; blocked: boolean; isConflict?: boolean }[] = [];
    for (const t of tasks) {
      for (const dep of t.depends_on) {
        if (nodes.has(dep) && nodes.has(t.id)) {
          const depTask = taskMap.get(dep);
          const blocked = !!depTask && depTask.status !== "DONE" && depTask.status !== "SKIPPED";
          result.push({ from: dep, to: t.id, blocked });
        }
      }
      // conflicts_with as dashed gray edges (bidirectional, deduplicate)
      for (const cId of t.conflicts_with ?? []) {
        if (nodes.has(cId) && nodes.has(t.id) && t.id < cId) {
          result.push({ from: t.id, to: cId, blocked: false, isConflict: true });
        }
      }
    }
    return result;
  }, [tasks, nodes, taskMap]);

  // Zoom with mouse wheel
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom((z) => Math.max(0.2, Math.min(3, z * delta)));
  }, []);

  // Pan with mouse drag
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    isPanning.current = true;
    panStart.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isPanning.current) return;
    setPan({
      x: panStart.current.panX + (e.clientX - panStart.current.x),
      y: panStart.current.panY + (e.clientY - panStart.current.y),
    });
  }, []);

  const handleMouseUp = useCallback(() => { isPanning.current = false; }, []);

  const resetView = useCallback(() => { setZoom(1); setPan({ x: 0, y: 0 }); }, []);

  const handleNodeClick = useCallback(
    (task: Task) => { router.push(`/projects/${slug}/tasks/${task.id}`); },
    [router, slug],
  );

  const handleNodeHover = useCallback(
    (e: React.MouseEvent, task: Task | null) => {
      if (!task) { setTooltip(null); return; }
      const svgEl = svgRef.current;
      if (!svgEl) return;
      const rect = svgEl.getBoundingClientRect();
      setTooltip({ task, x: e.clientX - rect.left + 12, y: e.clientY - rect.top - 8 });
    },
    [],
  );

  return (
    <div className="flex-1 overflow-hidden border rounded-lg bg-gray-50 relative"
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Zoom controls */}
      <div className="absolute top-2 right-2 z-10 flex gap-1">
        <button onClick={() => setZoom((z) => Math.min(3, z * 1.2))}
          className="w-7 h-7 bg-white border rounded text-xs hover:bg-gray-50 font-bold">+</button>
        <button onClick={() => setZoom((z) => Math.max(0.2, z * 0.8))}
          className="w-7 h-7 bg-white border rounded text-xs hover:bg-gray-50 font-bold">&minus;</button>
        <button onClick={resetView}
          className="h-7 px-2 bg-white border rounded text-[10px] hover:bg-gray-50">Reset</button>
        <span className="h-7 flex items-center px-1 text-[10px] text-gray-400">{Math.round(zoom * 100)}%</span>
      </div>

      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        viewBox={`${-pan.x / zoom} ${-pan.y / zoom} ${Math.max(width, 600) / zoom} ${Math.max(height, 200) / zoom}`}
        className="select-none"
        style={{ cursor: isPanning.current ? "grabbing" : "grab" }}
      >
        <defs>
          <marker id="arrow" markerWidth={ARROW_SIZE} markerHeight={ARROW_SIZE}
            refX={ARROW_SIZE} refY={ARROW_SIZE / 2} orient="auto">
            <polygon points={`0 0, ${ARROW_SIZE} ${ARROW_SIZE / 2}, 0 ${ARROW_SIZE}`} fill="#94a3b8" />
          </marker>
          <marker id="arrow-red" markerWidth={ARROW_SIZE} markerHeight={ARROW_SIZE}
            refX={ARROW_SIZE} refY={ARROW_SIZE / 2} orient="auto">
            <polygon points={`0 0, ${ARROW_SIZE} ${ARROW_SIZE / 2}, 0 ${ARROW_SIZE}`} fill="#ef4444" />
          </marker>
        </defs>

        {/* Edges */}
        {edges.map(({ from, to, blocked, isConflict }) => {
          const a = nodes.get(from)!;
          const b = nodes.get(to)!;
          if (isConflict) {
            // Conflict edges: dashed orange line between node centers
            const x1 = a.x + NODE_W / 2, y1 = a.y + NODE_H / 2;
            const x2 = b.x + NODE_W / 2, y2 = b.y + NODE_H / 2;
            return (
              <line key={`conflict-${from}-${to}`}
                x1={x1} y1={y1} x2={x2} y2={y2}
                stroke="#f97316" strokeWidth={1.5} strokeDasharray="4 4" opacity={0.6}
              />
            );
          }
          const x1 = a.x + NODE_W, y1 = a.y + NODE_H / 2;
          const x2 = b.x, y2 = b.y + NODE_H / 2;
          const cx1 = x1 + (x2 - x1) * 0.4, cx2 = x2 - (x2 - x1) * 0.4;
          return (
            <path
              key={`${from}-${to}`}
              d={`M ${x1} ${y1} C ${cx1} ${y1}, ${cx2} ${y2}, ${x2} ${y2}`}
              fill="none"
              stroke={blocked ? "#ef4444" : "#94a3b8"}
              strokeWidth={blocked ? 2 : 1.5}
              strokeDasharray={blocked ? "6 3" : undefined}
              markerEnd={blocked ? "url(#arrow-red)" : "url(#arrow)"}
            />
          );
        })}

        {/* Nodes */}
        {tasks.map((task) => {
          const pos = nodes.get(task.id);
          if (!pos) return null;
          const fill = STATUS_COLORS_HEX[task.status] ?? "#9ca3af";
          const textColor = STATUS_TEXT_HEX[task.status] ?? "#ffffff";
          const hasBlockedDecisions = (task.blocked_by_decisions ?? []).length > 0;

          return (
            <g
              key={task.id}
              transform={`translate(${pos.x}, ${pos.y})`}
              style={{ cursor: "pointer" }}
              onClick={() => handleNodeClick(task)}
              onMouseEnter={(e) => handleNodeHover(e, task)}
              onMouseMove={(e) => handleNodeHover(e, task)}
              onMouseLeave={(e) => handleNodeHover(e, null)}
            >
              <rect
                width={NODE_W} height={NODE_H} rx={8} ry={8}
                fill={fill}
                stroke={hasBlockedDecisions ? "#ef4444" : cycleNodes.has(task.id) ? "#f97316" : "#e5e7eb"}
                strokeWidth={hasBlockedDecisions || cycleNodes.has(task.id) ? 3 : 1}
                strokeDasharray={cycleNodes.has(task.id) ? "6 3" : hasBlockedDecisions ? "4 2" : undefined}
                className="transition-opacity hover:opacity-90"
              />
              <text x={NODE_W / 2} y={20} textAnchor="middle" fill={textColor}
                fontSize={11} fontWeight={600} fontFamily="ui-monospace, monospace">
                {task.id}
              </text>
              <text x={NODE_W / 2} y={40} textAnchor="middle" fill={textColor}
                fontSize={10} fontFamily="system-ui, sans-serif">
                {task.name.length > 22 ? task.name.slice(0, 20) + "\u2026" : task.name}
              </text>
              {hasBlockedDecisions && (
                <g>
                  <circle cx={NODE_W - 4} cy={4} r={8} fill="#ef4444" />
                  <text x={NODE_W - 4} y={8} textAnchor="middle" fill="#fff" fontSize={11} fontWeight={700}>!</text>
                </g>
              )}
            </g>
          );
        })}
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="absolute pointer-events-none z-10 bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs max-w-xs"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <div className="font-semibold text-gray-800 mb-1">
            {tooltip.task.id} &mdash; {tooltip.task.name}
          </div>
          <div className="text-gray-500 mb-1">
            Status: <span className="font-medium" style={{ color: STATUS_COLORS_HEX[tooltip.task.status] }}>
              {tooltip.task.status}
            </span>
          </div>
          {tooltip.task.description && (
            <div className="text-gray-600 leading-snug line-clamp-3">{tooltip.task.description}</div>
          )}
          {tooltip.task.scopes.length > 0 && (
            <div className="text-gray-400 mt-1">Scopes: {tooltip.task.scopes.join(", ")}</div>
          )}
          {tooltip.task.depends_on.length > 0 && (
            <div className="text-gray-400 mt-0.5">Depends on: {tooltip.task.depends_on.join(", ")}</div>
          )}
        </div>
      )}
    </div>
  );
}
