/**
 * Capability Contract Registry — static definitions of what the AI can do per scope.
 *
 * Each scope (skills, tasks, etc.) has a list of capabilities with:
 * - tool mapping to backend ToolRegistry
 * - availability flag (false = tool not yet implemented)
 * - action type for permission checking
 */

import type { LLMModulePermission } from "./types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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
}

export type PermissionStatus = "enabled" | "no-permission" | "coming-soon";

// ---------------------------------------------------------------------------
// Capability contracts per scope
// ---------------------------------------------------------------------------

export const CAPABILITY_CONTRACTS: Record<string, CapabilityDef[]> = {
  skills: [
    { id: "skills-list", label: "List skills", description: "View all available skills", action: "READ", scope: "skills", toolName: "listEntities", available: true },
    { id: "skills-search", label: "Search skills", description: "Search skills by query", action: "READ", scope: "skills", toolName: "searchEntities", available: true },
    { id: "skills-create", label: "Create skill", description: "Create a new skill definition", action: "WRITE", scope: "skills", toolName: "updateSkillContent", available: true },
    { id: "skills-edit", label: "Edit skill", description: "Modify skill content or metadata", action: "WRITE", scope: "skills", toolName: "updateSkillContent", available: true },
    { id: "skills-lint", label: "Lint skill", description: "Run TESLint quality check on a skill", action: "READ", scope: "skills", toolName: "runSkillLint", available: true },
    { id: "skills-delete", label: "Delete skill", description: "Remove a skill definition", action: "DELETE", scope: "skills", toolName: null, available: false },
    { id: "skills-promote", label: "Promote skill", description: "Promote skill to production", action: "WRITE", scope: "skills", toolName: null, available: false },
    { id: "skills-export", label: "Export skill", description: "Export skill as file", action: "READ", scope: "skills", toolName: null, available: false },
  ],
  tasks: [
    { id: "tasks-list", label: "List tasks", description: "View all tasks in project", action: "READ", scope: "tasks", toolName: "listEntities", available: true },
    { id: "tasks-search", label: "Search tasks", description: "Search tasks by query", action: "READ", scope: "tasks", toolName: "searchEntities", available: true },
    { id: "tasks-show", label: "Show task", description: "View full task details", action: "READ", scope: "tasks", toolName: "getEntity", available: true },
    { id: "tasks-create", label: "Create task", description: "Add a new task to pipeline", action: "WRITE", scope: "tasks", toolName: null, available: false },
    { id: "tasks-update", label: "Update task", description: "Modify task status or fields", action: "WRITE", scope: "tasks", toolName: null, available: false },
    { id: "tasks-complete", label: "Complete task", description: "Mark a task as done", action: "WRITE", scope: "tasks", toolName: null, available: false },
  ],
  objectives: [
    { id: "objectives-list", label: "List objectives", description: "View all business objectives", action: "READ", scope: "objectives", toolName: "listEntities", available: true },
    { id: "objectives-show", label: "Show objective", description: "View objective details and KR progress", action: "READ", scope: "objectives", toolName: "getEntity", available: true },
    { id: "objectives-create", label: "Create objective", description: "Define a new business objective", action: "WRITE", scope: "objectives", toolName: null, available: false },
    { id: "objectives-update", label: "Update objective", description: "Update KR values or status", action: "WRITE", scope: "objectives", toolName: null, available: false },
  ],
  ideas: [
    { id: "ideas-list", label: "List ideas", description: "View all ideas in staging", action: "READ", scope: "ideas", toolName: "listEntities", available: true },
    { id: "ideas-show", label: "Show idea", description: "View idea details and relations", action: "READ", scope: "ideas", toolName: "getEntity", available: true },
    { id: "ideas-create", label: "Create idea", description: "Add a new idea to staging", action: "WRITE", scope: "ideas", toolName: null, available: false },
    { id: "ideas-update", label: "Update idea", description: "Modify idea status or fields", action: "WRITE", scope: "ideas", toolName: null, available: false },
  ],
  decisions: [
    { id: "decisions-list", label: "List decisions", description: "View all decisions", action: "READ", scope: "decisions", toolName: "listEntities", available: true },
    { id: "decisions-show", label: "Show decision", description: "View full decision details", action: "READ", scope: "decisions", toolName: "getEntity", available: true },
    { id: "decisions-create", label: "Create decision", description: "Record a new decision", action: "WRITE", scope: "decisions", toolName: null, available: false },
    { id: "decisions-update", label: "Update decision", description: "Close or defer a decision", action: "WRITE", scope: "decisions", toolName: null, available: false },
  ],
  knowledge: [
    { id: "knowledge-list", label: "List knowledge", description: "View all knowledge objects", action: "READ", scope: "knowledge", toolName: "listEntities", available: true },
    { id: "knowledge-show", label: "Show knowledge", description: "View knowledge details", action: "READ", scope: "knowledge", toolName: "getEntity", available: true },
    { id: "knowledge-create", label: "Create knowledge", description: "Add domain knowledge", action: "WRITE", scope: "knowledge", toolName: null, available: false },
    { id: "knowledge-update", label: "Update knowledge", description: "Update knowledge content", action: "WRITE", scope: "knowledge", toolName: null, available: false },
  ],
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Get merged capabilities for a list of scopes (deduped by id).
 */
export function getCapabilitiesForScopes(scopes: string[]): CapabilityDef[] {
  const seen = new Set<string>();
  const result: CapabilityDef[] = [];

  for (const scope of scopes) {
    const caps = CAPABILITY_CONTRACTS[scope];
    if (!caps) continue;
    for (const cap of caps) {
      if (!seen.has(cap.id)) {
        seen.add(cap.id);
        result.push(cap);
      }
    }
  }

  return result;
}

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
