/**
 * Typed API client for Forge Platform v2.
 *
 * Base URL from NEXT_PUBLIC_API_URL env var (default: http://localhost:8000/api/v1).
 * Supports JWT and API key authentication.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

/** Stored JWT token (client-side only). */
let _token: string | null = null;

export function setToken(token: string | null) {
  _token = token;
}

export function getToken(): string | null {
  return _token;
}

/** API error with status code and structured detail. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
  ) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.name = "ApiError";
  }
}

/** Build headers with auth token. Only sets Content-Type for requests with body. */
function buildHeaders(hasBody: boolean, extra?: Record<string, string>): Record<string, string> {
  const h: Record<string, string> = { ...extra };
  if (hasBody) {
    h["Content-Type"] = "application/json";
  }
  if (_token) {
    h["Authorization"] = `Bearer ${_token}`;
  }
  return h;
}

/** Debug store — imported lazily. Set by app initialization. */
type AddEntryFn = (entry: {
  method: string; url: string; status: number | null;
  duration: number; timestamp: number;
  requestBody?: unknown; responseBody?: unknown; error?: string;
}) => void;

let _addEntry: AddEntryFn | null = null;

/** Called once by app code to wire up debug store (avoids circular import). */
export function setDebugInterceptor(fn: AddEntryFn): void {
  _addEntry = fn;
}

const MAX_BODY_SIZE = 8_000;
/** Truncate large JSON bodies to prevent memory bloat in debug store. */
function truncateBody(body: unknown): unknown {
  if (body === undefined) return undefined;
  const str = JSON.stringify(body);
  if (str.length <= MAX_BODY_SIZE) return body;
  return `[truncated: ${str.length} chars] ${str.slice(0, MAX_BODY_SIZE)}...`;
}

/** Generic fetch wrapper with error handling and debug capture. */
async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const method = init?.method ?? "GET";
  const hasBody = init?.body != null;
  const initHeaders = init?.headers as Record<string, string> | undefined;
  const startTime = Date.now();
  let requestBody: unknown;

  if (hasBody && typeof init?.body === "string") {
    try { requestBody = JSON.parse(init.body); } catch { requestBody = init.body; }
  }

  try {
    const res = await fetch(url, {
      ...init,
      headers: buildHeaders(hasBody, initHeaders),
    });

    const duration = Date.now() - startTime;

    if (!res.ok) {
      const body = await res.json().catch(() => res.statusText);
      _addEntry?.({
        method, url: path, status: res.status, duration,
        timestamp: startTime, requestBody: truncateBody(requestBody), responseBody: truncateBody(body),
        error: typeof body === "string" ? body : JSON.stringify(body),
      });
      throw new ApiError(res.status, body);
    }

    if (res.status === 204) {
      _addEntry?.({
        method, url: path, status: 204, duration,
        timestamp: startTime, requestBody: truncateBody(requestBody),
      });
      return undefined as T;
    }

    const responseBody = await res.json();
    _addEntry?.({
      method, url: path, status: res.status, duration,
      timestamp: startTime, requestBody: truncateBody(requestBody), responseBody: truncateBody(responseBody),
    });
    return responseBody;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    const duration = Date.now() - startTime;
    _addEntry?.({
      method, url: path, status: null, duration,
      timestamp: startTime, requestBody,
      error: (e as Error).message,
    });
    throw e;
  }
}

// ---------------------------------------------------------------------------
// Generic CRUD
// ---------------------------------------------------------------------------

export async function list<T>(path: string, params?: Record<string, string>): Promise<T> {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return request<T>(`${path}${qs}`);
}

export async function get<T>(path: string): Promise<T> {
  return request<T>(path);
}

export async function create<T>(path: string, data: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function update<T>(path: string, data: unknown): Promise<T> {
  return request<T>(path, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function remove<T>(path: string): Promise<T> {
  return request<T>(path, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export async function login(username: string, password: string): Promise<TokenResponse> {
  const res = await request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setToken(res.access_token);
  return res;
}

export async function refreshToken(): Promise<TokenResponse> {
  const res = await request<TokenResponse>("/auth/refresh", { method: "POST" });
  setToken(res.access_token);
  return res;
}

export function logout(): void {
  setToken(null);
}

export async function me(): Promise<{ sub: string; auth_method: string; role: string }> {
  return request("/auth/me");
}

// ---------------------------------------------------------------------------
// Entity helpers
// ---------------------------------------------------------------------------

export function projectPath(slug: string, entity?: string, id?: string): string {
  let p = `/projects/${slug}`;
  if (entity) p += `/${entity}`;
  if (id) p += `/${id}`;
  return p;
}

export async function health(): Promise<{ status: string; version: string }> {
  return request("/health");
}

// ---------------------------------------------------------------------------
// Entity-specific API (typed wrappers)
// ---------------------------------------------------------------------------

import type {
  ProjectDetail, ProjectCreate, ProjectStatus,
  Task, TaskCreate, TaskUpdate, TaskContext,
  Decision, DecisionCreate, DecisionUpdate,
  Objective, ObjectiveCreate, ObjectiveUpdate,
  Idea, IdeaCreate, IdeaUpdate,
  ChangeRecord, ChangeCreate,
  Guideline, GuidelineCreate, GuidelineUpdate,
  Knowledge, KnowledgeCreate, KnowledgeUpdate, KnowledgeLink,
  Lesson, LessonCreate, LessonPromote,
  ACTemplate, ACTemplateCreate, ACTemplateUpdate,
  Gate, GateCreate,
  MaintenanceReport, StaleReport,
  ExecutionState,
  AISuggestionEntityType,
  SuggestKnowledgeResponse,
  SuggestGuidelinesResponse,
  SuggestACResponse,
  EvaluateLessonResponse,
  AssessImpactResponse,
  DebugStatus, DebugSessionSummary, DebugSession,
} from "./types";

// -- Projects --
export const projects = {
  list: () => list<{ projects: string[] }>("/projects"),
  create: (data: ProjectCreate) => create<{ project: string; goal: string }>("/projects", data),
  get: (slug: string) => get<ProjectDetail>(`/projects/${slug}`),
  update: (slug: string, data: { goal?: string; config?: Record<string, unknown> }) =>
    update<ProjectDetail>(`/projects/${slug}`, data),
  status: (slug: string) => get<ProjectStatus>(`/projects/${slug}/status`),
};

// -- Tasks --
export const tasks = {
  list: (slug: string, params?: Record<string, string>) =>
    list<{ tasks: Task[]; count: number }>(projectPath(slug, "tasks"), params),
  create: (slug: string, data: TaskCreate[]) =>
    create<{ added: string[]; total: number }>(projectPath(slug, "tasks"), data),
  get: (slug: string, id: string) =>
    get<Task>(projectPath(slug, "tasks", id)),
  update: (slug: string, id: string, data: TaskUpdate) =>
    update<Task>(projectPath(slug, "tasks", id), data),
  remove: (slug: string, id: string) =>
    remove<{ removed: string }>(projectPath(slug, "tasks", id)),
  claimNext: (slug: string, agent?: string) => {
    const qs = agent ? `?agent=${encodeURIComponent(agent)}` : "";
    return create<Task>(projectPath(slug, "tasks") + "/next" + qs, {});
  },
  complete: (slug: string, id: string, reasoning?: string) =>
    create<Task>(projectPath(slug, "tasks", id) + "/complete",
      { reasoning: reasoning ?? "" }),
  context: (slug: string, id: string) =>
    get<TaskContext>(projectPath(slug, "tasks", id) + "/context"),
};

// -- Decisions --
export const decisions = {
  list: (slug: string, params?: Record<string, string>) =>
    list<{ decisions: Decision[]; count: number }>(projectPath(slug, "decisions"), params),
  create: (slug: string, data: DecisionCreate[]) =>
    create<{ added: string[]; total: number }>(projectPath(slug, "decisions"), data),
  get: (slug: string, id: string) =>
    get<Decision>(projectPath(slug, "decisions", id)),
  update: (slug: string, id: string, data: DecisionUpdate) =>
    update<Decision>(projectPath(slug, "decisions", id), data),
};

// -- Objectives --
export const objectives = {
  list: (slug: string) =>
    list<{ objectives: Objective[]; count: number }>(projectPath(slug, "objectives")),
  create: (slug: string, data: ObjectiveCreate[]) =>
    create<{ added: string[]; total: number }>(projectPath(slug, "objectives"), data),
  get: (slug: string, id: string) =>
    get<Objective>(projectPath(slug, "objectives", id)),
  update: (slug: string, id: string, data: ObjectiveUpdate) =>
    update<Objective>(projectPath(slug, "objectives", id), data),
  status: (slug: string) =>
    get<{ objectives: Objective[]; count: number }>(projectPath(slug, "objectives") + "/status"),
};

// -- Ideas --
export const ideas = {
  list: (slug: string, params?: Record<string, string>) =>
    list<{ ideas: Idea[]; count: number }>(projectPath(slug, "ideas"), params),
  create: (slug: string, data: IdeaCreate[]) =>
    create<{ added: string[]; total: number }>(projectPath(slug, "ideas"), data),
  get: (slug: string, id: string) =>
    get<Idea & { children: Idea[]; related_decisions: Decision[] }>(projectPath(slug, "ideas", id)),
  update: (slug: string, id: string, data: IdeaUpdate) =>
    update<Idea>(projectPath(slug, "ideas", id), data),
  commit: (slug: string, id: string) =>
    create<Idea>(projectPath(slug, "ideas", id) + "/commit", {}),
};

// -- Changes --
export const changes = {
  list: (slug: string, params?: Record<string, string>) =>
    list<{ changes: ChangeRecord[]; count: number }>(projectPath(slug, "changes"), params),
  create: (slug: string, data: ChangeCreate[]) =>
    create<{ added: string[]; total: number }>(projectPath(slug, "changes"), data),
  get: (slug: string, id: string) =>
    get<ChangeRecord>(projectPath(slug, "changes", id)),
  autoDetect: (slug: string, taskId?: string) =>
    create<{ message: string; task_id: string; changes: Array<Record<string, unknown>> }>(
      projectPath(slug, "changes") + "/auto" + (taskId ? `?task_id=${taskId}` : ""), {}),
};

// -- Guidelines --
export const guidelines = {
  list: (slug: string, params?: Record<string, string>) =>
    list<{ guidelines: Guideline[]; count: number }>(projectPath(slug, "guidelines"), params),
  create: (slug: string, data: GuidelineCreate[]) =>
    create<{ added: string[]; total: number }>(projectPath(slug, "guidelines"), data),
  get: (slug: string, id: string) =>
    get<Guideline>(projectPath(slug, "guidelines", id)),
  update: (slug: string, id: string, data: GuidelineUpdate) =>
    update<Guideline>(projectPath(slug, "guidelines", id), data),
  context: (slug: string, scopes?: string) =>
    get<{ must: Guideline[]; should: Guideline[]; may: Guideline[]; total: number }>(
      projectPath(slug, "guidelines") + "/context" + (scopes ? `?scopes=${scopes}` : ""),
    ),
};

// -- Knowledge --
export const knowledge = {
  list: (slug: string, params?: Record<string, string>) =>
    list<{ knowledge: Knowledge[]; count: number }>(projectPath(slug, "knowledge"), params),
  create: (slug: string, data: KnowledgeCreate[]) =>
    create<{ added: string[]; total: number }>(projectPath(slug, "knowledge"), data),
  get: (slug: string, id: string) =>
    get<Knowledge>(projectPath(slug, "knowledge", id)),
  update: (slug: string, id: string, data: KnowledgeUpdate) =>
    update<Knowledge>(projectPath(slug, "knowledge", id), data),
  versions: (slug: string, id: string) =>
    get<{ versions: Array<Record<string, unknown>>; count: number }>(
      projectPath(slug, "knowledge", id) + "/versions"),
  getVersion: (slug: string, id: string, version: number) =>
    get<Record<string, unknown>>(
      projectPath(slug, "knowledge", id) + `/versions/${version}`),
  impact: (slug: string, id: string) =>
    get<{ knowledge_id: string; title: string; total_affected: number; affected_entities: Array<Record<string, unknown>> }>(
      projectPath(slug, "knowledge", id) + "/impact"),
  link: (slug: string, id: string, data: KnowledgeLink) =>
    create<Record<string, unknown>>(projectPath(slug, "knowledge", id) + "/link", data),
  unlink: (slug: string, id: string, linkId: number) =>
    remove<{ removed: number }>(projectPath(slug, "knowledge", id) + `/link/${linkId}`),
};

// -- Knowledge Maintenance --
export const knowledgeMaintenance = {
  overview: (slug: string, staleDays?: number) => {
    const params: Record<string, string> = {};
    if (staleDays !== undefined) params.stale_days = String(staleDays);
    return list<MaintenanceReport>(
      projectPath(slug, "knowledge") + "/maintenance", params);
  },
  stale: (slug: string, staleDays?: number) => {
    const params: Record<string, string> = {};
    if (staleDays !== undefined) params.stale_days = String(staleDays);
    return list<StaleReport>(
      projectPath(slug, "knowledge") + "/maintenance/stale", params);
  },
};

// -- Lessons --
export const lessons = {
  list: (slug: string) =>
    list<{ lessons: Lesson[]; count: number }>(projectPath(slug, "lessons")),
  create: (slug: string, data: LessonCreate[]) =>
    create<{ added: string[]; total: number }>(projectPath(slug, "lessons"), data),
  get: (slug: string, id: string) =>
    get<Lesson>(projectPath(slug, "lessons", id)),
  promote: (slug: string, id: string, data: LessonPromote) =>
    create<{ promoted_to: string; guideline_id?: string; knowledge_id?: string }>(
      projectPath(slug, "lessons", id) + "/promote", data),
};

// -- AC Templates --
export const acTemplates = {
  list: (slug: string, params?: Record<string, string>) =>
    list<{ templates: ACTemplate[]; count: number }>(projectPath(slug, "ac-templates"), params),
  create: (slug: string, data: ACTemplateCreate[]) =>
    create<{ added: string[]; total: number }>(projectPath(slug, "ac-templates"), data),
  get: (slug: string, id: string) =>
    get<ACTemplate>(projectPath(slug, "ac-templates", id)),
  update: (slug: string, id: string, data: ACTemplateUpdate) =>
    update<ACTemplate>(projectPath(slug, "ac-templates", id), data),
  instantiate: (slug: string, id: string, params?: Record<string, string | number | boolean>) =>
    create<{ template_id: string; criterion: string }>(
      projectPath(slug, "ac-templates", id) + "/instantiate", { params: params ?? {} }),
};

// -- Gates --
export const gates = {
  list: (slug: string) =>
    list<{ gates: Gate[]; count: number }>(projectPath(slug, "gates")),
  create: (slug: string, data: GateCreate[]) =>
    create<{ configured: number }>(projectPath(slug, "gates"), data),
  check: (slug: string, taskId?: string) =>
    create<{ message: string; task: string; gates: Array<Record<string, unknown>> }>(
      projectPath(slug, "gates") + "/check" + (taskId ? `?task=${taskId}` : ""), {}),
};

// -- Execution --
export const execution = {
  start: (slug: string, taskId: string, mode?: string) =>
    create<ExecutionState>(
      `/projects/${slug}/execute/${taskId}`,
      mode ? { mode } : {},
    ),
  status: (slug: string, taskId: string) =>
    get<ExecutionState>(`/projects/${slug}/execute/${taskId}/status`),
  cancel: (slug: string, taskId: string) =>
    create<ExecutionState>(`/projects/${slug}/execute/${taskId}/cancel`, {}),
};

// -- AI Suggestions --
export const ai = {
  suggestKnowledge: (slug: string, entityType: AISuggestionEntityType, entityId: string) =>
    create<SuggestKnowledgeResponse>(
      `/projects/${slug}/ai/suggest-knowledge`,
      { entity_type: entityType, entity_id: entityId },
    ),
  suggestGuidelines: (slug: string, entityType: AISuggestionEntityType, entityId: string) =>
    create<SuggestGuidelinesResponse>(
      `/projects/${slug}/ai/suggest-guidelines`,
      { entity_type: entityType, entity_id: entityId },
    ),
  suggestAC: (slug: string, taskId: string) =>
    create<SuggestACResponse>(
      `/projects/${slug}/ai/suggest-ac`,
      { task_id: taskId },
    ),
  evaluateLesson: (slug: string, lessonId: string) =>
    create<EvaluateLessonResponse>(
      `/projects/${slug}/ai/evaluate-lesson`,
      { lesson_id: lessonId },
    ),
  assessImpact: (slug: string, knowledgeId: string) =>
    create<AssessImpactResponse>(
      `/projects/${slug}/ai/assess-impact`,
      { knowledge_id: knowledgeId },
    ),
};

// -- Debug Monitor --
export const debug = {
  enable: (slug: string) =>
    create<{ enabled: boolean; project: string }>(
      `/projects/${slug}/debug/enable`, {},
    ),
  disable: (slug: string) =>
    create<{ enabled: boolean; project: string }>(
      `/projects/${slug}/debug/disable`, {},
    ),
  status: (slug: string) =>
    get<DebugStatus>(`/projects/${slug}/debug/status`),
  sessions: (slug: string, params?: {
    task_id?: string;
    contract_id?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.task_id) searchParams.set("task_id", params.task_id);
    if (params?.contract_id) searchParams.set("contract_id", params.contract_id);
    if (params?.status) searchParams.set("status", params.status);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));
    const qs = searchParams.toString();
    return get<{ sessions: DebugSessionSummary[]; total: number }>(
      `/projects/${slug}/debug/sessions${qs ? `?${qs}` : ""}`,
    );
  },
  session: (slug: string, sessionId: string) =>
    get<DebugSession>(`/projects/${slug}/debug/sessions/${sessionId}`),
  clear: (slug: string) =>
    remove<{ cleared: number }>(`/projects/${slug}/debug/sessions`),
};
