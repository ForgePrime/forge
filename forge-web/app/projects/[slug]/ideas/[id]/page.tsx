"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ideas as ideasApi, objectives as objectivesApi } from "@/lib/api";
import { Badge, statusVariant } from "@/components/shared/Badge";
import { EntityLink } from "@/components/shared/EntityLink";
import type { Idea, Decision, Objective } from "@/lib/types";

const STATUS_TRANSITIONS: Record<string, Array<{ label: string; target: string; className: string }>> = {
  DRAFT: [
    { label: "Start Exploring", target: "EXPLORING", className: "bg-blue-600 hover:bg-blue-700" },
  ],
  EXPLORING: [
    { label: "Approve", target: "APPROVED", className: "bg-green-600 hover:bg-green-700" },
    { label: "Reject", target: "REJECTED", className: "bg-red-600 hover:bg-red-700" },
  ],
  APPROVED: [
    { label: "Commit", target: "COMMITTED", className: "bg-forge-600 hover:bg-forge-700" },
  ],
};

export default function IdeaDetailPage() {
  const { slug, id } = useParams() as { slug: string; id: string };
  const router = useRouter();
  const [idea, setIdea] = useState<(Idea & { children?: Idea[]; related_decisions?: Decision[] }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [linkedObjectives, setLinkedObjectives] = useState<Objective[]>([]);
  const [statusUpdating, setStatusUpdating] = useState(false);

  const fetchIdea = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await ideasApi.get(slug, id);
      setIdea(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [slug, id]);

  useEffect(() => {
    fetchIdea();
  }, [fetchIdea]);

  // Fetch linked objectives for KR progress display
  useEffect(() => {
    if (!idea || !idea.advances_key_results?.length) return;
    const fetchObjectives = async () => {
      try {
        // Extract unique objective IDs from "O-001/KR-1" format
        const objIds = Array.from(new Set(
          idea.advances_key_results.map((akr) => akr.split("/")[0])
        ));
        const objs = await Promise.all(
          objIds.map((oid) => objectivesApi.get(slug, oid).catch(() => null))
        );
        setLinkedObjectives(objs.filter((o): o is Objective => o !== null));
      } catch {
        // Silent fail
      }
    };
    fetchObjectives();
  }, [idea, slug]);

  const handleStatusChange = async (targetStatus: string) => {
    if (!idea) return;
    setStatusUpdating(true);
    try {
      if (targetStatus === "COMMITTED") {
        await ideasApi.commit(slug, id);
      } else {
        await ideasApi.update(slug, id, { status: targetStatus as Idea["status"] });
      }
      await fetchIdea();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setStatusUpdating(false);
    }
  };

  if (loading) return <p className="text-sm text-gray-400">Loading idea...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!idea) return <p className="text-sm text-gray-400">Idea not found</p>;

  const transitions = STATUS_TRANSITIONS[idea.status] || [];
  const explorations = (idea.related_decisions || []).filter((d) => d.type === "exploration");
  const risks = (idea.related_decisions || []).filter((d) => d.type === "risk");

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <button onClick={() => router.back()} className="text-xs text-gray-400 hover:text-gray-600 mb-2">
          &larr; Back
        </button>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm text-gray-400 font-mono">{idea.id}</span>
              <Badge variant={statusVariant(idea.status)}>{idea.status}</Badge>
              <Badge>{idea.category}</Badge>
              <Badge variant={idea.priority === "HIGH" ? "danger" : idea.priority === "LOW" ? "default" : "warning"}>
                {idea.priority}
              </Badge>
            </div>
            <h1 className="text-xl font-bold">{idea.title}</h1>
            {idea.parent_id && (
              <Link
                href={`/projects/${slug}/ideas/${idea.parent_id}`}
                className="text-xs text-forge-600 hover:underline"
              >
                Parent: {idea.parent_id}
              </Link>
            )}
          </div>
          {transitions.length > 0 && (
            <div className="flex gap-2">
              {transitions.map((t) => (
                <button
                  key={t.target}
                  onClick={() => handleStatusChange(t.target)}
                  disabled={statusUpdating}
                  className={`px-3 py-1.5 text-xs text-white rounded-md disabled:opacity-50 ${t.className}`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          )}
        </div>
        {idea.scopes?.length > 0 && (
          <div className="flex gap-1 mt-2">
            {idea.scopes.map((s) => (
              <span key={s} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{s}</span>
            ))}
          </div>
        )}
      </div>

      {/* Description */}
      {idea.description && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Description</h3>
          <p className="text-sm text-gray-600 whitespace-pre-wrap">{idea.description}</p>
        </section>
      )}

      {/* Linked KRs with Objective Progress */}
      {linkedObjectives.length > 0 && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Advances Key Results</h3>
          <div className="space-y-2">
            {linkedObjectives.map((obj) => (
              <div key={obj.id} className="rounded-lg border bg-white p-3">
                <Link
                  href={`/projects/${slug}/objectives/${obj.id}`}
                  className="text-xs text-forge-600 hover:underline font-mono"
                >
                  {obj.id}
                </Link>
                <span className="text-sm text-gray-700 ml-2">{obj.title}</span>
                <div className="mt-2 space-y-1">
                  {obj.key_results
                    .filter((_, krIdx) =>
                      idea.advances_key_results?.includes(`${obj.id}/KR-${krIdx + 1}`)
                    )
                    .map((kr, krIdx) => {
                      const baseline = kr.baseline ?? 0;
                      const span = (kr.target ?? 0) - baseline;
                      const pct = span !== 0 ? Math.min(100, Math.max(0, Math.round(((kr.current ?? baseline) - baseline) / span * 100))) : 0;
                      return (
                        <div key={krIdx} className="flex items-center gap-2 text-xs">
                          <span className="text-gray-500 flex-1 truncate">{kr.metric}</span>
                          <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div className="h-full bg-forge-500 rounded-full" style={{ width: `${Math.min(100, pct)}%` }} />
                          </div>
                          <span className="text-gray-400 w-8 text-right">{pct}%</span>
                        </div>
                      );
                    })}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Child Ideas */}
      {idea.children && idea.children.length > 0 && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Child Ideas ({idea.children.length})
          </h3>
          <div className="space-y-2">
            {idea.children.map((child) => (
              <Link
                key={child.id}
                href={`/projects/${slug}/ideas/${child.id}`}
                className="block rounded-lg border bg-white p-3 hover:border-forge-300 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 font-mono">{child.id}</span>
                  <Badge variant={statusVariant(child.status)}>{child.status}</Badge>
                  <Badge>{child.category}</Badge>
                  <span className="text-sm text-gray-700">{child.title}</span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Explorations */}
      {explorations.length > 0 && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Explorations ({explorations.length})
          </h3>
          <div className="space-y-2">
            {explorations.map((d) => (
              <Link
                key={d.id}
                href={`/projects/${slug}/decisions/${d.id}`}
                className="block rounded-lg border border-blue-200 bg-blue-50 p-3 hover:border-blue-300 transition-colors"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-gray-400 font-mono">{d.id}</span>
                  <Badge variant={statusVariant(d.status)}>{d.status}</Badge>
                  {d.exploration_type && <Badge variant="info">{d.exploration_type}</Badge>}
                </div>
                <p className="text-sm text-gray-700">{d.issue}</p>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Risks */}
      {risks.length > 0 && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Risks ({risks.length})
          </h3>
          <div className="space-y-2">
            {risks.map((d) => (
              <Link
                key={d.id}
                href={`/projects/${slug}/decisions/${d.id}`}
                className="block rounded-lg border border-red-200 bg-red-50 p-3 hover:border-red-300 transition-colors"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-gray-400 font-mono">{d.id}</span>
                  <Badge variant={statusVariant(d.status)}>{d.status}</Badge>
                  {d.severity && <Badge variant="danger">{d.severity}</Badge>}
                  {d.likelihood && <Badge variant="warning">{d.likelihood}</Badge>}
                </div>
                <p className="text-sm text-gray-700">{d.issue}</p>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Relations */}
      {idea.relations?.length > 0 && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Relations ({idea.relations.length})
          </h3>
          <div className="space-y-1">
            {idea.relations.map((rel, i) => {
              const relType = String(rel.type || "related");
              const targetId = rel.target_id ? String(rel.target_id) : null;
              return (
                <div key={i} className="flex items-center gap-2 text-sm text-gray-600">
                  <Badge>{relType}</Badge>
                  {targetId && <EntityLink id={targetId} />}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Tags */}
      {idea.tags?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-4">
          {idea.tags.map((t) => (
            <span key={t} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{t}</span>
          ))}
        </div>
      )}
    </div>
  );
}
