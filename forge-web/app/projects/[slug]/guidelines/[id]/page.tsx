"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { guidelines as guidelinesApi } from "@/lib/api";
import { Badge, statusVariant } from "@/components/shared/Badge";
import { EntityLink } from "@/components/shared/EntityLink";
import type { Guideline, GuidelineUpdate } from "@/lib/types";

const WEIGHT_VARIANT: Record<string, "danger" | "warning" | "default"> = {
  must: "danger",
  should: "warning",
  may: "default",
};

export default function GuidelineDetailPage() {
  const { slug, id } = useParams() as { slug: string; id: string };
  const router = useRouter();
  const [guideline, setGuideline] = useState<Guideline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  // Edit form state
  const [editTitle, setEditTitle] = useState("");
  const [editScope, setEditScope] = useState("");
  const [editWeight, setEditWeight] = useState<"must" | "should" | "may">("should");
  const [editContent, setEditContent] = useState("");
  const [editRationale, setEditRationale] = useState("");
  const [editExamples, setEditExamples] = useState<string[]>([]);
  const [editStatus, setEditStatus] = useState<"ACTIVE" | "DEPRECATED">("ACTIVE");

  const fetchGuideline = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await guidelinesApi.get(slug, id);
      setGuideline(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [slug, id]);

  useEffect(() => {
    fetchGuideline();
  }, [fetchGuideline]);

  const startEdit = () => {
    if (!guideline) return;
    setEditTitle(guideline.title);
    setEditScope(guideline.scope);
    setEditWeight(guideline.weight);
    setEditContent(guideline.content);
    setEditRationale(guideline.rationale || "");
    setEditExamples([...guideline.examples]);
    setEditStatus(guideline.status);
    setEditing(true);
  };

  const handleSave = async () => {
    if (!guideline) return;
    setSaving(true);
    try {
      const update: GuidelineUpdate = {
        title: editTitle,
        scope: editScope,
        weight: editWeight,
        content: editContent,
        rationale: editRationale || undefined,
        examples: editExamples,
        status: editStatus,
      };
      const updated = await guidelinesApi.update(slug, guideline.id, update);
      setGuideline(updated);
      setEditing(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="p-6 text-sm text-gray-400">Loading guideline...</p>;
  if (error) return <p className="p-6 text-sm text-red-600">{error}</p>;
  if (!guideline) return <p className="p-6 text-sm text-gray-400">Guideline not found</p>;

  return (
    <div className="p-6 max-w-4xl">
      {/* Back button */}
      <button onClick={() => router.back()} className="text-xs text-gray-400 hover:text-gray-600 mb-4">
        &larr; Back to guidelines
      </button>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm text-gray-400 font-mono">{guideline.id}</span>
            <Badge variant={statusVariant(guideline.status)}>{guideline.status}</Badge>
            <Badge variant={WEIGHT_VARIANT[guideline.weight] || "default"}>{guideline.weight}</Badge>
            <span className="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-600">{guideline.scope}</span>
          </div>
          <h1 className="text-xl font-bold text-gray-800">{guideline.title}</h1>
          {guideline.derived_from && (
            <div className="mt-1 text-xs text-gray-500">
              Derived from: <EntityLink id={guideline.derived_from} />
            </div>
          )}
        </div>
        {!editing && (
          <button
            onClick={startEdit}
            className="px-3 py-1.5 text-xs font-medium text-forge-700 border border-forge-300 rounded hover:bg-forge-50"
          >
            Edit
          </button>
        )}
      </div>

      {editing ? (
        /* Edit mode */
        <div className="space-y-4 border rounded-lg p-4 bg-gray-50">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Title</label>
            <input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="w-full rounded-md border px-3 py-1.5 text-sm"
            />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Scope</label>
              <input
                value={editScope}
                onChange={(e) => setEditScope(e.target.value)}
                className="w-full rounded-md border px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Weight</label>
              <select
                value={editWeight}
                onChange={(e) => setEditWeight(e.target.value as "must" | "should" | "may")}
                className="w-full rounded-md border px-3 py-1.5 text-sm"
              >
                <option value="must">must</option>
                <option value="should">should</option>
                <option value="may">may</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
              <select
                value={editStatus}
                onChange={(e) => setEditStatus(e.target.value as "ACTIVE" | "DEPRECATED")}
                className="w-full rounded-md border px-3 py-1.5 text-sm"
              >
                <option value="ACTIVE">ACTIVE</option>
                <option value="DEPRECATED">DEPRECATED</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Content</label>
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              rows={6}
              className="w-full rounded-md border px-3 py-2 text-sm font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Rationale</label>
            <textarea
              value={editRationale}
              onChange={(e) => setEditRationale(e.target.value)}
              rows={3}
              className="w-full rounded-md border px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Examples ({editExamples.length})
            </label>
            {editExamples.map((ex, i) => (
              <div key={i} className="flex items-start gap-2 mb-1">
                <textarea
                  value={ex}
                  onChange={(e) => {
                    const next = [...editExamples];
                    next[i] = e.target.value;
                    setEditExamples(next);
                  }}
                  rows={2}
                  className="flex-1 rounded-md border px-2 py-1 text-xs font-mono"
                />
                <button
                  onClick={() => setEditExamples(editExamples.filter((_, j) => j !== i))}
                  className="text-xs text-red-400 hover:text-red-600 mt-1"
                >
                  Remove
                </button>
              </div>
            ))}
            <button
              onClick={() => setEditExamples([...editExamples, ""])}
              className="text-xs text-forge-600 hover:underline mt-1"
            >
              + Add example
            </button>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-1.5 text-sm font-medium text-white bg-forge-600 rounded hover:bg-forge-700 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save"}
            </button>
            <button
              onClick={() => setEditing(false)}
              className="px-4 py-1.5 text-sm text-gray-600 border rounded hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        /* Read mode */
        <div className="space-y-6">
          {/* Content */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Content</h3>
            <div className="bg-gray-50 border rounded-md p-4">
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{guideline.content}</p>
            </div>
          </section>

          {/* Rationale */}
          {guideline.rationale && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Rationale</h3>
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{guideline.rationale}</p>
            </section>
          )}

          {/* Examples */}
          {guideline.examples.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">
                Examples ({guideline.examples.length})
              </h3>
              <div className="space-y-2">
                {guideline.examples.map((ex, i) => (
                  <div key={i} className="bg-gray-50 border rounded-md p-3">
                    <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">{ex}</pre>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Tags */}
          {guideline.tags.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">Tags</h3>
              <div className="flex flex-wrap gap-1">
                {guideline.tags.map((t) => (
                  <span key={t} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{t}</span>
                ))}
              </div>
            </section>
          )}

          {/* Metadata */}
          <section className="border-t pt-4">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs text-gray-500">
              <div>
                <span className="font-medium">Created: </span>
                {new Date(guideline.created_at).toLocaleDateString()}
              </div>
              <div>
                <span className="font-medium">Scope: </span>
                {guideline.scope}
              </div>
              {guideline.derived_from && (
                <div>
                  <span className="font-medium">Derived from: </span>
                  <EntityLink id={guideline.derived_from} />
                </div>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
