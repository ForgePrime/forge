"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  fetchContractsForScopes,
  getPermissionStatus,
  type CapabilityDef,
  type PermissionStatus,
} from "@/lib/capabilities";
import type { LLMModulePermission } from "@/lib/types";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface CapabilityContractProps {
  scopes: string[];
  disabledCapabilities: string[];
  permissions: Record<string, LLMModulePermission>;
  onToggle: (capabilityId: string, enabled: boolean) => void;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const ACTION_STYLES: Record<string, string> = {
  READ: "bg-emerald-900/40 text-emerald-400",
  WRITE: "bg-blue-900/40 text-blue-400",
  DELETE: "bg-red-900/40 text-red-400",
};

function ActionBadge({ action }: { action: string }) {
  return (
    <span
      className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${ACTION_STYLES[action] ?? "bg-gray-700 text-gray-300"}`}
    >
      {action}
    </span>
  );
}

function StatusLabel({ status }: { status: PermissionStatus }) {
  if (status === "no-permission") {
    return <span className="text-[10px] text-red-400">No permission</span>;
  }
  if (status === "coming-soon") {
    return <span className="text-[10px] text-gray-500">Coming soon</span>;
  }
  return null;
}

function Toggle({
  enabled,
  disabled,
  onChange,
}: {
  enabled: boolean;
  disabled: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      disabled={disabled}
      onClick={() => onChange(!enabled)}
      className={`
        relative inline-flex h-4 w-7 shrink-0 rounded-full transition-colors
        ${disabled ? "cursor-not-allowed opacity-40" : "cursor-pointer"}
        ${enabled ? "bg-blue-600" : "bg-gray-600"}
      `}
    >
      <span
        className={`
          pointer-events-none inline-block h-3 w-3 rounded-full bg-white
          shadow transform transition-transform mt-0.5
          ${enabled ? "translate-x-3.5 ml-0" : "translate-x-0.5"}
        `}
      />
    </button>
  );
}

function CapabilityRow({
  capability,
  status,
  isDisabled,
  onToggle,
}: {
  capability: CapabilityDef;
  status: PermissionStatus;
  isDisabled: boolean;
  onToggle: (id: string, enabled: boolean) => void;
}) {
  const toggleDisabled = status !== "enabled";
  const enabled = status === "enabled" && !isDisabled;

  return (
    <div className="flex items-center gap-2 py-1.5 px-2 rounded hover:bg-gray-800/50">
      <Toggle
        enabled={enabled}
        disabled={toggleDisabled}
        onChange={(v) => onToggle(capability.id, v)}
      />
      <span
        className={`flex-1 text-xs truncate ${toggleDisabled ? "text-gray-500" : "text-gray-300"}`}
        title={capability.description}
      >
        {capability.label}
      </span>
      <ActionBadge action={capability.action} />
      <StatusLabel status={status} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function CapabilityContract({
  scopes,
  disabledCapabilities,
  permissions,
  onToggle,
}: CapabilityContractProps) {
  const [expanded, setExpanded] = useState(false);
  const { data: capabilities = [] } = useSWR(
    scopes.length > 0 ? ["contracts", ...scopes] : null,
    () => fetchContractsForScopes(scopes),
  );

  if (capabilities.length === 0) return null;

  const disabledSet = new Set(disabledCapabilities);
  const enabledCount = capabilities.filter(
    (c) => getPermissionStatus(c, permissions) === "enabled" && !disabledSet.has(c.id),
  ).length;

  return (
    <div className="border border-gray-700/50 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full px-3 py-2 text-xs text-gray-400 hover:bg-gray-800/50"
      >
        <svg
          className={`w-3 h-3 transition-transform ${expanded ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
        <span className="font-medium">Capabilities</span>
        <span className="ml-auto text-gray-500">
          {enabledCount}/{capabilities.length}
        </span>
      </button>

      {expanded && (
        <div className="border-t border-gray-700/50 px-1 py-1">
          {capabilities.map((cap) => {
            const status = getPermissionStatus(cap, permissions);
            return (
              <CapabilityRow
                key={cap.id}
                capability={cap}
                status={status}
                isDisabled={disabledSet.has(cap.id)}
                onToggle={onToggle}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
