"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { lessons as lessonsApi } from "@/lib/api";
import { Badge } from "@/components/shared/Badge";
import { useToastStore } from "@/stores/toastStore";
import { useAIPage, useAIElement } from "@/lib/ai-context";
import type { Lesson, LessonPromote } from "@/lib/types";

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
  if (error) return <p className="text-sm text-red-600 p-4">{error}</p>;
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
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs text-gray-400">{lesson.id}</span>
          <Badge>{lesson.category}</Badge>
          {lesson.severity && (
            <Badge variant={severityVariant[lesson.severity]}>{lesson.severity}</Badge>
          )}
        </div>
        <h2 className="text-lg font-semibold">{lesson.title}</h2>
      </div>

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
    </div>
  );
}
