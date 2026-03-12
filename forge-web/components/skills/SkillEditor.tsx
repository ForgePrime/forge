"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { skills as skillsApi, ApiError, fetchBlob } from "@/lib/api";
import { Badge, statusVariant } from "@/components/shared/Badge";
import { Button } from "@/components/shared/Button";
import { SkillFileTree } from "./SkillFileTree";
import { parseFrontmatter, serializeFrontmatter } from "@/lib/utils/parseFrontmatter";
import { getCategoryColor, categoryLabel } from "@/lib/utils/categoryColors";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type {
  Skill,
  SkillStatus,
  SkillUpdate,
  SkillFile,
  SkillUsageEntry,
  TESLintFinding,
  PromotionHistoryEntry,
  ValidationResult,
} from "@/lib/types";

type Tab = "metadata" | "lint" | "history" | "usage" | "files";

const CATEGORIES = [
  "workflow", "analysis", "generation", "validation", "integration",
  "refactoring", "testing", "deployment", "documentation", "custom",
];

const validTransitions: Record<string, SkillStatus[]> = {
  DRAFT: ["DEPRECATED"],
  ACTIVE: ["DEPRECATED"],
  DEPRECATED: ["ARCHIVED", "ACTIVE"],
  ARCHIVED: ["DRAFT"],
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

  // Editable fields
  const [formCategories, setFormCategories] = useState<string[]>(
    skill?.categories ?? ["workflow"]
  );
  const [formTags, setFormTags] = useState(skill?.tags?.join(", ") ?? "");
  const [formScopes, setFormScopes] = useState(skill?.scopes?.join(", ") ?? "");
  const [formSync, setFormSync] = useState(skill?.sync ?? false);

  // Sync to repo state
  const [syncing, setSyncing] = useState(false);

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

  // Validation state
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [validating, setValidating] = useState(false);

  // Multi-file state
  const [activeFile, setActiveFile] = useState("SKILL.md");
  const [files, setFiles] = useState<SkillFile[]>(skill?.files ?? []);
  const [fileContents, setFileContents] = useState<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    for (const f of (skill?.files ?? [])) map[f.path] = f.content;
    return map;
  });
  const [dirtyFiles, setDirtyFiles] = useState<Set<string>>(new Set());

  // Pending file deletes (for confirm in right panel)
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  // Resizable file tree panel
  const [treeWidth, setTreeWidth] = useState(240);
  const resizingRef = useRef(false);

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
    skillsApi.usage(skill.name)
      .then((res) => setUsageData(res.usage))
      .catch(() => setUsageData([]))
      .finally(() => setUsageLoading(false));
  }, [tab, skill]);

  // Auto-generate SKILL.md frontmatter for create mode
  useEffect(() => {
    if (!isCreate || content) return;
    // Generate initial frontmatter
    setContent(
      `---\nname: new-skill\nversion: "1.0.0"\ndescription: "Describe what this skill does"\nallowed-tools: [Read, Glob, Grep]\n---\n\n# New Skill\n\n## Procedure\n\n1. First step...\n\n## Output Format\n\n...\n\n## Success Criteria\n\n- [ ] ...\n\n## Rules\n\n- ...\n`
    );
  }, [isCreate, content]);

  const handleContentChange = (val: string) => {
    if (activeFile === "SKILL.md") {
      setContent(val);
      setDirty(true);
    } else {
      setFileContents((prev) => ({ ...prev, [activeFile]: val }));
      setDirtyFiles((prev) => new Set(prev).add(activeFile));
    }
  };

  // File tree handlers
  const handleFileSelect = useCallback((path: string) => {
    setActiveFile(path);
  }, []);

  const handleFileAdd = useCallback((folder: string, name: string) => {
    const path = `${folder}${name}`;
    if (files.some((f) => f.path === path)) return;
    const fileType = folder === "scripts/" ? "script" as const
      : folder === "references/" ? "reference" as const
      : folder === "assets/" ? "asset" as const
      : "other" as const;
    const newFile: SkillFile = { path, content: "", file_type: fileType };
    setFiles((prev) => [...prev, newFile]);
    setFileContents((prev) => ({ ...prev, [path]: "" }));
    setDirtyFiles((prev) => new Set(prev).add(path));
    setActiveFile(path);
  }, [files]);

  const handleFileDelete = useCallback((path: string) => {
    // Move delete to right panel for confirmation
    setPendingDelete(path);
    setTab("files");
  }, []);

  const confirmDelete = useCallback(async () => {
    if (!pendingDelete) return;
    const path = pendingDelete;
    // Delete via API if editing existing skill
    if (skill) {
      try {
        await skillsApi.deleteFile(skill.name, path);
      } catch {
        // Ignore — file may not exist on server yet
      }
    }
    setFiles((prev) => prev.filter((f) => f.path !== path));
    setFileContents((prev) => {
      const next = { ...prev };
      delete next[path];
      return next;
    });
    if (activeFile === path) setActiveFile("SKILL.md");
    setPendingDelete(null);
  }, [pendingDelete, skill, activeFile]);

  const handleDropFiles = useCallback((newFiles: SkillFile[]) => {
    // Handle overwrite: replace existing files
    setFiles((prev) => {
      const newPaths = new Set(newFiles.map((f) => f.path));
      return [...prev.filter((f) => !newPaths.has(f.path)), ...newFiles];
    });
    setFileContents((prev) => {
      const next = { ...prev };
      for (const f of newFiles) next[f.path] = f.content;
      return next;
    });
    setDirtyFiles((prev) => {
      const next = new Set(prev);
      for (const f of newFiles) next.add(f.path);
      return next;
    });
  }, []);

  const handleMoveFile = useCallback(async (oldPath: string, newPath: string) => {
    // Call API for existing skills
    if (skill) {
      try {
        await skillsApi.moveFile(skill.name, oldPath, newPath);
      } catch (e) {
        setSaveError((e as Error).message);
        return;
      }
    }
    // Update local state
    const oldContent = fileContents[oldPath] ?? "";
    const newFileType = newPath.startsWith("scripts/") ? "script" as const
      : newPath.startsWith("references/") ? "reference" as const
      : newPath.startsWith("assets/") ? "asset" as const
      : "other" as const;
    setFiles((prev) => prev.map((f) =>
      f.path === oldPath ? { path: newPath, content: oldContent, file_type: newFileType } : f
    ));
    setFileContents((prev) => {
      const next = { ...prev };
      next[newPath] = oldContent;
      delete next[oldPath];
      return next;
    });
    if (activeFile === oldPath) setActiveFile(newPath);
  }, [skill, fileContents, activeFile]);

  // Toggle category in multi-select
  const toggleCategory = useCallback((cat: string) => {
    setFormCategories((prev) => {
      if (prev.includes(cat)) {
        if (prev.length <= 1) return prev; // min 1
        return prev.filter((c) => c !== cat);
      }
      return [...prev, cat];
    });
    setDirty(true);
  }, []);

  // Validate
  const handleValidate = useCallback(async () => {
    if (!skill) return;
    setValidating(true);
    try {
      const result = await skillsApi.validate(skill.name);
      setValidation(result);
    } catch {
      setValidation({ name: skill.name, valid: false, errors: ["Validation request failed"], warnings: [], error_count: 1, warning_count: 0 });
    } finally {
      setValidating(false);
    }
  }, [skill]);

  // Save
  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      if (isCreate) {
        const name = parsed.name || "new-skill";
        const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
        const description = parsed.description || "";
        const tags = formTags.split(",").map((t) => t.trim()).filter(Boolean);
        const scopes = formScopes.split(",").map((s) => s.trim()).filter(Boolean);
        const result = await skillsApi.create({
          name: slug,
          description,
          categories: formCategories,
          skill_md_content: content || null,
          tags,
          scopes,
        });
        // Save any bundled files
        for (const f of files) {
          const fc = fileContents[f.path];
          if (fc !== undefined) {
            await skillsApi.saveFile(result.name, f.path, fc);
          }
        }
        onSaved?.();
        router.push(`/skills/${result.name}`);
      } else {
        // Update existing skill
        const data: SkillUpdate = {
          skill_md_content: content || null,
          categories: formCategories,
          tags: formTags.split(",").map((t) => t.trim()).filter(Boolean),
          scopes: formScopes.split(",").map((s) => s.trim()).filter(Boolean),
          sync: formSync,
        };
        await skillsApi.update(skill.name, data);

        // Save dirty files individually
        for (const path of Array.from(dirtyFiles)) {
          if (path === "__deleted__") continue;
          const fc = fileContents[path];
          if (fc !== undefined) {
            await skillsApi.saveFile(skill.name, path, fc);
          }
        }
        setDirtyFiles(new Set());
        setDirty(false);
        onSaved?.();

        // Run validation after save (non-blocking)
        try {
          const v = await skillsApi.validate(skill.name);
          setValidation(v);
        } catch { /* ignore */ }
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
      const res = await skillsApi.lint(skill.name);
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
      await skillsApi.promote(skill.name, force);
      onSaved?.();
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
      await skillsApi.update(skill.name, { status: newStatus });
      onSaved?.();
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
      const blob = await fetchBlob(`/skills/${skill.name}/export`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${skill.name}-SKILL.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setSaveError((e as Error).message);
    }
  };

  // Sync to repo
  const handleSyncToRepo = async () => {
    if (!skill) return;
    setSyncing(true);
    setSaveError(null);
    try {
      // Ensure sync is enabled, save, then push
      if (!formSync) {
        setFormSync(true);
        await skillsApi.update(skill.name, { sync: true });
      }
      await skillsApi.gitPush(`Sync ${skill.name}`);
      onSaved?.();
    } catch (e) {
      setSaveError((e as Error).message);
    } finally {
      setSyncing(false);
    }
  };

  // Delete
  const handleDelete = async () => {
    if (!skill) return;
    if (!confirm("Are you sure you want to delete this skill? This cannot be undone.")) return;
    try {
      await skillsApi.remove(skill.name);
      router.push("/skills");
    } catch (e) {
      setSaveError((e as Error).message);
    }
  };

  const transitions = skill ? (validTransitions[skill.status] || []) : [];

  const tabs: { key: Tab; label: string }[] = [
    { key: "metadata", label: "Metadata" },
    { key: "files", label: `Files (${files.length})` },
    ...(skill ? [
      { key: "lint" as Tab, label: "Lint" },
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
            <span className="text-xs text-gray-500 font-mono">{skill.name}</span>
            <Badge variant={statusVariant(skill.status)}>{skill.status}</Badge>
            {formSync ? (
              <span className="text-[10px] text-blue-500" title="Sync enabled — pushed to git repo">
                &#9729; sync
              </span>
            ) : (
              <span className="text-[10px] text-gray-400" title="Local only — not synced to git">
                &#9729; local
              </span>
            )}
          </>
        )}
        {!skill && <span className="text-xs text-gray-500">New Skill</span>}

        <div className="flex-1" />

        {/* Actions */}
        {skill && (
          <Button
            size="sm"
            variant="secondary"
            onClick={handleSyncToRepo}
            disabled={syncing}
            title={formSync ? "Push to git repo" : "Enable sync and push"}
          >
            {syncing ? "Syncing..." : "Sync to Repo"}
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
          disabled={saving || (!dirty && dirtyFiles.size === 0 && !isCreate)}
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

      {/* Three-column layout: file tree | editor | tabs panel */}
      <div className="flex flex-1 min-h-0">
        {/* Left: File tree (resizable) */}
        <div
          className="flex-shrink-0 border-r bg-gray-50 overflow-y-auto"
          style={{ width: treeWidth, minWidth: 160, maxWidth: 400 }}
        >
          <div className="px-2 py-1.5 border-b text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
            Files
          </div>
          <SkillFileTree
            files={files}
            activeFile={activeFile}
            onSelect={handleFileSelect}
            onAdd={handleFileAdd}
            onDelete={handleFileDelete}
            onDropFiles={handleDropFiles}
            onMoveFile={handleMoveFile}
          />
        </div>
        {/* Resize handle */}
        <div
          className="w-1 cursor-col-resize bg-transparent hover:bg-forge-200 active:bg-forge-300 flex-shrink-0"
          onMouseDown={(e) => {
            e.preventDefault();
            resizingRef.current = true;
            const startX = e.clientX;
            const startW = treeWidth;
            const onMove = (ev: MouseEvent) => {
              if (!resizingRef.current) return;
              const newW = Math.max(160, Math.min(400, startW + ev.clientX - startX));
              setTreeWidth(newW);
            };
            const onUp = () => {
              resizingRef.current = false;
              document.removeEventListener("mousemove", onMove);
              document.removeEventListener("mouseup", onUp);
            };
            document.addEventListener("mousemove", onMove);
            document.addEventListener("mouseup", onUp);
          }}
        />

        {/* Center: Editor */}
        <div className="flex-1 flex flex-col border-r min-w-0">
          {/* Edit/Preview toggle + active file indicator */}
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
            <span className="text-gray-400 ml-2 font-mono">{activeFile}</span>
            {(dirty || dirtyFiles.size > 0) && (
              <span className="text-amber-500 ml-2">Unsaved changes</span>
            )}
          </div>

          {/* Content area */}
          {(() => {
            const isSkillMd = activeFile === "SKILL.md";
            const currentContent = isSkillMd ? content : (fileContents[activeFile] ?? "");

            if (preview) {
              // Strip YAML frontmatter for preview
              const previewBody = currentContent.replace(/^---[\s\S]*?---\n*/, "");
              return (
                <div className="flex-1 overflow-auto p-6">
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        pre: ({ children }) => (
                          <pre className="overflow-x-auto rounded-lg bg-gray-900 p-3 text-xs text-gray-100">
                            {children}
                          </pre>
                        ),
                        code: ({ children, className }) => {
                          const isBlock = className?.startsWith("language-");
                          if (isBlock) return <code className={className}>{children}</code>;
                          return (
                            <code className="rounded px-1.5 py-0.5 text-xs bg-gray-100 text-gray-800">
                              {children}
                            </code>
                          );
                        },
                        a: ({ href, children }) => (
                          <a href={href} target="_blank" rel="noopener noreferrer"
                            className="text-forge-600 underline hover:text-forge-800">
                            {children}
                          </a>
                        ),
                      }}
                    >
                      {previewBody}
                    </ReactMarkdown>
                  </div>
                </div>
              );
            }

            return (
              <textarea
                key={activeFile}
                value={currentContent}
                onChange={(e) => handleContentChange(e.target.value)}
                className="flex-1 p-4 font-mono text-sm resize-none focus:outline-none"
                placeholder={isSkillMd
                  ? `---\nname: My Skill\nversion: "1.0.0"\ndescription: "What this skill does"\nallowed-tools: [Read, Glob, Grep]\n---\n\n# My Skill\n\n## Procedure\n\n1. First step...\n2. Second step...\n\n## Output Format\n\n...\n\n## Success Criteria\n\n...\n\n## Rules\n\n- ...`
                  : `# ${activeFile}\n\nFile content goes here...`}
                spellCheck={false}
              />
            );
          })()}
        </div>

        {/* Right: Tabs panel */}
        <div className="w-80 flex-shrink-0 flex flex-col bg-gray-50">
          {/* Tabs */}
          <div className="flex gap-1 px-2 pt-2 border-b bg-gray-50 flex-wrap">
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
                {/* Editable frontmatter fields */}
                <div>
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    Frontmatter
                  </h4>
                  {parsed.valid ? (
                    <div className="space-y-2.5" key={`fm-${parsed.name}-${parsed.version}-${parsed.description?.slice(0, 20)}`}>
                      <div>
                        <label className="block text-xs text-gray-400 mb-0.5">Name (display)</label>
                        <input
                          type="text"
                          defaultValue={parsed.name ?? ""}
                          onBlur={(e) => {
                            const val = e.target.value.trim();
                            if (val && val !== parsed.name) {
                              const newContent = serializeFrontmatter(
                                { name: val },
                                parsed.raw,
                                parsed.body,
                              );
                              setContent(newContent);
                              setDirty(true);
                            }
                          }}
                          className="w-full text-lg font-bold border-b border-gray-200 focus:border-forge-500 outline-none pb-0.5 bg-transparent"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-400 mb-0.5">Description</label>
                        <textarea
                          defaultValue={parsed.description ?? ""}
                          rows={2}
                          onBlur={(e) => {
                            const val = e.target.value.trim();
                            if (val !== (parsed.description ?? "")) {
                              const newContent = serializeFrontmatter(
                                { description: val },
                                parsed.raw,
                                parsed.body,
                              );
                              setContent(newContent);
                              setDirty(true);
                            }
                          }}
                          className="w-full rounded-md border px-2 py-1.5 text-xs text-gray-600 focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-400 mb-0.5">Version</label>
                        <input
                          type="text"
                          defaultValue={parsed.version ?? ""}
                          onBlur={(e) => {
                            const val = e.target.value.trim();
                            if (val !== (parsed.version ?? "")) {
                              const newContent = serializeFrontmatter(
                                { version: val || undefined },
                                parsed.raw,
                                parsed.body,
                              );
                              setContent(newContent);
                              setDirty(true);
                            }
                          }}
                          className="w-full rounded-md border px-2 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-400 mb-0.5">Allowed Tools (comma-separated)</label>
                        <input
                          type="text"
                          defaultValue={parsed.allowedTools.join(", ")}
                          onBlur={(e) => {
                            const tools = e.target.value.split(",").map((t) => t.trim()).filter(Boolean);
                            const newContent = serializeFrontmatter(
                              { allowedTools: tools },
                              parsed.raw,
                              parsed.body,
                            );
                            setContent(newContent);
                            setDirty(true);
                          }}
                          className="w-full rounded-md border px-2 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
                        />
                      </div>
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

                {/* Validation section */}
                {skill && (
                  <>
                    <hr />
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                          Spec Validation
                        </h4>
                        <Button size="sm" variant="secondary" onClick={handleValidate} disabled={validating}>
                          {validating ? "Checking..." : "Validate"}
                        </Button>
                      </div>

                      {content && (() => {
                        const lineCount = content.split("\n").length;
                        const warn = lineCount > 500;
                        return (
                          <p className={`text-[10px] mb-1.5 ${warn ? "text-amber-600" : "text-gray-400"}`}>
                            SKILL.md: {lineCount} lines{warn ? " (recommended max 500)" : ""}
                          </p>
                        );
                      })()}

                      {validation && (
                        <div className="space-y-1.5">
                          <div className={`flex items-center gap-1.5 text-xs font-medium ${
                            validation.valid ? "text-green-600" : "text-red-600"
                          }`}>
                            <span>{validation.valid ? "\u2713" : "\u2717"}</span>
                            <span>{validation.valid ? "Valid" : `${validation.error_count} error(s)`}</span>
                            {validation.warning_count > 0 && (
                              <span className="text-amber-500 font-normal ml-1">
                                {validation.warning_count} warning(s)
                              </span>
                            )}
                          </div>
                          {validation.errors.map((e, i) => (
                            <p key={`e-${i}`} className="text-[10px] text-red-600 pl-4">{e}</p>
                          ))}
                          {validation.warnings.map((w, i) => (
                            <p key={`w-${i}`} className="text-[10px] text-amber-500 pl-4">{w}</p>
                          ))}
                        </div>
                      )}
                    </div>
                  </>
                )}

                <hr />

                {/* Editable fields */}
                <div>
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    Skill Settings
                  </h4>
                  <div className="space-y-3">
                    {/* Categories multi-select */}
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Categories</label>
                      <div className="flex flex-wrap gap-1.5">
                        {CATEGORIES.map((c) => {
                          const active = formCategories.includes(c);
                          const color = getCategoryColor(c);
                          return (
                            <button
                              key={c}
                              type="button"
                              onClick={() => toggleCategory(c)}
                              className={`text-[10px] px-2 py-1 rounded-full border transition-colors ${
                                active
                                  ? `${color.bg} ${color.text} border-current font-medium`
                                  : "bg-white text-gray-400 border-gray-200 hover:border-gray-400"
                              }`}
                            >
                              {categoryLabel(c)}
                            </button>
                          );
                        })}
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

                    {/* Sync toggle */}
                    {!isCreate && (
                      <div className="flex items-center justify-between">
                        <div>
                          <label className="block text-xs text-gray-500">Git Sync</label>
                          <p className="text-[10px] text-gray-400">
                            {formSync ? "Included in git push" : "Local only"}
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => { setFormSync(!formSync); setDirty(true); }}
                          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                            formSync ? "bg-blue-500" : "bg-gray-300"
                          }`}
                        >
                          <span
                            className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow transition-transform ${
                              formSync ? "translate-x-[18px]" : "translate-x-[2px]"
                            }`}
                          />
                        </button>
                      </div>
                    )}
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
                          const isActivating = ts === "ACTIVE" || ts === "DRAFT";
                          return (
                            <Button
                              key={ts}
                              size="sm"
                              variant={isDestructive ? "danger" : isActivating ? "success" : "secondary"}
                              onClick={() => {
                                if (isDestructive) {
                                  const label = ts === "DEPRECATED" ? "deprecate" : "archive";
                                  if (!confirm(`Are you sure you want to ${label} this skill?`)) return;
                                }
                                handleStatusChange(ts);
                              }}
                              disabled={changingStatus}
                            >
                              {ts === "DEPRECATED" ? "Deprecate"
                                : ts === "ARCHIVED" ? "Archive"
                                : ts === "ACTIVE" ? "Set ACTIVE"
                                : ts === "DRAFT" ? "Reactivate"
                                : `Set ${ts}`}
                            </Button>
                          );
                        })}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Files tab (with delete confirmation) */}
            {tab === "files" && (
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Bundled Files
                </h4>
                {files.length === 0 && (
                  <p className="text-xs text-gray-400 italic">No bundled files yet.</p>
                )}
                {files.map((f) => (
                  <div key={f.path} className="flex items-center justify-between text-xs bg-white rounded border p-2">
                    <span className="font-mono text-gray-700 truncate">{f.path}</span>
                    <button
                      onClick={() => setPendingDelete(f.path)}
                      className="text-red-400 hover:text-red-600 ml-2 flex-shrink-0"
                    >
                      Delete
                    </button>
                  </div>
                ))}

                {/* Delete confirmation */}
                {pendingDelete && (
                  <div className="rounded border border-red-200 bg-red-50 p-3 space-y-2">
                    <p className="text-xs text-red-700">
                      Delete <span className="font-mono font-medium">{pendingDelete}</span>?
                    </p>
                    <div className="flex gap-2">
                      <Button size="sm" variant="danger" onClick={confirmDelete}>
                        Confirm Delete
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => setPendingDelete(null)}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Lint tab */}
            {tab === "lint" && skill && (
              <div>
                <p className="text-xs text-gray-400 mb-3">
                  Validates SKILL.md structure: frontmatter fields, instruction quality, naming conventions, and best practices.
                </p>
                <Button size="sm" onClick={runLint} disabled={lintLoading} className="mb-3">
                  {lintLoading ? "Checking..." : "Run Lint Check"}
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
                          <span className="text-gray-500 font-mono">{f.rule_id}</span>
                          {f.line && <span className="text-gray-400 ml-auto">line {f.line}</span>}
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
                          {(entry.gates ?? []).map((g, gi) => (
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

      </div>
    </div>
  );
}
