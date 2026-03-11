import type { Knowledge, StaleKnowledge } from "@/lib/types";
import { Badge, statusVariant } from "@/components/shared/Badge";
import Link from "next/link";

interface KnowledgeCardProps {
  knowledge: Knowledge;
  slug: string;
  onEdit?: (knowledge: Knowledge) => void;
  /** Optional stale info from the maintenance endpoint. */
  staleInfo?: StaleKnowledge;
}

/** Check if knowledge is stale based on its own fields (client-side heuristic). */
function isStaleLocally(k: Knowledge): { stale: boolean; daysSince: number | null } {
  const lastUpdated = k.updated_at || k.created_at;
  if (!lastUpdated) return { stale: false, daysSince: null };

  const lastDate = new Date(lastUpdated);
  const now = new Date();
  const diffMs = now.getTime() - lastDate.getTime();
  const daysSince = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const interval = k.review_interval_days || 30;

  return { stale: daysSince > interval, daysSince };
}

export function KnowledgeCard({ knowledge: k, slug, onEdit, staleInfo }: KnowledgeCardProps) {
  // Use server-provided stale info if available, otherwise compute locally
  const localStale = isStaleLocally(k);
  const isStale = staleInfo
    ? true // if staleInfo is provided, it means this item IS stale
    : localStale.stale;
  const daysSince = staleInfo?.days_since_update ?? localStale.daysSince;

  const showStaleIndicator =
    isStale && k.status !== "ARCHIVED" && k.status !== "DEPRECATED";
  const isReviewNeeded = k.status === "REVIEW_NEEDED";

  return (
    <div
      className={`block rounded-lg border bg-white p-4 hover:border-forge-300 transition-colors ${
        showStaleIndicator || isReviewNeeded ? "border-l-4 border-l-amber-400" : ""
      }`}
    >
      <div className="flex items-start justify-between mb-1">
        <Link
          href={`/projects/${slug}/knowledge/${k.id}`}
          className="flex items-center gap-2 hover:underline"
        >
          <span className="text-xs text-gray-400">{k.id}</span>
          <Badge variant={statusVariant(k.status)}>{k.status}</Badge>
          <Badge>{k.category}</Badge>
          {showStaleIndicator && (
            <Badge variant="warning">
              Stale{daysSince != null ? ` (${daysSince}d)` : ""}
            </Badge>
          )}
          {isReviewNeeded && !showStaleIndicator && (
            <Badge variant="warning">Needs Review</Badge>
          )}
        </Link>
        {onEdit && (
          <button
            onClick={() => onEdit(k)}
            className="text-xs text-gray-400 hover:text-forge-600"
          >
            Edit
          </button>
        )}
      </div>
      <h3 className="font-medium text-sm">{k.title}</h3>
      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{k.content}</p>
      {staleInfo?.suggestion && (
        <p className="text-xs text-amber-600 mt-1 italic">{staleInfo.suggestion}</p>
      )}
      <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-400">
        {k.scopes.length > 0 && <span>scopes: {k.scopes.join(", ")}</span>}
        {k.linked_entities.length > 0 && (
          <span>{k.linked_entities.length} link{k.linked_entities.length !== 1 ? "s" : ""}</span>
        )}
        {k.dependencies.length > 0 && (
          <span>{k.dependencies.length} dep{k.dependencies.length !== 1 ? "s" : ""}</span>
        )}
      </div>
      {k.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {k.tags.map((t) => (
            <span key={t} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{t}</span>
          ))}
        </div>
      )}
    </div>
  );
}
