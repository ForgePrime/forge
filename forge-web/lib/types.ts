/**
 * TypeScript types for all Forge API entities.
 * Matches the Pydantic models in forge-api/app/routers/*.py.
 */

// ---------------------------------------------------------------------------
// Common
// ---------------------------------------------------------------------------

export type TaskStatus = "TODO" | "IN_PROGRESS" | "DONE" | "FAILED" | "SKIPPED" | "CLAIMING";
export type TaskType = "feature" | "bug" | "chore" | "investigation";
export type DecisionType =
  | "architecture" | "implementation" | "dependency" | "security"
  | "performance" | "testing" | "naming" | "convention" | "constraint"
  | "business" | "strategy" | "other" | "exploration" | "risk";
export type DecisionStatus = "OPEN" | "CLOSED" | "DEFERRED" | "ANALYZING" | "MITIGATED" | "ACCEPTED";
export type Confidence = "HIGH" | "MEDIUM" | "LOW";
export type IdeaStatus = "DRAFT" | "EXPLORING" | "APPROVED" | "REJECTED" | "COMMITTED";
export type IdeaCategory =
  | "feature" | "improvement" | "experiment" | "migration"
  | "refactor" | "infrastructure" | "business-opportunity" | "research";
export type GuidelineWeight = "must" | "should" | "may";
export type GuidelineStatus = "ACTIVE" | "DEPRECATED";
export type KnowledgeStatus = "DRAFT" | "ACTIVE" | "REVIEW_NEEDED" | "DEPRECATED" | "ARCHIVED";
export type KnowledgeCategory =
  | "domain-rules" | "api-reference" | "architecture" | "business-context"
  | "technical-context" | "code-patterns" | "integration" | "infrastructure";
export type LessonCategory =
  | "pattern-discovered" | "mistake-avoided" | "decision-validated"
  | "decision-reversed" | "tool-insight" | "architecture-lesson"
  | "process-improvement" | "market-insight";
export type LessonSeverity = "critical" | "important" | "minor";
export type ChangeAction = "create" | "edit" | "delete" | "rename" | "move";

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

export interface Project {
  slug: string;
  goal: string;
  created_at: string;
  config?: Record<string, unknown>;
}

export interface ProjectCreate {
  slug: string;
  goal: string;
}

export interface ProjectStatus {
  project: string;
  goal: string;
  total: number;
  done: number;
  in_progress: number;
  todo: number;
  failed: number;
  skipped: number;
}

// ---------------------------------------------------------------------------
// Tasks
// ---------------------------------------------------------------------------

export interface Task {
  id: string;
  name: string;
  description: string;
  instruction: string;
  type: TaskType;
  status: TaskStatus;
  depends_on: string[];
  blocked_by_decisions: string[];
  conflicts_with: string[];
  acceptance_criteria: string[];
  scopes: string[];
  parallel: boolean;
  skill: string | null;
  started_at: string | null;
  completed_at: string | null;
  failed_reason: string | null;
  agent?: string;
}

export interface TaskCreate {
  name: string;
  description?: string;
  instruction?: string;
  type?: TaskType;
  depends_on?: string[];
  blocked_by_decisions?: string[];
  conflicts_with?: string[];
  acceptance_criteria?: string[];
  scopes?: string[];
  parallel?: boolean;
  skill?: string | null;
}

export interface TaskUpdate {
  name?: string;
  description?: string;
  instruction?: string;
  status?: TaskStatus;
  failed_reason?: string;
  blocked_by_decisions?: string[];
}

// ---------------------------------------------------------------------------
// Decisions
// ---------------------------------------------------------------------------

export interface Decision {
  id: string;
  task_id: string;
  type: DecisionType;
  issue: string;
  recommendation: string;
  reasoning: string;
  alternatives: string[];
  confidence: Confidence;
  status: DecisionStatus;
  decided_by: "claude" | "user" | "imported";
  file: string;
  scope: string;
  tags: string[];
  created_at: string;
  updated_at?: string;
}

export interface DecisionCreate {
  task_id: string;
  type?: DecisionType;
  issue: string;
  recommendation: string;
  reasoning?: string;
  alternatives?: string[];
  confidence?: Confidence;
  status?: DecisionStatus;
  decided_by?: "claude" | "user" | "imported";
  tags?: string[];
}

export interface DecisionUpdate {
  status?: DecisionStatus;
  recommendation?: string;
  reasoning?: string;
  decided_by?: "claude" | "user" | "imported";
  resolution_notes?: string;
}

// ---------------------------------------------------------------------------
// Objectives
// ---------------------------------------------------------------------------

export interface KeyResult {
  metric: string;
  baseline?: number;
  target: number;
  current?: number;
}

export interface Objective {
  id: string;
  title: string;
  description: string;
  key_results: KeyResult[];
  appetite?: "small" | "medium" | "large";
  scope?: "project" | "cross-project";
  tags: string[];
  status: string;
  created_at: string;
}

export interface ObjectiveCreate {
  title: string;
  description: string;
  key_results: KeyResult[];
  appetite?: "small" | "medium" | "large";
  scope?: "project" | "cross-project";
  tags?: string[];
}

// ---------------------------------------------------------------------------
// Ideas
// ---------------------------------------------------------------------------

export interface Idea {
  id: string;
  title: string;
  description: string;
  category: IdeaCategory;
  priority: "HIGH" | "MEDIUM" | "LOW";
  status: IdeaStatus;
  tags: string[];
  parent_id: string | null;
  created_at: string;
}

export interface IdeaCreate {
  title: string;
  description: string;
  category?: IdeaCategory;
  priority?: "HIGH" | "MEDIUM" | "LOW";
  tags?: string[];
  parent_id?: string;
}

export interface IdeaUpdate {
  title?: string;
  description?: string;
  status?: IdeaStatus;
  category?: IdeaCategory;
  priority?: "HIGH" | "MEDIUM" | "LOW";
}

// ---------------------------------------------------------------------------
// Changes
// ---------------------------------------------------------------------------

export interface ChangeRecord {
  id: string;
  task_id: string;
  file: string;
  action: ChangeAction;
  summary: string;
  reasoning_trace?: Array<{ step: string; detail: string }>;
  decision_ids?: string[];
  lines_added?: number;
  lines_removed?: number;
  recorded_at: string;
}

export interface ChangeCreate {
  task_id: string;
  file: string;
  action: ChangeAction;
  summary: string;
  reasoning_trace?: Array<{ step: string; detail: string }>;
  decision_ids?: string[];
  lines_added?: number;
  lines_removed?: number;
}

// ---------------------------------------------------------------------------
// Guidelines
// ---------------------------------------------------------------------------

export interface Guideline {
  id: string;
  title: string;
  scope: string;
  content: string;
  rationale?: string;
  weight: GuidelineWeight;
  status: GuidelineStatus;
  tags: string[];
  created_at: string;
}

export interface GuidelineCreate {
  title: string;
  scope: string;
  content: string;
  rationale?: string;
  weight?: GuidelineWeight;
  tags?: string[];
}

export interface GuidelineUpdate {
  title?: string;
  content?: string;
  status?: GuidelineStatus;
  weight?: GuidelineWeight;
  scope?: string;
}

// ---------------------------------------------------------------------------
// Knowledge
// ---------------------------------------------------------------------------

export interface Knowledge {
  id: string;
  title: string;
  category: KnowledgeCategory;
  content: string;
  status: KnowledgeStatus;
  scopes: string[];
  tags: string[];
  version: number;
  created_at: string;
  updated_at?: string;
}

export interface KnowledgeCreate {
  title: string;
  category: KnowledgeCategory;
  content: string;
  scopes?: string[];
  tags?: string[];
}

export interface KnowledgeUpdate {
  title?: string;
  content?: string;
  status?: KnowledgeStatus;
  category?: KnowledgeCategory;
  change_reason?: string;
}

export interface KnowledgeLink {
  entity_type: string;
  entity_id: string;
  relation: string;
}

// ---------------------------------------------------------------------------
// Lessons
// ---------------------------------------------------------------------------

export interface Lesson {
  id: string;
  category: LessonCategory;
  title: string;
  detail: string;
  task_id?: string;
  severity?: LessonSeverity;
  tags: string[];
  created_at: string;
}

export interface LessonCreate {
  category: LessonCategory;
  title: string;
  detail: string;
  task_id?: string;
  decision_ids?: string[];
  severity?: LessonSeverity;
  tags?: string[];
}

// ---------------------------------------------------------------------------
// AC Templates
// ---------------------------------------------------------------------------

export interface ACTemplate {
  id: string;
  title: string;
  template: string;
  category: string;
  description?: string;
  parameters?: Array<{ name: string; type: string; default?: unknown; description?: string }>;
  status: "ACTIVE" | "DEPRECATED";
  created_at: string;
}

export interface ACTemplateCreate {
  title: string;
  template: string;
  category: string;
  description?: string;
  parameters?: Array<{ name: string; type: string; default?: unknown; description?: string }>;
}

// ---------------------------------------------------------------------------
// Gates
// ---------------------------------------------------------------------------

export interface Gate {
  name: string;
  command: string;
  required: boolean;
}

export interface GateCreate {
  name: string;
  command: string;
  required?: boolean;
}
