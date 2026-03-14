"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { lessons as lessonsApi } from "@/lib/api";
import { Badge } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import { ConfirmDeleteDialog } from "@/components/shared/ConfirmDeleteDialog";
import { useToastStore } from "@/stores/toastStore";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import type { Lesson, LessonCategory, LessonSeverity, LessonPromote } from "@/lib/types";

const severityVariant = {
  critical: "danger" as const,
  important: "warning" as const,
  minor: "default" as const,
};

export default function LessonDetailPage() {
  const { slug, id } = useParams() as { slug: string; id: string };
  const router = useRouter();
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [promoting, setPromoting] = useState<string | null>(null);

  // Edit mode state
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDetail, setEditDetail] = useState("");
  const [editCategory, setEditCategory] = useState<LessonCategory>("pattern-discovered");
  const [editSeverity, setEditSeverity] = useState<LessonSeverity | "">("");
  const [editAppliesTo, setEditAppliesTo] = useState("");
  const [editTags, setEditTags] = useState<string[]>([]);
  const [editTaskId, setEditTaskId] = useState("");
  const [editDecisionIds, setEditDecisionIds] = useState<string[]>([]);

  // Delete state
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Promote form state
  const [promoteScope, setPromoteScope] = useState("");
  const [promoteWeight, setPromoteWeight] = useState<"must" | "should" | "may">("should");
  const [promoteCategory, setPromoteCategory] = useState("architecture");

  const loadLesson = useCallback(async () => {
    setLoading(true);
    try {
      const data = await lessonsApi.get(slug, id);
      setLesson(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [slug, id]);

  useEffect(() => {
    loadLesson();
  }, [loadLesson]);

  const startEdit = () => {
    if (!lesson) return;
    setEditTitle(lesson.title);
    setEditDetail(lesson.detail);
    setEditCategory(lesson.category);
    setEditSeverity(lesson.severity || "");
    setEditAppliesTo(lesson.applies_to || "");
    setEditTags([...lesson.tags]);
    setEditTaskId(lesson.task_id || "");
    setEditDecisionIds([...(lesson.decision_ids || [])]);
    setEditing(true);
  };

  const handleSave = async () => {
    if (!lesson) return;
    setSaving(true);
    setError(null);
    try {
      const update: Partial<Lesson> = {};
      if (editTitle !== lesson.title) update.title = editTitle;
      if (editDetail !== lesson.detail) update.detail = editDetail;
      if (editCategory !== lesson.category) update.category = editCategory;
      if ((editSeverity || undefined) !== lesson.severity) update.severity = editSeverity as LessonSeverity || undefined;
      if (editAppliesTo !== (lesson.applies_to || "")) update.applies_to = editAppliesTo || undefined;
      if (JSON.stringify(editTags) !== JSON.stringify(lesson.tags)) update.tags = editTags;
      if (editTaskId !== (lesson.task_id || "")) update.task_id = editTaskId || undefined;
      if (JSON.stringify(editDecisionIds) !== JSON.stringify(lesson.decision_ids || [])) update.decision_ids = editDecisionIds;
      if (Object.keys(update).length > 0) {
        const updated = await lessonsApi.update(slug, lesson.id, update);
        setLesson(updated);
      }
      setEditing(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!lesson) return;
    setDeleting(true);
    try {
      await lessonsApi.remove(slug, lesson.id);
      router.push(`/projects/${slug}/lessons`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  useAIPage({
    id: "lesson-detail",
    title: `Lesson ${id}`,
    description: lesson ? `${lesson.title} — ${lesson.category}` : `Lesson ${id}`,
    route: `/projects/${slug}/lessons/${id}`,
  });

  const handlePromote = useCallback(async (target: "guideline" | "knowledge") => {
    if (!lesson) return;
    setPromoting(target);
    try {
      const data: LessonPromote = { target };
      if (target === "guideline") {
        data.scope = promoteScope || "general";
        data.weight = promoteWeight;
      } else {
        data.category = promoteCategory;
        data.scopes = promoteScope ? [promoteScope] : [];
      }
      const result = await lessonsApi.promote(slug, id, data);
      useToastStore.getState().addToast({
        message: `Promoted ${id} to ${target}: ${result.guideline_id || result.knowledge_id || result.promoted_to}`,
        action: "completed",
      });
      await loadLesson();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPromoting(null);
    }
  }, [slug, id, lesson, promoteScope, promoteWeight, promoteCategory, loadLesson]);

  const isPromoted = lesson?.promoted_to_guideline || lesson?.promoted_to_knowledge;

  useAIElement({
    id: "promote-actions",
    type: "action",
    label: "Promote Lesson",
    description: isPromoted
      ? `Already promoted: ${lesson?.promoted_to_guideline ? `G: ${lesson.promoted_to_guideline}` : ""} ${lesson?.promoted_to_knowledge ? `K: ${lesson.promoted_to_knowledge}` : ""}`
      : "Can promote to guideline or knowledge",
    data: {
      promoted_to_guideline: lesson?.promoted_to_guideline,
      promoted_to_knowledge: lesson?.promoted_to_knowledge,
    },
    actions: [
      {
        label: "Promote to Guideline",
        toolName: "promoteLesson",
        toolParams: ["lesson_id*", "target=guideline", "scope", "weight"],
        availableWhen: "not promoted_to_guideline",
      },
      {
        label: "Promote to Knowledge",
        toolName: "promoteLesson",
        toolParams: ["lesson_id*", "target=knowledge", "category", "scopes"],
        availableWhen: "not promoted_to_knowledge",
      },
    ],
  });

  if (loading) return <p className="text-sm text-gray-400 p-4">Loading...</p>;
  if (!lesson) return <p className="text-sm text-gray-400 p-4">Lesson not found.</p>;

  return (
    <div className="max-w-3xl">
      {/* Back + Header */}
      <div className="mb-4">
        <button
          onClick={() => router.back()}
          className="text-xs text-gray-400 hover:text-gray-600 mb-2"
        >
          &larr; Back to Lessons
        </button>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs text-gray-400">{lesson.id}</span>
              <Badge>{lesson.category}</Badge>
              {lesson.severity && (
                <Badge variant={severityVariant[lesson.severity]}>{lesson.severity}</Badge>
              )}
            </div>
            <h2 className="text-lg font-semibold">{lesson.title}</h2>
          </div>
          {!editing && (
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={startEdit}>Edit</Button>
              <Button variant="danger" size="sm" onClick={() => setDeleteOpen(true)}>Delete</Button>
            </div>
          )}
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center justify-between bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-4">
          <p className="text-sm text-red-600">{error}</p>
          <button onClick={() => setError(null)} className="text-xs text-red-400 hover:text-red-600">Dismiss</button>
        </div>
      )}

      {/* Promotion status */}
      {isPromoted && (
        <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 space-y-1">
          <span className="text-sm font-medium text-green-700">Promoted</span>
          {lesson.promoted_to_guideline && (
            <p className="text-xs text-green-600">
              Guideline: {lesson.promoted_to_guideline}
            </p>
          )}
          {lesson.promoted_to_knowledge && (
            <p className="text-xs text-green-600">
              Knowledge: {lesson.promoted_to_knowledge}
            </p>
          )}
        </div>
      )}

      {editing ? (
        <div className="space-y-4 border rounded-lg p-5 bg-gray-50 mb-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Title *</label>
            <input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="w-full rounded-md border px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Detail *</label>
            <textarea
              value={editDetail}
              onChange={(e) => setEditDetail(e.target.value)}
              rows={6}
              className="w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Category</label>
              <select
                value={editCategory}
                onChange={(e) => setEditCategory(e.target.value as LessonCategory)}
                className="w-full rounded-md border px-3 py-1.5 text-sm"
              >
                {["pattern-discovered", "mistake-avoided", "decision-validated", "decision-reversed", "tool-insight", "architecture-lesson", "process-improvement", "market-insight"].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Severity</label>
              <select
                value={editSeverity}
                onChange={(e) => setEditSeverity(e.target.value as LessonSeverity | "")}
                className="w-full rounded-md border px-3 py-1.5 text-sm"
              >
                <option value="">-- none --</option>
                <option value="critical">critical</option>
                <option value="important">important</option>
                <option value="minor">minor</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Task ID</label>
              <input
                value={editTaskId}
                onChange={(e) => setEditTaskId(e.target.value)}
                placeholder="T-001"
                className="w-full rounded-md border px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Applies To</label>
              <input
                value={editAppliesTo}
                onChange={(e) => setEditAppliesTo(e.target.value)}
                placeholder="e.g., backend, all projects"
                className="w-full rounded-md border px-3 py-1.5 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Decision IDs ({editDecisionIds.length})
            </label>
            {editDecisionIds.map((d, i) => (
              <div key={i} className="flex items-center gap-2 mb-1">
                <input
                  value={d}
                  onChange={(e) => { const next = [...editDecisionIds]; next[i] = e.target.value; setEditDecisionIds(next); }}
                  placeholder="D-001"
                  className="flex-1 rounded-md border px-2 py-1 text-xs"
                />
                <button
                  onClick={() => setEditDecisionIds(editDecisionIds.filter((_, j) => j !== i))}
                  className="text-xs text-red-400 hover:text-red-600"
                >
                  Remove
                </button>
              </div>
            ))}
            <button
              onClick={() => setEditDecisionIds([...editDecisionIds, ""])}
              className="text-xs text-forge-600 hover:underline mt-1"
            >
              + Add decision ID
            </button>
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
          {/* Detail */}
          <div className="rounded-lg border bg-white p-4 mb-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Detail</h3>
            <p className="text-sm text-gray-600 whitespace-pre-wrap">{lesson.detail}</p>
          </div>

          {/* Metadata */}
          <div className="rounded-lg border bg-white p-4 mb-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Metadata</h3>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {lesson.task_id && (
                <div>
                  <span className="text-gray-400">Task:</span>{" "}
                  <span className="text-gray-700">{lesson.task_id}</span>
                </div>
              )}
              {lesson.applies_to && (
                <div>
                  <span className="text-gray-400">Applies to:</span>{" "}
                  <span className="text-gray-700">{lesson.applies_to}</span>
                </div>
              )}
              {lesson.decision_ids && lesson.decision_ids.length > 0 && (
                <div>
                  <span className="text-gray-400">Decisions:</span>{" "}
                  <span className="text-gray-700">{lesson.decision_ids.join(", ")}</span>
                </div>
              )}
              <div>
                <span className="text-gray-400">Created:</span>{" "}
                <span className="text-gray-700">{new Date(lesson.created_at).toLocaleDateString()}</span>
              </div>
            </div>
            {lesson.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {lesson.tags.map((t) => (
                  <span key={t} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{t}</span>
                ))}
              </div>
            )}
          </div>

          {/* Promote actions */}
          {!isPromoted && (
            <div className="rounded-lg border bg-white p-4">
              <h3 className="text-sm font-medium text-gray-700 mb-3">Promote</h3>
              <div className="space-y-3">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={promoteScope}
                    onChange={(e) => setPromoteScope(e.target.value)}
                    placeholder="Scope (e.g., backend)"
                    className="flex-1 text-xs border rounded px-2 py-1.5 placeholder-gray-300"
                  />
                  <select
                    value={promoteWeight}
                    onChange={(e) => setPromoteWeight(e.target.value as "must" | "should" | "may")}
                    className="text-xs border rounded px-2 py-1.5 bg-white"
                  >
                    <option value="must">must</option>
                    <option value="should">should</option>
                    <option value="may">may</option>
                  </select>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handlePromote("guideline")}
                    disabled={promoting !== null}
                    className="px-3 py-1.5 text-xs text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    {promoting === "guideline" ? "Promoting..." : "Promote to Guideline"}
                  </button>
                  <button
                    onClick={() => handlePromote("knowledge")}
                    disabled={promoting !== null}
                    className="px-3 py-1.5 text-xs text-white bg-purple-600 rounded hover:bg-purple-700 disabled:opacity-50"
                  >
                    {promoting === "knowledge" ? "Promoting..." : "Promote to Knowledge"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      <ConfirmDeleteDialog
        open={deleteOpen}
        title={`Delete ${lesson.id}?`}
        description="This action cannot be undone. The lesson will be permanently removed."
        onConfirm={handleDelete}
        onCancel={() => setDeleteOpen(false)}
        loading={deleting}
      />
    </div>
  );
}
