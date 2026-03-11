"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { decisions as decisionsApi } from "@/lib/api";
import { Badge, statusVariant } from "@/components/shared/Badge";
import type { Decision } from "@/lib/types";

export default function DecisionDetailPage() {
  const { slug, id } = useParams() as { slug: string; id: string };
  const router = useRouter();
  const [decision, setDecision] = useState<Decision | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDecision = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await decisionsApi.get(slug, id);
      setDecision(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [slug, id]);

  useEffect(() => {
    fetchDecision();
  }, [fetchDecision]);

  if (loading) return <p className="text-sm text-gray-400">Loading decision...</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!decision) return <p className="text-sm text-gray-400">Decision not found</p>;

  const isRisk = decision.type === "risk";
  const isExploration = decision.type === "exploration";

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
              <span className="text-sm text-gray-400 font-mono">{decision.id}</span>
              <Badge variant={statusVariant(decision.status)}>{decision.status}</Badge>
              <Badge>{decision.type}</Badge>
              <Badge variant={
                decision.confidence === "HIGH" ? "success" :
                decision.confidence === "LOW" ? "danger" : "warning"
              }>
                {decision.confidence}
              </Badge>
            </div>
            {decision.task_id && (
              <Link
                href={`/projects/${slug}/tasks/${decision.task_id}`}
                className="text-xs text-forge-600 hover:underline"
              >
                Task: {decision.task_id}
              </Link>
            )}
          </div>
          <div className="text-xs text-gray-400 text-right">
            <div>By: {decision.decided_by}</div>
            <div>Created: {new Date(decision.created_at).toLocaleDateString()}</div>
            {decision.updated_at && <div>Updated: {new Date(decision.updated_at).toLocaleDateString()}</div>}
          </div>
        </div>
        {decision.tags.length > 0 && (
          <div className="flex gap-1 mt-2">
            {decision.tags.map((t) => (
              <span key={t} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{t}</span>
            ))}
          </div>
        )}
      </div>

      {/* Issue */}
      <section className="mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Issue</h3>
        <p className="text-sm text-gray-600 whitespace-pre-wrap">{decision.issue}</p>
      </section>

      {/* Recommendation */}
      {decision.recommendation && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Recommendation</h3>
          <div className="bg-forge-50 border border-forge-200 rounded-md p-3">
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{decision.recommendation}</p>
          </div>
        </section>
      )}

      {/* Reasoning */}
      {decision.reasoning && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Reasoning</h3>
          <p className="text-sm text-gray-600 whitespace-pre-wrap">{decision.reasoning}</p>
        </section>
      )}

      {/* Alternatives */}
      {decision.alternatives.length > 0 && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Alternatives ({decision.alternatives.length})
          </h3>
          <ul className="space-y-2">
            {decision.alternatives.map((alt, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="text-gray-400 shrink-0">{i + 1}.</span>
                <span className="text-gray-600">{alt}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Risk-specific fields */}
      {isRisk && <RiskSection decision={decision} />}

      {/* Exploration-specific fields */}
      {isExploration && <ExplorationSection decision={decision} />}

      {/* Resolution Notes */}
      {decision.resolution_notes && (
        <section className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Resolution Notes</h3>
          <p className="text-sm text-gray-600 whitespace-pre-wrap bg-green-50 border border-green-200 rounded-md p-3">
            {decision.resolution_notes}
          </p>
        </section>
      )}

      {/* Metadata */}
      <section className="border-t pt-4 mt-6">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs text-gray-500">
          {decision.file && <div><span className="font-medium">File:</span> {decision.file}</div>}
          {decision.scope && <div><span className="font-medium">Scope:</span> {decision.scope}</div>}
        </div>
      </section>
    </div>
  );
}

function RiskSection({ decision }: { decision: Decision }) {
  return (
    <section className="mb-6 border border-red-200 bg-red-50 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-red-700 mb-3">Risk Assessment</h3>
      <div className="grid grid-cols-2 gap-4 mb-3">
        {decision.severity && (
          <div>
            <span className="text-xs text-gray-500 block">Severity</span>
            <Badge variant={
              decision.severity === "critical" ? "danger" :
              decision.severity === "high" ? "warning" : "default"
            }>
              {decision.severity}
            </Badge>
          </div>
        )}
        {decision.likelihood && (
          <div>
            <span className="text-xs text-gray-500 block">Likelihood</span>
            <Badge variant={
              decision.likelihood === "high" ? "danger" :
              decision.likelihood === "medium" ? "warning" : "default"
            }>
              {decision.likelihood}
            </Badge>
          </div>
        )}
      </div>
      {decision.mitigation_plan && (
        <div className="mb-2">
          <span className="text-xs font-medium text-gray-600 block mb-1">Mitigation Plan</span>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{decision.mitigation_plan}</p>
        </div>
      )}
      {decision.linked_entity_id && (
        <div className="text-xs text-gray-500">
          Linked entity: {decision.linked_entity_type} {decision.linked_entity_id}
        </div>
      )}
    </section>
  );
}

function ExplorationSection({ decision }: { decision: Decision }) {
  return (
    <section className="mb-6 border border-blue-200 bg-blue-50 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-blue-700 mb-3">
        Exploration {decision.exploration_type ? `(${decision.exploration_type})` : ""}
      </h3>

      {decision.findings && decision.findings.length > 0 && (
        <div className="mb-3">
          <span className="text-xs font-medium text-gray-600 block mb-1">Findings</span>
          <ul className="space-y-1">
            {decision.findings.map((f, i) => (
              <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                <span className="text-blue-400 shrink-0">-</span>
                <span>{typeof f === "string" ? f : JSON.stringify(f)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {decision.options && decision.options.length > 0 && (
        <div className="mb-3">
          <span className="text-xs font-medium text-gray-600 block mb-1">Options</span>
          <ul className="space-y-1">
            {decision.options.map((o, i) => (
              <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                <span className="text-blue-400 shrink-0">{i + 1}.</span>
                <span>{typeof o === "string" ? o : JSON.stringify(o)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {decision.open_questions && decision.open_questions.length > 0 && (
        <div className="mb-3">
          <span className="text-xs font-medium text-gray-600 block mb-1">Open Questions</span>
          <ul className="space-y-1">
            {decision.open_questions.map((q, i) => (
              <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                <span className="text-blue-400 shrink-0">?</span>
                <span>{q}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {decision.blockers && decision.blockers.length > 0 && (
        <div>
          <span className="text-xs font-medium text-red-600 block mb-1">Blockers</span>
          <ul className="space-y-1">
            {decision.blockers.map((b, i) => (
              <li key={i} className="text-sm text-red-600 flex items-start gap-2">
                <span className="shrink-0">!</span>
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
