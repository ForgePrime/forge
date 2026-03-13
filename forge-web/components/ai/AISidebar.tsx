"use client";

import { useEffect, useCallback, useState, useRef } from "react";
import { useScopeResolver, SCOPE_TO_CONTEXT_TYPE } from "@/hooks/useScopeResolver";
import { CAPABILITY_CONTRACTS, getCapabilitiesForScopes, getPermissionStatus, type CapabilityDef } from "@/lib/capabilities";
import { useAIPageContextSafe, serializePageContext, deriveScopesFromElements } from "@/lib/ai-context";
import { useSidebarStore } from "@/stores/sidebarStore";
import { useChatStore } from "@/stores/chatStore";
import { useSkillStore, fetchSkills } from "@/stores/skillStore";
import type { LLMConfig } from "@/lib/types";
import LLMChat from "./LLMChat";
import useSWR from "swr";
import { llm } from "@/lib/api";
import Link from "next/link";

// ---------------------------------------------------------------------------
// Tab types
// ---------------------------------------------------------------------------

type SidebarTab = "chat" | "tools" | "scopes" | "conversations";

const TABS: { key: SidebarTab; label: string }[] = [
  { key: "chat", label: "Chat" },
  { key: "tools", label: "Tools" },
  { key: "scopes", label: "Scopes" },
  { key: "conversations", label: "History" },
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
}: {
  activeTab: SidebarTab;
  onChange: (tab: SidebarTab) => void;
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
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tools tab
// ---------------------------------------------------------------------------

function ToolsTab() {
  const { items: skills } = useSkillStore();

  useEffect(() => {
    if (skills.length === 0) {
      fetchSkills();
    }
  }, [skills.length]);

  if (skills.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-gray-400">
        No skills available
      </div>
    );
  }

  return (
    <div className="divide-y">
      {skills.map((skill) => (
        <Link
          key={skill.name}
          href={`/skills/${skill.name}`}
          className="block px-3 py-2 hover:bg-gray-50 transition-colors"
        >
          <div className="text-xs font-medium text-gray-800 truncate">{skill.display_name || skill.name}</div>
          {skill.description && (
            <div className="text-[11px] text-gray-500 truncate mt-0.5">{skill.description}</div>
          )}
          {skill.scopes && skill.scopes.length > 0 && (
            <div className="flex gap-1 mt-1">
              {skill.scopes.slice(0, 3).map((s: string) => (
                <span key={s} className="text-[10px] rounded bg-gray-100 px-1.5 py-0.5 text-gray-500">
                  {s}
                </span>
              ))}
            </div>
          )}
        </Link>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Scopes tab — scope checkboxes + capabilities for active scopes
// ---------------------------------------------------------------------------

const ALL_SCOPES = Object.keys(SCOPE_TO_CONTEXT_TYPE);

const ACTION_BADGE: Record<string, string> = {
  READ: "bg-blue-100 text-blue-700",
  WRITE: "bg-amber-100 text-amber-700",
  DELETE: "bg-red-100 text-red-700",
};

function ScopesTab({
  activeScopes,
  onAdd,
  onRemove,
  onReset,
  disabledCapabilities,
  permissions,
  onToggleCapability,
  pageTitle,
  pageElementCount,
  annotationScopes,
}: {
  activeScopes: string[];
  onAdd: (scope: string) => void;
  onRemove: (scope: string) => void;
  onReset: () => void;
  disabledCapabilities: string[];
  permissions: Record<string, { read: boolean; write: boolean; delete: boolean }>;
  onToggleCapability: (capabilityId: string, enabled: boolean) => void;
  /** Current page title from AI annotations (e.g., "Tasks (25)"). */
  pageTitle: string | null;
  /** Number of annotated elements on the page. */
  pageElementCount: number;
  /** Scopes derived from page annotations. */
  annotationScopes: string[];
}) {
  const activeSet = new Set(activeScopes);
  const disabledSet = new Set(disabledCapabilities);

  // Collect capabilities for active scopes
  const activeCaps: CapabilityDef[] = [];
  const seenIds = new Set<string>();
  for (const scope of activeScopes) {
    const caps = CAPABILITY_CONTRACTS[scope];
    if (!caps) continue;
    for (const cap of caps) {
      if (!seenIds.has(cap.id)) {
        seenIds.add(cap.id);
        activeCaps.push(cap);
      }
    }
  }

  return (
    <div className="px-3 py-2">
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
          const capCount = CAPABILITY_CONTRACTS[scope]?.length ?? 0;
          return (
            <label key={scope} className="flex items-center gap-2 py-1 cursor-pointer hover:bg-gray-50 rounded px-1">
              <input
                type="checkbox"
                checked={checked}
                onChange={() => (checked ? onRemove(scope) : onAdd(scope))}
                className="rounded border-gray-300 text-forge-600 focus:ring-forge-500 h-3.5 w-3.5"
              />
              <span className="text-xs text-gray-700">{scope}</span>
              <span className="text-[10px] text-gray-400 ml-auto">
                {capCount > 0 ? `${capCount} ops` : SCOPE_TO_CONTEXT_TYPE[scope]}
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
  const [searchQuery, setSearchQuery] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

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
    useChatStore.getState().startConversation("global", "");
    useSidebarStore.getState().setActiveTab("chat");
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between px-3 py-2 border-b">
        <button
          onClick={handleNew}
          className="text-xs font-medium text-forge-600 hover:text-forge-800"
        >
          + New conversation
        </button>
        <button
          onClick={() => { setSearchQuery(""); loadSessions(); }}
          disabled={sessionsLoading}
          className="text-[10px] text-gray-500 hover:text-gray-700"
          title="Refresh"
        >
          {sessionsLoading ? "..." : "Refresh"}
        </button>
      </div>

      {/* Search input */}
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

      {sessionList.length === 0 ? (
        <div className="flex items-center justify-center h-24 text-sm text-gray-400">
          {sessionsLoading ? "Loading..." : searchQuery ? "No matching conversations" : "No conversations yet"}
        </div>
      ) : (
        <div className="divide-y">
          {sessionList.map((session) => (
            <div
              key={session.session_id}
              className="px-3 py-2 hover:bg-gray-50 transition-colors cursor-pointer group"
              onClick={() => onResume(session.session_id)}
            >
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] rounded bg-forge-100 px-1.5 py-0.5 text-forge-600 font-medium">
                  {session.context_type}
                </span>
                {session.context_id && (
                  <span className="text-[10px] text-gray-500 truncate">{session.context_id}</span>
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
  } = useSidebarStore();

  // Hydrate from localStorage on mount
  useEffect(() => {
    hydrate();
  }, [hydrate]);

  // Resolve scopes from URL + overrides
  const { scopes: urlScopes, projectSlug, contextTypes, contextId: resolvedContextId } = useScopeResolver({
    addedScopes,
    removedScopes,
  });

  // AI page context from annotations
  const aiCtx = useAIPageContextSafe();
  const pageSnapshot = aiCtx?.getSnapshot() ?? null;
  const pageContextText = pageSnapshot && pageSnapshot.elements.size > 0
    ? serializePageContext(pageSnapshot)
    : undefined;

  // Merge URL scopes with annotation-derived scopes
  const annotationScopes = pageSnapshot && pageSnapshot.elements.size > 0
    ? deriveScopesFromElements(pageSnapshot.elements.values())
    : [];
  const scopes = Array.from(new Set([...urlScopes, ...annotationScopes]));

  // Load LLM config for permissions
  const { data: llmConfig } = useSWR<LLMConfig>("llm-config", () => llm.getConfig());
  const permissions = llmConfig?.permissions ?? {};

  // Map disabled capability IDs to tool names for backend
  const disabledToolNames = disabledCapabilities
    .map((id) => {
      const caps = getCapabilitiesForScopes(scopes);
      const cap = caps.find((c) => c.id === id);
      return cap?.toolName;
    })
    .filter(Boolean) as string[];

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

  return (
    <div className="flex flex-col h-full">
      {/* Scope chips */}
      <ScopeChips scopes={scopes} onRemove={removeScope} />

      {/* Tab bar */}
      <TabBar activeTab={activeTab} onChange={setActiveTab} />

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto flex flex-col min-h-0">
        {activeTab === "chat" && (
          <div className="flex flex-col flex-1 min-h-0">
            <LLMChat
              contextType={primaryContextType}
              contextId={resolvedContextId ?? ""}
              slug={projectSlug ?? ""}
              embedded
              scopes={scopes}
              disabledCapabilities={disabledToolNames}
              pageContext={pageContextText}
              className="flex-1 min-h-0"
            />
          </div>
        )}

        {activeTab === "tools" && <ToolsTab />}

        {activeTab === "scopes" && (
          <ScopesTab
            activeScopes={scopes}
            onAdd={addScope}
            onRemove={removeScope}
            onReset={resetScopes}
            disabledCapabilities={disabledCapabilities}
            permissions={permissions}
            onToggleCapability={toggleCapability}
            pageTitle={pageSnapshot?.pageConfig?.title ?? null}
            pageElementCount={pageSnapshot?.elements.size ?? 0}
            annotationScopes={annotationScopes}
          />
        )}

        {activeTab === "conversations" && (
          <ConversationsTab onResume={handleResume} />
        )}
      </div>
    </div>
  );
}
