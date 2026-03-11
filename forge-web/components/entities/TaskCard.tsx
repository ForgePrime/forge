import Link from "next/link";
import type { Task } from "@/lib/types";
import { Badge, statusVariant } from "@/components/shared/Badge";

interface TaskCardProps {
  task: Task;
  slug: string;
  onStatusChange?: (id: string, status: string) => void;
  onEdit?: (task: Task) => void;
}

const STATUS_ACTIONS: Record<string, Array<{ label: string; status: string; className: string }>> = {
  TODO: [
    { label: "Start", status: "IN_PROGRESS", className: "text-forge-600 hover:text-forge-700" },
    { label: "Skip", status: "SKIPPED", className: "text-gray-500 hover:text-gray-600" },
  ],
  IN_PROGRESS: [
    { label: "Done", status: "DONE", className: "text-green-600 hover:text-green-700" },
    { label: "Fail", status: "FAILED", className: "text-red-600 hover:text-red-700" },
  ],
  FAILED: [
    { label: "Retry", status: "TODO", className: "text-forge-600 hover:text-forge-700" },
  ],
};

export function TaskCard({ task, slug, onStatusChange, onEdit }: TaskCardProps) {
  const actions = STATUS_ACTIONS[task.status] || [];

  return (
    <div className="rounded-lg border bg-white p-4 hover:border-forge-300 transition-colors">
      <div className="flex items-start justify-between">
        <Link href={`/projects/${slug}/tasks/${task.id}`} className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-gray-400">{task.id}</span>
            <Badge variant={statusVariant(task.status)}>{task.status}</Badge>
            <Badge>{task.type}</Badge>
          </div>
          <h3 className="font-medium text-sm">{task.name}</h3>
          {task.description && (
            <p className="text-xs text-gray-500 mt-1 line-clamp-2">{task.description}</p>
          )}
        </Link>
        <div className="flex items-center gap-2 ml-2 flex-shrink-0">
          {onEdit && (task.status === "TODO" || task.status === "FAILED") && (
            <button
              onClick={(e) => { e.stopPropagation(); onEdit(task); }}
              className="text-xs text-gray-400 hover:text-gray-600 font-medium"
            >
              Edit
            </button>
          )}
          {onStatusChange && actions.map((action) => (
            <button
              key={action.status}
              onClick={(e) => { e.stopPropagation(); onStatusChange(task.id, action.status); }}
              className={`text-xs font-medium ${action.className}`}
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex flex-wrap gap-1 mt-2">
        {task.scopes.map((s) => (
          <span key={s} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{s}</span>
        ))}
        {task.depends_on.length > 0 && (
          <span className="text-[10px] text-gray-400">depends: {task.depends_on.join(", ")}</span>
        )}
      </div>
    </div>
  );
}
