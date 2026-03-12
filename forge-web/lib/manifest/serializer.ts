/**
 * ManifestSerializer — converts PageManifest + live state into AI-readable text
 *
 * This is what Claude receives as page context. It describes:
 * - What page the user is on
 * - What elements exist (buttons, filters, tables, forms)
 * - What actions are available
 * - What data is currently displayed
 * - What the current filter/form state is
 */

import type {
  PageManifest,
  PageSnapshot,
  ManifestElement,
  DataState,
  ElementState,
  AISidebarState,
  ApiCallAction,
  ButtonElement,
  SelectElement,
  TextInputElement,
  CardListElement,
  DataTableElement,
  FormDrawerElement,
  SectionElement,
  TabsElement,
  BadgeElement,
  TextDisplayElement,
  ProgressBarElement,
  ContainerElement,
  AISidebarElement,
  CustomElement,
  ManifestAction,
  Condition,
} from "./types";
import { deriveScopes } from "./types";

export interface SerializeOptions {
  /** Max data rows to include per data source (default: 10) */
  maxRows?: number;
  /** Max total characters (default: 6000) */
  maxChars?: number;
  /** Include AI sidebar self-awareness (default: true) */
  includeSidebar?: boolean;
}

/**
 * Serialize a manifest + live snapshot into structured text for AI context.
 *
 * Output format:
 * ```
 * Page: task-list — "Tasks"
 * Scopes: [tasks]
 * Layout: list (areas: toolbar, filters, list)
 *
 * [toolbar]
 *   text "Tasks (12)" (h2)
 *   button "New Task" → opens task-form
 *
 * [filters]
 *   select "Status" = "TODO" → filters task-list by status
 *   select "Type" = "" → filters task-list by type
 *
 * [list] card-list "task-list" (12 items, showing 10)
 *   [1] T-001 | status:TODO | type:feature
 *       "Setup Redis caching"
 *       actions: [Start] [Edit]
 *   [2] T-002 | status:IN_PROGRESS | type:bug
 *       "Fix auth timeout"
 *       actions: [Done] [Fail]
 *   ...
 *
 * [form: task-form] (closed)
 *   fields: name*, description, instruction, type*, scopes, depends_on, acceptance_criteria
 *   submit → POST /projects/{slug}/tasks
 *
 * AI Sidebar:
 *   session: sess-abc | messages: 5 | tab: chat
 *   tools used: [listEntities, getEntity]
 * ```
 */
export function serializeManifest(
  manifest: PageManifest,
  snapshot: PageSnapshot,
  sidebarState?: AISidebarState,
  options: SerializeOptions = {},
): string {
  const { maxRows = 10, maxChars = 6000, includeSidebar = true } = options;
  const lines: string[] = [];

  // Header
  const scopes = deriveScopes(manifest);
  lines.push(`Page: ${manifest.id} — "${manifest.title}"`);
  if (manifest.description) {
    lines.push(`  ${manifest.description}`);
  }
  lines.push(`Scopes: [${scopes.join(", ")}]`);
  lines.push(`Layout: ${manifest.layout.type} (areas: ${manifest.layout.areas.join(", ")})`);
  if (snapshot.params && Object.keys(snapshot.params).length > 0) {
    lines.push(`Params: ${JSON.stringify(snapshot.params)}`);
  }
  lines.push("");

  // Group elements by area
  const byArea = groupByArea(manifest.elements);

  for (const [area, elements] of Object.entries(byArea)) {
    lines.push(`[${area}]`);
    for (const el of elements) {
      const elLines = serializeElement(el, snapshot, manifest, maxRows, 1);
      lines.push(...elLines);
    }
    lines.push("");
  }

  // Forms (not area-bound, always shown)
  const forms = findElements(manifest.elements, "form-drawer") as FormDrawerElement[];
  for (const form of forms) {
    const formState = snapshot.elementStates[form.id];
    const isOpen = formState?.value === true;
    lines.push(`[form: ${form.id}] (${isOpen ? "open" : "closed"})`);
    const fieldDescs = form.fields.map(f => {
      const req = f.required ? "*" : "";
      const val = snapshot.elementStates[f.id]?.value;
      const valStr = val !== undefined && val !== "" ? ` = ${JSON.stringify(val)}` : "";
      return `${f.name}${req}${valStr}`;
    });
    lines.push(`  fields: ${fieldDescs.join(", ")}`);
    lines.push(`  submit → ${describeAction(form.submitAction)}`);
    lines.push("");
  }

  // AI Sidebar
  if (includeSidebar && sidebarState) {
    lines.push("AI Sidebar:");
    lines.push(`  session: ${sidebarState.sessionId ?? "none"} | messages: ${sidebarState.messageCount} | tab: ${sidebarState.activeTab}`);
    if (sidebarState.toolsUsedThisSession.length > 0) {
      lines.push(`  tools used: [${sidebarState.toolsUsedThisSession.join(", ")}]`);
    }
    if (sidebarState.lastMessages.length > 0) {
      lines.push("  recent:");
      for (const msg of sidebarState.lastMessages.slice(-3)) {
        lines.push(`    ${msg.role}: ${msg.summary}`);
      }
    }
    lines.push("");
  }

  let result = lines.join("\n");

  // Truncate if needed
  if (result.length > maxChars) {
    result = result.slice(0, maxChars - 50) + "\n\n... (truncated, use tools to fetch full data)";
  }

  return result;
}

// ---------------------------------------------------------------------------
// Element serialization
// ---------------------------------------------------------------------------

function serializeElement(
  el: ManifestElement,
  snapshot: PageSnapshot,
  manifest: PageManifest,
  maxRows: number,
  indent: number,
): string[] {
  const pad = "  ".repeat(indent);
  const lines: string[] = [];

  // Check visibility
  const elState = snapshot.elementStates[el.id];
  if (elState && !elState.visible) return lines;

  switch (el.type) {
    case "button": {
      const btn = el as ButtonElement;
      lines.push(`${pad}button "${btn.label}" → ${describeAction(btn.action)}`);
      break;
    }

    case "select": {
      const sel = el as SelectElement;
      const val = elState?.value ?? sel.defaultValue ?? "";
      const actionDesc = sel.action ? ` → ${describeAction(sel.action)}` : "";
      lines.push(`${pad}select "${sel.label}" = "${val}"${actionDesc}`);
      break;
    }

    case "text-input": {
      const inp = el as TextInputElement;
      const val = elState?.value ?? "";
      const actionDesc = inp.action ? ` → ${describeAction(inp.action)}` : "";
      lines.push(`${pad}input "${inp.label}" = "${val}"${actionDesc}`);
      break;
    }

    case "text": {
      const txt = el as TextDisplayElement;
      const content = resolveTextContent(txt, snapshot);
      lines.push(`${pad}${txt.variant ?? "text"} "${content}"`);
      break;
    }

    case "badge": {
      const badge = el as BadgeElement;
      const val = badge.value ?? elState?.value ?? "";
      lines.push(`${pad}[${val}]`);
      break;
    }

    case "progress-bar": {
      const bar = el as ProgressBarElement;
      lines.push(`${pad}progress ${bar.label ?? ""} ${bar.currentBind}/${bar.maxBind}`);
      break;
    }

    case "card-list": {
      const cl = el as CardListElement;
      const data = snapshot.dataStates[cl.dataSource];
      if (!data) {
        lines.push(`${pad}card-list "${cl.id}" (loading...)`);
        break;
      }

      const showing = Math.min(data.rows.length, maxRows);
      lines.push(`${pad}card-list "${cl.id}" (${data.totalCount} items, showing ${showing})`);

      // Show active filters
      if (Object.keys(data.activeFilters).length > 0) {
        const filters = Object.entries(data.activeFilters)
          .filter(([, v]) => v !== "" && v !== null)
          .map(([k, v]) => `${k}=${v}`)
          .join(", ");
        if (filters) {
          lines.push(`${pad}  active filters: ${filters}`);
        }
      }

      // Show rows
      for (let i = 0; i < showing; i++) {
        const row = data.rows[i];
        lines.push(...serializeCardRow(cl, row, i + 1, indent + 1));
      }

      if (data.totalCount > showing) {
        lines.push(`${pad}  ... ${data.totalCount - showing} more`);
      }
      break;
    }

    case "data-table": {
      const dt = el as DataTableElement;
      const data = snapshot.dataStates[dt.dataSource];
      if (!data) {
        lines.push(`${pad}table "${dt.id}" (loading...)`);
        break;
      }
      lines.push(`${pad}table "${dt.id}" (${data.totalCount} rows)`);
      // Column headers
      lines.push(`${pad}  | ${dt.columns.map(c => c.label).join(" | ")} |`);
      // Data rows
      const showing = Math.min(data.rows.length, maxRows);
      for (let i = 0; i < showing; i++) {
        const row = data.rows[i];
        const vals = dt.columns.map(c => String(row[c.field] ?? ""));
        lines.push(`${pad}  | ${vals.join(" | ")} |`);
      }
      break;
    }

    case "section": {
      const sec = el as SectionElement;
      lines.push(`${pad}--- ${sec.title} ---`);
      for (const child of sec.children) {
        lines.push(...serializeElement(child, snapshot, manifest, maxRows, indent + 1));
      }
      break;
    }

    case "container": {
      const cont = el as ContainerElement;
      for (const child of cont.children) {
        lines.push(...serializeElement(child, snapshot, manifest, maxRows, indent));
      }
      break;
    }

    case "tabs": {
      const tabs = el as TabsElement;
      const activeTab = elState?.value ?? tabs.tabs[0]?.id;
      lines.push(`${pad}tabs: ${tabs.tabs.map(t => t.id === activeTab ? `[${t.label}]` : t.label).join(" | ")}`);
      const active = tabs.tabs.find(t => t.id === activeTab);
      if (active) {
        for (const child of active.children) {
          lines.push(...serializeElement(child, snapshot, manifest, maxRows, indent + 1));
        }
      }
      break;
    }

    case "ai-sidebar": {
      // Handled separately in main serializer
      break;
    }

    case "custom": {
      const cust = el as CustomElement;
      lines.push(`${pad}[${cust.component}] ${cust.aiDescription}`);
      break;
    }

    default:
      lines.push(`${pad}${el.type} "${el.label ?? el.id}"`);
  }

  return lines;
}

// ---------------------------------------------------------------------------
// Card row serialization
// ---------------------------------------------------------------------------

function serializeCardRow(
  cardList: CardListElement,
  row: Record<string, unknown>,
  index: number,
  indent: number,
): string[] {
  const pad = "  ".repeat(indent);
  const lines: string[] = [];
  const card = cardList.card;

  // Header line: badges
  const badges = card.header
    .filter(h => h.type === "badge")
    .map(h => {
      const badge = h as BadgeElement;
      const field = badge.bind;
      return field ? String(row[field] ?? "") : badge.value ?? "";
    })
    .filter(Boolean);

  lines.push(`${pad}[${index}] ${badges.join(" | ")}`);

  // Body: title and description
  for (const bodyEl of card.body) {
    if (bodyEl.type === "text") {
      const txt = bodyEl as TextDisplayElement;
      if (txt.bind && row[txt.bind] !== undefined) {
        const val = row[txt.bind];
        if (Array.isArray(val)) {
          if (val.length > 0) {
            lines.push(`${pad}    ${txt.description ?? txt.bind}: ${val.join(", ")}`);
          }
        } else if (txt.variant === "h3") {
          lines.push(`${pad}    "${val}"`);
        } else if (val) {
          const str = String(val);
          const truncated = str.length > 80 ? str.slice(0, 77) + "..." : str;
          lines.push(`${pad}    ${truncated}`);
        }
      }
    }
  }

  // Actions: show which are available for this row
  if (card.actions) {
    const available = card.actions.filter(a => {
      if (!("visibleWhen" in a) || !a.visibleWhen) return true;
      return evaluateCondition(a.visibleWhen, row);
    });
    if (available.length > 0) {
      const actionNames = available.map(a => `[${(a as ButtonElement).label}]`);
      lines.push(`${pad}    actions: ${actionNames.join(" ")}`);
    }
  }

  return lines;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function describeAction(action: ManifestAction): string {
  switch (action.type) {
    case "api-call":
      return `${action.method} ${action.endpoint}`;
    case "filter":
      return `filters ${action.target} by ${action.field}`;
    case "navigate":
      return `navigate to ${action.path}`;
    case "open-form":
      return `opens ${action.formId}`;
    case "set-state":
      return `set ${action.key}`;
    case "composite":
      return action.actions.map(describeAction).join(" → ");
  }
}

function resolveTextContent(
  el: TextDisplayElement,
  snapshot: PageSnapshot,
): string {
  if (el.bind) {
    // Could be a data source field reference
    return `{${el.bind}}`;
  }
  if (el.content) {
    // Replace {dataSource.field} references with actual values
    return el.content.replace(/\{(\w+)\.(\w+)\}/g, (_, dsId, field) => {
      const data = snapshot.dataStates[dsId];
      if (!data) return `{${dsId}.${field}}`;
      if (field === "count") return String(data.totalCount);
      return `{${dsId}.${field}}`;
    });
  }
  return el.label ?? el.id;
}

function evaluateCondition(
  condition: Condition,
  context: Record<string, unknown>,
): boolean {
  switch (condition.type) {
    case "field": {
      const val = context[condition.field];
      switch (condition.operator) {
        case "equals":
          return val === condition.value;
        case "not-equals":
          return val !== condition.value;
        case "in":
          return Array.isArray(condition.value) && condition.value.includes(val);
        case "not-in":
          return Array.isArray(condition.value) && !condition.value.includes(val);
        case "truthy":
          return Array.isArray(val) ? val.length > 0 : Boolean(val);
        case "falsy":
          return Array.isArray(val) ? val.length === 0 : !val;
      }
      return false;
    }
    case "state":
      return false; // Needs UI state context
    case "and":
      return condition.conditions.every(c => evaluateCondition(c, context));
    case "or":
      return condition.conditions.some(c => evaluateCondition(c, context));
    case "not":
      return !evaluateCondition(condition.condition, context);
  }
}

function groupByArea(
  elements: ManifestElement[],
): Record<string, ManifestElement[]> {
  const result: Record<string, ManifestElement[]> = {};

  for (const el of elements) {
    // Skip form drawers (serialized separately)
    if (el.type === "form-drawer") continue;

    const area = ("position" in el && el.position?.area) || "content";
    if (!result[area]) result[area] = [];
    result[area].push(el);
  }

  // Sort by order within each area
  for (const area of Object.keys(result)) {
    result[area].sort((a, b) => {
      const orderA = ("position" in a && a.position?.order) || 0;
      const orderB = ("position" in b && b.position?.order) || 0;
      return orderA - orderB;
    });
  }

  return result;
}

function findElements(
  elements: ManifestElement[],
  type: string,
): ManifestElement[] {
  const result: ManifestElement[] = [];
  for (const el of elements) {
    if (el.type === type) result.push(el);
    if ("children" in el && Array.isArray((el as ContainerElement).children)) {
      result.push(...findElements((el as ContainerElement).children, type));
    }
  }
  return result;
}
