"use client";

import { useState, useCallback, useRef, useMemo } from "react";
import type { SkillFile, SkillFileType } from "@/lib/types";

const DEFAULT_FOLDERS = ["scripts/", "references/", "assets/"] as const;

const FOLDER_ICONS: Record<string, string> = {
  "scripts/": "\u{1F4DC}",
  "references/": "\u{1F4D6}",
  "assets/": "\u{1F4E6}",
};

const ALLOWED_EXTENSIONS = new Set([
  ".md", ".txt", ".py", ".js", ".ts", ".json", ".yaml", ".yml", ".sh", ".css", ".html",
]);
const MAX_DROP_FILES = 10;
const MAX_FILE_SIZE = 1024 * 1024; // 1MB

/** Map file extension to target directory and file_type. */
function classifyFile(name: string): { folder: string; file_type: SkillFileType } {
  const ext = name.includes(".") ? "." + name.split(".").pop()!.toLowerCase() : "";
  if ([".py", ".sh", ".js", ".ts"].includes(ext)) return { folder: "scripts/", file_type: "script" };
  if ([".md", ".txt"].includes(ext)) return { folder: "references/", file_type: "reference" };
  return { folder: "assets/", file_type: "asset" };
}

function fileTypeForFolder(folder: string): SkillFileType {
  if (folder.startsWith("scripts")) return "script";
  if (folder.startsWith("references")) return "reference";
  if (folder.startsWith("assets")) return "asset";
  return "other";
}

interface SkillFileTreeProps {
  files: SkillFile[];
  activeFile: string;
  onSelect: (path: string) => void;
  onAdd: (folder: string, name: string) => void;
  onDelete: (path: string) => void;
  onDropFiles?: (newFiles: SkillFile[]) => void;
  onMoveFile?: (oldPath: string, newPath: string) => void;
  readOnly?: boolean;
}

type OverwritePrompt = {
  file: SkillFile;
  existingPath: string;
  resolve: (action: "overwrite" | "rename" | "cancel") => void;
};

export function SkillFileTree({
  files,
  activeFile,
  onSelect,
  onAdd,
  onDelete,
  onDropFiles,
  onMoveFile,
  readOnly,
}: SkillFileTreeProps) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [adding, setAdding] = useState<string | null>(null); // folder prefix for new file
  const [addingFolder, setAddingFolder] = useState<string | null>(null); // parent prefix for new folder
  const [newName, setNewName] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [dragOverFolder, setDragOverFolder] = useState<string | null>(null);
  const [dropError, setDropError] = useState<string | null>(null);
  const [draggingFile, setDraggingFile] = useState<string | null>(null);
  const [overwritePrompt, setOverwritePrompt] = useState<OverwritePrompt | null>(null);
  // Custom folders (created by user, not derived from files)
  const [customFolders, setCustomFolders] = useState<Set<string>>(new Set());
  const uploadRefs = useRef<Record<string, HTMLInputElement | null>>({});
  const rootUploadRef = useRef<HTMLInputElement | null>(null);

  // Filter out .keep files from display
  const visibleFiles = useMemo(() =>
    files.filter((f) => !f.path.endsWith("/.keep") && f.path !== ".keep"),
  [files]);

  // Compute all folders dynamically: defaults + from file paths + custom
  const allFolders = useMemo(() => {
    const folderSet = new Set<string>(DEFAULT_FOLDERS);
    customFolders.forEach((f) => folderSet.add(f));
    for (const f of files) {
      const lastSlash = f.path.lastIndexOf("/");
      if (lastSlash > 0) {
        const folder = f.path.substring(0, lastSlash + 1);
        folderSet.add(folder);
        const parts = folder.split("/").filter(Boolean);
        for (let i = 1; i < parts.length; i++) {
          folderSet.add(parts.slice(0, i).join("/") + "/");
        }
      }
    }
    return Array.from(folderSet).sort();
  }, [files, customFolders]);

  const topFolders = useMemo(() => {
    return allFolders.filter((f) => {
      const parts = f.split("/").filter(Boolean);
      return parts.length === 1;
    });
  }, [allFolders]);

  const getSubFolders = useCallback((parentPrefix: string) => {
    return allFolders.filter((f) => {
      if (f === parentPrefix) return false;
      if (!f.startsWith(parentPrefix)) return false;
      const rest = f.substring(parentPrefix.length);
      const parts = rest.split("/").filter(Boolean);
      return parts.length === 1;
    });
  }, [allFolders]);

  const toggleFolder = (prefix: string) => {
    setCollapsed((prev) => ({ ...prev, [prefix]: !prev[prefix] }));
  };

  const filesInFolder = (prefix: string) =>
    visibleFiles.filter((f) => {
      if (!f.path.startsWith(prefix)) return false;
      const rest = f.path.substring(prefix.length);
      return !rest.includes("/");
    });

  const rootFiles = visibleFiles.filter((f) => !f.path.includes("/"));

  const handleAdd = (folder: string) => {
    const trimmed = newName.trim();
    if (!trimmed) return;
    onAdd(folder, trimmed);
    setNewName("");
    setAdding(null);
  };

  const handleAddFolder = (parentPrefix: string) => {
    const trimmed = newName.trim().replace(/\//g, "");
    if (!trimmed) return;
    const folderPath = `${parentPrefix}${trimmed}/`;
    setCustomFolders((prev) => new Set(prev).add(folderPath));
    setNewName("");
    setAddingFolder(null);
  };

  const canDeleteFolder = useCallback((prefix: string) => {
    const isDefault = (DEFAULT_FOLDERS as readonly string[]).includes(prefix);
    if (isDefault) return false;
    const children = files.filter((f) => f.path.startsWith(prefix));
    return children.length === 0;
  }, [files]);

  const handleDeleteFolder = useCallback((prefix: string) => {
    // Remove any hidden files (.keep)
    const hiddenFiles = files.filter(
      (f) => f.path.startsWith(prefix) && f.path.endsWith(".keep"),
    );
    for (const f of hiddenFiles) onDelete(f.path);
    // Remove from custom folders
    setCustomFolders((prev) => {
      const next = new Set(prev);
      next.delete(prefix);
      return next;
    });
  }, [files, onDelete]);

  const cancelAdd = () => {
    setNewName("");
    setAdding(null);
    setAddingFolder(null);
  };

  // Upload handler
  const handleUpload = useCallback(async (folder: string, fileList: FileList | null) => {
    if (!fileList || !onDropFiles) return;
    const existingPaths = new Set(files.map((f) => f.path));
    const newFiles: SkillFile[] = [];
    const errors: string[] = [];

    for (const file of Array.from(fileList)) {
      const ext = file.name.includes(".") ? "." + file.name.split(".").pop()!.toLowerCase() : "";
      if (!ALLOWED_EXTENSIONS.has(ext)) {
        errors.push(`${file.name}: unsupported extension`);
        continue;
      }
      if (file.size > MAX_FILE_SIZE) {
        errors.push(`${file.name}: too large (max 1MB)`);
        continue;
      }
      const path = `${folder}${file.name}`;
      const file_type = fileTypeForFolder(folder);

      if (existingPaths.has(path)) {
        const action = await new Promise<"overwrite" | "rename" | "cancel">((resolve) => {
          setOverwritePrompt({ file: { path, content: "", file_type }, existingPath: path, resolve });
        });
        setOverwritePrompt(null);
        if (action === "cancel") continue;
        if (action === "rename") {
          const base = file.name.replace(/(\.\w+)$/, "");
          const extPart = file.name.slice(base.length);
          const newPath = `${folder}${base}-copy${extPart}`;
          try {
            const content = await file.text();
            newFiles.push({ path: newPath, content, file_type });
          } catch { errors.push(`${file.name}: read error`); }
          continue;
        }
      }

      try {
        const content = await file.text();
        newFiles.push({ path, content, file_type });
        existingPaths.add(path);
      } catch {
        errors.push(`${file.name}: read error`);
      }
    }

    if (errors.length > 0) setDropError(errors.join("; "));
    if (newFiles.length > 0) onDropFiles(newFiles);
  }, [files, onDropFiles]);

  // Top-level drag-and-drop (auto-classify)
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (readOnly || !onDropFiles) return;
    e.dataTransfer.dropEffect = draggingFile ? "move" : "copy";
    setDragOver(true);
  }, [readOnly, onDropFiles, draggingFile]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    setDragOverFolder(null);
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    setDragOverFolder(null);
    setDropError(null);
    if (readOnly || !onDropFiles) return;

    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length === 0) return;
    if (droppedFiles.length > MAX_DROP_FILES) {
      setDropError(`Max ${MAX_DROP_FILES} files per drop`);
      return;
    }

    const errors: string[] = [];
    const newFiles: SkillFile[] = [];
    const existingPaths = new Set(files.map((f) => f.path));

    for (const file of droppedFiles) {
      const ext = file.name.includes(".") ? "." + file.name.split(".").pop()!.toLowerCase() : "";
      if (!ALLOWED_EXTENSIONS.has(ext)) { errors.push(`${file.name}: unsupported`); continue; }
      if (file.size > MAX_FILE_SIZE) { errors.push(`${file.name}: too large`); continue; }
      const { folder, file_type } = classifyFile(file.name);
      const path = `${folder}${file.name}`;
      if (existingPaths.has(path)) { errors.push(`${path}: exists`); continue; }
      try {
        const content = await file.text();
        newFiles.push({ path, content, file_type });
        existingPaths.add(path);
      } catch { errors.push(`${file.name}: read error`); }
    }

    if (errors.length > 0) setDropError(errors.join("; "));
    if (newFiles.length > 0) onDropFiles(newFiles);
  }, [readOnly, onDropFiles, files]);

  // Internal drag-to-move
  const handleFileDragStart = useCallback((e: React.DragEvent, path: string) => {
    e.dataTransfer.setData("text/plain", path);
    e.dataTransfer.effectAllowed = "move";
    setDraggingFile(path);
  }, []);

  const handleFileDragEnd = useCallback(() => {
    setDraggingFile(null);
    setDragOverFolder(null);
  }, []);

  const handleFolderDragOver = useCallback((e: React.DragEvent, prefix: string) => {
    if (!onMoveFile && !onDropFiles) return;
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = draggingFile ? "move" : "copy";
    setDragOverFolder(prefix);
  }, [draggingFile, onMoveFile, onDropFiles]);

  const handleFolderDrop = useCallback(async (e: React.DragEvent, targetPrefix: string) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverFolder(null);

    if (draggingFile && onMoveFile) {
      setDraggingFile(null);
      const sourcePath = e.dataTransfer.getData("text/plain");
      if (!sourcePath) return;
      const parts = sourcePath.split("/");
      const fileName = parts[parts.length - 1];
      const newPath = `${targetPrefix}${fileName}`;
      if (sourcePath === newPath) return;
      if (files.some((f) => f.path === newPath)) {
        if (!confirm(`File ${newPath} already exists. Overwrite?`)) return;
      }
      onMoveFile(sourcePath, newPath);
      return;
    }

    if (!onDropFiles) return;
    setDraggingFile(null);
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length === 0) return;
    if (droppedFiles.length > MAX_DROP_FILES) { setDropError(`Max ${MAX_DROP_FILES} files`); return; }

    const errors: string[] = [];
    const newFiles: SkillFile[] = [];
    const existingPaths = new Set(files.map((f) => f.path));
    const file_type = fileTypeForFolder(targetPrefix);

    for (const file of droppedFiles) {
      const ext = file.name.includes(".") ? "." + file.name.split(".").pop()!.toLowerCase() : "";
      if (!ALLOWED_EXTENSIONS.has(ext)) { errors.push(`${file.name}: unsupported`); continue; }
      if (file.size > MAX_FILE_SIZE) { errors.push(`${file.name}: too large`); continue; }
      const path = `${targetPrefix}${file.name}`;
      if (existingPaths.has(path)) { errors.push(`${path}: exists`); continue; }
      try {
        const content = await file.text();
        newFiles.push({ path, content, file_type });
        existingPaths.add(path);
      } catch { errors.push(`${file.name}: read error`); }
    }
    if (errors.length > 0) setDropError(errors.join("; "));
    if (newFiles.length > 0) onDropFiles(newFiles);
  }, [draggingFile, onMoveFile, onDropFiles, files]);

  // -- Icon button helper --
  const IconBtn = ({ onClick, title, children, className = "" }: {
    onClick: () => void; title: string; children: React.ReactNode; className?: string;
  }) => (
    <button
      onClick={onClick}
      title={title}
      className={`p-0.5 rounded hover:bg-gray-200 transition-colors text-sm ${className}`}
    >
      {children}
    </button>
  );

  // Render a folder and its contents recursively
  const renderFolder = (prefix: string, depth: number = 0) => {
    const folderFiles = filesInFolder(prefix);
    const children = getSubFolders(prefix);
    const isCollapsed = collapsed[prefix];
    const isDragTarget = dragOverFolder === prefix;
    const folderName = prefix.split("/").filter(Boolean).pop() ?? prefix;
    const icon = FOLDER_ICONS[prefix] ?? "\u{1F4C1}"; // 📁
    const totalFiles = folderFiles.length + children.reduce(
      (sum, c) => sum + filesInFolder(c).length, 0
    );

    return (
      <div key={prefix}>
        {/* Folder header */}
        <div
          className={`group flex items-center ${isDragTarget ? "bg-forge-100 ring-1 ring-forge-300" : ""}`}
          onDragOver={(e) => handleFolderDragOver(e, prefix)}
          onDrop={(e) => handleFolderDrop(e, prefix)}
        >
          <button
            onClick={() => toggleFolder(prefix)}
            className="flex-1 flex items-center gap-1.5 py-1.5 text-left hover:bg-gray-100 transition-colors"
            style={{ paddingLeft: `${8 + depth * 12}px` }}
          >
            <span className="text-[11px]">{isCollapsed ? "\u25B6" : "\u25BC"}</span>
            <span className="text-sm">{icon}</span>
            <span className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
              {folderName}
            </span>
            <span className="text-[10px] text-gray-400 ml-auto pr-1">{totalFiles}</span>
          </button>
          {!readOnly && (
            <div className="hidden group-hover:flex items-center gap-0.5 pr-1">
              <IconBtn onClick={() => uploadRefs.current[prefix]?.click()} title={`Upload to ${folderName}/`}>
                <span className="text-blue-500">{"\u2B06\uFE0F"}</span>
              </IconBtn>
              <input
                ref={(el) => { uploadRefs.current[prefix] = el; }}
                type="file"
                multiple
                accept={Array.from(ALLOWED_EXTENSIONS).join(",")}
                className="hidden"
                onChange={(e) => { handleUpload(prefix, e.target.files); e.target.value = ""; }}
              />
              <IconBtn onClick={() => { setAdding(prefix); setAddingFolder(null); setNewName(""); }} title={`New file in ${folderName}/`}>
                <span className="text-green-600">{"\uD83D\uDCC4"}</span>
              </IconBtn>
              <IconBtn onClick={() => { setAddingFolder(prefix); setAdding(null); setNewName(""); }} title={`New subfolder in ${folderName}/`}>
                <span className="text-indigo-500">{"\uD83D\uDCC2"}</span>
              </IconBtn>
              {canDeleteFolder(prefix) && (
                <IconBtn onClick={() => handleDeleteFolder(prefix)} title="Delete empty folder" className="text-red-400 hover:text-red-600">
                  <span>{"\uD83D\uDDD1"}</span>
                </IconBtn>
              )}
            </div>
          )}
        </div>

        {/* Inline add file input */}
        {adding === prefix && (
          <div className="flex items-center gap-1 py-1 bg-gray-50" style={{ paddingLeft: `${20 + depth * 12}px` }}>
            <input
              autoFocus
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleAdd(prefix); if (e.key === "Escape") cancelAdd(); }}
              className="flex-1 min-w-0 border rounded px-1 py-0.5 text-xs focus:border-forge-500 focus:outline-none"
              placeholder="filename"
            />
            <button onClick={() => handleAdd(prefix)} className="text-green-600 hover:text-green-800 text-xs px-1">&#10003;</button>
            <button onClick={cancelAdd} className="text-gray-400 hover:text-gray-600 text-xs px-1">&times;</button>
          </div>
        )}

        {/* Inline add subfolder input */}
        {addingFolder === prefix && (
          <div className="flex items-center gap-1 py-1 bg-indigo-50" style={{ paddingLeft: `${20 + depth * 12}px` }}>
            <input
              autoFocus
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleAddFolder(prefix); if (e.key === "Escape") cancelAdd(); }}
              className="flex-1 min-w-0 border rounded px-1 py-0.5 text-xs focus:border-indigo-500 focus:outline-none"
              placeholder="folder name"
            />
            <button onClick={() => handleAddFolder(prefix)} className="text-indigo-600 hover:text-indigo-800 text-xs px-1">&#10003;</button>
            <button onClick={cancelAdd} className="text-gray-400 hover:text-gray-600 text-xs px-1">&times;</button>
          </div>
        )}

        {/* Contents */}
        {!isCollapsed && (
          <>
            {folderFiles.map((f) => {
              const fileName = f.path.substring(prefix.length);
              return (
                <div key={f.path} className="group flex items-center">
                  <button
                    onClick={() => onSelect(f.path)}
                    draggable={!readOnly && !!onMoveFile}
                    onDragStart={(e) => handleFileDragStart(e, f.path)}
                    onDragEnd={handleFileDragEnd}
                    className={`flex-1 flex items-center gap-1.5 pr-2 py-1 text-left hover:bg-gray-100 truncate ${
                      activeFile === f.path ? "bg-forge-50 text-forge-700 font-medium" : "text-gray-600"
                    } ${draggingFile === f.path ? "opacity-50" : ""}`}
                    style={{ paddingLeft: `${20 + depth * 12}px` }}
                  >
                    <span className="text-[10px] text-gray-400">&middot;</span>
                    <span className="truncate text-xs">{fileName}</span>
                  </button>
                  {!readOnly && (
                    <button
                      onClick={() => onDelete(f.path)}
                      className="hidden group-hover:block px-1.5 text-red-400 hover:text-red-600 text-xs"
                      title="Delete file"
                    >
                      &times;
                    </button>
                  )}
                </div>
              );
            })}
            {children.map((child) => renderFolder(child, depth + 1))}
          </>
        )}
      </div>
    );
  };

  return (
    <div
      className={`flex flex-col h-full select-none relative ${
        dragOver && !draggingFile ? "ring-2 ring-inset ring-forge-400 bg-forge-50/50" : ""
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drop overlay */}
      {dragOver && !draggingFile && (
        <div className="absolute inset-0 flex items-center justify-center bg-forge-50/80 z-10 pointer-events-none">
          <div className="text-center">
            <div className="text-forge-600 font-medium text-sm">Drop files here</div>
            <div className="text-[10px] text-forge-400 mt-0.5">.md .txt .py .js .ts .json .yaml .sh</div>
          </div>
        </div>
      )}

      {/* Drop error */}
      {dropError && (
        <div className="px-2 py-1 bg-red-50 text-red-600 text-[10px] border-b border-red-200">
          {dropError}
          <button onClick={() => setDropError(null)} className="ml-1 text-red-400 hover:text-red-600">&times;</button>
        </div>
      )}

      {/* Overwrite prompt */}
      {overwritePrompt && (
        <div className="px-2 py-2 bg-amber-50 border-b border-amber-200 space-y-1">
          <p className="text-[10px] text-amber-700 font-medium">{overwritePrompt.existingPath} already exists</p>
          <div className="flex gap-1">
            <button onClick={() => overwritePrompt.resolve("overwrite")} className="px-1.5 py-0.5 text-[10px] bg-amber-200 text-amber-800 rounded hover:bg-amber-300">Overwrite</button>
            <button onClick={() => overwritePrompt.resolve("rename")} className="px-1.5 py-0.5 text-[10px] bg-gray-200 text-gray-700 rounded hover:bg-gray-300">Rename</button>
            <button onClick={() => overwritePrompt.resolve("cancel")} className="px-1.5 py-0.5 text-[10px] text-gray-500 hover:text-gray-700">Cancel</button>
          </div>
        </div>
      )}

      {/* SKILL.md — always first */}
      <button
        onClick={() => onSelect("SKILL.md")}
        className={`flex items-center gap-1.5 px-2 py-1.5 text-left hover:bg-gray-100 transition-colors ${
          activeFile === "SKILL.md" ? "bg-forge-50 text-forge-700 font-medium" : "text-gray-700"
        }`}
      >
        <span className="text-sm">{"\uD83D\uDCDD"}</span>
        <span className="truncate text-sm font-medium">SKILL.md</span>
      </button>

      {/* Root-level actions bar */}
      {!readOnly && (
        <div className="group flex items-center gap-1 px-2 py-1 border-b border-gray-200 bg-gray-50/50">
          <span className="text-[10px] text-gray-400 flex-1">Root</span>
          <IconBtn onClick={() => rootUploadRef.current?.click()} title="Upload file to root">
            <span className="text-blue-500">{"\u2B06\uFE0F"}</span>
          </IconBtn>
          <input
            ref={rootUploadRef}
            type="file"
            multiple
            accept={Array.from(ALLOWED_EXTENSIONS).join(",")}
            className="hidden"
            onChange={(e) => { handleUpload("", e.target.files); e.target.value = ""; }}
          />
          <IconBtn onClick={() => { setAdding("__root__"); setAddingFolder(null); setNewName(""); }} title="New file in root">
            <span className="text-green-600">{"\uD83D\uDCC4"}</span>
          </IconBtn>
          <IconBtn onClick={() => { setAddingFolder("__root__"); setAdding(null); setNewName(""); }} title="New folder">
            <span className="text-indigo-500">{"\uD83D\uDCC2"}</span>
          </IconBtn>
        </div>
      )}

      {/* Root-level add inputs */}
      {adding === "__root__" && (
        <div className="flex items-center gap-1 px-2 py-1 bg-gray-50">
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { handleAdd(""); } if (e.key === "Escape") cancelAdd(); }}
            className="flex-1 min-w-0 border rounded px-1 py-0.5 text-xs focus:border-forge-500 focus:outline-none"
            placeholder="filename"
          />
          <button onClick={() => handleAdd("")} className="text-green-600 hover:text-green-800 text-xs px-1">&#10003;</button>
          <button onClick={cancelAdd} className="text-gray-400 hover:text-gray-600 text-xs px-1">&times;</button>
        </div>
      )}
      {addingFolder === "__root__" && (
        <div className="flex items-center gap-1 px-2 py-1 bg-indigo-50">
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleAddFolder(""); if (e.key === "Escape") cancelAdd(); }}
            className="flex-1 min-w-0 border rounded px-1 py-0.5 text-xs focus:border-indigo-500 focus:outline-none"
            placeholder="folder name"
          />
          <button onClick={() => handleAddFolder("")} className="text-indigo-600 hover:text-indigo-800 text-xs px-1">&#10003;</button>
          <button onClick={cancelAdd} className="text-gray-400 hover:text-gray-600 text-xs px-1">&times;</button>
        </div>
      )}

      {/* Root-level files */}
      {rootFiles.map((f) => (
        <div key={f.path} className="group flex items-center">
          <button
            onClick={() => onSelect(f.path)}
            draggable={!readOnly && !!onMoveFile}
            onDragStart={(e) => handleFileDragStart(e, f.path)}
            onDragEnd={handleFileDragEnd}
            className={`flex-1 flex items-center gap-1.5 px-2 py-1 text-left hover:bg-gray-100 truncate ${
              activeFile === f.path ? "bg-forge-50 text-forge-700 font-medium" : "text-gray-600"
            } ${draggingFile === f.path ? "opacity-50" : ""}`}
          >
            <span className="text-[10px] text-gray-400">&middot;</span>
            <span className="truncate text-xs">{f.path}</span>
          </button>
          {!readOnly && (
            <button
              onClick={() => onDelete(f.path)}
              className="hidden group-hover:block px-1.5 text-red-400 hover:text-red-600 text-xs"
              title="Delete file"
            >
              &times;
            </button>
          )}
        </div>
      ))}

      {/* Folders */}
      {topFolders.map((prefix) => renderFolder(prefix, 0))}
    </div>
  );
}
