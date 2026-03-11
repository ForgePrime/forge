import type { Objective } from "@/lib/types";
import { Badge, statusVariant } from "@/components/shared/Badge";

interface ObjectiveCardProps {
  objective: Objective;
  onEdit?: (objective: Objective) => void;
}

export function ObjectiveCard({ objective, onEdit }: ObjectiveCardProps) {
  return (
    <div className="rounded-lg border bg-white p-4 hover:border-forge-300 transition-colors">
      <div className="flex items-start justify-between mb-1">
        <div className="flex items-center gap-2">
        <span className="text-xs text-gray-400">{objective.id}</span>
        <Badge variant={statusVariant(objective.status)}>{objective.status}</Badge>
        <Badge>{objective.appetite}</Badge>
      </div>
      <h3 className="font-medium text-sm">{objective.title}</h3>
      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{objective.description}</p>
      {objective.key_results.length > 0 && (
        <div className="mt-2 space-y-1">
          {objective.key_results.map((kr, i) => {
            const baseline = kr.baseline ?? 0;
            const span = kr.target - baseline;
            const pct = span !== 0 ? Math.min(100, Math.max(0, Math.round(((kr.current ?? baseline) - baseline) / span * 100))) : 0;
            return (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span className="text-gray-500 flex-1 truncate">{kr.metric}</span>
                <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full bg-forge-500 rounded-full" style={{ width: `${Math.min(100, pct)}%` }} />
                </div>
                <span className="text-gray-400 w-8 text-right">{pct}%</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
