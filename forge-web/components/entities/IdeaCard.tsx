import type { Idea } from "@/lib/types";
import { Badge, statusVariant } from "@/components/shared/Badge";

interface IdeaCardProps {
  idea: Idea;
  onEdit?: (idea: Idea) => void;
}

export function IdeaCard({ idea, onEdit }: IdeaCardProps) {
  return (
    <div className="rounded-lg border bg-white p-4 hover:border-forge-300 transition-colors">
      <div className="flex items-start justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">{idea.id}</span>
          <Badge variant={statusVariant(idea.status)}>{idea.status}</Badge>
          <Badge>{idea.category}</Badge>
          <Badge variant={idea.priority === "HIGH" ? "danger" : idea.priority === "LOW" ? "default" : "warning"}>
            {idea.priority}
          </Badge>
        </div>
        {onEdit && (
          <button
            onClick={() => onEdit(idea)}
            className="text-xs text-gray-400 hover:text-forge-600"
          >
            Edit
          </button>
        )}
      </div>
      <h3 className="font-medium text-sm">{idea.title}</h3>
      {idea.description && (
        <p className="text-xs text-gray-500 mt-1 line-clamp-2">{idea.description}</p>
      )}
      {idea.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {idea.tags.map((t) => (
            <span key={t} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{t}</span>
          ))}
        </div>
      )}
    </div>
  );
}
