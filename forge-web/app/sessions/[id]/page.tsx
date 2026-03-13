"use client";

import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import Message from "@/components/ai/Message";
import { EntityLink } from "@/components/shared/EntityLink";
import { Badge, statusVariant } from "@/components/shared/Badge";
import type { ChatSession, ChatMessage } from "@/lib/types";

/** Format token count. */
function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

/** Badge color per session type. */
function typeBadgeVariant(type?: string): "info" | "success" | "warning" | "danger" | "default" {
  switch (type) {
    case "plan": return "info";
    case "execute": return "success";
    case "verify": return "warning";
    case "compound": return "danger";
    default: return "default";
  }
}

/** Extract entity IDs from tool call results (e.g., createTask → T-001). */
function extractEntityIds(messages: ChatMessage[]): string[] {
  const ids = new Set<string>();
  const ID_RE = /\b([TDKOIGLR]-\d{3,})\b/g;

  for (const msg of messages) {
    if (!msg.toolCalls) continue;
    for (const tc of msg.toolCalls) {
      if (!tc.result) continue;
      const resultStr = JSON.stringify(tc.result);
      let match: RegExpExecArray | null;
      while ((match = ID_RE.exec(resultStr)) !== null) {
        ids.add(match[1]);
      }
      ID_RE.lastIndex = 0;
    }
  }
  return Array.from(ids).sort();
}

/** Compute session duration from first to last message. */
function computeDuration(messages: ChatMessage[]): string {
  if (messages.length < 2) return "-";
  const first = new Date(messages[0].created_at).getTime();
  const last = new Date(messages[messages.length - 1].created_at).getTime();
  const diff = last - first;
  if (diff < 60_000) return `${Math.round(diff / 1000)}s`;
  if (diff < 3600_000) return `${Math.round(diff / 60_000)}m`;
  return `${(diff / 3600_000).toFixed(1)}h`;
}

export default function SessionDetailPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();

  const { data: session, error, isLoading } = useSWR<ChatSession>(`/llm/sessions/${id}`);

  if (isLoading) return <p className="p-6 text-sm text-gray-400">Loading session...</p>;
  if (error) return <p className="p-6 text-sm text-red-600">{(error as Error).message}</p>;
  if (!session) return <p className="p-6 text-sm text-gray-400">Session not found</p>;

  const messages = session.messages ?? [];
  const entityIds = extractEntityIds(messages);
  const duration = computeDuration(messages);

  return (
    <div className="flex h-full">
      {/* Messages panel */}
      <div className="flex-1 overflow-y-auto p-6">
        <button onClick={() => router.back()} className="text-xs text-gray-400 hover:text-gray-600 mb-4">
          &larr; Back to sessions
        </button>

        <h1 className="text-xl font-bold mb-4">
          Session: <span className="font-mono text-gray-600">{session.session_id}</span>
        </h1>

        {messages.length === 0 ? (
          <p className="text-sm text-gray-400">No messages in this session.</p>
        ) : (
          <div className="space-y-3">
            {messages.map((msg: ChatMessage) => (
              <Message key={msg.id} message={msg} />
            ))}
          </div>
        )}
      </div>

      {/* Metadata sidebar */}
      <div className="w-72 border-l bg-gray-50 overflow-y-auto p-4 space-y-5 flex-shrink-0">
        {/* Session info */}
        <section>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Session</h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <Badge variant={typeBadgeVariant(session.session_type)}>
                {session.session_type || "chat"}
              </Badge>
              <Badge variant={statusVariant((session.session_status || "active").toUpperCase())}>
                {session.session_status || "active"}
              </Badge>
            </div>
            {session.target_entity_id && (
              <div>
                <span className="text-xs text-gray-500">Target: </span>
                <EntityLink id={session.target_entity_id} />
              </div>
            )}
            <div>
              <span className="text-xs text-gray-500">Context: </span>
              <span className="text-xs text-gray-700">
                {session.context_type}{session.context_id ? `: ${session.context_id}` : ""}
              </span>
            </div>
            {session.project && (
              <div>
                <span className="text-xs text-gray-500">Project: </span>
                <span className="text-xs text-gray-700">{session.project}</span>
              </div>
            )}
          </div>
        </section>

        {/* Model & usage */}
        <section>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Usage</h3>
          <div className="space-y-1 text-xs text-gray-600">
            {session.model_used && (
              <div>
                <span className="text-gray-500">Model: </span>
                {session.model_used}
              </div>
            )}
            <div>
              <span className="text-gray-500">Messages: </span>
              {messages.length}
            </div>
            <div>
              <span className="text-gray-500">Input tokens: </span>
              {fmtTokens(session.total_tokens_in)}
            </div>
            <div>
              <span className="text-gray-500">Output tokens: </span>
              {fmtTokens(session.total_tokens_out)}
            </div>
            <div>
              <span className="text-gray-500">Cost: </span>
              ${session.estimated_cost.toFixed(4)}
            </div>
            <div>
              <span className="text-gray-500">Duration: </span>
              {duration}
            </div>
          </div>
        </section>

        {/* Entities modified */}
        {entityIds.length > 0 && (
          <section>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Entities Modified ({entityIds.length})
            </h3>
            <div className="flex flex-wrap gap-1">
              {entityIds.map((eid) => (
                <EntityLink key={eid} id={eid} />
              ))}
            </div>
          </section>
        )}

        {/* Timestamps */}
        <section>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Timestamps</h3>
          <div className="space-y-1 text-xs text-gray-500">
            <div>Created: {new Date(session.created_at).toLocaleString()}</div>
            <div>Updated: {new Date(session.updated_at).toLocaleString()}</div>
          </div>
        </section>
      </div>
    </div>
  );
}
