"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ideas as ideasApi, objectives as objectivesApi } from "@/lib/api";
import { Badge, statusVariant } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import { ConfirmDeleteDialog } from "@/components/shared/ConfirmDeleteDialog";
import { EntityLink } from "@/components/shared/EntityLink";
import { useChatStore } from "@/stores/chatStore";
import { useSidebarStore } from "@/stores/sidebarStore";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import type { Idea, IdeaCategory, IdeaUpdate, Decision, Objective } from "@/lib/types";

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

  // Edit mode state
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editCategory, setEditCategory] = useState<Idea["category"]>("feature");
  const [editPriority, setEditPriority] = useState<"HIGH" | "MEDIUM" | "LOW">("MEDIUM");
  const [editTags, setEditTags] = useState<string[]>([]);
  const [editScopes, setEditScopes] = useState<string[]>([]);
  const [editAdvancesKR, setEditAdvancesKR] = useState<string[]>([]);
  const [editParentId, setEditParentId] = useState("");

  // Delete state
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

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

  const startEdit = () => {
    if (!idea) return;
    setEditTitle(idea.title);
    setEditDescription(idea.description || "");
    setEditCategory(idea.category);
    setEditPriority(idea.priority);
    setEditTags([...idea.tags]);
    setEditScopes([...(idea.scopes || [])]);
    setEditAdvancesKR([...(idea.advances_key_results || [])]);
    setEditParentId(idea.parent_id || "");
    setEditing(true);
  };

  const handleSave = async () => {
    if (!idea) return;
    setSaving(true);
    setError(null);
    try {
      const update: IdeaUpdate = {};
      if (editTitle !== idea.title) update.title = editTitle;
      if (editDescription !== (idea.description || "")) update.description = editDescription;
      if (editCategory !== idea.category) update.category = editCategory;
      if (editPriority !== idea.priority) update.priority = editPriority;
      if (JSON.stringify(editTags) !== JSON.stringify(idea.tags)) update.tags = editTags;
      if (JSON.stringify(editScopes) !== JSON.stringify(idea.scopes || [])) update.scopes = editScopes;
      if (JSON.stringify(editAdvancesKR) !== JSON.stringify(idea.advances_key_results || [])) update.advances_key_results = editAdvancesKR;
      if (editParentId !== (idea.parent_id || "")) update.parent_id = editParentId || undefined;
      if (Object.keys(update).length > 0) {
        const updated = await ideasApi.update(slug, idea.id, update);
        setIdea({ ...idea, ...updated });
      }
      setEditing(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!idea) return;
    setDeleting(true);
    try {
      await ideasApi.remove(slug, idea.id);
      router.push(`/projects/${slug}/ideas`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  const launchResearchSession = () => {
    useChatStore.getState().startConversation("idea", id, slug);
    useChatStore.getState().setPendingSessionMeta({
      sessionType: "chat",
      targetEntityType: "idea",
      targetEntityId: id,
    });
    useSidebarStore.getState().setActiveTab("chat");
  };

  // --- AI Annotations ---
  useAIPage({
    id: "idea-detail",
    title: idea ? `Idea ${idea.id} — ${idea.title}` : "Idea Detail (loading)",
    description: idea ? `${idea.category} — ${idea.status}` : "Loading...",
    route: `/projects/${slug}/ideas/${id}`,
  });

  useAIElement({
    id: "idea-entity",
    type: "display",
    label: idea ? `Idea ${idea.id}` : "Idea",
    description: idea ? `${idea.status} ${idea.category}` : undefined,
    data: idea ? {
      status: idea.status,
      category: idea.category,
      priority: idea.priority,
      parent_id: idea.parent_id,
      children_count: idea.children?.length ?? 0,
      advances_krs: idea.advances_key_results,
    } : undefined,
    actions: [
      { label: "Update idea", toolName: "updateIdea", toolParams: ["id*", "status", "exploration_notes", "relations"] },
      { label: "Commit idea", toolName: "commitIdea", toolParams: ["id*"], availableWhen: "status = APPROVED" },
    ],
  });

  if (loading) return <p className="text-sm text-gray-400">Loading idea...</p>;
  if (error && !idea) return <p className="text-sm text-red-600">{error}</p>;
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
          <div className="flex gap-2">
            {!editing && (
              <>
                <Button variant="secondary" size="sm" onClick={startEdit}>Edit</Button>
                {idea.status !== "COMMITTED" && (
                  <Button variant="danger" size="sm" onClick={() => setDeleteOpen(true)}>Delete</Button>
                )}
              </>
            )}
            <button
              onClick={launchResearchSession}
              className="px-3 py-1.5 text-xs font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700"
            >
              Research with AI
            </button>
            {!editing && transitions.map((t) => (
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
        </div>
        {idea.scopes?.length > 0 && (
          <div className="flex gap-1 mt-2">
            {idea.scopes.map((s) => (
              <span key={s} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{s}</span>
            ))}
          </div>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center justify-between bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-4">
          <p className="text-sm text-red-600">{error}</p>
          <button onClick={() => setError(null)} className="text-xs text-red-400 hover:text-red-600">Dismiss</button>
        </div>
      )}

      {editing ? (
        <div className="space-y-4 border rounded-lg p-5 bg-gray-50 mb-6">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Title *</label>
            <input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="w-full rounded-md border px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
            <textarea
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              rows={4}
              className="w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Category</label>
              <select
                value={editCategory}
                onChange={(e) => setEditCategory(e.target.value as IdeaCategory)}
                className="w-full rounded-md border px-3 py-1.5 text-sm"
              >
                {["feature", "improvement", "experiment", "migration", "refactor", "infrastructure", "business-opportunity", "research"].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Priority</label>
              <select
                value={editPriority}
                onChange={(e) => setEditPriority(e.target.value as "HIGH" | "MEDIUM" | "LOW")}
                className="w-full rounded-md border px-3 py-1.5 text-sm"
              >
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Parent Idea</label>
            <input
              value={editParentId}
              onChange={(e) => setEditParentId(e.target.value)}
              placeholder="I-001 (leave empty for no parent)"
              className="w-full rounded-md border px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Tags ({editTags.length})
            </label>
            {editTags.map((tag, i) => (
              <div key={i} className="flex items-center gap-2 mb-1">
                <input
                  value={tag}
                  onChange={(e) => { const next = [...editTags]; next[i] = e.target.value; setEditTags(next); }}
                  className="flex-1 rounded-md border px-2 py-1 text-xs"
                />
                <button
                  onClick={() => setEditTags(editTags.filter((_, j) => j !== i))}
                  className="text-xs text-red-400 hover:text-red-600"
                >
                  Remove
                </button>
              </div>
            ))}
            <button
              onClick={() => setEditTags([...editTags, ""])}
              className="text-xs text-forge-600 hover:underline mt-1"
            >
              + Add tag
            </button>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Scopes ({editScopes.length})
            </label>
            {editScopes.map((scope, i) => (
              <div key={i} className="flex items-center gap-2 mb-1">
                <input
                  value={scope}
                  onChange={(e) => { const next = [...editScopes]; next[i] = e.target.value; setEditScopes(next); }}
                  className="flex-1 rounded-md border px-2 py-1 text-xs"
                />
                <button
                  onClick={() => setEditScopes(editScopes.filter((_, j) => j !== i))}
                  className="text-xs text-red-400 hover:text-red-600"
                >
                  Remove
                </button>
              </div>
            ))}
            <button
              onClick={() => setEditScopes([...editScopes, ""])}
              className="text-xs text-forge-600 hover:underline mt-1"
            >
              + Add scope
            </button>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Advances Key Results ({editAdvancesKR.length})
            </label>
            {editAdvancesKR.map((kr, i) => (
              <div key={i} className="flex items-center gap-2 mb-1">
                <input
                  value={kr}
                  onChange={(e) => { const next = [...editAdvancesKR]; next[i] = e.target.value; setEditAdvancesKR(next); }}
                  placeholder="O-001/KR-1"
                  className="flex-1 rounded-md border px-2 py-1 text-xs"
                />
                <button
                  onClick={() => setEditAdvancesKR(editAdvancesKR.filter((_, j) => j !== i))}
                  className="text-xs text-red-400 hover:text-red-600"
                >
                  Remove
                </button>
              </div>
            ))}
            <button
              onClick={() => setEditAdvancesKR([...editAdvancesKR, ""])}
              className="text-xs text-forge-600 hover:underline mt-1"
            >
              + Add key result
            </button>
          </div>
          <div className="flex items-center gap-2 pt-2">
            <Button onClick={handleSave} disabled={saving} size="sm">
              {saving ? "Saving..." : "Save"}
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setEditing(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <>
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
        </>
      )}

      <ConfirmDeleteDialog
        open={deleteOpen}
        title={`Delete ${idea.id}?`}
        description="This action cannot be undone. The idea and all its data will be permanently removed."
        onConfirm={handleDelete}
        onCancel={() => setDeleteOpen(false)}
        loading={deleting}
      />
    </div>
  );
}
