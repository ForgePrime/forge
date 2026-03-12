"use client";

import { useRef, useState, useCallback, type KeyboardEvent, type DragEvent } from "react";
import type { ChatFileAttachment } from "@/lib/types";
import { llm } from "@/lib/api";

const MAX_FILE_SIZE = 1 * 1024 * 1024; // 1 MB
const MAX_FILES_PER_SESSION = 10;
const ALLOWED_EXTENSIONS = new Set([
  ".md", ".txt", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
  ".sh", ".css", ".html", ".pdf",
]);

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getExtension(name: string): string {
  const idx = name.lastIndexOf(".");
  return idx >= 0 ? name.slice(idx).toLowerCase() : "";
}

interface ChatInputProps {
  onSend: (message: string, fileIds?: string[]) => void;
  disabled?: boolean;
  placeholder?: string;
  sessionId?: string | null;
}

export default function ChatInput({
  onSend,
  disabled = false,
  placeholder,
  sessionId,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const [dragging, setDragging] = useState(false);
  const [attachments, setAttachments] = useState<ChatFileAttachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dragCounter = useRef(0);
  // Stable pre-session ID for file uploads before a chat session is created
  const preSessionId = useRef(`pre-${Date.now()}-${Math.random().toString(36).slice(2)}`);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if ((!trimmed && attachments.length === 0) || disabled) return;
    const fileIds = attachments.length > 0
      ? attachments.map((a) => a.file_id)
      : undefined;
    onSend(trimmed || "(files attached)", fileIds);
    setValue("");
    setAttachments([]);
    setUploadError(null);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, disabled, onSend, attachments]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const handleInput = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }, []);

  // --- Drag & Drop ---
  const handleDragEnter = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current++;
    if (e.dataTransfer.types.includes("Files")) {
      setDragging(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current--;
    if (dragCounter.current <= 0) {
      dragCounter.current = 0;
      setDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    async (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounter.current = 0;
      setDragging(false);
      setUploadError(null);

      const files = Array.from(e.dataTransfer.files);
      if (files.length === 0) return;
      if (uploading) return; // Guard against concurrent drops

      // Use real session ID if available, otherwise stable pre-session ID
      const sid = sessionId ?? preSessionId.current;

      // Check session limit
      const remaining = MAX_FILES_PER_SESSION - attachments.length;
      if (remaining <= 0) {
        setUploadError(`Session limit reached (max ${MAX_FILES_PER_SESSION} files).`);
        return;
      }

      const toUpload = files.slice(0, remaining);
      const rejected: string[] = [];

      // Validate files
      const valid: File[] = [];
      for (const file of toUpload) {
        const ext = getExtension(file.name);
        if (!ALLOWED_EXTENSIONS.has(ext)) {
          rejected.push(`${file.name}: unsupported type (${ext || "no extension"})`);
          continue;
        }
        if (file.size > MAX_FILE_SIZE) {
          rejected.push(`${file.name}: too large (${formatFileSize(file.size)}, max 1 MB)`);
          continue;
        }
        valid.push(file);
      }

      if (files.length > toUpload.length) {
        rejected.push(`${files.length - toUpload.length} file(s) skipped — session limit.`);
      }

      if (valid.length === 0) {
        setUploadError(rejected.join("; "));
        return;
      }

      // Upload valid files
      setUploading(true);
      const newAttachments: ChatFileAttachment[] = [];
      const errors: string[] = [...rejected];

      for (const file of valid) {
        try {
          const result = await llm.uploadFile(file, sid);
          newAttachments.push(result);
        } catch (err) {
          const msg = err instanceof Error ? err.message : "Upload failed";
          errors.push(`${file.name}: ${msg}`);
        }
      }

      setUploading(false);

      if (newAttachments.length > 0) {
        setAttachments((prev) => [...prev, ...newAttachments]);
      }
      if (errors.length > 0) {
        setUploadError(errors.join("; "));
      }
    },
    [sessionId, attachments.length],
  );

  const removeAttachment = useCallback((fileId: string) => {
    setAttachments((prev) => prev.filter((a) => a.file_id !== fileId));
  }, []);

  return (
    <div
      className="relative border-t border-gray-200 bg-white"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Drop zone overlay */}
      {dragging && (
        <div className="absolute inset-0 z-10 flex items-center justify-center rounded-b-lg border-2 border-dashed border-forge-400 bg-forge-50/90">
          <div className="text-center">
            <svg className="mx-auto h-8 w-8 text-forge-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="mt-1 text-sm font-medium text-forge-700">Drop files to attach</p>
            <p className="text-xs text-forge-500">Max 1 MB per file</p>
          </div>
        </div>
      )}

      {/* Upload error */}
      {uploadError && (
        <div className="border-b border-amber-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-700">
          {uploadError}
          <button onClick={() => setUploadError(null)} className="ml-2 underline hover:no-underline">
            dismiss
          </button>
        </div>
      )}

      {/* File attachment chips */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-3 pt-2">
          {attachments.map((att) => (
            <span
              key={att.file_id}
              className="inline-flex items-center gap-1 rounded-full bg-forge-100 px-2.5 py-1 text-xs text-forge-700"
            >
              <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
              <span className="max-w-[120px] truncate" title={att.filename}>{att.filename}</span>
              <span className="text-forge-400">({formatFileSize(att.size)})</span>
              <button
                onClick={() => removeAttachment(att.file_id)}
                className="ml-0.5 rounded-full p-0.5 hover:bg-forge-200 transition-colors"
                title="Remove"
              >
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Uploading indicator */}
      {uploading && (
        <div className="px-3 pt-1 text-xs text-forge-500 animate-pulse">
          Uploading files...
        </div>
      )}

      {/* Input area */}
      <div className="flex items-end gap-2 p-3">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            handleInput();
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder ?? "Type a message or drop files..."}
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm
            focus:border-forge-500 focus:outline-none focus:ring-1 focus:ring-forge-500
            disabled:bg-gray-50 disabled:text-gray-400"
        />
        <button
          onClick={handleSend}
          disabled={disabled || (!value.trim() && attachments.length === 0)}
          className="rounded-lg bg-forge-600 px-3 py-2 text-sm font-medium text-white
            hover:bg-forge-700 disabled:bg-gray-300 disabled:cursor-not-allowed
            transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}
