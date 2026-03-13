/**
 * Capability system — dynamic contracts from backend ToolRegistry.
 *
 * Previously contained a ~700-line static CAPABILITY_CONTRACTS registry.
 * Now fetches contracts dynamically from GET /llm/contracts.
 *
 * Keeps: type definitions, permission helpers, scope list.
 */

import type { LLMModulePermission, BackendToolContract } from "./types";
import { llm } from "./api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CapabilityParam {
  name: string;
  type: "string" | "number" | "boolean" | "array" | "object";
  required: boolean;
  description: string;
  enum?: string[];
}

export interface CapabilityContract {
  params: CapabilityParam[];
  returns: string;
}

export interface CapabilityDef {
  /** Unique ID, e.g., "skills-list". */
  id: string;
  /** Display label, e.g., "List all skills". */
  label: string;
  /** Short description of what this capability does. */
  description: string;
  /** Action type — used for permission checks. */
  action: "READ" | "WRITE" | "DELETE";
  /** Scope this capability belongs to. */
  scope: string;
  /** Backend tool name, or null if not yet implemented. */
  toolName: string | null;
  /** Whether the backend tool exists. */
  available: boolean;
  /** Contract — parameter list and return description. */
  contract?: CapabilityContract;
}

export type PermissionStatus = "enabled" | "no-permission" | "coming-soon";

// ---------------------------------------------------------------------------
// All known scopes (static list — matches backend SCOPE_TO_CONTEXT_TYPE)
// ---------------------------------------------------------------------------

export const ALL_SCOPES = [
  "skills", "tasks", "planning", "objectives", "ideas",
  "decisions", "knowledge", "guidelines", "lessons",
  "changes", "ac_templates", "research", "projects",
  "verification", "dashboard",
];

// ---------------------------------------------------------------------------
// Transform backend contract → CapabilityDef
// ---------------------------------------------------------------------------

/** Convert camelCase tool name to human label: "createTask" → "Create task". */
function humanize(name: string): string {
  const spaced = name.replace(/([A-Z])/g, " $1").trim();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1).toLowerCase();
}

/** Map backend action string to our action enum. */
function mapAction(action: string): "READ" | "WRITE" | "DELETE" {
  const upper = action.toUpperCase();
  if (upper === "DELETE") return "DELETE";
  if (upper === "WRITE") return "WRITE";
  return "READ";
}

/** Convert JSON Schema parameters to CapabilityParam list. */
function jsonSchemaToParams(params: Record<string, unknown>): CapabilityParam[] {
  if (!params || typeof params !== "object") return [];
  const properties = params.properties as Record<string, Record<string, unknown>> | undefined;
  if (!properties) return [];

  const required = new Set((params.required as string[]) ?? []);
  return Object.entries(properties).map(([name, prop]) => ({
    name,
    type: (prop.type as CapabilityParam["type"]) ?? "string",
    required: required.has(name),
    description: (prop.description as string) ?? "",
    ...(prop.enum ? { enum: prop.enum as string[] } : {}),
  }));
}

/** Transform a backend contract to a CapabilityDef. */
export function transformContract(c: BackendToolContract): CapabilityDef {
  return {
    id: `${c.scope ?? "global"}-${c.name}`,
    label: humanize(c.name),
    description: c.description ?? "",
    action: mapAction(c.action),
    scope: c.scope ?? "global",
    toolName: c.name,
    available: true,
    contract: {
      params: jsonSchemaToParams(c.parameters),
      returns: "",
    },
  };
}

// ---------------------------------------------------------------------------
// Dynamic fetch
// ---------------------------------------------------------------------------

/** Fetch contracts for given scopes from backend and transform to CapabilityDef[]. */
export async function fetchContractsForScopes(scopes: string[]): Promise<CapabilityDef[]> {
  if (scopes.length === 0) return [];
  const data = await llm.getContracts(scopes);
  return data.contracts.map(transformContract);
}

/** Fetch all contracts from backend. */
export async function fetchAllContracts(): Promise<CapabilityDef[]> {
  const data = await llm.getContracts();
  return data.contracts.map(transformContract);
}

// ---------------------------------------------------------------------------
// Helpers (kept for backward compatibility)
// ---------------------------------------------------------------------------

/**
 * Get the permission status for a capability given the current LLM permissions.
 */
export function getPermissionStatus(
  capability: CapabilityDef,
  permissions: Record<string, LLMModulePermission>,
): PermissionStatus {
  if (!capability.available) return "coming-soon";

  const modulePerms = permissions[capability.scope];
  if (!modulePerms) return "enabled"; // no restriction configured

  const actionKey = capability.action.toLowerCase() as keyof LLMModulePermission;
  if (!modulePerms[actionKey]) return "no-permission";

  return "enabled";
}
