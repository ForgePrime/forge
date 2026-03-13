import type { AIContextSnapshot, AIElementDescriptor, AIActionDescriptor } from "./types";
import { toolScopeFromName, TOOL_ENTITY_TO_SCOPE } from "./deriveScopes";

export interface SerializeOptions {
  /** Max total characters (default: 4000) */
  maxChars?: number;
  /** Max list/data items to show (default: 15) */
  maxItems?: number;
  /** Active scopes — if provided, filter actions to only show available tools */
  activeScopes?: string[];
  /** Tool names disabled by user — filtered from page context */
  disabledTools?: string[];
}

// ---------------------------------------------------------------------------
// Scope → entity type mapping (for browsing hints)
// ---------------------------------------------------------------------------

const SCOPE_TO_ENTITY: Record<string, string> = {};
for (const [entity, scope] of Object.entries(TOOL_ENTITY_TO_SCOPE)) {
  // "Task" → "tasks" scope → entity_type "task" (lowercase singular)
  SCOPE_TO_ENTITY[scope] = entity.toLowerCase();
}

// Global tools that are always available (no scope needed)
const GLOBAL_TOOLS = new Set([
  "searchEntities", "getEntity", "listEntities", "getProject", "getProjectStatus",
]);

/**
 * Serialize collected AI annotations into SKILL-like instructive text for LLM context.
 *
 * Output format:
 * ```
 * ## Current Page: Tasks
 * Task list for project
 *
 * ### Page State
 * - Tasks list: 42 items (status: TODO: 10, DONE: 20, IN_PROGRESS: 12)
 * - Status Filter: "TODO"
 *
 * ### Available Actions
 * - **Create task**: `createTask(name, type, description, scopes)` — name and type required
 * - **Update task**: `updateTask(task_id, name, status)` — task_id required [when: status = TODO]
 *
 * ### Browsing
 * - Search: `searchEntities(query, entity_type="task")`
 * - Get details: `getEntity(entity_type="task", entity_id="T-001")`
 * ```
 */
export function serializePageContext(
  snapshot: AIContextSnapshot,
  options: SerializeOptions = {},
): string {
  const { maxChars = 4000, maxItems = 15, activeScopes, disabledTools } = options;
  const lines: string[] = [];

  // --- Header ---
  if (snapshot.pageConfig) {
    const { title, description } = snapshot.pageConfig;
    lines.push(`## Current Page: ${title}`);
    if (description) lines.push(description);
    lines.push("");
  } else if (snapshot.elements.size > 0) {
    lines.push("## Current Page");
    lines.push("");
  }

  const elements = Array.from(snapshot.elements.values());

  // --- Page State ---
  const stateLines = serializePageState(elements, maxItems);
  if (stateLines.length > 0) {
    lines.push("### Page State");
    lines.push(...stateLines);
    lines.push("");
  }

  // --- Available Actions ---
  const { actionLines, filteredCount } = serializeActions(elements, activeScopes, disabledTools);
  if (actionLines.length > 0) {
    lines.push("### Available Actions");
    lines.push(...actionLines);
    if (filteredCount > 0) {
      lines.push(`\n_${filteredCount} action(s) hidden — enable their scope in the Scopes tab to use them._`);
    }
    lines.push("");
  }

  // --- Browsing hints ---
  const entityType = deriveEntityType(snapshot);
  if (entityType) {
    lines.push("### Browsing");
    lines.push(`- Search: \`searchEntities(query, entity_type="${entityType}")\``);
    lines.push(`- Get details: \`getEntity(entity_type="${entityType}", entity_id="...")\``);
    lines.push("");
  }

  let result = lines.join("\n");
  if (result.length > maxChars) {
    const suffix = "\n... (truncated, use tools for full data)";
    result = result.slice(0, maxChars - suffix.length) + suffix;
  }

  return result;
}

// ---------------------------------------------------------------------------
// Page State — what the user sees (data, filters, displays)
// ---------------------------------------------------------------------------

function serializePageState(
  elements: AIElementDescriptor[],
  maxItems: number,
): string[] {
  const lines: string[] = [];

  for (const el of elements) {
    const label = el.label ?? el.id;

    // Build value part
    let valuePart = "";
    if (el.value !== undefined && el.value !== null && el.value !== "") {
      valuePart = `: ${JSON.stringify(el.value)}`;
    }

    // Build data summary
    let dataPart = "";
    if (el.data && Object.keys(el.data).length > 0) {
      const parts: string[] = [];
      for (const [key, val] of Object.entries(el.data)) {
        if (typeof val === "object" && val !== null && !Array.isArray(val)) {
          const entries = Object.entries(val as Record<string, unknown>)
            .filter(([, v]) => v !== 0 && v !== undefined)
            .map(([k, v]) => `${k}: ${v}`);
          if (entries.length > 0) {
            parts.push(`${key}: ${entries.join(", ")}`);
          }
        } else if (Array.isArray(val)) {
          const shown = val.slice(0, maxItems);
          const rest = val.length - shown.length;
          parts.push(`${key}: [${shown.join(", ")}${rest > 0 ? `, +${rest} more` : ""}]`);
        } else if (val !== undefined && val !== null) {
          parts.push(`${key}: ${val}`);
        }
      }
      if (parts.length > 0) {
        dataPart = ` (${parts.join("; ")})`;
      }
    }

    // Build description part
    const descPart = el.description ? ` — ${el.description}` : "";

    lines.push(`- ${label}${valuePart}${dataPart}${descPart}`);
  }

  return lines;
}

// ---------------------------------------------------------------------------
// Available Actions — what the LLM can do (tools)
// ---------------------------------------------------------------------------

interface ActionEntry {
  label: string;
  toolName: string;
  toolParams: string[];
  availableWhen?: string;
  available?: boolean;
  description?: string;
}

function serializeActions(
  elements: AIElementDescriptor[],
  activeScopes?: string[],
  disabledTools?: string[],
): { actionLines: string[]; filteredCount: number } {
  // Collect all actions with toolName
  const actions: ActionEntry[] = [];
  const seenTools = new Set<string>();

  for (const el of elements) {
    if (!el.actions) continue;
    for (const action of el.actions) {
      if (!action.toolName) continue;

      // Deduplicate by toolName + label combo
      const key = `${action.toolName}:${action.label}`;
      if (seenTools.has(key)) continue;
      seenTools.add(key);

      actions.push({
        label: action.label,
        toolName: action.toolName,
        toolParams: action.toolParams ?? [],
        availableWhen: action.availableWhen,
        available: action.available,
        description: action.description,
      });
    }
  }

  if (actions.length === 0) return { actionLines: [], filteredCount: 0 };

  const activeScopeSet = activeScopes ? new Set(activeScopes) : null;
  const disabledSet = disabledTools ? new Set(disabledTools) : null;
  const lines: string[] = [];
  let filteredCount = 0;

  for (const action of actions) {
    // Scope filtering: skip actions whose scope is not active
    if (activeScopeSet && !GLOBAL_TOOLS.has(action.toolName)) {
      const scope = toolScopeFromName(action.toolName);
      if (scope && !activeScopeSet.has(scope)) {
        filteredCount++;
        continue;
      }
    }

    // Capability filtering: skip tools disabled by user
    if (disabledSet && disabledSet.has(action.toolName)) {
      filteredCount++;
      continue;
    }

    // Format: - **Label**: `toolName(params)` — notes
    const callSig = formatCallSignature(action.toolName, action.toolParams);
    const notes = formatNotes(action);

    lines.push(`- **${action.label}**: \`${callSig}\`${notes}`);
  }

  return { actionLines: lines, filteredCount };
}

/**
 * Format a tool call signature from toolName and toolParams.
 *
 * Param formats:
 *   "name*"           → required param (shown without *)
 *   "status=CLOSED"   → param with default value
 *   "description"     → optional param
 */
function formatCallSignature(toolName: string, params: string[]): string {
  if (params.length === 0) return `${toolName}()`;

  const formatted = params.map((p) => {
    if (p.includes("=")) {
      // Param with default/expected value: show as name="value"
      const [name, value] = p.split("=", 2);
      return `${name.replace("*", "")}="${value}"`;
    }
    // Strip * marker for display (required noted separately)
    return p.replace("*", "");
  });

  return `${toolName}(${formatted.join(", ")})`;
}

/**
 * Format notes for an action line (required params, conditions).
 */
function formatNotes(action: ActionEntry): string {
  const parts: string[] = [];

  // Note required params
  const required = action.toolParams
    .filter((p) => p.includes("*"))
    .map((p) => p.replace("*", "").split("=")[0]);

  if (required.length > 0) {
    parts.push(`${required.join(", ")} required`);
  }

  // Add description if present
  if (action.description) {
    parts.push(action.description);
  }

  // Add availability condition
  if (action.availableWhen) {
    parts.push(`when: ${action.availableWhen}`);
  }

  // Mark disabled
  if (action.available === false) {
    parts.push("currently disabled");
  }

  if (parts.length === 0) return "";
  return ` — ${parts.join(" · ")}`;
}

// ---------------------------------------------------------------------------
// Entity type derivation (for browsing hints)
// ---------------------------------------------------------------------------

function deriveEntityType(snapshot: AIContextSnapshot): string | null {
  // Try from pageConfig.id
  if (snapshot.pageConfig?.id) {
    const pageId = snapshot.pageConfig.id.replace(/-detail$/, "").replace(/-list$/, "");
    // Check if it maps to a known entity
    for (const [scope, entity] of Object.entries(SCOPE_TO_ENTITY)) {
      if (pageId === scope || pageId === entity || pageId === entity + "s") {
        return entity;
      }
    }
  }

  // Try from tool names in elements
  const scopeSet = new Set<string>();
  for (const el of Array.from(snapshot.elements.values())) {
    if (!el.actions) continue;
    for (const action of el.actions) {
      if (action.toolName) {
        const scope = toolScopeFromName(action.toolName);
        if (scope) scopeSet.add(scope);
      }
    }
  }

  // If exactly one entity scope found, use it
  if (scopeSet.size === 1) {
    const scope = Array.from(scopeSet)[0];
    return SCOPE_TO_ENTITY[scope] ?? null;
  }

  return null;
}
