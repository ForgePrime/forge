import type { AIContextSnapshot, AIElementDescriptor } from "./types";

export interface SerializeOptions {
  /** Max total characters (default: 4000) */
  maxChars?: number;
  /** Max list/data items to show (default: 15) */
  maxItems?: number;
}

/**
 * Serialize collected AI annotations into structured text for LLM context.
 *
 * Output example:
 * ```
 * Page: Tasks — Task list for project
 *
 * Elements:
 *   [filter] Status Filter = "TODO"
 *   [list] Tasks (42 items) — status: 10 TODO, 20 DONE, 12 IN_PROGRESS
 *     actions: Start (PATCH /projects/{slug}/tasks/{id}), Create (POST /projects/{slug}/tasks)
 *   [form] Task Form (closed)
 *     fields: name*, description, type*, scopes
 *     submit: POST /projects/{slug}/tasks
 * ```
 */
export function serializePageContext(
  snapshot: AIContextSnapshot,
  options: SerializeOptions = {},
): string {
  const { maxChars = 4000, maxItems = 15 } = options;
  const lines: string[] = [];

  // Page header
  if (snapshot.pageConfig) {
    const { title, description } = snapshot.pageConfig;
    lines.push(`Page: ${title}${description ? ` — ${description}` : ""}`);
    lines.push("");
  }

  // Elements
  if (snapshot.elements.size > 0) {
    lines.push("Elements:");
    for (const el of snapshot.elements.values()) {
      lines.push(...serializeElement(el, maxItems));
    }
  }

  let result = lines.join("\n");

  if (result.length > maxChars) {
    const suffix = "\n... (truncated, use tools for full data)";
    result = result.slice(0, maxChars - suffix.length) + suffix;
  }

  return result;
}

function serializeElement(
  el: AIElementDescriptor,
  maxItems: number,
): string[] {
  const lines: string[] = [];
  const indent = "  ";

  // Main line: [type] label = value
  let main = `${indent}[${el.type}] ${el.label ?? el.id}`;
  if (el.value !== undefined && el.value !== null && el.value !== "") {
    main += ` = ${JSON.stringify(el.value)}`;
  }
  if (el.description) {
    main += ` — ${el.description}`;
  }
  lines.push(main);

  // Data summary
  if (el.data && Object.keys(el.data).length > 0) {
    const dataParts: string[] = [];
    for (const [key, val] of Object.entries(el.data)) {
      if (typeof val === "object" && val !== null && !Array.isArray(val)) {
        // Object: show key:value pairs (e.g., status distribution)
        const entries = Object.entries(val as Record<string, unknown>)
          .filter(([, v]) => v !== 0 && v !== undefined)
          .map(([k, v]) => `${k}: ${v}`);
        if (entries.length > 0) {
          dataParts.push(`${key}: ${entries.join(", ")}`);
        }
      } else if (Array.isArray(val)) {
        const shown = val.slice(0, maxItems);
        const rest = val.length - shown.length;
        dataParts.push(
          `${key}: [${shown.join(", ")}${rest > 0 ? `, ... +${rest} more` : ""}]`,
        );
      } else {
        dataParts.push(`${key}: ${val}`);
      }
    }
    if (dataParts.length > 0) {
      lines.push(`${indent}  ${dataParts.join(" | ")}`);
    }
  }

  // Actions
  if (el.actions && el.actions.length > 0) {
    const actionDescs = el.actions
      .map((a) => {
        let desc = a.label;
        if (a.method && a.endpoint) {
          desc += ` (${a.method} ${a.endpoint})`;
        }
        if (a.available === false) {
          desc += " [disabled]";
        }
        if (a.availableWhen) {
          desc += ` [when: ${a.availableWhen}]`;
        }
        return desc;
      })
      .join(", ");
    lines.push(`${indent}  actions: ${actionDescs}`);
  }

  return lines;
}
