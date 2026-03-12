/**
 * UI Manifest Schema — Single Source of Truth
 *
 * This schema drives BOTH:
 * 1. React rendering (ManifestRenderer) — visual UI for humans
 * 2. AI serialization (ManifestSerializer) — structured text for LLM context
 *
 * Scopes are derived automatically from API endpoints in data sources and actions.
 * No manual scope mapping needed.
 */

// =============================================================================
// Core Types
// =============================================================================

/** A complete page definition */
export interface PageManifest {
  /** Unique page identifier (e.g., "task-list", "project-dashboard") */
  id: string;

  /** Human-readable page title */
  title: string;

  /** Brief description for AI context */
  description?: string;

  /** Page layout type */
  layout: PageLayout;

  /** Top-level elements on this page */
  elements: ManifestElement[];

  /** Global data sources shared across elements */
  dataSources?: DataSource[];

  /** Page-level conditions (e.g., requires project context) */
  requires?: PageRequires;
}

/** What context the page needs to function */
export interface PageRequires {
  /** URL parameters needed (e.g., ["slug", "taskId"]) */
  params?: string[];

  /** Must be authenticated? */
  auth?: boolean;

  /** WebSocket connection needed? */
  websocket?: boolean;
}

// =============================================================================
// Layout
// =============================================================================

export type PageLayout =
  | ListPageLayout
  | DashboardLayout
  | DetailLayout
  | SettingsLayout;

interface BaseLayout {
  type: string;
  /** Named areas where elements are placed */
  areas: LayoutArea[];
}

/** List page: toolbar + scrollable list of cards */
export interface ListPageLayout extends BaseLayout {
  type: "list";
  areas: ["toolbar", "filters", "list", "sidebar?"];
}

/** Dashboard: grid of sections/cards */
export interface DashboardLayout extends BaseLayout {
  type: "dashboard";
  areas: ["header", "grid", "sidebar?"];
  columns?: { sm: number; md: number; lg: number };
}

/** Detail view: full content area */
export interface DetailLayout extends BaseLayout {
  type: "detail";
  areas: ["header", "content", "sidebar?"];
}

/** Settings: sections with form controls */
export interface SettingsLayout extends BaseLayout {
  type: "settings";
  areas: ["sections"];
}

export type LayoutArea = string;

// =============================================================================
// Elements — the building blocks
// =============================================================================

/**
 * Every UI element on the page. Elements are composable:
 * a container element holds child elements.
 */
export type ManifestElement =
  | ButtonElement
  | SelectElement
  | TextInputElement
  | CheckboxElement
  | TextDisplayElement
  | BadgeElement
  | DataTableElement
  | CardListElement
  | CardElement
  | FormDrawerElement
  | FormFieldElement
  | SectionElement
  | ProgressBarElement
  | ContainerElement
  | ToggleElement
  | TabsElement
  | AlertElement
  | AISidebarElement
  | CustomElement;

/** Common properties shared by all elements */
interface BaseElement {
  /** Unique element ID within the page */
  id: string;

  /** Element type discriminator */
  type: string;

  /** Human-readable label */
  label?: string;

  /** Description for AI context */
  description?: string;

  /** Where this element is placed */
  position?: ElementPosition;

  /** When is this element visible? */
  visibleWhen?: Condition;

  /** When is this element interactive? */
  enabledWhen?: Condition;

  /** CSS class overrides (escape hatch for styling) */
  className?: string;
}

export interface ElementPosition {
  /** Layout area this element belongs to */
  area: LayoutArea;

  /** Order within the area (lower = earlier) */
  order: number;

  /** Grouping within the area (elements with same group render together) */
  group?: string;
}

// =============================================================================
// Interactive Elements
// =============================================================================

export interface ButtonElement extends BaseElement {
  type: "button";
  variant?: "primary" | "secondary" | "danger" | "ghost";
  icon?: string;
  action: ManifestAction;
}

export interface SelectElement extends BaseElement {
  type: "select";
  options: SelectOption[] | { fromDataSource: string; labelField: string; valueField: string };
  defaultValue?: string;
  action?: ManifestAction;
}

export interface SelectOption {
  label: string;
  value: string;
}

export interface TextInputElement extends BaseElement {
  type: "text-input";
  placeholder?: string;
  /** Debounce ms for live filtering */
  debounce?: number;
  action?: ManifestAction;
}

export interface CheckboxElement extends BaseElement {
  type: "checkbox";
  defaultChecked?: boolean;
  action?: ManifestAction;
}

export interface ToggleElement extends BaseElement {
  type: "toggle";
  defaultValue?: boolean;
  action?: ManifestAction;
}

// =============================================================================
// Display Elements
// =============================================================================

export interface TextDisplayElement extends BaseElement {
  type: "text";
  /** Static text or template with {variable} refs */
  content?: string;
  /** Bind to data source field */
  bind?: string;
  variant?: "h1" | "h2" | "h3" | "body" | "caption" | "code";
  truncate?: number;
}

export interface BadgeElement extends BaseElement {
  type: "badge";
  /** Static value or bind to data field */
  value?: string;
  bind?: string;
  /** Map values to visual variants */
  variantMap?: Record<string, "success" | "warning" | "danger" | "info" | "default">;
}

export interface ProgressBarElement extends BaseElement {
  type: "progress-bar";
  /** Bind current and max to data fields */
  currentBind: string;
  maxBind: string;
  showLabel?: boolean;
  showPercentage?: boolean;
}

export interface AlertElement extends BaseElement {
  type: "alert";
  severity: "info" | "warning" | "error";
  content: string;
  visibleWhen: Condition;
}

// =============================================================================
// Composite Elements
// =============================================================================

/** A generic container that groups child elements */
export interface ContainerElement extends BaseElement {
  type: "container";
  direction?: "horizontal" | "vertical";
  gap?: number;
  children: ManifestElement[];
}

/** Named section with optional header/description */
export interface SectionElement extends BaseElement {
  type: "section";
  title: string;
  collapsible?: boolean;
  defaultCollapsed?: boolean;
  children: ManifestElement[];
}

/** Tab container with labeled panels */
export interface TabsElement extends BaseElement {
  type: "tabs";
  tabs: Array<{
    id: string;
    label: string;
    children: ManifestElement[];
  }>;
}

// =============================================================================
// Data Elements
// =============================================================================

/** Table with columns, sorting, and row actions */
export interface DataTableElement extends BaseElement {
  type: "data-table";
  dataSource: string;
  columns: TableColumn[];
  rowActions?: RowAction[];
  selectable?: boolean;
  emptyMessage?: string;
}

export interface TableColumn {
  field: string;
  label: string;
  type?: "text" | "badge" | "progress" | "date" | "link";
  /** For badge columns — map values to variants */
  variantMap?: Record<string, "success" | "warning" | "danger" | "info" | "default">;
  sortable?: boolean;
  truncate?: number;
  width?: string;
}

export interface RowAction {
  id: string;
  label: string;
  icon?: string;
  action: ManifestAction;
  variant?: "primary" | "secondary" | "danger" | "ghost";
  visibleWhen?: Condition;
  /** Confirmation dialog before executing */
  confirm?: string;
}

/** Scrollable list of entity cards */
export interface CardListElement extends BaseElement {
  type: "card-list";
  dataSource: string;
  card: CardElement;
  emptyMessage?: string;
  /** Client-side filters applied to the data source */
  filters?: CardFilter[];
}

export interface CardFilter {
  /** Element ID of the filter control (select, text-input) */
  controlId: string;
  /** Data field to filter on */
  field: string;
  /** Filter type */
  match: "equals" | "contains" | "includes";
}

/** Definition of a single card (used as template within CardList) */
export interface CardElement extends BaseElement {
  type: "card";
  /** Elements composing the card header (badges, title) */
  header: ManifestElement[];
  /** Elements composing the card body (description, metadata) */
  body: ManifestElement[];
  /** Action buttons on the card */
  actions?: ManifestElement[];
  /** Click action for the entire card */
  onClick?: ManifestAction;
}

// =============================================================================
// Form Elements
// =============================================================================

/** Modal form drawer (slides from right) */
export interface FormDrawerElement extends BaseElement {
  type: "form-drawer";
  title: string;
  /** API action to submit the form */
  submitAction: ManifestAction;
  fields: FormFieldElement[];
  /** Element ID of the button that opens this drawer */
  triggeredBy?: string;
}

export interface FormFieldElement extends BaseElement {
  type: "form-field";
  fieldType: "text" | "textarea" | "select" | "multi-select" | "entity-ref"
    | "dynamic-list" | "checkbox" | "number" | "date";
  /** The field name in the submitted data */
  name: string;
  required?: boolean;
  placeholder?: string;
  /** For select/multi-select */
  options?: SelectOption[];
  /** For entity-ref */
  entityType?: string;
  /** For textarea */
  rows?: number;
  /** Default value */
  defaultValue?: unknown;
  /** Validation rules */
  validation?: {
    minLength?: number;
    maxLength?: number;
    pattern?: string;
    message?: string;
  };
}

// =============================================================================
// Special Elements
// =============================================================================

/** AI Sidebar — self-aware element that AI can introspect */
export interface AISidebarElement extends BaseElement {
  type: "ai-sidebar";
  /** Session info is auto-populated at serialization time */
  tabs: Array<{
    id: string;
    label: string;
    /** What this tab provides to the AI */
    aiDescription: string;
  }>;
}

/** Escape hatch for custom React components */
export interface CustomElement extends BaseElement {
  type: "custom";
  /** React component name to render */
  component: string;
  /** Props to pass to the component */
  props?: Record<string, unknown>;
  /** AI description of what this component shows/does */
  aiDescription: string;
}

// =============================================================================
// Actions — what happens when user (or AI) interacts
// =============================================================================

export type ManifestAction =
  | ApiCallAction
  | FilterAction
  | NavigateAction
  | OpenFormAction
  | SetStateAction
  | CompositeAction;

/** Call an API endpoint */
export interface ApiCallAction {
  type: "api-call";
  method: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  /** Endpoint path with {param} placeholders */
  endpoint: string;
  /** Request body template — values from form data or row context */
  body?: Record<string, unknown>;
  /** What to do after success */
  onSuccess?: "refresh-data" | "close-form" | "navigate" | "toast";
  /** Toast message on success */
  successMessage?: string;
}

/** Filter a data source (client-side) */
export interface FilterAction {
  type: "filter";
  /** ID of the data source or card-list to filter */
  target: string;
  field: string;
}

/** Navigate to another page */
export interface NavigateAction {
  type: "navigate";
  /** Path with {param} placeholders */
  path: string;
}

/** Open a form drawer */
export interface OpenFormAction {
  type: "open-form";
  /** ID of the FormDrawerElement to open */
  formId: string;
  /** Pre-populate with data from context (e.g., row data for editing) */
  prefill?: "row" | "selected";
}

/** Set local UI state */
export interface SetStateAction {
  type: "set-state";
  key: string;
  value: unknown;
}

/** Execute multiple actions in sequence */
export interface CompositeAction {
  type: "composite";
  actions: ManifestAction[];
}

// =============================================================================
// Conditions — when elements are visible/enabled
// =============================================================================

export type Condition =
  | FieldCondition
  | StateCondition
  | AndCondition
  | OrCondition
  | NotCondition;

/** Compare a data field to a value */
export interface FieldCondition {
  type: "field";
  field: string;
  operator: "equals" | "not-equals" | "in" | "not-in" | "truthy" | "falsy";
  value?: unknown;
}

/** Check local UI state */
export interface StateCondition {
  type: "state";
  key: string;
  operator: "equals" | "truthy" | "falsy";
  value?: unknown;
}

export interface AndCondition {
  type: "and";
  conditions: Condition[];
}

export interface OrCondition {
  type: "or";
  conditions: Condition[];
}

export interface NotCondition {
  type: "not";
  condition: Condition;
}

// =============================================================================
// Data Sources — where the data comes from
// =============================================================================

export interface DataSource {
  /** Unique ID referenced by elements */
  id: string;

  /** API endpoint with {param} placeholders */
  endpoint: string;

  /** HTTP method (default: GET) */
  method?: "GET" | "POST";

  /** Query parameters */
  params?: Record<string, string>;

  /** Response field to extract items from */
  itemsField?: string;

  /** Response field for total count */
  countField?: string;

  /** Refresh interval in ms (0 = no auto-refresh) */
  refreshInterval?: number;

  /** WebSocket event types that trigger refresh */
  refreshOnEvents?: string[];
}

// =============================================================================
// Scope Derivation
// =============================================================================

/**
 * Scopes are NOT manually defined. They are derived from manifest at load time:
 *
 * 1. Collect all endpoints from dataSources[].endpoint and actions[].endpoint
 * 2. Extract module segment: /api/{module}/... or /projects/{slug}/{module}/...
 * 3. Deduplicate → those are the page's scopes
 *
 * Example:
 *   dataSources: [{ endpoint: "/projects/{slug}/tasks" }]
 *   actions: [{ endpoint: "/projects/{slug}/decisions/{id}" }]
 *   → scopes = ["tasks", "decisions"]
 */
export function deriveScopes(manifest: PageManifest): string[] {
  const endpoints = new Set<string>();

  // Collect from data sources
  manifest.dataSources?.forEach(ds => {
    endpoints.add(ds.endpoint);
  });

  // Collect from all elements recursively
  collectEndpoints(manifest.elements, endpoints);

  // Extract module names
  const scopes = new Set<string>();
  endpoints.forEach(ep => {
    // /projects/{slug}/{module}/...
    const projectMatch = ep.match(/\/projects\/\{[^}]+\}\/([a-z_-]+)/);
    if (projectMatch) {
      scopes.add(projectMatch[1]);
      return;
    }
    // /api/{module}/... or /{module}/...
    const directMatch = ep.match(/^\/?(?:api\/)?([a-z_-]+)/);
    if (directMatch && !["projects", "api"].includes(directMatch[1])) {
      scopes.add(directMatch[1]);
    }
  });

  return Array.from(scopes);
}

function collectEndpoints(elements: ManifestElement[], endpoints: Set<string>): void {
  for (const el of elements) {
    // Check element-level actions
    if ("action" in el && el.action && typeof el.action === "object" && "endpoint" in el.action) {
      endpoints.add((el.action as ApiCallAction).endpoint);
    }
    if ("submitAction" in el && el.submitAction && "endpoint" in el.submitAction) {
      endpoints.add((el.submitAction as ApiCallAction).endpoint);
    }
    if ("onClick" in el && el.onClick && typeof el.onClick === "object" && "endpoint" in el.onClick) {
      endpoints.add((el.onClick as ApiCallAction).endpoint);
    }

    // Recurse into children
    if ("children" in el && Array.isArray(el.children)) {
      collectEndpoints(el.children, endpoints);
    }
    if ("header" in el && Array.isArray(el.header)) {
      collectEndpoints(el.header, endpoints);
    }
    if ("body" in el && Array.isArray(el.body)) {
      collectEndpoints(el.body, endpoints);
    }
    if ("actions" in el && Array.isArray(el.actions)) {
      collectEndpoints(el.actions as ManifestElement[], endpoints);
    }
    if ("fields" in el && Array.isArray(el.fields)) {
      collectEndpoints(el.fields, endpoints);
    }
    if ("rowActions" in el && Array.isArray(el.rowActions)) {
      for (const ra of el.rowActions) {
        if (ra.action && "endpoint" in ra.action) {
          endpoints.add((ra.action as ApiCallAction).endpoint);
        }
      }
    }
    if ("tabs" in el && Array.isArray(el.tabs)) {
      for (const tab of (el as TabsElement).tabs) {
        if ("children" in tab) {
          collectEndpoints(tab.children, endpoints);
        }
      }
    }
  }
}

// =============================================================================
// Live State Snapshot (for AI serialization)
// =============================================================================

/** Captured state of the page at a point in time */
export interface PageSnapshot {
  /** Manifest page ID */
  pageId: string;

  /** Derived scopes */
  scopes: string[];

  /** URL params (slug, taskId, etc.) */
  params: Record<string, string>;

  /** Current state of each interactive element */
  elementStates: Record<string, ElementState>;

  /** Current data from data sources */
  dataStates: Record<string, DataState>;

  /** Timestamp */
  capturedAt: string;
}

export interface ElementState {
  /** Current value (for inputs, selects, checkboxes) */
  value?: unknown;
  /** Is the element currently visible? */
  visible: boolean;
  /** Is the element currently enabled? */
  enabled: boolean;
}

export interface DataState {
  /** Data rows currently loaded */
  rows: Record<string, unknown>[];
  /** Total count (may be > rows.length if paginated) */
  totalCount: number;
  /** Active filters */
  activeFilters: Record<string, unknown>;
  /** Is data currently loading? */
  loading: boolean;
}

/** AI sidebar self-awareness state */
export interface AISidebarState {
  sessionId: string | null;
  messageCount: number;
  lastMessages: Array<{
    role: "user" | "assistant";
    summary: string;
    timestamp: string;
  }>;
  toolsUsedThisSession: string[];
  activeTab: string;
}
