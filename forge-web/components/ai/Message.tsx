"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "@/lib/types";
import ToolCallBlock from "./ToolCallBlock";
import { useSidebarStore } from "@/stores/sidebarStore";
import { ErrorDetail } from "@/components/debug/ErrorDetail";

// ---------------------------------------------------------------------------
// Scope suggestion extraction
// ---------------------------------------------------------------------------

const SCOPE_SUGGESTION_RE = /\[suggest-scope:([a-z_-]+)\]/g;

function extractScopeSuggestions(content: string): {
  cleanContent: string;
  scopes: string[];
} {
  const scopes: string[] = [];
  const cleanContent = content.replace(SCOPE_SUGGESTION_RE, (_, scope: string) => {
    if (!scopes.includes(scope)) scopes.push(scope);
    return "";
  });
  return { cleanContent: cleanContent.trim(), scopes };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface MessageProps {
  message: ChatMessage;
}

export default function Message({ message }: MessageProps) {
  const isUser = message.role === "user";
  const isStreaming = message.streaming;
  const addScope = useSidebarStore((s) => s.addScope);

  // Extract scope suggestions from assistant messages
  const { cleanContent, scopes: suggestedScopes } =
    !isUser && message.content
      ? extractScopeSuggestions(message.content)
      : { cleanContent: message.content, scopes: [] };

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
          isUser
            ? "bg-forge-600 text-white"
            : "bg-gray-100 text-gray-900"
        }`}
      >
        {/* Error detail (rich rendering for ApiError) */}
        {message.error != null ? (
          <div className="mb-2">
            <ErrorDetail error={message.error} />
          </div>
        ) : null}

        {/* Markdown content */}
        {!message.error && cleanContent ? (
          <div className={`prose prose-sm max-w-none ${isUser ? "prose-invert" : ""}`}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                pre: ({ children }) => (
                  <pre className="overflow-x-auto rounded bg-gray-800 p-2 text-xs text-gray-100">
                    {children}
                  </pre>
                ),
                code: ({ children, className }) => {
                  const isBlock = className?.startsWith("language-");
                  if (isBlock) return <code className={className}>{children}</code>;
                  return (
                    <code className={`rounded px-1 py-0.5 text-xs ${
                      isUser ? "bg-forge-700" : "bg-gray-200"
                    }`}>
                      {children}
                    </code>
                  );
                },
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer"
                    className={isUser ? "text-forge-200 underline" : "text-forge-600 underline"}>
                    {children}
                  </a>
                ),
              }}
            >
              {cleanContent}
            </ReactMarkdown>
          </div>
        ) : isStreaming ? (
          <span className="inline-flex items-center gap-1 text-gray-400">
            <span className="animate-pulse">●</span> Thinking...
          </span>
        ) : null}

        {/* Scope suggestion buttons */}
        {suggestedScopes.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {suggestedScopes.map((scope) => (
              <button
                key={scope}
                onClick={() => addScope(scope)}
                className="inline-flex items-center gap-1 rounded-full bg-forge-100 px-2.5 py-1
                  text-xs font-medium text-forge-700 hover:bg-forge-200 transition-colors
                  border border-forge-200"
              >
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Add scope: {scope}
              </button>
            ))}
          </div>
        )}

        {/* Tool calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-2">
            {message.toolCalls.map((tc, i) => (
              <ToolCallBlock key={`${tc.name}-${i}`} toolCall={tc} />
            ))}
          </div>
        )}

        {/* Streaming indicator */}
        {isStreaming && message.content && (
          <span className="inline-block animate-pulse text-forge-500 ml-0.5">▊</span>
        )}
      </div>
    </div>
  );
}
