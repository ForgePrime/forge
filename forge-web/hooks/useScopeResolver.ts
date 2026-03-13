/**
 * useScopeResolver — maps the current pathname to scopes for the AI sidebar.
 *
 * Returns auto-detected scopes from the URL, supports manual overrides,
 * extracts project slug, and maps scopes to backend context_types.
 */
"use client";

import { useMemo } from "react";
import { usePathname } from "next/navigation";

// ---------------------------------------------------------------------------
// Scope → context_type mapping (must match backend SCOPE_TO_CONTEXT_TYPE)
// ---------------------------------------------------------------------------

export const SCOPE_TO_CONTEXT_TYPE: Record<string, string> = {
  skills: "skill",
  tasks: "task",
  objectives: "objective",
  ideas: "idea",
  decisions: "decision",
  knowledge: "knowledge",
  guidelines: "guideline",
  lessons: "lesson",
  projects: "project",
  ac_templates: "ac_template",
  changes: "change",
  sessions: "global",
  dashboard: "global",
  settings: "global",
};

// ---------------------------------------------------------------------------
// Route → scope rules (ordered, first match wins)
// ---------------------------------------------------------------------------

interface RouteRule {
  pattern: RegExp;
  scopes: string[];
  /** If true, capture group 1 is the project slug. */
  hasProject?: boolean;
}

const ROUTE_RULES: RouteRule[] = [
  // Skills (global, not project-scoped)
  { pattern: /^\/skills\/new$/, scopes: ["skills"] },
  { pattern: /^\/skills\/([^/]+)$/, scopes: ["skills"] },
  { pattern: /^\/skills$/, scopes: ["skills"] },

  // Project sub-pages (order: specific before general)
  { pattern: /^\/projects\/([^/]+)\/tasks\/([^/]+)$/, scopes: ["tasks"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/tasks$/, scopes: ["tasks"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/board$/, scopes: ["tasks"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/execution\/context\/([^/]+)$/, scopes: ["tasks"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/execution\/([^/]+)$/, scopes: ["tasks"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/objectives\/([^/]+)$/, scopes: ["objectives"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/objectives$/, scopes: ["objectives"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/ideas\/([^/]+)$/, scopes: ["ideas"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/ideas$/, scopes: ["ideas"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/decisions\/([^/]+)$/, scopes: ["decisions"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/decisions$/, scopes: ["decisions"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/knowledge\/([^/]+)$/, scopes: ["knowledge"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/knowledge$/, scopes: ["knowledge"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/guidelines\/([^/]+)$/, scopes: ["guidelines"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/guidelines$/, scopes: ["guidelines"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/changes$/, scopes: ["changes"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/lessons$/, scopes: ["lessons"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/ac-templates$/, scopes: ["ac_templates"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/settings$/, scopes: ["settings"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)\/debug$/, scopes: ["dashboard"], hasProject: true },
  { pattern: /^\/projects\/([^/]+)$/, scopes: ["projects"], hasProject: true },

  // Top-level pages
  { pattern: /^\/sessions\/([^/]+)$/, scopes: ["sessions"] },
  { pattern: /^\/sessions$/, scopes: ["sessions"] },
  { pattern: /^\/projects$/, scopes: ["projects"] },
  { pattern: /^\/settings/, scopes: ["settings"] },
  { pattern: /^\/$/, scopes: ["dashboard"] },
];

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface ScopeResolverResult {
  /** Auto-detected scopes from URL (merged with overrides). */
  scopes: string[];
  /** First scope in the list. */
  primaryScope: string;
  /** Project slug extracted from URL, or null. */
  projectSlug: string | null;
  /** Scopes mapped to backend context_types. */
  contextTypes: string[];
  /** Entity ID extracted from detail page routes (e.g., "T-001"), or null. */
  contextId: string | null;
}

interface ScopeResolverOptions {
  /** Extra scopes to add (e.g., user manually added "knowledge"). */
  addedScopes?: string[];
  /** Scopes to remove (e.g., user deselected "tasks"). */
  removedScopes?: string[];
}

export function useScopeResolver(
  options: ScopeResolverOptions = {},
): ScopeResolverResult {
  const pathname = usePathname();
  const { addedScopes = [], removedScopes = [] } = options;

  return useMemo(() => {
    return resolveScopes(pathname, addedScopes, removedScopes);
  }, [pathname, addedScopes, removedScopes]);
}

/**
 * Pure function for scope resolution — testable without React.
 */
export function resolveScopes(
  pathname: string,
  addedScopes: string[] = [],
  removedScopes: string[] = [],
): ScopeResolverResult {
  let autoScopes: string[] = ["dashboard"];
  let projectSlug: string | null = null;
  let contextId: string | null = null;

  for (const rule of ROUTE_RULES) {
    const match = pathname.match(rule.pattern);
    if (match) {
      autoScopes = rule.scopes;
      if (rule.hasProject && match[1]) {
        projectSlug = match[1];
        // Detail pages have entity ID in capture group 2
        if (match[2]) {
          contextId = match[2];
        }
      }
      break;
    }
  }

  // Merge overrides: (auto + added) - removed
  const removed = new Set(removedScopes);
  const merged = new Set(autoScopes.concat(addedScopes));
  const scopes = Array.from(merged).filter((s) => !removed.has(s));

  // Fallback if everything was removed
  if (scopes.length === 0) {
    scopes.push("dashboard");
  }

  const contextTypes = scopes
    .map((s) => SCOPE_TO_CONTEXT_TYPE[s])
    .filter(Boolean);

  return {
    scopes,
    primaryScope: scopes[0],
    projectSlug,
    contextTypes,
    contextId,
  };
}
