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

/** API error with status code, endpoint info, and structured detail. */
export class ApiError extends Error {
  /** HTTP method (GET, POST, etc.) — empty when not available. */
  public method: string;
  /** Request URL path — empty when not available. */
  public url: string;
  /** First 500 chars of the response body for diagnostics. */
  public responseExcerpt: string;

  constructor(
    public status: number,
    public detail: unknown,
    opts?: { method?: string; url?: string },
  ) {
    const msg = typeof detail === "string" ? detail : JSON.stringify(detail);
    super(msg || `API error ${status}`);
    this.name = "ApiError";
    this.method = opts?.method ?? "";
    this.url = opts?.url ?? "";
    const raw = typeof detail === "string" ? detail : (JSON.stringify(detail) ?? "");
    this.responseExcerpt = raw.slice(0, 500);
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
  requestBody?: unknown; responseBody?: unknown;
  requestHeaders?: Record<string, string>; error?: string;
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

  const requestHeaders = buildHeaders(hasBody, initHeaders);

  try {
    const res = await fetch(url, {
      ...init,
      headers: requestHeaders,
    });

    const duration = Date.now() - startTime;

    if (!res.ok) {
      const body = await res.json().catch(() => res.statusText);
      _addEntry?.({
        method, url: path, status: res.status, duration,
        timestamp: startTime, requestBody: truncateBody(requestBody), responseBody: truncateBody(body),
        requestHeaders, error: typeof body === "string" ? body : JSON.stringify(body),
      });
      throw new ApiError(res.status, body, { method, url: path });
    }

    if (res.status === 204) {
      _addEntry?.({
        method, url: path, status: 204, duration,
        timestamp: startTime, requestBody: truncateBody(requestBody),
        requestHeaders,
      });
      return undefined as T;
    }

    const responseBody = await res.json();
    _addEntry?.({
      method, url: path, status: res.status, duration,
      timestamp: startTime, requestBody: truncateBody(requestBody), responseBody: truncateBody(responseBody),
      requestHeaders,
    });
    return responseBody;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    const duration = Date.now() - startTime;
    _addEntry?.({
      method, url: path, status: null, duration,
      timestamp: startTime, requestBody, requestHeaders,
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

export async function put<T>(path: string, data: unknown): Promise<T> {
  return request<T>(path, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function remove<T>(path: string): Promise<T> {
  return request<T>(path, { method: "DELETE" });
}

/** Fetch a file/blob from the API (for export downloads). */
export async function fetchBlob(path: string): Promise<Blob> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: buildHeaders(false),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => res.statusText);
    throw new ApiError(res.status, body);
  }
  return res.blob();
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
  Task, TaskCreate, TaskUpdate, TaskContext, DraftTaskItem, DraftPlan, DraftPlanResponse, ApprovePlanResponse,
  Decision, DecisionCreate, DecisionUpdate,
  Objective, ObjectiveCreate, ObjectiveUpdate,
  Idea, IdeaCreate, IdeaUpdate,
  ChangeRecord, ChangeCreate,
  Guideline, GuidelineCreate, GuidelineUpdate,
  Knowledge, KnowledgeCreate, KnowledgeUpdate, KnowledgeLink,
  Research, ResearchCreate, ResearchUpdate,
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
  Skill, SkillCreate, SkillUpdate, ValidationResult, LintResult, PromoteResult,
  SkillGenerateRequest, SkillImportRequest, BulkLintResult, SkillCategoryDef, SkillUsageEntry,
  ChatSendRequest, ChatSendResponse, ChatSession, ChatFileAttachment,
  LLMProvider, LLMProviderTestResult, LLMConfig, ProviderModel,
  BackendToolContract,
  WorkflowExecution, WorkflowStartRequest,
  Notification, NotificationCreate, NotificationStatusUpdate, NotificationRespond, BulkStatusUpdate,
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
  draftPlan: (slug: string, data: { tasks: DraftTaskItem[]; idea_id?: string; objective_id?: string }) =>
    create<DraftPlanResponse>(projectPath(slug, "tasks") + "/draft-plan", data),
  getDraft: (slug: string) =>
    get<DraftPlan>(projectPath(slug, "tasks") + "/draft"),
  approvePlan: (slug: string) =>
    create<ApprovePlanResponse>(projectPath(slug, "tasks") + "/approve-plan", {}),
  discardDraft: (slug: string) =>
    remove<{ status: string; removed_tasks: number }>(projectPath(slug, "tasks") + "/draft"),
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
  remove: (slug: string, id: string) =>
    remove<{ removed: string }>(projectPath(slug, "decisions", id)),
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
  remove: (slug: string, id: string) =>
    remove<{ removed: string }>(projectPath(slug, "objectives", id)),
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
  remove: (slug: string, id: string) =>
    remove<{ removed: string }>(projectPath(slug, "ideas", id)),
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
  remove: (slug: string, id: string) =>
    remove<{ removed: string }>(projectPath(slug, "guidelines", id)),
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
  remove: (slug: string, id: string) =>
    remove<{ removed: string }>(projectPath(slug, "knowledge", id)),
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

// -- Research --
export const research = {
  list: (slug: string, params?: Record<string, string>) =>
    list<{ research: Research[]; count: number }>(projectPath(slug, "research"), params),
  create: (slug: string, data: ResearchCreate[]) =>
    create<{ added: string[]; total: number }>(projectPath(slug, "research"), data),
  get: (slug: string, id: string) =>
    get<Research>(projectPath(slug, "research", id)),
  update: (slug: string, id: string, data: ResearchUpdate) =>
    update<Research>(projectPath(slug, "research", id), data),
  context: (slug: string, entity: string) =>
    get<{ research: Research[]; count: number; entity: string }>(
      projectPath(slug, "research") + `/context?entity=${entity}`),
  remove: (slug: string, id: string) =>
    remove<{ removed: string }>(projectPath(slug, "research", id)),
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
  update: (slug: string, id: string, data: Partial<Lesson>) =>
    update<Lesson>(projectPath(slug, "lessons", id), data),
  remove: (slug: string, id: string) =>
    remove<{ removed: string }>(projectPath(slug, "lessons", id)),
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
  remove: (slug: string, id: string) =>
    remove<{ removed: string }>(projectPath(slug, "ac-templates", id)),
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
  suggestKR: (slug: string, objectiveId: string, context?: string) =>
    create<import("@/lib/types").SuggestKRResponse>(
      `/projects/${slug}/ai/suggest-kr`,
      { objective_id: objectiveId, ...(context ? { context } : {}) },
    ),
};

// -- Skills (global, no project slug) — routed by name (slug) --
export const skills = {
  list: (params?: Record<string, string>) =>
    list<{ skills: Skill[]; count: number }>("/skills", params),
  create: (data: SkillCreate) =>
    create<Skill>("/skills", data),
  get: (name: string) =>
    get<Skill>(`/skills/${name}`),
  update: (name: string, data: SkillUpdate) =>
    update<Skill>(`/skills/${name}`, data),
  remove: (name: string) =>
    remove<{ removed: string }>(`/skills/${name}`),
  validate: (name: string) =>
    create<ValidationResult>(`/skills/${name}/validate`, {}),
  lint: (name: string) =>
    create<LintResult>(`/skills/${name}/lint`, {}),
  lintAll: (params?: Record<string, string>) =>
    create<BulkLintResult>(`/skills/lint-all`, params ?? {}),
  promote: (name: string, force: boolean = false) =>
    create<PromoteResult>(`/skills/${name}/promote`, { force }),
  generate: (data: SkillGenerateRequest) =>
    create<{ skill_md_content: string; parsed_metadata: Record<string, unknown> }>("/skills/generate", data),
  importSkill: (data: SkillImportRequest) =>
    create<{ name: string; parsed_frontmatter: Record<string, unknown> }>("/skills/import", data),
  usage: (name: string) =>
    get<{ name: string; usage: SkillUsageEntry[]; count: number }>(`/skills/${name}/usage`),
  exportSkill: (name: string) =>
    fetchBlob(`/skills/${name}/export`),
  exportBulk: (names?: string[], format: "json" | "zip" = "zip") =>
    create<Blob | { skills: Skill[]; count: number }>("/skills/export-bulk", { names, format }),
  categories: () =>
    get<{ categories: SkillCategoryDef[] }>("/skills/categories"),
  addCategory: (data: { key: string; label: string; color: string }) =>
    create<{ added: string; categories: SkillCategoryDef[] }>("/skills/categories", data),
  removeCategory: (key: string) =>
    remove<{ removed: string }>(`/skills/categories/${key}`),
  // File CRUD (real files on disk)
  listFiles: (name: string) =>
    get<{ name: string; files: Array<{ path: string; file_type: string; size: number }>; count: number }>(`/skills/${name}/files`),
  getFile: (name: string, path: string) =>
    get<{ name: string; path: string; content: string }>(`/skills/${name}/files/${path}`),
  saveFile: (name: string, path: string, content: string) =>
    put<{ name: string; path: string; saved: boolean }>(`/skills/${name}/files/${path}`, { content }),
  deleteFile: (name: string, path: string) =>
    remove<{ name: string; deleted: string }>(`/skills/${name}/files/${path}`),
  moveFile: (name: string, oldPath: string, newPath: string) =>
    create<{ name: string; moved: string; to: string }>(`/skills/${name}/files/move`, { old_path: oldPath, new_path: newPath }),
  // Git sync
  gitStatus: () =>
    get<import("@/lib/types").SkillGitStatus>("/skills/git/status"),
  gitPull: () =>
    create<import("@/lib/types").SkillSyncResult>("/skills/git/pull", {}),
  gitPush: (message: string = "Sync skills", skillNames?: string[]) =>
    create<import("@/lib/types").SkillSyncResult>("/skills/git/push", {
      message,
      ...(skillNames?.length ? { skill_names: skillNames } : {}),
    }),
  gitScan: () =>
    create<{ resynced: number; skills: string[]; remote_only?: string[]; remote_only_count?: number }>("/skills/git/scan", {}),
  gitInit: () =>
    create<import("@/lib/types").SkillSyncResult>("/skills/git/init", {}),
  gitRemoteSkills: () =>
    get<{ skills: import("@/lib/types").RemoteSkill[]; total: number; repo_only: number }>("/skills/git/remote-skills"),
  gitCheckout: (name: string) =>
    create<import("@/lib/types").SkillSyncResult>(`/skills/git/checkout/${name}`, {}),
  gitDeleteRemote: (name: string, message?: string) =>
    remove<import("@/lib/types").SkillSyncResult>(`/skills/git/remote/${name}${message ? `?message=${encodeURIComponent(message)}` : ""}`),
  // Config
  getConfig: () =>
    get<{
      repo_url: string; skills_dir: string; configured_via: string;
      git_user_name: string; git_user_email: string; git_token: string; has_git_token: boolean;
    }>("/skills/config"),
  updateConfig: (data: {
    repo_url?: string; skills_dir?: string;
    git_user_name?: string; git_user_email?: string; git_token?: string;
    skill_injection_enabled?: boolean; max_skill_count?: number;
    per_skill_char_limit?: number; total_skill_char_budget?: number;
  }) =>
    put<Record<string, unknown>>("/skills/config", data),
};

// -- LLM Chat --
export const llm = {
  send: (data: ChatSendRequest) =>
    create<ChatSendResponse>("/llm/chat", data),
  uploadFile: async (file: File, sessionId: string): Promise<ChatFileAttachment> => {
    const form = new FormData();
    form.append("file", file);
    form.append("session_id", sessionId);
    const headers: Record<string, string> = {};
    if (_token) headers["Authorization"] = `Bearer ${_token}`;
    const res = await fetch(`${API_BASE}/llm/chat/files`, {
      method: "POST",
      headers,
      body: form,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => res.statusText);
      throw new ApiError(res.status, body);
    }
    return res.json();
  },
  getSession: (sessionId: string) =>
    get<ChatSession>(`/llm/sessions/${sessionId}`),
  listSessions: (limit?: number) =>
    list<{ sessions: ChatSession[]; count: number }>(
      "/llm/sessions", limit ? { limit: String(limit) } : undefined),
  deleteSession: (sessionId: string) =>
    remove<{ deleted: boolean; session_id: string }>(`/llm/sessions/${sessionId}`),
  resumeSession: (sessionId: string) =>
    create<{ resumed: boolean; session_id: string }>(`/llm/sessions/${sessionId}/resume`, {}),
  updateSessionScopes: (sessionId: string, scopes: string[]) =>
    update<{ session_id: string; scopes: string[]; updated_at: string }>(
      `/llm/sessions/${sessionId}/scopes`, { scopes }),
  searchSessions: (query: string, searchLimit?: number) =>
    list<{ sessions: ChatSession[]; count: number; query: string }>(
      "/llm/sessions/search",
      { q: query, ...(searchLimit ? { limit: String(searchLimit) } : {}) },
    ),
  getProviders: () =>
    get<{ providers: LLMProvider[] }>("/llm/providers"),
  getProviderModels: (name: string) =>
    get<{ provider: string; models: ProviderModel[] }>(`/llm/providers/${name}/models`),
  testProvider: (provider: string) =>
    create<LLMProviderTestResult>("/llm/providers/test", { provider }),
  getConfig: () =>
    get<LLMConfig>("/llm/config"),
  updateConfig: (data: Partial<LLMConfig>) =>
    request<LLMConfig>("/llm/config", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  // Contracts — dynamic tool contracts from backend ToolRegistry
  getContracts: (scopes?: string[]) =>
    get<{ contracts: BackendToolContract[]; total: number }>(
      "/llm/contracts" + (scopes?.length ? `?scope=${scopes.join(",")}` : ""),
    ),
  getContract: (toolName: string) =>
    get<{ contract: Record<string, unknown> }>(`/llm/contracts/${toolName}`),
  // Page registry
  registerPage: (page: { id: string; title: string; description: string; route: string }) =>
    create<{ registered: boolean; id: string }>("/llm/pages/register", page),
  getPages: () =>
    get<{ pages: Array<{ id: string; title: string; description: string; route: string; last_seen: string }>; count: number }>("/llm/pages"),
  // App Context preview
  getAppContext: (scopes?: string[], project?: string, disabledTools?: string[]) => {
    const params = new URLSearchParams();
    if (scopes?.length) params.set("scopes", scopes.join(","));
    if (project) params.set("project", project);
    if (disabledTools?.length) params.set("disabled_tools", disabledTools.join(","));
    const qs = params.toString();
    return get<{ text: string; length: number; scopes: string[] }>(
      "/llm/app-context" + (qs ? `?${qs}` : ""),
    );
  },
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

// -- Notifications (O-002) --
export const notifications = {
  list: (slug: string, params?: Record<string, string>) =>
    list<{ notifications: Notification[]; total: number; unread_count: number }>(
      projectPath(slug, "notifications"), params),
  get: (slug: string, id: string) =>
    get<Notification>(projectPath(slug, "notifications", id)),
  create: (slug: string, data: NotificationCreate[]) =>
    create<{ added: string[]; total: number; unread_count: number }>(
      projectPath(slug, "notifications"), data),
  update: (slug: string, id: string, data: NotificationStatusUpdate) =>
    update<Notification>(projectPath(slug, "notifications", id), data),
  respond: (slug: string, id: string, data: NotificationRespond) =>
    create<Notification>(projectPath(slug, "notifications", id) + "/respond", data),
  bulkUpdate: (slug: string, data: BulkStatusUpdate) =>
    update<{ updated: string[]; count: number; unread_count: number }>(
      projectPath(slug, "notifications") + "/bulk", data),
  unreadCount: (slug: string) =>
    get<{ unread_count: number }>(projectPath(slug, "notifications") + "/unread-count"),
  remove: (slug: string, id: string) =>
    remove<{ removed: string }>(projectPath(slug, "notifications", id)),
};

// -- Workflows (O-001) --
export const workflows = {
  list: (slug: string, params?: Record<string, string>) =>
    list<{ workflows: WorkflowExecution[] }>(
      projectPath(slug, "workflows"), params),
  get: (slug: string, extId: string) =>
    get<WorkflowExecution>(projectPath(slug, "workflows", extId)),
  start: (slug: string, data: WorkflowStartRequest) =>
    create<WorkflowExecution>(projectPath(slug, "workflows"), data),
  resume: (slug: string, extId: string, userResponse: unknown) =>
    create<WorkflowExecution>(
      projectPath(slug, "workflows", extId) + "/resume",
      { user_response: userResponse }),
  cancel: (slug: string, extId: string) =>
    create<WorkflowExecution>(
      projectPath(slug, "workflows", extId) + "/cancel", {}),
};
