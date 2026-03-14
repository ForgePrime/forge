"use client";

import { useEffect, useCallback, useState, useRef } from "react";
import { usePathname } from "next/navigation";
import { useScopeResolver, SCOPE_TO_CONTEXT_TYPE } from "@/hooks/useScopeResolver";
import { fetchContractsForScopes, getPermissionStatus, type CapabilityDef } from "@/lib/capabilities";
import { useAIPageContextSafe, serializePageContext, deriveScopesFromElements, type AIElementDescriptor } from "@/lib/ai-context";
import { useSidebarStore, type SidebarTab } from "@/stores/sidebarStore";
import { useChatStore } from "@/stores/chatStore";
import { useProjectStore } from "@/stores/projectStore";
import type { LLMConfig } from "@/lib/types";
import LLMChat from "./LLMChat";
import WorkflowProgress from "./WorkflowProgress";
import TokenCounter from "./TokenCounter";
import { useStreamDebug, subscribeToStreamEvents } from "@/lib/hooks/useStreamDebug";
import { StreamView } from "./stream/StreamView";
import useSWR from "swr";
import { llm } from "@/lib/api";
import { ToolsTabEnhanced } from "./ToolsTabEnhanced";

// ---------------------------------------------------------------------------
// Tab types
// ---------------------------------------------------------------------------

/** Entity type colors (matching EntityNode config). */
const ENTITY_TYPE_COLORS: Record<string, string> = {
  objective: "#3B82F6",
  idea: "#8B5CF6",
  task: "#10B981",
  decision: "#F59E0B",
  research: "#EC4899",
  knowledge: "#6366F1",
  guideline: "#14B8A6",
  lesson: "#F97316",
  ac_template: "#64748B",
};

const TABS: { key: SidebarTab; label: string }[] = [
  { key: "chat", label: "Chat" },
  { key: "tools", label: "Tools" },
  { key: "scopes", label: "Scopes" },
  { key: "conversations", label: "History" },
  { key: "debug", label: "Debug" },
];

// ---------------------------------------------------------------------------
// Scope chips
// ---------------------------------------------------------------------------

function ScopeChips({
  scopes,
  onRemove,
}: {
  scopes: string[];
  onRemove: (scope: string) => void;
}) {
  if (scopes.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1 px-3 py-2 border-b">
      {scopes.map((scope) => (
        <span
          key={scope}
          className="inline-flex items-center gap-1 rounded-full bg-forge-100 px-2 py-0.5 text-xs font-medium text-forge-700"
        >
          {scope}
          <button
            onClick={() => onRemove(scope)}
            className="ml-0.5 rounded-full hover:bg-forge-200 transition-colors"
            title={`Remove ${scope}`}
          >
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </span>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab bar
// ---------------------------------------------------------------------------

function TabBar({
  activeTab,
  onChange,
  streaming,
}: {
  activeTab: SidebarTab;
  onChange: (tab: SidebarTab) => void;
  streaming?: boolean;
}) {
  return (
    <div className="flex border-b px-1">
      {TABS.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          className={`flex-1 px-2 py-1.5 text-xs font-medium transition-colors ${
            activeTab === tab.key
              ? "text-forge-700 border-b-2 border-forge-500"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          {tab.label}
          {tab.key === "debug" && streaming && (
            <span className="ml-1 inline-block animate-pulse text-forge-500">●</span>
          )}
        </button>
      ))}
    </div>
  );
}

// ToolsTab replaced by ToolsTabEnhanced (imported)

// ---------------------------------------------------------------------------
// Scopes tab — scope checkboxes + capabilities for active scopes
// ---------------------------------------------------------------------------

const ALL_SCOPES = Object.keys(SCOPE_TO_CONTEXT_TYPE);

const ACTION_BADGE: Record<string, string> = {
  READ: "bg-blue-100 text-blue-700",
  WRITE: "bg-amber-100 text-amber-700",
  DELETE: "bg-red-100 text-red-700",
};

/** Guess action type from tool name convention. */
function guessActionType(toolName: string): "READ" | "WRITE" | "DELETE" {
  if (/^(delete|remove)/.test(toolName)) return "DELETE";
  if (/^(create|update|add|set|record|draft|approve|complete)/.test(toolName)) return "WRITE";
  return "READ";
}

function ScopesTab({
  activeScopes,
  onAdd,
  onRemove,
  onReset,
  disabledCapabilities,
  disabledToolNames,
  permissions,
  onToggleCapability,
  pageTitle,
  pageElementCount,
  annotationScopes,
  pageContextText,
  pageElements,
  projectSlug,
}: {
  activeScopes: string[];
  onAdd: (scope: string) => void;
  onRemove: (scope: string) => void;
  onReset: () => void;
  disabledCapabilities: string[];
  /** Tool names (not capability IDs) disabled in this session. */
  disabledToolNames: string[];
  permissions: Record<string, { read: boolean; write: boolean; delete: boolean }>;
  onToggleCapability: (capabilityId: string, enabled: boolean) => void;
  /** Current page title from AI annotations (e.g., "Tasks (25)"). */
  pageTitle: string | null;
  /** Number of annotated elements on the page. */
  pageElementCount: number;
  /** Scopes derived from page annotations. */
  annotationScopes: string[];
  /** Full serialized page context text (what the LLM actually sees). */
  pageContextText?: string;
  /** Page annotation elements — for deriving extra capabilities not in static registry. */
  pageElements?: AIElementDescriptor[];
  /** Current project slug for app context preview. */
  projectSlug?: string | null;
  /** Scopes applied by entity_type_defaults. */
  entityDefaultScopes?: string[];
}) {
  const [contextExpanded, setContextExpanded] = useState(false);
  const [appContextExpanded, setAppContextExpanded] = useState(false);
  const activeSet = new Set(activeScopes);
  const disabledSet = new Set(disabledCapabilities);
  const defaultSet = new Set(entityDefaultScopes ?? []);

  // Fetch App Context preview (SKILL text) from backend
  const disabledKey = disabledToolNames.length > 0 ? disabledToolNames.join(",") : "";
  const { data: appContextData } = useSWR(
    activeScopes.length > 0 ? ["app-context", ...activeScopes, projectSlug ?? "", disabledKey] : null,
    () => llm.getAppContext(activeScopes, projectSlug ?? undefined, disabledToolNames.length > 0 ? disabledToolNames : undefined),
  );

  // Fetch capabilities for active scopes from backend (dynamic)
  const { data: fetchedCaps } = useSWR(
    activeScopes.length > 0 ? ["contracts", ...activeScopes] : null,
    () => fetchContractsForScopes(activeScopes),
  );

  // Build active caps: fetched from backend + page-annotation extras
  const activeCaps: CapabilityDef[] = [];
  const seenIds = new Set<string>();
  const seenTools = new Set<string>();

  if (fetchedCaps) {
    for (const cap of fetchedCaps) {
      if (!seenIds.has(cap.id)) {
        seenIds.add(cap.id);
        activeCaps.push(cap);
        if (cap.toolName) seenTools.add(cap.toolName);
      }
    }
  }

  // Merge page-annotation actions not already in backend registry
  if (pageElements) {
    for (const el of pageElements) {
      if (!el.actions) continue;
      for (const action of el.actions) {
        if (!action.toolName || seenTools.has(action.toolName)) continue;
        const capId = `page-${action.toolName}`;
        if (seenIds.has(capId)) continue;
        seenIds.add(capId);
        seenTools.add(action.toolName);
        activeCaps.push({
          id: capId,
          label: action.label,
          description: action.description ?? `${action.label} (from page)`,
          action: guessActionType(action.toolName),
          scope: "page",
          toolName: action.toolName,
          available: action.available !== false,
        });
      }
    }
  }

  return (
    <div className="px-3 py-2">
      {/* App Context — SKILL-format system prompt the AI receives */}
      {appContextData && (
        <div className="mb-3 rounded-md bg-indigo-50 border border-indigo-200 px-2.5 py-2">
          <div className="flex items-center gap-1.5 mb-1">
            <svg className="w-3.5 h-3.5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <span className="text-xs font-medium text-indigo-700">App Context</span>
            <span className="text-[10px] text-indigo-400 ml-auto">{appContextData.length} chars</span>
          </div>
          <div className="text-[11px] text-indigo-600">
            SKILL-format system prompt with modules, tools, workflows
          </div>
          <div className="mt-1.5 border-t border-indigo-200 pt-1.5">
            <button
              onClick={() => setAppContextExpanded((v) => !v)}
              className="flex items-center gap-1 text-[10px] text-indigo-500 hover:text-indigo-700"
            >
              <svg
                className={`w-3 h-3 transition-transform ${appContextExpanded ? "rotate-90" : ""}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              AI sees (raw)
            </button>
            {appContextExpanded && (
              <div className="mt-1 relative">
                <button
                  onClick={() => navigator.clipboard.writeText(appContextData.text)}
                  className="absolute top-1 right-1 text-[9px] text-gray-400 hover:text-indigo-600 bg-white/80 px-1.5 py-0.5 rounded border"
                >
                  Copy
                </button>
                <pre className="text-[10px] text-gray-600 bg-white/60 border rounded p-2 max-h-64 overflow-auto whitespace-pre-wrap font-mono leading-relaxed">
                  {appContextData.text}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Page Context — what AI sees from annotations */}
      {pageTitle && (
        <div className="mb-3 rounded-md bg-forge-50 border border-forge-200 px-2.5 py-2">
          <div className="flex items-center gap-1.5 mb-1">
            <svg className="w-3.5 h-3.5 text-forge-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            <span className="text-xs font-medium text-forge-700">Page Context</span>
          </div>
          <div className="text-[11px] text-forge-600">
            AI sees: <span className="font-medium">{pageTitle}</span>
          </div>
          <div className="text-[10px] text-forge-500 mt-0.5">
            {pageElementCount} element{pageElementCount !== 1 ? "s" : ""} annotated
            {annotationScopes.length > 0 && (
              <> &middot; scopes: {annotationScopes.join(", ")}</>
            )}
          </div>
          {/* Collapsible raw context preview */}
          {pageContextText && (
            <div className="mt-1.5 border-t border-forge-200 pt-1.5">
              <button
                onClick={() => setContextExpanded((v) => !v)}
                className="flex items-center gap-1 text-[10px] text-forge-500 hover:text-forge-700"
              >
                <svg
                  className={`w-3 h-3 transition-transform ${contextExpanded ? "rotate-90" : ""}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                AI sees (raw)
              </button>
              {contextExpanded && (
                <div className="mt-1 relative">
                  <button
                    onClick={() => navigator.clipboard.writeText(pageContextText)}
                    className="absolute top-1 right-1 text-[9px] text-gray-400 hover:text-forge-600 bg-white/80 px-1.5 py-0.5 rounded border"
                  >
                    Copy
                  </button>
                  <pre className="text-[10px] text-gray-600 bg-gray-50 border rounded p-2 max-h-64 overflow-auto whitespace-pre-wrap font-mono leading-relaxed">
                    {pageContextText}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Scope checkboxes */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-gray-700">Active Scopes</span>
        <button
          onClick={onReset}
          className="text-[10px] text-gray-500 hover:text-gray-700 underline"
        >
          Reset
        </button>
      </div>
      <div className="space-y-1 mb-3">
        {ALL_SCOPES.map((scope) => {
          const checked = activeSet.has(scope);
          const capCount = fetchedCaps ? fetchedCaps.filter((c) => c.scope === scope).length : 0;
          return (
            <label key={scope} className="flex items-center gap-2 py-1 cursor-pointer hover:bg-gray-50 rounded px-1">
              <input
                type="checkbox"
                checked={checked}
                onChange={() => (checked ? onRemove(scope) : onAdd(scope))}
                className="rounded border-gray-300 text-forge-600 focus:ring-forge-500 h-3.5 w-3.5"
              />
              <span className="text-xs text-gray-700">{scope}</span>
              {(defaultSet.has(scope) || defaultSet.has("*")) && (
                <span className="text-[9px] bg-indigo-100 text-indigo-600 px-1 py-0.5 rounded">default</span>
              )}
              <span className="text-[10px] text-gray-400 ml-auto">
                {checked && capCount > 0 ? `${capCount} ops` : SCOPE_TO_CONTEXT_TYPE[scope]}
              </span>
            </label>
          );
        })}
      </div>

      {/* Capabilities for active scopes */}
      {activeCaps.length > 0 && (
        <>
          <div className="border-t pt-2 mb-1.5">
            <span className="text-xs font-medium text-gray-700">
              Session Capabilities ({activeCaps.length})
            </span>
          </div>
          <div className="space-y-0.5">
            {activeCaps.map((cap) => {
              const permStatus = getPermissionStatus(cap, permissions);
              const sessionDisabled = disabledSet.has(cap.id);
              const settingsBlocked = permStatus === "no-permission";
              const notAvailable = permStatus === "coming-soon";

              return (
                <label
                  key={cap.id}
                  className={`flex items-center gap-1.5 py-1 px-1 rounded cursor-pointer hover:bg-gray-50 ${
                    notAvailable ? "opacity-50 cursor-default" : ""
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={!sessionDisabled && !settingsBlocked && !notAvailable}
                    onChange={() => {
                      if (!settingsBlocked && !notAvailable) {
                        onToggleCapability(cap.id, sessionDisabled);
                      }
                    }}
                    disabled={settingsBlocked || notAvailable}
                    className="rounded border-gray-300 text-forge-600 focus:ring-forge-500 h-3 w-3"
                  />
                  <span className={`text-[9px] font-bold px-1 py-0.5 rounded ${ACTION_BADGE[cap.action] ?? "bg-gray-100 text-gray-600"}`}>
                    {cap.action[0]}
                  </span>
                  <span className="text-[11px] text-gray-700 flex-1 truncate" title={cap.description}>
                    {cap.label}
                  </span>
                  {settingsBlocked && (
                    <span className="text-[9px] text-red-400" title="Blocked in Settings">OFF</span>
                  )}
                  {sessionDisabled && !settingsBlocked && (
                    <span className="text-[9px] text-amber-500" title="Disabled for this session">skip</span>
                  )}
                </label>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Conversations tab
// ---------------------------------------------------------------------------

function ConversationsTab({
  onResume,
}: {
  onResume: (sessionId: string) => void;
}) {
  const { sessionList, sessionsLoading, loadSessions, deleteSession, searchSessions } = useChatStore();
  const targetEntity = useSidebarStore((s) => s.targetEntity);
  const [showAll, setShowAll] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const [entitySessions, setEntitySessions] = useState<typeof sessionList>([]);
  const [entityLoading, setEntityLoading] = useState(false);

  // Load entity-specific sessions when targetEntity is set
  useEffect(() => {
    if (!targetEntity || showAll) return;
    setEntityLoading(true);
    llm.listSessions({ entity_type: targetEntity.type, entity_id: targetEntity.id })
      .then((result) => {
        setEntitySessions(result.sessions as typeof sessionList);
        setEntityLoading(false);
      })
      .catch(() => setEntityLoading(false));
  }, [targetEntity, showAll]);

  // Load all sessions for showAll mode or when no entity
  useEffect(() => {
    if (!targetEntity || showAll) {
      loadSessions();
    }
  }, [loadSessions, targetEntity, showAll]);

  const handleSearch = useCallback(
    (value: string) => {
      setSearchQuery(value);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        if (value.trim()) {
          searchSessions(value.trim());
        } else {
          loadSessions();
        }
      }, 300);
    },
    [searchSessions, loadSessions],
  );

  // Cleanup debounce on unmount
  useEffect(() => () => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
  }, []);

  const handleNew = useCallback(() => {
    const entity = useSidebarStore.getState().targetEntity;
    if (entity) {
      useChatStore.getState().setPendingSessionMeta({
        sessionType: "chat",
        targetEntityType: entity.type,
        targetEntityId: entity.id,
      });
    }
    useChatStore.getState().startConversation("global", "");
    useSidebarStore.getState().setActiveTab("chat");
  }, []);

  const isFiltered = !!targetEntity && !showAll;
  const displaySessions = isFiltered ? entitySessions : sessionList;
  const isLoading = isFiltered ? entityLoading : sessionsLoading;

  const handleRefresh = useCallback(() => {
    setSearchQuery("");
    if (isFiltered && targetEntity) {
      setEntityLoading(true);
      llm.listSessions({ entity_type: targetEntity.type, entity_id: targetEntity.id })
        .then((result) => {
          setEntitySessions(result.sessions as typeof sessionList);
          setEntityLoading(false);
        })
        .catch(() => setEntityLoading(false));
    } else {
      loadSessions();
    }
  }, [isFiltered, targetEntity, loadSessions]);

  return (
    <div>
      <div className="flex items-center justify-between px-3 py-2 border-b">
        <button
          onClick={handleNew}
          className="text-xs font-medium text-forge-600 hover:text-forge-800"
        >
          + New conversation
        </button>
        <div className="flex items-center gap-2">
          {targetEntity && (
            <button
              onClick={() => setShowAll(!showAll)}
              className={`text-[10px] px-1.5 py-0.5 rounded ${showAll ? "bg-gray-200 text-gray-700" : "bg-forge-100 text-forge-600"}`}
              title={showAll ? "Show entity sessions" : "Show all sessions"}
            >
              {showAll ? "All" : targetEntity.id}
            </button>
          )}
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="text-[10px] text-gray-500 hover:text-gray-700"
            title="Refresh"
          >
            {isLoading ? "..." : "Refresh"}
          </button>
        </div>
      </div>

      {/* Search input (only in showAll / no entity mode) */}
      {(!targetEntity || showAll) && (
        <div className="px-3 py-1.5 border-b">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search conversations..."
            className="w-full rounded border border-gray-200 px-2 py-1 text-xs
              focus:border-forge-400 focus:outline-none focus:ring-1 focus:ring-forge-400
              placeholder:text-gray-400"
          />
        </div>
      )}

      {displaySessions.length === 0 ? (
        <div className="flex items-center justify-center h-24 text-sm text-gray-400">
          {isLoading ? "Loading..." : searchQuery ? "No matching conversations" : "No conversations yet"}
        </div>
      ) : (
        <div className="divide-y">
          {displaySessions.map((session) => (
            <div
              key={session.session_id}
              className="px-3 py-2 hover:bg-gray-50 transition-colors cursor-pointer group"
              onClick={() => onResume(session.session_id)}
            >
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] rounded bg-forge-100 px-1.5 py-0.5 text-forge-600 font-medium">
                  {session.context_type}
                </span>
                {session.target_entity_id && (
                  <span className="text-[10px] text-gray-500 truncate font-mono">
                    {session.target_entity_id}
                  </span>
                )}
                <span className="text-[10px] text-gray-400 ml-auto shrink-0">
                  {formatTimeAgo(session.updated_at)}
                </span>
              </div>
              {/* Snippet from search results */}
              {session.snippet && (
                <div className="mt-0.5 text-[10px] text-gray-500 italic truncate" title={session.snippet}>
                  {session.snippet}
                </div>
              )}
              <div className="flex items-center justify-between mt-1">
                <span className="text-[11px] text-gray-600">
                  {session.message_count} messages
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteSession(session.session_id);
                  }}
                  className="text-[10px] text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Delete"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function formatTimeAgo(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// ---------------------------------------------------------------------------
// Debug tab — structured stream view (always mounted to capture events)
// ---------------------------------------------------------------------------

function DebugTab({
  visible,
}: {
  visible: boolean;
}) {
  const { blocks, metadata, streaming, clear } = useStreamDebug();

  const elapsed = metadata.startTime
    ? ((Date.now() - metadata.startTime) / 1000).toFixed(1)
    : null;

  return (
    <div data-debug-panel className={`flex flex-col flex-1 min-h-0 ${visible ? "" : "hidden"}`} style={{ backgroundColor: "var(--debug-bg-primary)", color: "var(--debug-text-primary)" }}>
      {/* Metadata bar */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b bg-gray-50 text-[10px] text-gray-500 flex-shrink-0">
        {metadata.model && (
          <span className="font-medium text-gray-600">{metadata.model}</span>
        )}
        {metadata.tokensIn > 0 && (
          <span className="tabular-nums">{metadata.tokensIn}↓ {metadata.tokensOut}↑</span>
        )}
        {elapsed && (
          <span className="tabular-nums">{elapsed}s</span>
        )}
        <button
          onClick={clear}
          className="ml-auto text-[10px] text-gray-400 hover:text-gray-600"
        >
          Clear
        </button>
      </div>

      {/* Stream blocks */}
      <div className="flex-1 overflow-y-auto px-2 py-2">
        <StreamView blocks={blocks} streaming={streaming} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main AISidebar
// ---------------------------------------------------------------------------

export default function AISidebar() {
  const {
    addedScopes,
    removedScopes,
    disabledCapabilities,
    activeTab,
    hydrate,
    addScope,
    removeScope,
    resetScopes,
    toggleCapability,
    setActiveTab,
    targetEntity,
    clearTargetEntity,
  } = useSidebarStore();

  // Active workflow state (reactive)
  const activeWorkflow = useChatStore((s) => {
    const sid = s.activeSessionId;
    return sid ? s.conversations[sid]?.workflowState ?? null : null;
  });

  // Hydrate from localStorage on mount
  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const pathname = usePathname();

  // Extract project slug from URL
  const projectSlugFromPath = pathname?.match(/\/projects\/([^/]+)/)?.[1] ?? null;

  // Auto-detect entity from URL path: /projects/{slug}/{entityPlural}/{id}
  const setTargetEntity = useSidebarStore((s) => s.setTargetEntity);
  useEffect(() => {
    const match = pathname?.match(/\/projects\/[^/]+\/(objectives|ideas|tasks|decisions|research|knowledge|guidelines|lessons|ac-templates)\/([A-Z]+-?\d+|[^/]+)$/);
    if (!match) {
      // Not on an entity detail page — clear binding
      useSidebarStore.getState().clearTargetEntity();
      return;
    }
    const [, segment, id] = match;
    const ROUTE_TO_TYPE: Record<string, string> = {
      objectives: "objective", ideas: "idea", tasks: "task",
      decisions: "decision", research: "research", knowledge: "knowledge",
      guidelines: "guideline", lessons: "lesson", "ac-templates": "ac_template",
    };
    const entityType = ROUTE_TO_TYPE[segment];
    if (entityType) {
      setTargetEntity({ type: entityType, id, label: id });
    }
  }, [pathname, setTargetEntity]);

  // Apply entity_type_defaults scopes from project config
  const projectDetails = useProjectStore((s) => s.details);
  useEffect(() => {
    if (!targetEntity || !projectSlugFromPath) {
      useSidebarStore.getState().setEntityDefaultScopes([]);
      return;
    }
    const detail = projectDetails[projectSlugFromPath];
    const defaults = (detail?.config as Record<string, unknown>)?.entity_type_defaults as
      Record<string, { scopes?: string[] }> | undefined;
    const entityScopes = defaults?.[targetEntity.type]?.scopes ?? [];
    useSidebarStore.getState().setEntityDefaultScopes(entityScopes);
  }, [targetEntity, projectDetails, projectSlugFromPath]);

  // Resolve scopes from URL + overrides
  const { scopes: urlScopes, projectSlug, contextTypes, contextId: resolvedContextId } = useScopeResolver({
    addedScopes,
    removedScopes,
  });

  // AI page context from annotations — subscribe for reactive updates
  const aiCtx = useAIPageContextSafe();
  const [, setAnnotationVersion] = useState(0);
  useEffect(() => {
    if (!aiCtx) return;
    return aiCtx.subscribe(() => setAnnotationVersion((v) => v + 1));
  }, [aiCtx]);
  const pageSnapshot = aiCtx?.getSnapshot() ?? null;
  // Merge URL scopes with annotation-derived scopes
  const annotationScopes = pageSnapshot && pageSnapshot.elements.size > 0
    ? deriveScopesFromElements(pageSnapshot.elements.values())
    : [];
  const entityDefaultScopes = useSidebarStore((s) => s.entityDefaultScopes);
  // "*" in entity defaults means all available scopes
  const entityScopes = entityDefaultScopes.includes("*") ? urlScopes : entityDefaultScopes;
  const scopes = Array.from(new Set([...urlScopes, ...annotationScopes, ...entityScopes]));

  // Sync scopes to active session backend when they change
  const scopesKey = scopes.join(",");
  const prevScopesRef = useRef(scopesKey);
  useEffect(() => {
    if (prevScopesRef.current !== scopesKey) {
      prevScopesRef.current = scopesKey;
      useChatStore.getState().updateSessionScopes(scopesKey.split(",").filter(Boolean));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scopesKey]);

  // Load LLM config for permissions
  const { data: llmConfig } = useSWR<LLMConfig>("llm-config", () => llm.getConfig());
  const permissions = llmConfig?.permissions ?? {};

  // Fetch capabilities for current scopes (for tool name mapping)
  const { data: currentCaps } = useSWR(
    scopes.length > 0 ? ["contracts", ...scopes] : null,
    () => fetchContractsForScopes(scopes),
  );

  // Map disabled capability IDs to tool names for backend
  const disabledToolNames = disabledCapabilities
    .map((id) => {
      const cap = currentCaps?.find((c) => c.id === id);
      return cap?.toolName;
    })
    .filter(Boolean) as string[];

  // Build enabled session tools from backend contracts (for Page Context Session Tools section)
  const enabledSessionTools = currentCaps
    ?.filter((cap) => cap.toolName && !disabledToolNames.includes(cap.toolName))
    .map((cap) => ({ toolName: cap.toolName!, label: cap.label, scope: cap.scope }))
    ?? [];

  // Serialize page context — filtered by active scopes AND disabled capabilities
  // App Context is now server-side (AppContextBuilder), so we only send page context
  const pageContextText = pageSnapshot && pageSnapshot.elements.size > 0
    ? serializePageContext(pageSnapshot, {
        activeScopes: scopes,
        disabledTools: disabledToolNames,
        sessionTools: enabledSessionTools,
      })
    : undefined;

  // Resume session handler
  const handleResume = useCallback(
    async (sessionId: string) => {
      await useChatStore.getState().resumeSession(sessionId);
      setActiveTab("chat");
    },
    [setActiveTab],
  );

  // Primary context for chat
  const primaryContextType = contextTypes[0] ?? "global";

  // Lightweight streaming indicator for the Debug tab badge
  const [debugStreaming, setDebugStreaming] = useState(false);
  useEffect(() => {
    return subscribeToStreamEvents((event) => {
      if (event.event === "chat.token") setDebugStreaming(true);
      else if (event.event === "chat.complete" || event.event === "chat.error") setDebugStreaming(false);
    });
  }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Entity binding badge */}
      {targetEntity && (
        <div className="flex items-center gap-2 px-3 py-1.5 border-b bg-gray-50">
          <span
            className="text-[10px] font-bold px-1.5 py-0.5 rounded text-white"
            style={{ backgroundColor: ENTITY_TYPE_COLORS[targetEntity.type] ?? "#94A3B8" }}
          >
            {targetEntity.type.toUpperCase()}
          </span>
          <span className="text-xs font-medium text-gray-700 truncate flex-1">{targetEntity.label}</span>
          <span className="text-[10px] text-gray-400 font-mono">{targetEntity.id}</span>
          <button
            onClick={clearTargetEntity}
            className="ml-1 rounded-full hover:bg-gray-200 p-0.5 transition-colors"
            title="Clear entity binding"
          >
            <svg className="h-3.5 w-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Scope chips */}
      <ScopeChips scopes={scopes} onRemove={removeScope} />

      {/* Tab bar */}
      <TabBar activeTab={activeTab} onChange={setActiveTab} streaming={debugStreaming} />

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto flex flex-col min-h-0">
        {activeTab === "chat" && (
          <div className="flex flex-col flex-1 min-h-0">
            {activeWorkflow && <WorkflowProgress workflow={activeWorkflow} />}
            <LLMChat
              contextType={primaryContextType}
              contextId={resolvedContextId ?? ""}
              slug={projectSlug ?? ""}
              embedded
              scopes={scopes}
              disabledCapabilities={disabledToolNames}
              pageContext={pageContextText}
              targetEntityType={targetEntity?.type}
              targetEntityId={targetEntity?.id}
              className="flex-1 min-h-0"
            />
            <TokenCounter />
          </div>
        )}

        {activeTab === "tools" && <ToolsTabEnhanced />}

        {activeTab === "scopes" && (
          <ScopesTab
            activeScopes={scopes}
            onAdd={addScope}
            onRemove={removeScope}
            onReset={resetScopes}
            disabledCapabilities={disabledCapabilities}
            disabledToolNames={disabledToolNames}
            permissions={permissions}
            onToggleCapability={toggleCapability}
            pageTitle={pageSnapshot?.pageConfig?.title ?? null}
            pageElementCount={pageSnapshot?.elements.size ?? 0}
            annotationScopes={annotationScopes}
            pageContextText={pageContextText}
            pageElements={pageSnapshot ? Array.from(pageSnapshot.elements.values()) : undefined}
            projectSlug={projectSlug}
            entityDefaultScopes={entityDefaultScopes}
          />
        )}

        {activeTab === "conversations" && (
          <ConversationsTab onResume={handleResume} />
        )}

        {/* Debug tab — always mounted so it captures stream events */}
        <DebugTab visible={activeTab === "debug"} />
      </div>
    </div>
  );
}
