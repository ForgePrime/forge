"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { research as researchApi } from "@/lib/api";
import { Badge, statusVariant } from "@/components/shared/Badge";
import { EntityLink } from "@/components/shared/EntityLink";
import { ConfirmDeleteDialog } from "@/components/shared/ConfirmDeleteDialog";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Research, ResearchUpdate, ResearchCategory } from "@/lib/types";

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

const CATEGORIES: ResearchCategory[] = [
  "architecture", "business", "domain", "feasibility", "risk", "technical",
];

export default function ResearchDetailPage() {
  const { slug, id } = useParams() as { slug: string; id: string };
  const router = useRouter();
  const [item, setItem] = useState<Research | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit mode
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editTopic, setEditTopic] = useState("");
  const [editSummary, setEditSummary] = useState("");
  const [editCategory, setEditCategory] = useState<ResearchCategory>("technical");
  const [editKeyFindings, setEditKeyFindings] = useState<string[]>([]);
  const [editDecisionIds, setEditDecisionIds] = useState<string[]>([]);
  const [editScopes, setEditScopes] = useState<string[]>([]);
  const [editTags, setEditTags] = useState<string[]>([]);
  const [editLinkedEntityType, setEditLinkedEntityType] = useState("");
  const [editLinkedEntityId, setEditLinkedEntityId] = useState("");
  const [editContent, setEditContent] = useState("");

  // Delete state
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

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

  const startEdit = () => {
    if (!item) return;
    setEditTitle(item.title);
    setEditTopic(item.topic);
    setEditSummary(item.summary);
    setEditCategory(item.category);
    setEditKeyFindings([...item.key_findings]);
    setEditDecisionIds([...item.decision_ids]);
    setEditScopes([...item.scopes]);
    setEditTags([...item.tags]);
    setEditLinkedEntityType(item.linked_entity_type || "");
    setEditLinkedEntityId(item.linked_entity_id || "");
    setEditContent(item.content || "");
    setEditing(true);
  };

  const handleSave = async () => {
    if (!item) return;
    setSaving(true);
    setError(null);
    try {
      const update: ResearchUpdate = {};
      if (editTitle !== item.title) update.title = editTitle;
      if (editTopic !== item.topic) update.topic = editTopic;
      if (editSummary !== item.summary) update.summary = editSummary;
      if (editCategory !== item.category) update.category = editCategory;
      if (JSON.stringify(editKeyFindings) !== JSON.stringify(item.key_findings)) update.key_findings = editKeyFindings;
      if (JSON.stringify(editDecisionIds) !== JSON.stringify(item.decision_ids)) update.decision_ids = editDecisionIds;
      if (JSON.stringify(editScopes) !== JSON.stringify(item.scopes)) update.scopes = editScopes;
      if (JSON.stringify(editTags) !== JSON.stringify(item.tags)) update.tags = editTags;
      if (editLinkedEntityType !== (item.linked_entity_type || "")) update.linked_entity_type = editLinkedEntityType || undefined;
      if (editLinkedEntityId !== (item.linked_entity_id || "")) update.linked_entity_id = editLinkedEntityId || undefined;
      if (editContent !== (item.content || "")) update.content = editContent;

      if (Object.keys(update).length > 0) {
        const updated = await researchApi.update(slug, id, update);
        setItem(updated);
      }
      setEditing(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await researchApi.remove(slug, id);
      router.push(`/projects/${slug}/research`);
    } catch (e) {
      setError((e as Error).message);
      setDeleting(false);
      setDeleteOpen(false);
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
  if (error && !item) return <p className="text-sm text-red-600">{error}</p>;
  if (!item) return <p className="text-sm text-gray-400">Research not found</p>;

  const transitions = STATUS_TRANSITIONS[item.status] ?? [];

  return (
    <div className="space-y-6">
      {/* Delete confirmation */}
      <ConfirmDeleteDialog
        open={deleteOpen}
        title={`Delete ${item.id}?`}
        description="This will permanently remove this research object and cannot be undone."
        onConfirm={handleDelete}
        onCancel={() => setDeleteOpen(false)}
        loading={deleting}
      />

      {/* Header */}
      <div>
        <button
          onClick={() => router.back()}
          className="text-xs text-gray-400 hover:text-gray-600 mb-2"
        >
          &larr; Back
        </button>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400">{item.id}</span>
            <Badge variant={statusVariant(item.status)}>{item.status}</Badge>
            <Badge>{item.category}</Badge>
            {item.skill && (
              <span className="text-xs text-gray-400">via {item.skill}</span>
            )}
          </div>
          <div className="flex items-center gap-2">
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
          </div>
        </div>
        <h1 className="text-xl font-semibold mt-1">{item.title}</h1>
        <p className="text-sm text-gray-500 mt-1">{item.topic}</p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center justify-between bg-red-50 border border-red-200 rounded-md px-3 py-2">
          <p className="text-sm text-red-600">{error}</p>
          <button onClick={() => setError(null)} className="text-xs text-red-400 hover:text-red-600">Dismiss</button>
        </div>
      )}

      {/* Status actions — separate from edit mode */}
      {!editing && transitions.length > 0 && (
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

      {editing ? (
        /* ===== Edit mode ===== */
        <div className="space-y-5 border rounded-lg p-5 bg-gray-50">
          <fieldset>
            <legend className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Core</legend>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Title *</label>
                <input
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="w-full rounded-md border px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Topic</label>
                <input
                  value={editTopic}
                  onChange={(e) => setEditTopic(e.target.value)}
                  className="w-full rounded-md border px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Category</label>
                <select
                  value={editCategory}
                  onChange={(e) => setEditCategory(e.target.value as ResearchCategory)}
                  className="w-full rounded-md border px-3 py-1.5 text-sm"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Summary</label>
                <textarea
                  value={editSummary}
                  onChange={(e) => setEditSummary(e.target.value)}
                  rows={4}
                  className="w-full rounded-md border px-3 py-2 text-sm"
                />
              </div>
            </div>
          </fieldset>

          <fieldset>
            <legend className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Key Findings</legend>
            <EditableList items={editKeyFindings} setItems={setEditKeyFindings} label="Findings" addLabel="Add finding" rows={2} />
          </fieldset>

          <fieldset>
            <legend className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Linked Decisions</legend>
            <EditableList items={editDecisionIds} setItems={setEditDecisionIds} label="Decision IDs" addLabel="Add decision ID" />
          </fieldset>

          <fieldset>
            <legend className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Linked Entity</legend>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Entity Type</label>
                <select
                  value={editLinkedEntityType}
                  onChange={(e) => setEditLinkedEntityType(e.target.value)}
                  className="w-full rounded-md border px-3 py-1.5 text-sm"
                >
                  <option value="">None</option>
                  <option value="objective">Objective</option>
                  <option value="idea">Idea</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Entity ID</label>
                <input
                  value={editLinkedEntityId}
                  onChange={(e) => setEditLinkedEntityId(e.target.value)}
                  placeholder="O-001 or I-001"
                  className="w-full rounded-md border px-3 py-1.5 text-sm"
                />
              </div>
            </div>
          </fieldset>

          <fieldset>
            <legend className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Full Analysis (Markdown)</legend>
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              rows={12}
              placeholder="Full analysis content in markdown..."
              className="w-full rounded-md border px-3 py-2 text-sm font-mono"
            />
          </fieldset>

          <fieldset>
            <legend className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Metadata</legend>
            <EditableList items={editScopes} setItems={setEditScopes} label="Scopes" addLabel="Add scope" />
            <div className="mt-3">
              <EditableList items={editTags} setItems={setEditTags} label="Tags" addLabel="Add tag" />
            </div>
          </fieldset>

          <div className="flex items-center gap-2 pt-2">
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
        /* ===== Read mode ===== */
        <>
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
        </>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------------------
 * Editable list helper
 * --------------------------------------------------------------------------- */

function EditableList({
  items, setItems, label, addLabel, rows = 1,
}: {
  items: string[];
  setItems: (items: string[]) => void;
  label: string;
  addLabel: string;
  rows?: number;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">
        {label} ({items.length})
      </label>
      {items.map((item, i) => (
        <div key={i} className="flex items-start gap-2 mb-1">
          {rows > 1 ? (
            <textarea
              value={item}
              onChange={(e) => { const next = [...items]; next[i] = e.target.value; setItems(next); }}
              rows={rows}
              className="flex-1 rounded-md border px-2 py-1 text-xs"
            />
          ) : (
            <input
              value={item}
              onChange={(e) => { const next = [...items]; next[i] = e.target.value; setItems(next); }}
              className="flex-1 rounded-md border px-2 py-1 text-xs"
            />
          )}
          <button
            onClick={() => setItems(items.filter((_, j) => j !== i))}
            className="text-xs text-red-400 hover:text-red-600 mt-1"
          >
            Remove
          </button>
        </div>
      ))}
      <button
        onClick={() => setItems([...items, ""])}
        className="text-xs text-forge-600 hover:underline mt-1"
      >
        + {addLabel}
      </button>
    </div>
  );
}
