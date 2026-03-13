import type { AIElementDescriptor } from "./types";

/**
 * Derive scopes from AI element annotations.
 * Extracts module names from API endpoints in element actions.
 *
 * Examples:
 *   /projects/{slug}/tasks/{id} → "tasks"
 *   /projects/{slug}/decisions   → "decisions"
 *   /api/skills                  → "skills"
 *   /settings/llm                → "settings"
 */
export function deriveScopesFromElements(
  elements: Iterable<AIElementDescriptor>,
): string[] {
  const scopes = new Set<string>();

  for (const el of elements) {
    if (!el.actions) continue;
    for (const action of el.actions) {
      if (!action.endpoint) continue;
      extractScope(action.endpoint, scopes);
    }
  }

  return Array.from(scopes);
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
  if (directMatch && !["projects", "api"].includes(directMatch[1])) {
    scopes.add(directMatch[1]);
  }
}
