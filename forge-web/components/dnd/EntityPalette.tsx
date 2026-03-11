"use client";

import { useEffect, useMemo } from "react";
import { useEntityStore, type EntityType } from "@/stores/entityStore";
import { DragItem } from "./DragItem";
import { Badge, statusVariant } from "@/components/shared/Badge";
import type {
  Task,
  Decision,
  Objective,
  Idea,
  Guideline,
  Knowledge,
  Lesson,
} from "@/lib/types";
import type { DragData, DragEntityType } from "@/lib/hooks/useDragDrop";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Entity groups to display in the palette. */
const PALETTE_GROUPS: Array<{
  type: EntityType;
  dragType: DragEntityType;
  label: string;
  icon: string;
}> = [
  { type: "tasks", dragType: "tasks", label: "Tasks", icon: "T" },
  { type: "decisions", dragType: "decisions", label: "Decisions", icon: "D" },
  { type: "objectives", dragType: "objectives", label: "Objectives", icon: "O" },
  { type: "ideas", dragType: "ideas", label: "Ideas", icon: "I" },
  { type: "guidelines", dragType: "guidelines", label: "Guidelines", icon: "G" },
  { type: "knowledge", dragType: "knowledge", label: "Knowledge", icon: "K" },
  { type: "lessons", dragType: "lessons", label: "Lessons", icon: "L" },
];

// ---------------------------------------------------------------------------
// Helpers — extract display info from entities
// ---------------------------------------------------------------------------

interface PaletteItem {
  id: string;
  label: string;
  status: string;
  type: string;
  dragData: DragData;
}

function toPaletteItem(
  entity: Task | Decision | Objective | Idea | Guideline | Knowledge | Lesson,
  dragType: DragEntityType,
): PaletteItem {
  const id = (entity as { id: string }).id;
  let label = id;
  let status = "";
  let type = "";

  if ("name" in entity && typeof entity.name === "string") {
    label = entity.name;
  } else if ("title" in entity && typeof entity.title === "string") {
    label = entity.title;
  } else if ("issue" in entity && typeof entity.issue === "string") {
    label = entity.issue;
  }

  if ("status" in entity && typeof entity.status === "string") {
    status = entity.status;
  }

  if ("type" in entity && typeof entity.type === "string") {
    type = entity.type;
  } else if ("category" in entity && typeof entity.category === "string") {
    type = entity.category;
  }

  return {
    id,
    label,
    status,
    type,
    dragData: { entityType: dragType, entityId: id, label },
  };
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface EntityPaletteProps {
  /** Current project slug. */
  slug: string;
  /** Called when a drag starts from the palette. */
  onDragStart?: (data: DragData) => void;
  /** Called when a drag ends. */
  onDragEnd?: () => void;
  /** Extra CSS classes for the sidebar. */
  className?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Sidebar palette showing draggable items grouped by entity type.
 *
 * Loads entities from the entityStore for the current project and
 * renders them as compact, draggable chips inside collapsible groups.
 */
export function EntityPalette({
  slug,
  onDragStart,
  onDragEnd,
  className = "",
}: EntityPaletteProps) {
  const { slices, fetchEntities } = useEntityStore();

  // Fetch all entity types on mount
  useEffect(() => {
    for (const group of PALETTE_GROUPS) {
      fetchEntities(slug, group.type);
    }
  }, [slug, fetchEntities]);

  // Build palette items grouped by type
  const groups = useMemo(() => {
    return PALETTE_GROUPS.map((group) => {
      const slice = slices[group.type];
      const items = (slice.items as Array<Task | Decision | Objective | Idea | Guideline | Knowledge | Lesson>)
        .map((entity) => toPaletteItem(entity, group.dragType));
      return {
        ...group,
        items,
        loading: slice.loading,
        count: slice.count,
      };
    });
  }, [slices]);

  return (
    <aside
      className={`w-64 bg-white border-r overflow-y-auto flex flex-col ${className}`}
      aria-label="Entity palette"
    >
      <div className="p-3 border-b">
        <h2 className="text-sm font-semibold text-gray-700">Entity Palette</h2>
        <p className="text-xs text-gray-400 mt-0.5">Drag items to create relationships</p>
      </div>

      <div className="flex-1 overflow-y-auto">
        {groups.map((group) => (
          <PaletteGroup
            key={group.type}
            label={group.label}
            icon={group.icon}
            items={group.items}
            loading={group.loading}
            count={group.count}
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
          />
        ))}
      </div>
    </aside>
  );
}

// ---------------------------------------------------------------------------
// PaletteGroup — collapsible section for one entity type
// ---------------------------------------------------------------------------

interface PaletteGroupProps {
  label: string;
  icon: string;
  items: PaletteItem[];
  loading: boolean;
  count: number;
  onDragStart?: (data: DragData) => void;
  onDragEnd?: () => void;
}

function PaletteGroup({
  label,
  icon,
  items,
  loading,
  count,
  onDragStart,
  onDragEnd,
}: PaletteGroupProps) {
  return (
    <details className="border-b" open>
      <summary className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-gray-50 select-none">
        <div className="flex items-center gap-2">
          <span className="w-5 h-5 rounded bg-forge-100 text-forge-700 text-[10px] font-bold flex items-center justify-center">
            {icon}
          </span>
          <span className="text-sm font-medium text-gray-700">{label}</span>
        </div>
        <span className="text-xs text-gray-400">
          {loading ? "..." : count}
        </span>
      </summary>

      <div className="px-2 pb-2 space-y-1">
        {loading && items.length === 0 && (
          <div className="text-xs text-gray-400 px-2 py-1">Loading...</div>
        )}
        {!loading && items.length === 0 && (
          <div className="text-xs text-gray-400 px-2 py-1">No items</div>
        )}
        {items.map((item) => (
          <DragItem
            key={item.id}
            data={item.dragData}
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
            className="block"
          >
            <div className="flex items-center gap-1.5 px-2 py-1.5 rounded border bg-white hover:border-forge-300 hover:shadow-sm transition-all text-xs">
              <span className="text-[10px] text-gray-400 font-mono shrink-0">
                {item.id}
              </span>
              <span className="truncate flex-1 text-gray-700" title={item.label}>
                {item.label}
              </span>
              {item.status && (
                <Badge variant={statusVariant(item.status)} className="text-[9px] px-1.5 py-0">
                  {item.status}
                </Badge>
              )}
            </div>
          </DragItem>
        ))}
      </div>
    </details>
  );
}
