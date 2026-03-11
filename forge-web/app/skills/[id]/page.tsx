"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { skills as skillsApi, ApiError } from "@/lib/api";
import { Badge, statusVariant } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import type { Skill, SkillStatus, TESLintFinding, PromotionHistoryEntry } from "@/lib/types";

type Tab = "skill_md" | "evals" | "lint" | "history";

const validTransitions: Record<string, SkillStatus[]> = {
  DRAFT: ["DEPRECATED"],
  ACTIVE: ["DEPRECATED"],
  DEPRECATED: ["ARCHIVED", "ACTIVE"],
  ARCHIVED: [],
};

export default function SkillDetailPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();
  const [skill, setSkill] = useState<Skill | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("skill_md");

  // Lint state
  const [lintFindings, setLintFindings] = useState<TESLintFinding[]>([]);
  const [lintLoading, setLintLoading] = useState(false);
  const [lintError, setLintError] = useState<string | null>(null);
  const [lintRan, setLintRan] = useState(false);

  // Promote state
  const [promoting, setPromoting] = useState(false);
  const [promoteError, setPromoteError] = useState<string | null>(null);
  const [showForceConfirm, setShowForceConfirm] = useState(false);

  // Status change state
  const [changingStatus, setChangingStatus] = useState(false);

  const fetchSkill = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await skillsApi.get(id);
      setSkill(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchSkill();
  }, [fetchSkill]);

  const runLint = async () => {
    setLintLoading(true);
    setLintError(null);
    try {
      const res = await skillsApi.lint(id);
      setLintFindings(res.findings);
      setLintRan(true);
      if (res.error_message) setLintError(res.error_message);
    } catch (e) {
      setLintError((e as Error).message);
    } finally {
      setLintLoading(false);
    }
  };

  const handlePromote = async (force: boolean) => {
    setPromoting(true);
    setPromoteError(null);
    setShowForceConfirm(false);
    try {
      await skillsApi.promote(id, force);
      // Success — backend returns 200 with status=ACTIVE
      await fetchSkill();
    } catch (e) {
      const msg = (e as Error).message;
      setPromoteError(msg);
      // Backend returns 422 when gates fail. Offer force-promote
      // only if this was a non-forced attempt (force override available).
      if (!force && e instanceof ApiError && e.status === 422) {
        setShowForceConfirm(true);
      }
    } finally {
      setPromoting(false);
    }
  };

  const handleStatusChange = async (newStatus: SkillStatus) => {
    if (!skill) return;
    setChangingStatus(true);
    setError(null);
    try {
      const updated = await skillsApi.update(id, { status: newStatus });
      setSkill(updated);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setChangingStatus(false);
    }
  };

  if (loading) return <p className="text-sm text-gray-400">Loading...</p>;
  if (!skill && error) return <p className="text-sm text-red-600">{error}</p>;
  if (!skill) return <p className="text-sm text-gray-400">Not found</p>;

  const transitions = validTransitions[skill.status] || [];

  const tabs: { key: Tab; label: string }[] = [
    { key: "skill_md", label: "SKILL.md" },
    { key: "evals", label: `Evals (${skill.evals_json.length})` },
    { key: "lint", label: "TESLint" },
    { key: "history", label: `History (${skill.promotion_history.length})` },
  ];

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-2 mb-1">
        <button onClick={() => router.push("/skills")} className="text-xs text-gray-400 hover:text-gray-600">
          &larr; Skills
        </button>
        <span className="text-xs text-gray-400">{skill.id}</span>
        <Badge variant={statusVariant(skill.status)}>{skill.status}</Badge>
        <Badge>{skill.category}</Badge>
        {skill.promoted_with_warnings && (
          <Badge variant="warning">Promoted with warnings</Badge>
        )}
      </div>
      <h2 className="text-lg font-semibold mb-1">{skill.name}</h2>
      {skill.description && (
        <p className="text-sm text-gray-500 mb-2">{skill.description}</p>
      )}

      {/* Metadata row */}
      <div className="flex flex-wrap gap-3 text-xs text-gray-400 mb-4">
        {skill.scopes.length > 0 && <span>scopes: {skill.scopes.join(", ")}</span>}
        <span>used {skill.usage_count} time{skill.usage_count !== 1 ? "s" : ""}</span>
        {skill.created_by && <span>by: {skill.created_by}</span>}
        <span>updated: {new Date(skill.updated_at).toLocaleDateString()}</span>
      </div>

      {/* Tags */}
      {skill.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-4">
          {skill.tags.map((t) => (
            <span key={t} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">{t}</span>
          ))}
        </div>
      )}

      {/* Action bar */}
      <div className="flex flex-wrap items-center gap-2 mb-4 p-3 rounded-lg bg-gray-50 border">
        {skill.status === "DRAFT" && (
          <Button
            size="sm"
            onClick={() => handlePromote(false)}
            disabled={promoting}
          >
            {promoting ? "Promoting..." : "Promote to ACTIVE"}
          </Button>
        )}
        {transitions.map((ts) => {
          const isDestructive = ts === "ARCHIVED" || ts === "DEPRECATED";
          return (
            <Button
              key={ts}
              size="sm"
              variant={isDestructive ? "danger" : "secondary"}
              onClick={() => {
                if (isDestructive) {
                  const label = ts === "DEPRECATED" ? "deprecate" : "archive";
                  if (!confirm(`Are you sure you want to ${label} this skill?${ts === "ARCHIVED" ? " This cannot be undone." : ""}`)) return;
                }
                handleStatusChange(ts);
              }}
              disabled={changingStatus}
            >
              {ts === "DEPRECATED" ? "Deprecate" : ts === "ARCHIVED" ? "Archive" : `Set ${ts}`}
            </Button>
          );
        })}
        {promoteError && (
          <span className="text-xs text-red-600">{promoteError}</span>
        )}
        {showForceConfirm && (
          <Button
            size="sm"
            variant="danger"
            onClick={() => handlePromote(true)}
            disabled={promoting}
          >
            Force Promote (override warnings)
          </Button>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center justify-between bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-4">
          <p className="text-sm text-red-600">{error}</p>
          <button onClick={() => setError(null)} className="text-xs text-red-400 hover:text-red-600">Dismiss</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b mb-4">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? "border-forge-500 text-forge-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab: SKILL.md */}
      {tab === "skill_md" && (
        <div>
          {skill.skill_md_content ? (
            <pre className="rounded-lg border bg-gray-50 p-4 whitespace-pre-wrap font-mono text-sm overflow-x-auto">
              {skill.skill_md_content}
            </pre>
          ) : (
            <p className="text-sm text-gray-400 italic">
              No SKILL.md content yet. Edit this skill to add content.
            </p>
          )}
        </div>
      )}

      {/* Tab: Evals */}
      {tab === "evals" && (
        <div>
          {skill.evals_json.length === 0 ? (
            <p className="text-sm text-gray-400">No evals defined. At least 1 eval is required for promotion.</p>
          ) : (
            <div className="space-y-3">
              {skill.evals_json.map((ev, i) => (
                <div key={i} className="rounded-lg border bg-white p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge>Eval #{i + 1}</Badge>
                    {"name" in ev && ev.name ? <span className="text-sm font-medium">{String(ev.name)}</span> : null}
                  </div>
                  <pre className="text-xs bg-gray-50 rounded p-2 overflow-x-auto mt-1">
                    {JSON.stringify(ev, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab: TESLint */}
      {tab === "lint" && (
        <div>
          <div className="flex items-center gap-3 mb-4">
            <Button size="sm" onClick={runLint} disabled={lintLoading}>
              {lintLoading ? "Running..." : "Run Lint"}
            </Button>
            {lintRan && !lintLoading && (
              <span className="text-xs text-gray-400">
                {lintFindings.length === 0
                  ? "No findings"
                  : `${lintFindings.length} finding${lintFindings.length !== 1 ? "s" : ""}`}
              </span>
            )}
          </div>
          {lintError && (
            <p className="text-sm text-amber-600 mb-3">{lintError}</p>
          )}
          {lintFindings.length > 0 && (
            <div className="space-y-2">
              {lintFindings.map((f, i) => (
                <div
                  key={i}
                  className={`rounded-md border p-3 ${
                    f.severity === "error"
                      ? "border-red-200 bg-red-50"
                      : f.severity === "warning"
                      ? "border-yellow-200 bg-yellow-50"
                      : "border-blue-200 bg-blue-50"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        f.severity === "error" ? "danger" :
                        f.severity === "warning" ? "warning" : "info"
                      }
                    >
                      {f.severity}
                    </Badge>
                    <span className="text-xs text-gray-500">{f.rule_id}</span>
                    {f.line && <span className="text-xs text-gray-400">line {f.line}</span>}
                  </div>
                  <p className="text-sm mt-1">{f.message}</p>
                </div>
              ))}
            </div>
          )}
          {lintRan && lintFindings.length === 0 && !lintError && (
            <div className="rounded-md border border-green-200 bg-green-50 p-4 text-center">
              <p className="text-sm text-green-700">All checks passed</p>
            </div>
          )}
        </div>
      )}

      {/* Tab: Promotion History */}
      {tab === "history" && (
        <div>
          {skill.promotion_history.length === 0 ? (
            <p className="text-sm text-gray-400">No promotion attempts yet.</p>
          ) : (
            <div className="space-y-3">
              {[...skill.promotion_history].reverse().map((entry: PromotionHistoryEntry, i: number) => (
                <div key={i} className="rounded-lg border bg-white p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Badge variant={entry.forced ? "warning" : "success"}>
                        {entry.forced ? "Forced" : "Clean"}
                      </Badge>
                      <span className="text-xs text-gray-500">
                        {new Date(entry.promoted_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="text-xs text-gray-400">
                      {entry.error_count} errors, {entry.warning_count} warnings
                    </div>
                  </div>
                  <div className="space-y-1">
                    {entry.gates.map((g, gi) => (
                      <div key={gi} className="flex items-center gap-2 text-xs">
                        <span className={g.passed ? "text-green-600" : "text-red-600"}>
                          {g.passed ? "PASS" : "FAIL"}
                        </span>
                        <span className="font-medium">{g.gate}</span>
                        <span className="text-gray-400">{g.detail}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
