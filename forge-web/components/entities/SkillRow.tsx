import Link from "next/link";
import type { Skill } from "@/lib/types";
import { Badge, statusVariant } from "@/components/shared/Badge";
import { getCategoryColor, categoryLabel } from "@/lib/utils/categoryColors";

interface SkillRowProps {
  skill: Skill;
  selected?: boolean;
  onSelect?: (name: string, checked: boolean) => void;
}

export function SkillRow({ skill: s, selected, onSelect }: SkillRowProps) {
  const cats = s.categories ?? [];
  const primaryCat = cats[0] ?? "custom";
  const cat = getCategoryColor(primaryCat);

  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-md border bg-white hover:border-forge-300 transition-colors group">
      {/* Checkbox */}
      {onSelect && (
        <input
          type="checkbox"
          checked={selected ?? false}
          onChange={(e) => onSelect(s.name, e.target.checked)}
          className="h-3.5 w-3.5 rounded border-gray-300 text-forge-600 focus:ring-forge-500"
        />
      )}

      {/* Status badge */}
      <Badge variant={statusVariant(s.status)} className="text-[10px] px-1.5 py-0 w-20 text-center justify-center">
        {s.status}
      </Badge>

      {/* Category badges (max 3, +N) */}
      <div className="flex items-center gap-1 w-32 flex-shrink-0">
        {cats.slice(0, 3).map((c) => {
          const cc = getCategoryColor(c);
          return (
            <span key={c} className={`inline-flex items-center rounded-full px-1.5 py-0 text-[10px] font-medium ${cc.bg} ${cc.text}`}>
              {categoryLabel(c)}
            </span>
          );
        })}
        {cats.length > 3 && (
          <span className="text-[10px] text-gray-400">+{cats.length - 3}</span>
        )}
      </div>

      {/* Name */}
      <Link
        href={`/skills/${s.name}`}
        className="font-medium text-sm truncate flex-1 min-w-0 hover:text-forge-600"
      >
        {s.name}
      </Link>

      {/* Short description */}
      <span className="text-xs text-gray-400 truncate max-w-[200px] hidden xl:block">
        {s.description}
      </span>

      {/* Sync badge */}
      {s.sync && (
        <span className="text-[10px] text-blue-500 flex-shrink-0" title="Synced to repo">
          &#9729; sync
        </span>
      )}

      {/* Stats */}
      <div className="flex items-center gap-3 text-[10px] text-gray-400 flex-shrink-0">
        {(s.evals_json ?? []).length > 0 && (
          <span>{s.evals_json.length} eval{s.evals_json.length !== 1 ? "s" : ""}</span>
        )}
        {(s.usage_count ?? 0) > 0 && (
          <span>used {s.usage_count}x</span>
        )}
      </div>

      {/* Warning indicator */}
      {s.promoted_with_warnings && (
        <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" title="Promoted with warnings" />
      )}
    </div>
  );
}
