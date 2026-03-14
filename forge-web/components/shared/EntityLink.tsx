"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Badge, statusVariant } from "./Badge";
import {
  tasks as tasksApi,
  decisions as decisionsApi,
  objectives as objectivesApi,
  ideas as ideasApi,
  knowledge as knowledgeApi,
  guidelines as guidelinesApi,
  lessons as lessonsApi,
  research as researchApi,
} from "@/lib/api";

interface EntityLinkProps {
  id: string;
  showPreview?: boolean;
  className?: string;
  /** Override project slug (for pages without slug in URL, e.g. /sessions). */
  projectSlug?: string;
}

const ENTITY_MAP: Record<string, { type: string; route: string; color: string }> = {
  T: { type: "task", route: "tasks", color: "text-blue-600" },
  D: { type: "decision", route: "decisions", color: "text-purple-600" },
  K: { type: "knowledge", route: "knowledge", color: "text-teal-600" },
  O: { type: "objective", route: "objectives", color: "text-amber-600" },
  I: { type: "idea", route: "ideas", color: "text-green-600" },
  G: { type: "guideline", route: "guidelines", color: "text-gray-600" },
  L: { type: "lesson", route: "lessons", color: "text-rose-600" },
  R: { type: "research", route: "research", color: "text-indigo-600" },
};

function parseEntityId(id: string) {
  const prefix = id.split("-")[0];
  return ENTITY_MAP[prefix] || null;
}

// Simple entity cache to avoid refetching (bounded to prevent memory leaks)
const MAX_PREVIEW_CACHE = 200;
const previewCache = new Map<string, EntityPreviewData>();

interface EntityPreviewData {
  title: string;
  status?: string;
  type?: string;
  description?: string;
}

async function fetchPreview(slug: string, entityId: string): Promise<EntityPreviewData | null> {
  const cached = previewCache.get(`${slug}/${entityId}`);
  if (cached) return cached;

  const info = parseEntityId(entityId);
  if (!info) return null;

  try {
    let data: EntityPreviewData | null = null;
    switch (info.type) {
      case "task": {
        const t = await tasksApi.get(slug, entityId);
        data = { title: t.name, status: t.status, type: t.type, description: t.description };
        break;
      }
      case "decision": {
        const d = await decisionsApi.get(slug, entityId);
        data = { title: d.issue, status: d.status, type: d.type };
        break;
      }
      case "objective": {
        const o = await objectivesApi.get(slug, entityId);
        data = { title: o.title, status: o.status, description: o.description };
        break;
      }
      case "idea": {
        const i = await ideasApi.get(slug, entityId);
        data = { title: i.title, status: i.status, type: i.category };
        break;
      }
      case "knowledge": {
        const k = await knowledgeApi.get(slug, entityId);
        data = { title: k.title, status: k.status, type: k.category };
        break;
      }
      case "guideline": {
        const g = await guidelinesApi.get(slug, entityId);
        data = { title: g.title, status: g.status, type: g.weight };
        break;
      }
      case "lesson": {
        const l = await lessonsApi.get(slug, entityId);
        data = { title: l.title, type: l.category };
        break;
      }
      case "research": {
        const r = await researchApi.get(slug, entityId);
        data = { title: r.title, status: r.status, type: r.category, description: r.summary };
        break;
      }
    }
    if (data) {
      if (previewCache.size >= MAX_PREVIEW_CACHE) {
        // Evict oldest entry
        const firstKey = previewCache.keys().next().value;
        if (firstKey) previewCache.delete(firstKey);
      }
      previewCache.set(`${slug}/${entityId}`, data);
    }
    return data;
  } catch {
    return null;
  }
}

export function EntityLink({ id, showPreview = true, className, projectSlug }: EntityLinkProps) {
  const params = useParams() as { slug?: string };
  const slug = projectSlug || params.slug || "";
  const info = parseEntityId(id);
  const [preview, setPreview] = useState<EntityPreviewData | null>(null);
  const [showCard, setShowCard] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);

  const handleMouseEnter = useCallback(() => {
    if (!showPreview || !slug) return;
    timerRef.current = setTimeout(async () => {
      const data = await fetchPreview(slug, id);
      if (data) {
        setPreview(data);
        setShowCard(true);
      }
    }, 300);
  }, [showPreview, slug, id]);

  const handleMouseLeave = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setShowCard(false);
  }, []);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  if (!info || !slug) {
    return <span className={`font-mono text-xs ${className || ""}`}>{id}</span>;
  }

  return (
    <span className="relative inline-block" onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
      <Link
        href={`/projects/${slug}/${info.route}/${id}`}
        className={`font-mono text-xs ${info.color} hover:underline ${className || ""}`}
      >
        {id}
      </Link>
      {showCard && preview && (
        <div
          ref={cardRef}
          className="absolute z-50 left-0 top-full mt-1 w-64 rounded-lg border bg-white shadow-lg p-3 pointer-events-none"
        >
          <div className="flex items-center gap-1.5 mb-1">
            <span className={`text-[10px] font-semibold uppercase ${info.color}`}>{info.type}</span>
            {preview.status && (
              <Badge variant={statusVariant(preview.status)}>{preview.status}</Badge>
            )}
            {preview.type && <Badge>{preview.type}</Badge>}
          </div>
          <p className="text-xs font-medium text-gray-800 line-clamp-2">{preview.title}</p>
          {preview.description && (
            <p className="text-[10px] text-gray-500 mt-1 line-clamp-2">{preview.description}</p>
          )}
        </div>
      )}
    </span>
  );
}
