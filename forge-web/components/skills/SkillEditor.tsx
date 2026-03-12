"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { skills as skillsApi, ApiError, fetchBlob } from "@/lib/api";
import { Badge, statusVariant } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import { GenerateSkillModal } from "@/components/skills/GenerateSkillModal";
import LLMChat from "@/components/ai/LLMChat";
import { parseFrontmatter } from "@/lib/utils/parseFrontmatter";
import { getCategoryColor, categoryLabel } from "@/lib/utils/categoryColors";
import type {
  Skill,
  SkillStatus,
  SkillUpdate,
  SkillUsageEntry,
  TESLintFinding,
  PromotionHistoryEntry,
  LLMConfig,
} from "@/lib/types";

type Tab = "metadata" | "evals" | "lint" | "history" | "usage";

const CATEGORIES = [
  "workflow", "analysis", "generation", "validation", "integration",
  "refactoring", "testing", "deployment", "documentation", "custom",
];

const AI_PANEL_KEY = "forge:skill-editor:ai-panel";

const validTransitions: Record<string, SkillStatus[]> = {
  DRAFT: ["DEPRECATED"],
  ACTIVE: ["DEPRECATED"],
  DEPRECATED: ["ARCHIVED", "ACTIVE"],
  ARCHIVED: [],
};

interface SkillEditorProps {
  skill?: Skill;        // undefined = create mode
  onSaved?: () => void; // callback after save
}

export function SkillEditor({ skill, onSaved }: SkillEditorProps) {
  const router = useRouter();
  const isCreate = !skill;

  // Editor content
  const [content, setContent] = useState(skill?.skill_md_content ?? "");
  const [preview, setPreview] = useState(false);
  const [dirty, setDirty] = useState(false);

  // Metadata from frontmatter (auto-parsed)
  const [parsed, setParsed] = useState(() => parseFrontmatter(content));

  // Editable fields (not from frontmatter)
  const [formCategory, setFormCategory] = useState(skill?.category ?? "workflow");
  const [formTags, setFormTags] = useState(skill?.tags?.join(", ") ?? "");
  const [formScopes, setFormScopes] = useState(skill?.scopes?.join(", ") ?? "");

  // Right panel tab
  const [tab, setTab] = useState<Tab>("metadata");

  // Lint state
  const [lintFindings, setLintFindings] = useState<TESLintFinding[]>([]);
  const [lintLoading, setLintLoading] = useState(false);
  const [lintError, setLintError] = useState<string | null>(null);
  const [lintRan, setLintRan] = useState(false);

  // Promote state
  const [promoting, setPromoting] = useState(false);
  const [promoteError, setPromoteError] = useState<string | null>(null);
  const [showForceConfirm, setShowForceConfirm] = useState(false);

  // Save state
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Status change
  const [changingStatus, setChangingStatus] = useState(false);

  // Usage tab
  const [usageData, setUsageData] = useState<SkillUsageEntry[]>([]);
  const [usageLoading, setUsageLoading] = useState(false);

  // Generate modal
  const [showGenerate, setShowGenerate] = useState(false);

  // AI chat panel
  const [aiOpen, setAiOpen] = useState(false);
  useEffect(() => {
    if (localStorage.getItem(AI_PANEL_KEY) === "1") setAiOpen(true);
  }, []);
  const { data: llmConfig } = useSWR<LLMConfig>("/llm/config");
  const aiEnabled = llmConfig?.feature_flags?.skills ?? false;

  const toggleAi = useCallback(() => {
    setAiOpen((prev) => {
      const next = !prev;
      localStorage.setItem(AI_PANEL_KEY, next ? "1" : "0");
      return next;
    });
  }, []);

  // Close AI overlay on Escape
  useEffect(() => {
    if (!aiOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") toggleAi();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [aiOpen, toggleAi]);

  // Auto-parse frontmatter on content change (debounced)
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => {
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setParsed(parseFrontmatter(content));
    }, 400);
    return () => clearTimeout(timerRef.current);
  }, [content]);

  // Fetch usage when tab is selected
  useEffect(() => {
    if (tab !== "usage" || !skill) return;
    setUsageLoading(true);
    skillsApi.usage(skill.id)
      .then((res) => setUsageData(res.usage))
      .catch(() => setUsageData([]))
      .finally(() => setUsageLoading(false));
  }, [tab, skill]);

  const handleContentChange = (val: string) => {
    setContent(val);
    setDirty(true);
  };

  // Save
  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      if (isCreate) {
        // Create new skill
        const name = parsed.name || "Untitled Skill";
        const description = parsed.description || "";
        const tags = formTags.split(",").map((t) => t.trim()).filter(Boolean);
        const scopes = formScopes.split(",").map((s) => s.trim()).filter(Boolean);
        await skillsApi.create([{
          name,
          description,
          category: formCategory,
          skill_md_content: content || null,
          tags,
          scopes,
        }]);
        onSaved?.();
        router.push("/skills");
      } else {
        // Update existing skill
        const data: SkillUpdate = {
          skill_md_content: content || null,
          category: formCategory,
          tags: formTags.split(",").map((t) => t.trim()).filter(Boolean),
          scopes: formScopes.split(",").map((s) => s.trim()).filter(Boolean),
        };
        await skillsApi.update(skill.id, data);
        setDirty(false);
        onSaved?.();
      }
    } catch (e) {
      setSaveError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  // Lint
  const runLint = async () => {
    if (!skill) return;
    setLintLoading(true);
    setLintError(null);
    try {
      const res = await skillsApi.lint(skill.id);
      setLintFindings(res.findings);
      setLintRan(true);
      if (res.error_message) setLintError(res.error_message);
    } catch (e) {
      setLintError((e as Error).message);
    } finally {
      setLintLoading(false);
    }
  };

  // Promote
  const handlePromote = async (force: boolean) => {
    if (!skill) return;
    setPromoting(true);
    setPromoteError(null);
    setShowForceConfirm(false);
    try {
      await skillsApi.promote(skill.id, force);
      router.refresh();
    } catch (e) {
      const msg = (e as Error).message;
      setPromoteError(msg);
      if (!force && e instanceof ApiError && e.status === 422) {
        setShowForceConfirm(true);
      }
    } finally {
      setPromoting(false);
    }
  };

  // Status change
  const handleStatusChange = async (newStatus: SkillStatus) => {
    if (!skill) return;
    setChangingStatus(true);
    try {
      await skillsApi.update(skill.id, { status: newStatus });
      router.refresh();
    } catch (e) {
      setSaveError((e as Error).message);
    } finally {
      setChangingStatus(false);
    }
  };

  // Export
  const handleExport = async () => {
    if (!skill) return;
    try {
      const blob = await fetchBlob(`/skills/${skill.id}/export`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${skill.id}-SKILL.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setSaveError((e as Error).message);
    }
  };

  // Delete
  const handleDelete = async () => {
    if (!skill) return;
    if (!confirm("Are you sure you want to delete this skill? This cannot be undone.")) return;
    try {
      await skillsApi.remove(skill.id);
      router.push("/skills");
    } catch (e) {
      setSaveError((e as Error).message);
    }
  };

  const handleGenerated = useCallback((generatedContent: string) => {
    setContent(generatedContent);
    setDirty(true);
    setShowGenerate(false);
  }, []);

  const transitions = skill ? (validTransitions[skill.status] || []) : [];
  const catColor = getCategoryColor(formCategory);

  const tabs: { key: Tab; label: string }[] = [
    { key: "metadata", label: "Metadata" },
    ...(skill ? [
      { key: "evals" as Tab, label: `Evals (${skill.evals_json.length})` },
      { key: "lint" as Tab, label: "TESLint" },
      { key: "history" as Tab, label: `History (${skill.promotion_history.length})` },
      { key: "usage" as Tab, label: `Usage (${skill.usage_count})` },
    ] : []),
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Header bar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b bg-white">
        <button
          onClick={() => router.push("/skills")}
          className="text-xs text-gray-400 hover:text-gray-600"
        >
          &larr; Skills
        </button>

        {skill && (
          <>
            <span className="text-xs text-gray-400 font-mono">{skill.id}</span>
            <Badge variant={statusVariant(skill.status)}>{skill.status}</Badge>
          </>
        )}
        {!skill && <span className="text-xs text-gray-500">New Skill</span>}

        <div className="flex-1" />

        {/* Actions */}
        <Button
          size="sm"
          variant="secondary"
          onClick={() => setShowGenerate(true)}
        >
          Generate with AI
        </Button>

        {aiEnabled && skill && (
          <Button
            size="sm"
            variant={aiOpen ? "primary" : "secondary"}
            onClick={toggleAi}
            title={aiOpen ? "Hide AI Chat" : "Show AI Chat"}
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 inline-block mr-1">
              <path fillRule="evenodd" d="M3.43 2.524A41.29 41.29 0 0110 2c2.236 0 4.43.18 6.57.524 1.437.231 2.43 1.49 2.43 2.902v5.148c0 1.413-.993 2.67-2.43 2.902a41.102 41.102 0 01-3.55.414c-.28.02-.521.18-.643.413l-1.712 3.293a.75.75 0 01-1.33 0l-1.713-3.293a.783.783 0 00-.642-.413 41.108 41.108 0 01-3.55-.414C1.993 13.245 1 11.986 1 10.574V5.426c0-1.413.993-2.67 2.43-2.902z" clipRule="evenodd"/>
            </svg>
            AI Chat
          </Button>
        )}

        {skill && (
          <Button size="sm" variant="secondary" onClick={handleExport}>
            Export
          </Button>
        )}

        {skill && skill.status === "DRAFT" && (
          <Button
            size="sm"
            variant="secondary"
            onClick={() => handlePromote(false)}
            disabled={promoting}
          >
            {promoting ? "Promoting..." : "Promote"}
          </Button>
        )}

        <Button
          size="sm"
          onClick={handleSave}
          disabled={saving || (!dirty && !isCreate)}
        >
          {saving ? "Saving..." : isCreate ? "Create" : "Save"}
        </Button>

        {skill && (
          <Button size="sm" variant="danger" onClick={handleDelete}>
            Delete
          </Button>
        )}
      </div>

      {/* Error banner */}
      {(saveError || promoteError) && (
        <div className="flex items-center justify-between bg-red-50 border-b border-red-200 px-4 py-2">
          <p className="text-sm text-red-600">{saveError || promoteError}</p>
          <button
            onClick={() => { setSaveError(null); setPromoteError(null); }}
            className="text-xs text-red-400 hover:text-red-600"
          >
            Dismiss
          </button>
        </div>
      )}

      {showForceConfirm && (
        <div className="flex items-center gap-3 bg-amber-50 border-b border-amber-200 px-4 py-2">
          <span className="text-sm text-amber-700">Promotion gates failed. Force promote?</span>
          <Button size="sm" variant="danger" onClick={() => handlePromote(true)} disabled={promoting}>
            Force Promote
          </Button>
        </div>
      )}

      {/* Two-column layout */}
      <div className="flex flex-1 min-h-0">
        {/* Left: Editor */}
        <div className="flex-1 flex flex-col border-r min-w-0">
          {/* Edit/Preview toggle */}
          <div className="flex items-center gap-1 px-3 py-1.5 bg-gray-50 border-b text-xs">
            <button
              onClick={() => setPreview(false)}
              className={`px-2 py-1 rounded ${!preview ? "bg-white shadow-sm font-medium" : "text-gray-500"}`}
            >
              Edit
            </button>
            <button
              onClick={() => setPreview(true)}
              className={`px-2 py-1 rounded ${preview ? "bg-white shadow-sm font-medium" : "text-gray-500"}`}
            >
              Preview
            </button>
            {dirty && <span className="text-amber-500 ml-2">Unsaved changes</span>}
          </div>

          {/* Content area */}
          {preview ? (
            <div className="flex-1 overflow-auto p-4">
              <pre className="whitespace-pre-wrap font-mono text-sm">{content}</pre>
            </div>
          ) : (
            <textarea
              value={content}
              onChange={(e) => handleContentChange(e.target.value)}
              className="flex-1 p-4 font-mono text-sm resize-none focus:outline-none"
              placeholder={`---\nname: My Skill\nversion: "1.0.0"\ndescription: "What this skill does"\nallowed-tools: [Read, Glob, Grep]\n---\n\n# My Skill\n\n## Procedure\n\n1. First step...\n2. Second step...\n\n## Output Format\n\n...\n\n## Success Criteria\n\n...\n\n## Rules\n\n- ...`}
              spellCheck={false}
            />
          )}
        </div>

        {/* Right: Tabs panel */}
        <div className="w-80 flex-shrink-0 flex flex-col bg-gray-50">
          {/* Tabs */}
          <div className="flex gap-1 px-2 pt-2 border-b bg-gray-50">
            {tabs.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`px-2 py-1.5 text-xs font-medium border-b-2 transition-colors ${
                  tab === t.key
                    ? "border-forge-500 text-forge-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-auto p-3">
            {/* Metadata tab */}
            {tab === "metadata" && (
              <div className="space-y-4">
                {/* Parsed frontmatter (read-only) */}
                <div>
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    From Frontmatter
                  </h4>
                  {parsed.valid ? (
                    <div className="space-y-2 text-sm">
                      <div>
                        <span className="text-xs text-gray-400">Name</span>
                        <p className="font-medium">{parsed.name}</p>
                      </div>
                      <div>
                        <span className="text-xs text-gray-400">Description</span>
                        <p className="text-gray-600 text-xs">{parsed.description}</p>
                      </div>
                      {parsed.version && (
                        <div>
                          <span className="text-xs text-gray-400">Version</span>
                          <p>{parsed.version}</p>
                        </div>
                      )}
                      {parsed.allowedTools.length > 0 && (
                        <div>
                          <span className="text-xs text-gray-400">Allowed Tools</span>
                          <div className="flex flex-wrap gap-1 mt-0.5">
                            {parsed.allowedTools.map((t) => (
                              <span key={t} className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                                {t}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {parsed.errors.map((e, i) => (
                        <p key={i} className="text-xs text-amber-600">{e}</p>
                      ))}
                      {parsed.errors.length === 0 && (
                        <p className="text-xs text-gray-400 italic">
                          Add YAML frontmatter to see parsed metadata
                        </p>
                      )}
                    </div>
                  )}
                </div>

                <hr />

                {/* Editable fields */}
                <div>
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    Skill Settings
                  </h4>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Category</label>
                      <select
                        value={formCategory}
                        onChange={(e) => { setFormCategory(e.target.value); setDirty(true); }}
                        className="w-full rounded-md border px-2 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
                      >
                        {CATEGORIES.map((c) => (
                          <option key={c} value={c}>
                            {categoryLabel(c)}
                          </option>
                        ))}
                      </select>
                      <div className="flex items-center gap-1 mt-1">
                        <span className={`w-2 h-2 rounded-full ${catColor.dot}`} />
                        <span className={`text-[10px] ${catColor.text}`}>
                          {categoryLabel(formCategory)}
                        </span>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Tags (comma-separated)</label>
                      <input
                        type="text"
                        value={formTags}
                        onChange={(e) => { setFormTags(e.target.value); setDirty(true); }}
                        placeholder="security, code-review"
                        className="w-full rounded-md border px-2 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Scopes (comma-separated)</label>
                      <input
                        type="text"
                        value={formScopes}
                        onChange={(e) => { setFormScopes(e.target.value); setDirty(true); }}
                        placeholder="backend, frontend"
                        className="w-full rounded-md border px-2 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
                      />
                    </div>
                  </div>
                </div>

                {/* Status transitions */}
                {skill && transitions.length > 0 && (
                  <>
                    <hr />
                    <div>
                      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                        Status Actions
                      </h4>
                      <div className="flex flex-wrap gap-2">
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
                                  if (!confirm(`Are you sure you want to ${label} this skill?`)) return;
                                }
                                handleStatusChange(ts);
                              }}
                              disabled={changingStatus}
                            >
                              {ts === "DEPRECATED" ? "Deprecate" : ts === "ARCHIVED" ? "Archive" : `Set ${ts}`}
                            </Button>
                          );
                        })}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Evals tab */}
            {tab === "evals" && skill && (
              <div>
                {skill.evals_json.length === 0 ? (
                  <p className="text-xs text-gray-400">No evals defined.</p>
                ) : (
                  <div className="space-y-2">
                    {skill.evals_json.map((ev, i) => (
                      <div key={i} className="rounded border bg-white p-2">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge>Eval #{i + 1}</Badge>
                          {"name" in ev && ev.name ? <span className="text-xs font-medium">{String(ev.name)}</span> : null}
                        </div>
                        <pre className="text-[10px] bg-gray-50 rounded p-2 overflow-x-auto">
                          {JSON.stringify(ev, null, 2)}
                        </pre>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* TESLint tab */}
            {tab === "lint" && skill && (
              <div>
                <Button size="sm" onClick={runLint} disabled={lintLoading} className="mb-3">
                  {lintLoading ? "Running..." : "Run Lint"}
                </Button>
                {lintError && <p className="text-xs text-amber-600 mb-2">{lintError}</p>}
                {lintRan && lintFindings.length === 0 && !lintError && (
                  <div className="rounded border border-green-200 bg-green-50 p-3 text-center">
                    <p className="text-xs text-green-700">All checks passed</p>
                  </div>
                )}
                {lintFindings.length > 0 && (
                  <div className="space-y-2">
                    {lintFindings.map((f, i) => (
                      <div
                        key={i}
                        className={`rounded border p-2 text-xs ${
                          f.severity === "error"
                            ? "border-red-200 bg-red-50"
                            : f.severity === "warning"
                            ? "border-yellow-200 bg-yellow-50"
                            : "border-blue-200 bg-blue-50"
                        }`}
                      >
                        <div className="flex items-center gap-1">
                          <Badge
                            variant={
                              f.severity === "error" ? "danger" :
                              f.severity === "warning" ? "warning" : "info"
                            }
                          >
                            {f.severity}
                          </Badge>
                          <span className="text-gray-500">{f.rule_id}</span>
                        </div>
                        <p className="mt-1">{f.message}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Usage tab */}
            {tab === "usage" && skill && (
              <div>
                {usageLoading ? (
                  <p className="text-xs text-gray-400">Loading usage data...</p>
                ) : usageData.length === 0 ? (
                  <p className="text-xs text-gray-400">No tasks reference this skill yet.</p>
                ) : (
                  <div className="space-y-1.5">
                    {usageData.map((u) => (
                      <a
                        key={`${u.project}-${u.task_id}`}
                        href={`/projects/${u.project}/tasks/${u.task_id}`}
                        className="flex items-center gap-2 rounded border bg-white p-2 hover:bg-gray-50 transition-colors"
                      >
                        <span className="text-xs font-mono text-forge-600">{u.task_id}</span>
                        <span className="text-xs text-gray-700 truncate flex-1">{u.task_name}</span>
                        <Badge variant={statusVariant(u.status)}>{u.status}</Badge>
                      </a>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* History tab */}
            {tab === "history" && skill && (
              <div>
                {skill.promotion_history.length === 0 ? (
                  <p className="text-xs text-gray-400">No promotion attempts.</p>
                ) : (
                  <div className="space-y-2">
                    {[...skill.promotion_history].reverse().map((entry: PromotionHistoryEntry, i: number) => (
                      <div key={i} className="rounded border bg-white p-2">
                        <div className="flex items-center justify-between mb-1">
                          <Badge variant={entry.forced ? "warning" : "success"}>
                            {entry.forced ? "Forced" : "Clean"}
                          </Badge>
                          <span className="text-[10px] text-gray-400">
                            {new Date(entry.promoted_at).toLocaleString()}
                          </span>
                        </div>
                        <div className="space-y-0.5">
                          {entry.gates.map((g, gi) => (
                            <div key={gi} className="flex items-center gap-1 text-[10px]">
                              <span className={g.passed ? "text-green-600" : "text-red-600"}>
                                {g.passed ? "PASS" : "FAIL"}
                              </span>
                              <span className="font-medium">{g.gate}</span>
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
        </div>

        {/* AI Chat panel — collapsible third column */}
        {aiEnabled && skill && aiOpen && (
          <>
            {/* Desktop: inline panel */}
            <div className="hidden xl:flex w-96 flex-shrink-0 flex-col border-l bg-white">
              <LLMChat
                contextType="skill"
                contextId={skill.id}
                className="h-full border-0 rounded-none"
              />
            </div>
            {/* Mobile/tablet: overlay drawer */}
            <div className="xl:hidden fixed inset-0 z-50 flex">
              <div className="flex-1 bg-black/30" onClick={toggleAi} />
              <div className="w-96 max-w-full flex flex-col bg-white shadow-xl">
                <LLMChat
                  contextType="skill"
                  contextId={skill.id}
                  className="flex-1 border-0 rounded-none"
                />
              </div>
            </div>
          </>
        )}
      </div>

      {/* Generate modal */}
      {showGenerate && (
        <GenerateSkillModal
          onGenerated={handleGenerated}
          onClose={() => setShowGenerate(false)}
        />
      )}
    </div>
  );
}
