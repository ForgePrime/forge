import type { AIElementDescriptor } from "./types";

/**
 * Tool name prefix → scope mapping.
 * E.g., "createTask" starts with "Task" entity → scope "tasks".
 */
export const TOOL_ENTITY_TO_SCOPE: Record<string, string> = {
  Task: "tasks",
  Decision: "decisions",
  Objective: "objectives",
  Idea: "ideas",
  Knowledge: "knowledge",
  Guideline: "guidelines",
  Lesson: "lessons",
  Change: "changes",
  Skill: "skills",
  Research: "research",
  ACTemplate: "ac_templates",
  Project: "projects",
  Plan: "planning",
  Gate: "verification",
  Draft: "planning",
};

/**
 * Derive scopes from AI element annotations.
 * Extracts module names from tool names or API endpoints in element actions.
 *
 * Examples:
 *   toolName: "createTask"             → "tasks"
 *   toolName: "updateGuideline"        → "guidelines"
 *   endpoint: /projects/{slug}/tasks   → "tasks"
 */
export function deriveScopesFromElements(
  elements: Iterable<AIElementDescriptor> | AIElementDescriptor[],
): string[] {
  const scopes = new Set<string>();
  const arr = Array.isArray(elements) ? elements : Array.from(elements);

  for (const el of arr) {
    if (!el.actions) continue;
    for (const action of el.actions) {
      if (action.toolName) {
        extractScopeFromTool(action.toolName, scopes);
      } else if (action.endpoint) {
        extractScope(action.endpoint, scopes);
      }
    }
  }

  return Array.from(scopes);
}

/**
 * Get the scope name for a tool, or null if unknown.
 * E.g., "createTask" → "tasks", "updateGuideline" → "guidelines".
 */
export function toolScopeFromName(toolName: string): string | null {
  for (const [entity, scope] of Object.entries(TOOL_ENTITY_TO_SCOPE)) {
    if (toolName.includes(entity)) return scope;
  }
  return null;
}

function extractScopeFromTool(toolName: string, scopes: Set<string>): void {
  for (const [entity, scope] of Object.entries(TOOL_ENTITY_TO_SCOPE)) {
    if (toolName.includes(entity)) {
      scopes.add(scope);
      return;
    }
  }
}

function extractScope(endpoint: string, scopes: Set<string>): void {
  // /projects/{slug}/{module}/...
  const projectMatch = endpoint.match(/\/projects\/\{[^}]+\}\/([a-z_-]+)/);
  if (projectMatch) {
    scopes.add(projectMatch[1]);
    return;
  }
  // /api/{module}/... or /{module}/...
  const directMatch = endpoint.match(/^\/?(?:api\/)?([a-z_-]+)/);
  if (directMatch && directMatch[1] !== "api") {
    scopes.add(directMatch[1]);
  }
}
