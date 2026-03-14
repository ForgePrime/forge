"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { research as researchApi } from "@/lib/api";
import { Badge, statusVariant } from "@/components/shared/Badge";
import { EntityLink } from "@/components/shared/EntityLink";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Research } from "@/lib/types";

const STATUS_TRANSITIONS: Record<
  string,
  Array<{ label: string; target: string; className: string }>
> = {
  DRAFT: [
    {
      label: "Activate",
      target: "ACTIVE",
      className: "bg-green-600 hover:bg-green-700",
    },
    {
      label: "Archive",
      target: "ARCHIVED",
      className: "bg-gray-600 hover:bg-gray-700",
    },
  ],
  ACTIVE: [
    {
      label: "Supersede",
      target: "SUPERSEDED",
      className: "bg-yellow-600 hover:bg-yellow-700",
    },
    {
      label: "Archive",
      target: "ARCHIVED",
      className: "bg-gray-600 hover:bg-gray-700",
    },
  ],
};

export default function ResearchDetailPage() {
  const { slug, id } = useParams() as { slug: string; id: string };
  const router = useRouter();
  const [item, setItem] = useState<Research | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchItem = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await researchApi.get(slug, id);
      setItem(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [slug, id]);

  useEffect(() => {
    fetchItem();
  }, [fetchItem]);

  const handleStatusChange = async (target: string) => {
    try {
      const updated = await researchApi.update(slug, id, { status: target as Research["status"] });
      setItem(updated);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  // --- AI Annotations ---
  useAIPage({
    id: "research-detail",
    title: item ? `Research ${item.id} — ${item.title}` : "Research Detail (loading)",
    description: item ? `${item.category} — ${item.status}` : "Loading...",
    route: `/projects/${slug}/research/${id}`,
  });

  useAIElement({
    id: "research-entity",
    type: "display",
    label: item ? `Research ${item.id}` : "Research",
    description: item ? `${item.status} ${item.category}` : undefined,
    data: item
      ? {
          status: item.status,
          category: item.category,
          linked_entity: item.linked_entity_id,
          decision_count: item.decision_ids.length,
          findings_count: item.key_findings.length,
        }
      : undefined,
    actions: [
      {
        label: "Update status",
        toolName: "updateResearch",
        toolParams: ["research_id*", "status"],
      },
    ],
  });

  if (loading) return <p className="text-sm text-gray-400">Loading research...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!item) return <p className="text-sm text-gray-400">Research not found</p>;

  const transitions = STATUS_TRANSITIONS[item.status] ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <button
          onClick={() => router.back()}
          className="text-xs text-gray-400 hover:text-gray-600 mb-2"
        >
          &larr; Back
        </button>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">{item.id}</span>
          <Badge variant={statusVariant(item.status)}>{item.status}</Badge>
          <Badge>{item.category}</Badge>
          {item.skill && (
            <span className="text-xs text-gray-400">via {item.skill}</span>
          )}
        </div>
        <h1 className="text-xl font-semibold mt-1">{item.title}</h1>
        <p className="text-sm text-gray-500 mt-1">{item.topic}</p>
      </div>

      {/* Status actions */}
      {transitions.length > 0 && (
        <div className="flex gap-2">
          {transitions.map((t) => (
            <button
              key={t.target}
              onClick={() => handleStatusChange(t.target)}
              className={`px-3 py-1 text-xs text-white rounded ${t.className}`}
            >
              {t.label}
            </button>
          ))}
        </div>
      )}

      {/* Summary */}
      <div className="rounded-lg border bg-white p-4">
        <h2 className="text-sm font-semibold mb-2">Summary</h2>
        <p className="text-sm text-gray-700">{item.summary}</p>
      </div>

      {/* Key Findings */}
      {item.key_findings.length > 0 && (
        <div className="rounded-lg border bg-white p-4">
          <h2 className="text-sm font-semibold mb-2">
            Key Findings ({item.key_findings.length})
          </h2>
          <ul className="list-disc list-inside space-y-1">
            {item.key_findings.map((f, i) => (
              <li key={i} className="text-sm text-gray-700">
                {f}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Linked Entity */}
      {item.linked_entity_id && (
        <div className="rounded-lg border bg-white p-4">
          <h2 className="text-sm font-semibold mb-2">Linked Entity</h2>
          <EntityLink id={item.linked_entity_id} />
          {item.linked_idea_id && (
            <div className="mt-1">
              <EntityLink id={item.linked_idea_id} />
            </div>
          )}
        </div>
      )}

      {/* Linked Decisions */}
      {item.decision_ids.length > 0 && (
        <div className="rounded-lg border bg-white p-4">
          <h2 className="text-sm font-semibold mb-2">
            Decisions ({item.decision_ids.length})
          </h2>
          <div className="flex flex-wrap gap-2">
            {item.decision_ids.map((dId) => (
              <EntityLink key={dId} id={dId} />
            ))}
          </div>
        </div>
      )}

      {/* Content (rendered markdown) */}
      {item.content && (
        <div className="rounded-lg border bg-white p-4">
          <h2 className="text-sm font-semibold mb-2">Full Analysis</h2>
          <div className="prose prose-sm max-w-none text-gray-700">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.content}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* Metadata */}
      <div className="rounded-lg border bg-white p-4">
        <h2 className="text-sm font-semibold mb-2">Metadata</h2>
        <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
          {item.file_path && (
            <>
              <span>File Path</span>
              <span className="font-mono">{item.file_path}</span>
            </>
          )}
          <span>Created By</span>
          <span>{item.created_by}</span>
          {item.scopes.length > 0 && (
            <>
              <span>Scopes</span>
              <span>{item.scopes.join(", ")}</span>
            </>
          )}
        </div>
        {item.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {item.tags.map((t) => (
              <span
                key={t}
                className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded"
              >
                {t}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
