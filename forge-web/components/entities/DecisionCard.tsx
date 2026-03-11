import type { Decision } from "@/lib/types";
import { Badge, statusVariant } from "@/components/shared/Badge";

interface DecisionCardProps {
  decision: Decision;
  onStatusChange?: (id: string, status: string) => void;
  onEdit?: (decision: Decision) => void;
}

const STATUS_ACTIONS: Record<string, Array<{ label: string; status: string; className: string }>> = {
  OPEN: [
    { label: "Close", status: "CLOSED", className: "text-green-600 hover:text-green-700" },
    { label: "Defer", status: "DEFERRED", className: "text-yellow-600 hover:text-yellow-700" },
  ],
  ANALYZING: [
    { label: "Close", status: "CLOSED", className: "text-green-600 hover:text-green-700" },
    { label: "Mitigate", status: "MITIGATED", className: "text-blue-600 hover:text-blue-700" },
    { label: "Accept", status: "ACCEPTED", className: "text-gray-600 hover:text-gray-700" },
  ],
  DEFERRED: [
    { label: "Reopen", status: "OPEN", className: "text-forge-600 hover:text-forge-700" },
  ],
};

export function DecisionCard({ decision, onStatusChange, onEdit }: DecisionCardProps) {
  const actions = STATUS_ACTIONS[decision.status] || [];

  return (
    <div className="rounded-lg border bg-white p-4 hover:border-forge-300 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-gray-400">{decision.id}</span>
            <Badge variant={statusVariant(decision.status)}>{decision.status}</Badge>
            <Badge>{decision.type}</Badge>
            <Badge variant={decision.confidence === "HIGH" ? "success" : decision.confidence === "LOW" ? "danger" : "warning"}>
              {decision.confidence}
            </Badge>
          </div>
          <h3 className="font-medium text-sm">{decision.issue}</h3>
          <p className="text-xs text-gray-500 mt-1">{decision.recommendation}</p>
        </div>
        <div className="flex items-center gap-2 ml-2 flex-shrink-0">
          {onEdit && (
            <button
              onClick={(e) => { e.stopPropagation(); onEdit(decision); }}
              className="text-xs text-gray-400 hover:text-gray-600 font-medium"
            >
              Edit
            </button>
          )}
          {onStatusChange && actions.map((action) => (
            <button
              key={action.status}
              onClick={(e) => { e.stopPropagation(); onStatusChange(decision.id, action.status); }}
              className={`text-xs font-medium ${action.className}`}
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>
      {decision.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {decision.tags.map((t) => (
            <span key={t} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{t}</span>
          ))}
        </div>
      )}
    </div>
  );
}
