"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { objectiveUpdateSchema, type ObjectiveUpdateForm } from "@/lib/schemas/objective";
import { objectives as objectivesApi, ideas as ideasApi, guidelines as guidelinesApi, knowledge as knowledgeApi, tasks as tasksApi } from "@/lib/api";
import { Badge, statusVariant } from "@/components/shared/Badge";
import { ConfirmDeleteDialog } from "@/components/shared/ConfirmDeleteDialog";
import { TextField } from "@/components/forms/TextField";
import { TextAreaField } from "@/components/forms/TextAreaField";
import { SelectField } from "@/components/forms/SelectField";
import { DynamicListField } from "@/components/forms/DynamicListField";
import { useChatStore } from "@/stores/chatStore";
import { useSidebarStore } from "@/stores/sidebarStore";
import { useToastStore } from "@/stores/toastStore";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import type { Objective, Idea, Guideline, Task, KeyResult, ObjectiveRelation, ObjectiveStatus, ObjectiveUpdate } from "@/lib/types";

const APPETITE_OPTIONS = [
  { value: "small", label: "Small (days)" },
  { value: "medium", label: "Medium (weeks)" },
  { value: "large", label: "Large (months)" },
];

const KR_STATUS_OPTIONS = ["NOT_STARTED", "IN_PROGRESS", "ACHIEVED"] as const;

/* ---------- Status transition logic ---------- */
interface ActionItem {
  label: string;
  action: string;
  destructive?: boolean;
  targetStatus?: ObjectiveStatus;
}

function getAvailableActions(status: ObjectiveStatus): ActionItem[] {
  const actions: ActionItem[] = [
    { label: "Update KR Progress", action: "update_kr" },
  ];

  switch (status) {
    case "ACTIVE":
      actions.push(
        { label: "Pause", action: "status", targetStatus: "PAUSED" },
        { label: "Mark as Achieved", action: "status", targetStatus: "ACHIEVED", destructive: true },
        { label: "Mark as Abandoned", action: "status", targetStatus: "ABANDONED", destructive: true },
      );
      break;
    case "PAUSED":
      actions.push(
        { label: "Resume", action: "status", targetStatus: "ACTIVE" },
        { label: "Mark as Achieved", action: "status", targetStatus: "ACHIEVED", destructive: true },
        { label: "Mark as Abandoned", action: "status", targetStatus: "ABANDONED", destructive: true },
      );
      break;
    // ACHIEVED / ABANDONED are terminal — no status transitions
  }

  return actions;
}
const KR_STATUS_COLORS: Record<string, string> = {
  NOT_STARTED: "bg-gray-100 text-gray-600",
  IN_PROGRESS: "bg-blue-100 text-blue-700",
  ACHIEVED: "bg-green-100 text-green-700",
};
const RELATION_TYPE_COLORS: Record<string, string> = {
  depends_on: "bg-blue-100 text-blue-700",
  related_to: "bg-gray-100 text-gray-600",
  supersedes: "bg-orange-100 text-orange-700",
  duplicates: "bg-red-100 text-red-700",
};

export default function ObjectiveDetailPage() {
  const { slug, id } = useParams() as { slug: string; id: string };
  const router = useRouter();
  const [objective, setObjective] = useState<Objective | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Related data
  const [linkedIdeas, setLinkedIdeas] = useState<Idea[]>([]);
  const [derivedGuidelines, setDerivedGuidelines] = useState<Guideline[]>([]);
  const [scopeGuidelines, setScopeGuidelines] = useState<Guideline[]>([]);
  const [assignedGuidelines, setAssignedGuidelines] = useState<Guideline[]>([]);
  const [allObjectives, setAllObjectives] = useState<Objective[]>([]);
  const [allKnowledge, setAllKnowledge] = useState<any[]>([]);
  const [linkedTasks, setLinkedTasks] = useState<Task[]>([]);

  // Inline KR edit state
  const [editingKR, setEditingKR] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const [saving, setSaving] = useState(false);

  // Full edit mode state
  const [editing, setEditing] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const editForm = useForm<ObjectiveUpdateForm>({
    resolver: zodResolver(objectiveUpdateSchema),
  });

  // Delete state
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Actions menu state
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<ActionItem | null>(null);
  const [statusSaving, setStatusSaving] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const fetchObjective = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await objectivesApi.get(slug, id);
      setObjective(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [slug, id]);

  useEffect(() => {
    fetchObjective();
  }, [fetchObjective]);

  // Fetch related data
  useEffect(() => {
    if (!objective) return;
    const fetchRelated = async () => {
      try {
        // Ideas advancing this objective's KRs
        const ideaRes = await ideasApi.list(slug);
        const matchedIdeas = ideaRes.ideas.filter((idea) =>
          idea.advances_key_results.some((akr) => akr.startsWith(id))
        );
        setLinkedIdeas(matchedIdeas);

        // Tasks originated from this objective or its linked ideas
        const taskRes = await tasksApi.list(slug);
        const ideaIds = new Set(matchedIdeas.map((i) => i.id));
        setLinkedTasks(
          taskRes.tasks.filter((t) =>
            t.origin === id || (t.origin && ideaIds.has(t.origin))
          )
        );

        // Guidelines
        const glRes = await guidelinesApi.list(slug);
        const allGls = glRes.guidelines || [];

        // Derived guidelines
        setDerivedGuidelines(allGls.filter((g) => {
          const gAny = g as unknown as { derived_from?: string };
          return gAny.derived_from === id;
        }));

        // Scope-based guidelines
        const objScopes = new Set(objective.scopes || []);
        setScopeGuidelines(allGls.filter((g) =>
          g.status === "ACTIVE" && objScopes.has(g.scope)
        ));

        // Explicitly assigned guidelines
        const assignedIds = new Set(objective.guideline_ids || []);
        setAssignedGuidelines(allGls.filter((g) => assignedIds.has(g.id)));

        // Objectives for relation display
        const objRes = await objectivesApi.list(slug);
        setAllObjectives(objRes.objectives || []);

        // Knowledge objects
        const kRes = await knowledgeApi.list(slug);
        setAllKnowledge(kRes.knowledge || []);
      } catch {
        // Silent fail for related data
      }
    };
    fetchRelated();
  }, [objective, slug, id]);

  const handleKRSave = async (krIndex: number) => {
    if (!objective) return;
    setSaving(true);
    try {
      const kr = objective.key_results[krIndex];
      const updatedKRs = objective.key_results.map((k, i) => {
        if (i !== krIndex) return k;
        if (k.metric) {
          return { ...k, current: parseFloat(editValue) || 0 };
        }
        return { ...k, status: editValue as any };
      });
      await objectivesApi.update(slug, id, { key_results: updatedKRs });
      setObjective({ ...objective, key_results: updatedKRs });
      setEditingKR(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const getObjectiveTitle = (objId: string) => {
    const obj = allObjectives.find((o) => o.id === objId);
    return obj ? obj.title : objId;
  };

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  const handleAction = (item: ActionItem) => {
    setMenuOpen(false);
    if (item.action === "update_kr") {
      // Activate edit on first KR
      if (objective && objective.key_results.length > 0) {
        const kr = objective.key_results[0];
        setEditingKR(0);
        setEditValue(kr.metric ? String(kr.current ?? 0) : kr.status || "NOT_STARTED");
      }
      return;
    }
    if (item.action === "status" && item.targetStatus) {
      if (item.destructive) {
        setConfirmAction(item);
      } else {
        executeStatusChange(item.targetStatus);
      }
    }
  };

  const executeStatusChange = async (newStatus: ObjectiveStatus) => {
    if (!objective) return;
    setStatusSaving(true);
    try {
      await objectivesApi.update(slug, id, { status: newStatus });
      await fetchObjective();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setStatusSaving(false);
      setConfirmAction(null);
    }
  };

  const launchPlanSession = () => {
    useChatStore.getState().startConversation("objective", id, slug);
    useChatStore.getState().setPendingSessionMeta({
      sessionType: "plan",
      targetEntityType: "objective",
      targetEntityId: id,
    });
    useSidebarStore.getState().setActiveTab("chat");
  };

  // Full edit mode
  const startEdit = () => {
    if (!objective) return;
    editForm.reset({
      title: objective.title,
      description: objective.description || "",
      appetite: objective.appetite,
      scopes: [...objective.scopes],
      tags: [...objective.tags],
      assumptions: [...objective.assumptions],
      guideline_ids: [...(objective.guideline_ids || [])],
    });
    setEditing(true);
  };

  const handleEditSave = editForm.handleSubmit(async (data) => {
    if (!objective) return;
    setEditSaving(true);
    setError(null);
    try {
      const update: ObjectiveUpdate = {};
      if (data.title && data.title !== objective.title) update.title = data.title;
      if (data.description !== undefined && data.description !== (objective.description || "")) update.description = data.description;
      if (data.appetite && data.appetite !== objective.appetite) update.appetite = data.appetite;
      if (data.scopes && JSON.stringify(data.scopes) !== JSON.stringify(objective.scopes)) update.scopes = data.scopes;
      if (data.tags && JSON.stringify(data.tags) !== JSON.stringify(objective.tags)) update.tags = data.tags;
      if (data.assumptions && JSON.stringify(data.assumptions) !== JSON.stringify(objective.assumptions)) update.assumptions = data.assumptions;
      if (data.guideline_ids && JSON.stringify(data.guideline_ids) !== JSON.stringify(objective.guideline_ids || [])) update.guideline_ids = data.guideline_ids;

      if (Object.keys(update).length > 0) {
        const updated = await objectivesApi.update(slug, id, update);
        setObjective(updated);
      }
      setEditing(false);
      useToastStore.getState().addToast({ message: `${objective.id} updated`, entityId: objective.id, entityType: "objective", action: "updated" });
    } catch (e) {
      setError((e as Error).message);
      useToastStore.getState().addToast({ message: `Failed to update ${objective.id}`, action: "failed" });
    } finally {
      setEditSaving(false);
    }
  });

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await objectivesApi.remove(slug, id);
      router.push(`/projects/${slug}/objectives`);
    } catch (e) {
      setError((e as Error).message);
      setDeleting(false);
      setDeleteOpen(false);
    }
  };

  // --- AI Annotations ---
  useAIPage({
    id: "objective-detail",
    title: objective ? `Objective ${objective.id} — ${objective.title}` : "Objective Detail (loading)",
    description: objective ? `${objective.status}, ${objective.key_results?.length ?? 0} KRs` : "Loading...",
    route: `/projects/${slug}/objectives/${id}`,
  });

  useAIElement({
    id: "objective-entity",
    type: "display",
    label: objective ? `Objective ${objective.id}` : "Objective",
    description: objective ? `${objective.status} objective` : undefined,
    data: objective ? {
      status: objective.status,
      appetite: objective.appetite,
      key_results_count: objective.key_results?.length ?? 0,
      linked_ideas: linkedIdeas.length,
      derived_guidelines: derivedGuidelines.length,
    } : undefined,
    actions: [
      { label: "Update status", toolName: "updateObjective", toolParams: ["id*", "status"], availableWhen: "status = ACTIVE or PAUSED" },
      { label: "Update KR progress", toolName: "updateObjective", toolParams: ["id*", "key_results"] },
    ],
  });

  if (loading) return <p className="text-sm text-gray-400">Loading objective...</p>;
  if (error && !objective) return <p className="text-sm text-red-600">{error}</p>;
  if (!objective) return <p className="text-sm text-gray-400">Objective not found</p>;

  const knowledgeIds = objective.knowledge_ids || [];

  return (
    <div>
      {/* Confirmation Dialog for status change */}
      {confirmAction && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-sm w-full mx-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-2">
              {confirmAction.label}?
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              {confirmAction.targetStatus === "ACHIEVED"
                ? "This will mark the objective as achieved. Derived guidelines should be reviewed."
                : "This will mark the objective as abandoned. Derived guidelines should be reviewed."}
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setConfirmAction(null)}
                className="px-3 py-1.5 text-xs text-gray-600 border rounded hover:bg-gray-50"
                disabled={statusSaving}
              >
                Cancel
              </button>
              <button
                onClick={() => executeStatusChange(confirmAction.targetStatus!)}
                className={`px-3 py-1.5 text-xs text-white rounded disabled:opacity-50 ${
                  confirmAction.targetStatus === "ABANDONED"
                    ? "bg-red-600 hover:bg-red-700"
                    : "bg-green-600 hover:bg-green-700"
                }`}
                disabled={statusSaving}
              >
                {statusSaving ? "Saving..." : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirmation */}
      <ConfirmDeleteDialog
        open={deleteOpen}
        title={`Delete ${objective.id}?`}
        description="This will permanently remove this objective and cannot be undone."
        onConfirm={handleDelete}
        onCancel={() => setDeleteOpen(false)}
        loading={deleting}
      />

      {/* Header */}
      <div className="mb-6">
        <button onClick={() => router.back()} className="text-xs text-gray-400 hover:text-gray-600 mb-2">
          &larr; Back
        </button>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400 font-mono">{objective.id}</span>
            <Badge variant={statusVariant(objective.status)}>{objective.status}</Badge>
            <Badge>{objective.appetite}</Badge>
            <Badge variant="info">{objective.scope}</Badge>
          </div>

          <div className="flex items-center gap-2">
          {/* Edit / Delete buttons (only in read mode) */}
          {!editing && (
            <>
              <button
                onClick={startEdit}
                className="px-3 py-1.5 text-xs font-medium text-forge-700 border border-forge-300 rounded hover:bg-forge-50"
              >
                Edit
              </button>
              <button
                onClick={() => setDeleteOpen(true)}
                className="px-3 py-1.5 text-xs font-medium text-red-600 border border-red-300 rounded hover:bg-red-50"
              >
                Delete
              </button>
            </>
          )}

          {/* AI session launch */}
          <button
            onClick={launchPlanSession}
            className="px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
          >
            Plan with AI
          </button>

          {/* Actions dropdown */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-gray-700 border rounded-md hover:bg-gray-50"
            >
              Actions
              <svg className="w-3 h-3" viewBox="0 0 12 12" fill="none">
                <path d="M3 5l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
            </button>
            {menuOpen && (
              <div className="absolute right-0 mt-1 w-48 bg-white border rounded-md shadow-lg z-30 py-1">
                {getAvailableActions(objective.status).map((item) => (
                  <button
                    key={item.label}
                    onClick={() => handleAction(item)}
                    className={`w-full text-left px-3 py-1.5 text-xs hover:bg-gray-50 ${
                      item.destructive ? "text-red-600 hover:bg-red-50" : "text-gray-700"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            )}
          </div>
          </div>
        </div>

        {/* Error banner */}
        {error && (
          <div className="flex items-center justify-between bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-4">
            <p className="text-sm text-red-600">{error}</p>
            <button onClick={() => setError(null)} className="text-xs text-red-400 hover:text-red-600">Dismiss</button>
          </div>
        )}

        {editing ? (
          /* ===== Full Edit mode (react-hook-form + zod) ===== */
          <form onSubmit={handleEditSave} className="border rounded-lg p-5 bg-gray-50 mt-4">
            <TextField name="title" control={editForm.control} label="Title" required />
            <TextAreaField name="description" control={editForm.control} label="Description" />
            <SelectField name="appetite" control={editForm.control} label="Appetite" options={APPETITE_OPTIONS} />
            <DynamicListField name="scopes" control={editForm.control} label="Scopes" addLabel="Add scope" placeholder="e.g., backend" />
            <DynamicListField name="tags" control={editForm.control} label="Tags" addLabel="Add tag" placeholder="e.g., performance" />
            <DynamicListField name="assumptions" control={editForm.control} label="Assumptions" addLabel="Add assumption" placeholder="What must hold true?" />
            <DynamicListField name="guideline_ids" control={editForm.control} label="Guideline IDs" addLabel="Add guideline ID" placeholder="G-001" />

            <div className="flex items-center gap-2 pt-2">
              <button
                type="submit"
                disabled={editSaving}
                className="px-4 py-1.5 text-sm font-medium text-white bg-forge-600 rounded hover:bg-forge-700 disabled:opacity-50"
              >
                {editSaving ? "Saving..." : "Save"}
              </button>
              <button
                type="button"
                onClick={() => setEditing(false)}
                className="px-4 py-1.5 text-sm text-gray-600 border rounded hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        ) : (
          /* ===== Read mode ===== */
          <>
            <h1 className="text-xl font-bold">{objective.title}</h1>
            {objective.description && (
              <p className="text-sm text-gray-600 mt-2">{objective.description}</p>
            )}
            {objective.scopes.length > 0 && (
              <div className="flex gap-1 mt-2">
                {objective.scopes.map((s) => (
                  <span key={s} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{s}</span>
                ))}
              </div>
            )}
            {objective.tags.length > 0 && (
              <div className="flex gap-1 mt-2">
                {objective.tags.map((t) => (
                  <span key={t} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{t}</span>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Key Results — always visible (KR inline editing is a separate feature) */}
      <section className="mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          Key Results ({objective.key_results.length})
        </h3>
        <div className="space-y-3">
          {objective.key_results.map((kr, i) => (
            kr.metric ? (
              <NumericKRCard
                key={i}
                kr={kr}
                index={i}
                editing={editingKR === i}
                editValue={editValue}
                saving={saving}
                onStartEdit={() => { setEditingKR(i); setEditValue(String(kr.current ?? 0)); }}
                onCancelEdit={() => setEditingKR(null)}
                onSave={() => handleKRSave(i)}
                onValueChange={setEditValue}
              />
            ) : (
              <DescriptiveKRCard
                key={i}
                kr={kr}
                index={i}
                editing={editingKR === i}
                editValue={editValue}
                saving={saving}
                onStartEdit={() => { setEditingKR(i); setEditValue(kr.status || "NOT_STARTED"); }}
                onCancelEdit={() => setEditingKR(null)}
                onSave={() => handleKRSave(i)}
                onValueChange={setEditValue}
              />
            )
          ))}
        </div>
      </section>

      {/* Applied Guidelines */}
      {(scopeGuidelines.length > 0 || assignedGuidelines.length > 0) && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Applied Guidelines ({scopeGuidelines.length + assignedGuidelines.length})
          </h3>
          {scopeGuidelines.length > 0 && (
            <div className="mb-3">
              <p className="text-[10px] text-gray-400 uppercase tracking-wide mb-1">From scopes ({scopeGuidelines.length})</p>
              <div className="space-y-1">
                {scopeGuidelines.map((g) => (
                  <Link key={g.id} href={`/projects/${slug}/guidelines`} className="flex items-center gap-2 p-2 rounded border bg-white text-xs hover:border-forge-300 transition-colors">
                    <span className="font-mono text-forge-600">{g.id}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      g.weight === "must" ? "bg-red-100 text-red-700" :
                      g.weight === "should" ? "bg-yellow-100 text-yellow-700" :
                      "bg-gray-100 text-gray-600"
                    }`}>{g.weight}</span>
                    <span className="text-gray-700 truncate">{g.title || g.content?.slice(0, 60)}</span>
                  </Link>
                ))}
              </div>
            </div>
          )}
          {assignedGuidelines.length > 0 && (
            <div>
              <p className="text-[10px] text-gray-400 uppercase tracking-wide mb-1">Explicitly assigned ({assignedGuidelines.length})</p>
              <div className="space-y-1">
                {assignedGuidelines.map((g) => (
                  <Link key={g.id} href={`/projects/${slug}/guidelines`} className="flex items-center gap-2 p-2 rounded border bg-forge-50 border-forge-200 text-xs hover:border-forge-300 transition-colors">
                    <span className="font-mono text-forge-600">{g.id}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      g.weight === "must" ? "bg-red-100 text-red-700" :
                      g.weight === "should" ? "bg-yellow-100 text-yellow-700" :
                      "bg-gray-100 text-gray-600"
                    }`}>{g.weight}</span>
                    <span className="text-gray-700 truncate">{g.title || g.content?.slice(0, 60)}</span>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* Relations */}
      {objective.relations && objective.relations.length > 0 && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Relations ({objective.relations.length})
          </h3>
          <div className="space-y-2">
            {objective.relations.map((rel, i) => (
              <div key={i} className="flex items-center gap-2 p-2 rounded border bg-white text-xs">
                <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                  RELATION_TYPE_COLORS[rel.type] || "bg-gray-100 text-gray-600"
                }`}>{rel.type}</span>
                <span className="text-gray-400">→</span>
                <Link
                  href={`/projects/${slug}/objectives/${rel.target_id}`}
                  className="text-forge-600 hover:text-forge-800 font-medium"
                >
                  {rel.target_id}: {getObjectiveTitle(rel.target_id)?.slice(0, 40)}
                </Link>
                {rel.notes && <span className="text-gray-400 italic ml-2">{rel.notes}</span>}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Knowledge */}
      {knowledgeIds.length > 0 && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Knowledge ({knowledgeIds.length})
          </h3>
          <div className="flex flex-wrap gap-2">
            {knowledgeIds.map((kId: string) => {
              const k = allKnowledge.find((kn: any) => kn.id === kId);
              return (
                <Link
                  key={kId}
                  href={`/projects/${slug}/knowledge/${kId}`}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded border bg-white text-xs hover:border-forge-300"
                >
                  <span className="font-mono text-gray-400">{kId}</span>
                  {k && <span className="text-gray-600">{k.title?.slice(0, 30)}</span>}
                </Link>
              );
            })}
          </div>
        </section>
      )}

      {/* Linked Ideas */}
      {linkedIdeas.length > 0 && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Linked Ideas ({linkedIdeas.length})
          </h3>
          <div className="space-y-2">
            {linkedIdeas.map((idea) => (
              <Link
                key={idea.id}
                href={`/projects/${slug}/ideas/${idea.id}`}
                className="block rounded-lg border bg-white p-3 hover:border-forge-300 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 font-mono">{idea.id}</span>
                  <Badge variant={statusVariant(idea.status)}>{idea.status}</Badge>
                  <Badge>{idea.category}</Badge>
                  <span className="text-sm text-gray-700">{idea.title}</span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Derived Guidelines */}
      {derivedGuidelines.length > 0 && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Derived Guidelines ({derivedGuidelines.length})
          </h3>
          <div className="space-y-2">
            {derivedGuidelines.map((g) => (
              <Link
                key={g.id}
                href={`/projects/${slug}/guidelines`}
                className="block rounded-lg border bg-white p-3 hover:border-forge-300 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs text-forge-600 font-mono">{g.id}</span>
                  <Badge>{g.weight}</Badge>
                  <Badge>{g.scope}</Badge>
                </div>
                <p className="text-sm text-gray-700 mt-1">{g.content}</p>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Linked Tasks */}
      {linkedTasks.length > 0 && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Tasks ({linkedTasks.length})
          </h3>
          <div className="space-y-2">
            {linkedTasks.map((task) => (
              <Link
                key={task.id}
                href={`/projects/${slug}/execution/${task.id}`}
                className="block rounded-lg border bg-white p-3 hover:border-forge-300 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 font-mono">{task.id}</span>
                  <Badge variant={statusVariant(task.status)}>{task.status}</Badge>
                  <Badge>{task.type}</Badge>
                  <span className="text-sm text-gray-700 truncate">{task.name}</span>
                </div>
                {task.origin && (
                  <span className="text-[10px] text-gray-400 mt-1 block">
                    Origin: {task.origin}
                  </span>
                )}
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Assumptions */}
      {!editing && objective.assumptions.length > 0 && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Assumptions ({objective.assumptions.length})
          </h3>
          <ul className="space-y-1">
            {objective.assumptions.map((a, i) => (
              <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                <span className="text-gray-400 shrink-0">-</span>
                <span>{a}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

/* Numeric KR with progress bar */
function NumericKRCard({
  kr, index, editing, editValue, saving,
  onStartEdit, onCancelEdit, onSave, onValueChange,
}: {
  kr: KeyResult; index: number; editing: boolean; editValue: string;
  saving: boolean; onStartEdit: () => void; onCancelEdit: () => void;
  onSave: () => void; onValueChange: (v: string) => void;
}) {
  const baseline = kr.baseline ?? 0;
  const target = kr.target ?? 0;
  const span = target - baseline;
  const current = kr.current ?? baseline;
  const pct = span !== 0 ? Math.min(100, Math.max(0, Math.round((current - baseline) / span * 100))) : 0;

  return (
    <div className="rounded-lg border bg-white p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">
          KR-{index + 1}: {kr.metric}
        </span>
        <div className="flex items-center gap-2">
          {editing ? (
            <>
              <input
                type="number"
                value={editValue}
                onChange={(e) => onValueChange(e.target.value)}
                className="w-20 text-xs border rounded px-2 py-1"
                autoFocus
              />
              <button onClick={onSave} disabled={saving}
                className="text-xs text-forge-600 hover:text-forge-700 font-medium disabled:opacity-50">Save</button>
              <button onClick={onCancelEdit} className="text-xs text-gray-400 hover:text-gray-600">Cancel</button>
            </>
          ) : (
            <>
              <span className="text-xs text-gray-500">{current} / {target}</span>
              <button onClick={onStartEdit} className="text-xs text-gray-400 hover:text-forge-600">Edit</button>
            </>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              pct >= 100 ? "bg-green-500" : pct >= 50 ? "bg-forge-500" : "bg-amber-500"
            }`}
            style={{ width: `${Math.min(100, pct)}%` }}
          />
        </div>
        <span className="text-xs font-medium text-gray-600 w-10 text-right">{pct}%</span>
      </div>
      {baseline > 0 && (
        <div className="text-[10px] text-gray-400 mt-1">Baseline: {baseline}</div>
      )}
      {kr.description && (
        <p className="text-[11px] text-gray-500 mt-1 italic">{kr.description}</p>
      )}
    </div>
  );
}

/* Descriptive KR with status badge */
function DescriptiveKRCard({
  kr, index, editing, editValue, saving,
  onStartEdit, onCancelEdit, onSave, onValueChange,
}: {
  kr: KeyResult; index: number; editing: boolean; editValue: string;
  saving: boolean; onStartEdit: () => void; onCancelEdit: () => void;
  onSave: () => void; onValueChange: (v: string) => void;
}) {
  const status = kr.status || "NOT_STARTED";

  return (
    <div className="rounded-lg border bg-white p-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-gray-700">
          KR-{index + 1}
        </span>
        <div className="flex items-center gap-2">
          {editing ? (
            <>
              <select
                value={editValue}
                onChange={(e) => onValueChange(e.target.value)}
                className="text-xs border rounded px-2 py-1"
                autoFocus
              >
                {KR_STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>{s.replace("_", " ")}</option>
                ))}
              </select>
              <button onClick={onSave} disabled={saving}
                className="text-xs text-forge-600 hover:text-forge-700 font-medium disabled:opacity-50">Save</button>
              <button onClick={onCancelEdit} className="text-xs text-gray-400 hover:text-gray-600">Cancel</button>
            </>
          ) : (
            <>
              <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                KR_STATUS_COLORS[status] || "bg-gray-100 text-gray-600"
              }`}>{status.replace("_", " ")}</span>
              <button onClick={onStartEdit} className="text-xs text-gray-400 hover:text-forge-600">Toggle</button>
            </>
          )}
        </div>
      </div>
      <p className="text-sm text-gray-600">{kr.description}</p>
    </div>
  );
}
