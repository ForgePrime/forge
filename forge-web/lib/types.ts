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
export type ChangeAction = "create" | "edit" | "delete" | "rename" | "move" | "verify";
export type ObjectiveStatus = "ACTIVE" | "ACHIEVED" | "ABANDONED" | "PAUSED";
export type ACTemplateCategory =
  | "performance" | "security" | "quality" | "functionality"
  | "accessibility" | "reliability" | "data-integrity" | "ux";
export type KnowledgeLinkEntityType =
  | "task" | "idea" | "objective" | "knowledge" | "guideline" | "lesson";
export type KnowledgeLinkRelation =
  | "required" | "context" | "reference" | "depends_on"
  | "references" | "derived-from" | "supports" | "contradicts";

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

export interface ProjectDetail {
  project: string;
  goal: string;
  config: Record<string, unknown>;
  created: string;
  updated: string;
  task_count: number;
}

export interface ProjectCreate {
  slug: string;
  goal: string;
  config?: Record<string, unknown>;
}

export interface ProjectStatus {
  project: string;
  goal: string;
  total_tasks: number;
  progress_pct: number;
  status_counts: Record<string, number>;
  blockers: Array<{ id: string; name: string; reason: string }>;
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
  skill_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  failed_reason: string | null;
  agent?: string;
  origin?: string;
  knowledge_ids?: string[];
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
  skill_id?: string | null;
}

export interface TaskUpdate {
  name?: string;
  description?: string;
  instruction?: string;
  status?: TaskStatus;
  failed_reason?: string;
  blocked_by_decisions?: string[];
}

export interface ContextSection {
  name: string;
  header: string;
  content: string;
  token_estimate: number;
  was_truncated: boolean;
}

export interface TaskContext {
  task: Task;
  sections: ContextSection[];
  total_token_estimate: number;
  scopes: string[];
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
  exploration_type?: string;
  findings?: unknown[];
  options?: unknown[];
  open_questions?: string[];
  blockers?: string[];
  ready_for_tracker?: boolean;
  evidence_refs?: string[];
  severity?: string;
  likelihood?: string;
  mitigation_plan?: string;
  resolution_notes?: string;
  linked_entity_type?: string;
  linked_entity_id?: string;
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
  file?: string;
  scope?: string;
  tags?: string[];
  exploration_type?: string;
  findings?: unknown[];
  options?: unknown[];
  open_questions?: string[];
  blockers?: string[];
  ready_for_tracker?: boolean;
  evidence_refs?: string[];
  severity?: string;
  likelihood?: string;
  mitigation_plan?: string;
  resolution_notes?: string;
  linked_entity_type?: string;
  linked_entity_id?: string;
}

export interface DecisionUpdate {
  // Core fields
  status?: DecisionStatus;
  task_id?: string;
  issue?: string;
  recommendation?: string;
  reasoning?: string;
  alternatives?: string[];
  confidence?: Confidence;
  decided_by?: "claude" | "user" | "imported";
  file?: string;
  scope?: string;
  tags?: string[];
  resolution_notes?: string;
  evidence_refs?: string[];
  // Linked entity (generic — all decision types)
  linked_entity_type?: string;
  linked_entity_id?: string;
  // Risk fields
  severity?: string;
  likelihood?: string;
  mitigation_plan?: string;
  // Exploration fields
  exploration_type?: string;
  open_questions?: string[];
  blockers?: string[];
}

// ---------------------------------------------------------------------------
// Objectives
// ---------------------------------------------------------------------------

export interface KeyResult {
  id?: string;
  metric?: string;
  baseline?: number;
  target?: number;
  current?: number;
  description?: string;
  status?: "NOT_STARTED" | "IN_PROGRESS" | "ACHIEVED";
}

export interface ObjectiveRelation {
  type: "depends_on" | "related_to" | "supersedes" | "duplicates";
  target_id: string;
  notes?: string;
}

export interface Objective {
  id: string;
  title: string;
  description: string;
  key_results: KeyResult[];
  appetite: "small" | "medium" | "large";
  scope: "project" | "cross-project";
  assumptions: string[];
  tags: string[];
  scopes: string[];
  derived_guidelines: string[];
  knowledge_ids: string[];
  guideline_ids: string[];
  relations: ObjectiveRelation[];
  status: ObjectiveStatus;
  created_at: string;
}

export interface ObjectiveCreate {
  title: string;
  description: string;
  key_results: KeyResult[];
  appetite?: "small" | "medium" | "large";
  scope?: "project" | "cross-project";
  assumptions?: string[];
  tags?: string[];
  scopes?: string[];
  derived_guidelines?: string[];
  knowledge_ids?: string[];
  guideline_ids?: string[];
  relations?: ObjectiveRelation[];
}

export interface ObjectiveUpdate {
  title?: string;
  description?: string;
  status?: ObjectiveStatus;
  appetite?: "small" | "medium" | "large";
  assumptions?: string[];
  tags?: string[];
  key_results?: KeyResult[];
  scopes?: string[];
  derived_guidelines?: string[];
  knowledge_ids?: string[];
  guideline_ids?: string[];
  relations?: ObjectiveRelation[];
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
  related_ideas: string[];
  guidelines: string[];
  relations: Array<Record<string, unknown>>;
  scopes: string[];
  advances_key_results: string[];
  knowledge_ids: string[];
  created_at: string;
}

export interface IdeaCreate {
  title: string;
  description?: string;
  category?: IdeaCategory;
  priority?: "HIGH" | "MEDIUM" | "LOW";
  tags?: string[];
  parent_id?: string;
  related_ideas?: string[];
  guidelines?: string[];
  relations?: Array<Record<string, unknown>>;
  scopes?: string[];
  advances_key_results?: string[];
  knowledge_ids?: string[];
}

export interface IdeaUpdate {
  title?: string;
  description?: string;
  status?: IdeaStatus;
  category?: IdeaCategory;
  priority?: "HIGH" | "MEDIUM" | "LOW";
  rejection_reason?: string;
  merged_into?: string;
  tags?: string[];
  related_ideas?: string[];
  guidelines?: string[];
  exploration_notes?: string;
  parent_id?: string;
  relations?: Array<Record<string, unknown>>;
  scopes?: string[];
  advances_key_results?: string[];
  knowledge_ids?: string[];
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
  group_id?: string;
  guidelines_checked?: string[];
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
  group_id?: string;
  guidelines_checked?: string[];
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
  examples: string[];
  weight: GuidelineWeight;
  status: GuidelineStatus;
  tags: string[];
  derived_from?: string;
  created_at: string;
}

export interface GuidelineCreate {
  title: string;
  scope: string;
  content: string;
  rationale?: string;
  examples?: string[];
  tags?: string[];
  weight?: GuidelineWeight;
}

export interface GuidelineUpdate {
  title?: string;
  content?: string;
  status?: GuidelineStatus;
  rationale?: string;
  scope?: string;
  examples?: string[];
  tags?: string[];
  weight?: GuidelineWeight;
  derived_from?: string;
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
  source?: Record<string, unknown> | null;
  linked_entities: Array<Record<string, unknown>>;
  dependencies: string[];
  review_interval_days: number;
  created_by: "user" | "ai";
  created_at: string;
  updated_at?: string;
}

export interface KnowledgeCreate {
  title: string;
  category: KnowledgeCategory;
  content: string;
  scopes?: string[];
  tags?: string[];
  source?: Record<string, unknown> | null;
  linked_entities?: Array<Record<string, unknown>>;
  dependencies?: string[];
  review_interval_days?: number;
  created_by?: "user" | "ai";
}

export interface KnowledgeUpdate {
  title?: string;
  content?: string;
  status?: KnowledgeStatus;
  category?: KnowledgeCategory;
  scopes?: string[];
  tags?: string[];
  source?: Record<string, unknown> | null;
  dependencies?: string[];
  review_interval_days?: number;
  change_reason?: string;
  changed_by?: "user" | "ai";
}

export interface KnowledgeLink {
  entity_type: KnowledgeLinkEntityType;
  entity_id: string;
  relation: KnowledgeLinkRelation;
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
  decision_ids?: string[];
  severity?: LessonSeverity;
  applies_to?: string;
  tags: string[];
  project?: string;
  created_at: string;
}

export interface LessonCreate {
  category: LessonCategory;
  title: string;
  detail: string;
  task_id?: string;
  decision_ids?: string[];
  severity?: LessonSeverity;
  applies_to?: string;
  tags?: string[];
}

export interface LessonPromote {
  target: "guideline" | "knowledge";
  scope?: string;
  weight?: GuidelineWeight;
  category?: string;
  scopes?: string[];
}

// ---------------------------------------------------------------------------
// AC Templates
// ---------------------------------------------------------------------------

export interface ACTemplate {
  id: string;
  title: string;
  template: string;
  category: ACTemplateCategory;
  description?: string;
  parameters?: Array<{ name: string; type: string; default?: unknown; description?: string }>;
  scopes: string[];
  tags: string[];
  verification_method?: string;
  usage_count?: number;
  status: "ACTIVE" | "DEPRECATED";
  created_at: string;
}

export interface ACTemplateCreate {
  title: string;
  template: string;
  category: ACTemplateCategory;
  description?: string;
  parameters?: Array<{ name: string; type: string; default?: unknown; description?: string }>;
  scopes?: string[];
  tags?: string[];
  verification_method?: string;
}

export interface ACTemplateUpdate {
  title?: string;
  template?: string;
  description?: string;
  category?: string;
  parameters?: Array<{ name: string; type: string; default?: unknown; description?: string }>;
  scopes?: string[];
  tags?: string[];
  verification_method?: string;
  status?: "ACTIVE" | "DEPRECATED";
}

// ---------------------------------------------------------------------------
// Execution
// ---------------------------------------------------------------------------

export type ExecutionStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
}

export interface ExecutionState {
  execution_id: string;
  task_id: string;
  project: string;
  status: ExecutionStatus;
  started_at: string;
  completed_at: string | null;
  output_chunks: Array<{ index: number; content: string; timestamp?: string }>;
  token_usage: TokenUsage;
  error: string | null;
}

export interface ExecutionStreamChunk {
  type: "chunk" | "status" | "error" | "token_usage" | "done";
  content?: string;
  status?: ExecutionStatus;
  error?: string;
  token_usage?: TokenUsage;
  timestamp: string;
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

// ---------------------------------------------------------------------------
// Knowledge Maintenance
// ---------------------------------------------------------------------------

export interface MaintenanceSummary {
  total_knowledge: number;
  active: number;
  draft: number;
  review_needed: number;
  deprecated: number;
  archived: number;
  stale_count: number;
  stale_days_threshold: number;
}

export interface StaleKnowledge {
  id: string;
  title: string;
  status: KnowledgeStatus;
  category: KnowledgeCategory;
  days_since_update: number | null;
  review_interval_days: number;
  total_references?: number;
  linked_entities_count?: number;
  last_updated: string | null;
  suggestion?: string;
  priority?: "high" | "medium";
}

export interface ReviewSuggestion {
  id: string;
  title: string;
  suggestion: string;
  priority: "high" | "medium";
}

export interface UsageStat {
  id: string;
  title: string;
  status: KnowledgeStatus;
  category: KnowledgeCategory;
  linked_entities: number;
  referencing_tasks: number;
  referencing_ideas: number;
  referencing_objectives: number;
  total_references: number;
}

export interface MaintenanceReport {
  summary: MaintenanceSummary;
  stale: StaleKnowledge[];
  review_suggestions: ReviewSuggestion[];
  usage_stats: UsageStat[];
}

export interface StaleReport {
  stale: StaleKnowledge[];
  count: number;
  stale_days_threshold: number;
}

// ---------------------------------------------------------------------------
// AI Suggestions
// ---------------------------------------------------------------------------

export type AISuggestionEntityType = "task" | "idea" | "objective" | "guideline" | "lesson" | "knowledge";
export type AISuggestionType = "knowledge" | "guidelines" | "ac";

export interface KnowledgeSuggestion {
  knowledge_id: string;
  title: string;
  relevance_score: number;
  reason: string;
}

export interface SuggestKnowledgeResponse {
  entity_type: string;
  entity_id: string;
  suggestions: KnowledgeSuggestion[];
  mode: string;
}

export interface GuidelineSuggestion {
  guideline_id: string;
  title: string;
  weight: string;
  relevance_score: number;
  reason: string;
}

export interface SuggestGuidelinesResponse {
  entity_type: string;
  entity_id: string;
  suggestions: GuidelineSuggestion[];
  mode: string;
}

export interface ACSuggestion {
  template_id: string;
  title: string;
  category: string;
  suggested_criterion: string;
  relevance_score: number;
  reason: string;
}

export interface SuggestACResponse {
  task_id: string;
  suggestions: ACSuggestion[];
  mode: string;
}

export interface KRSuggestion {
  description: string;
  metric?: string;
  metric_hint?: string;
  rationale: string;
  relevance_score: number;
}

export interface SuggestKRResponse {
  objective_id: string;
  suggestions: KRSuggestion[];
  mode: string;
}

export interface PromotionRecommendation {
  target: "knowledge" | "guideline" | "none";
  confidence: number;
  reason: string;
  suggested_scope: string;
  suggested_category: string;
  suggested_weight: string;
}

export interface EvaluateLessonResponse {
  lesson_id: string;
  lesson_title: string;
  recommendation: PromotionRecommendation;
  mode: string;
}

export interface ImpactItem {
  entity_type: string;
  entity_id: string;
  name: string;
  impact_level: "high" | "medium" | "low";
  reason: string;
}

export interface AssessImpactResponse {
  knowledge_id: string;
  knowledge_title: string;
  total_affected: number;
  impact_items: ImpactItem[];
  summary: string;
  mode: string;
}

// ---------------------------------------------------------------------------
// Skills
// ---------------------------------------------------------------------------

export type SkillStatus = "DRAFT" | "ACTIVE" | "DEPRECATED" | "ARCHIVED";
export type SkillCategory = string;

export interface TESLintFinding {
  rule_id: string;
  severity: "error" | "warning" | "info";
  message: string;
  line: number | null;
  column: number | null;
}

export interface PromotionHistoryEntry {
  promoted_at: string;
  error_count: number;
  warning_count: number;
  forced: boolean;
  gates: Array<{ gate: string; passed: boolean; detail: string }>;
}

export type SkillFileType = "script" | "reference" | "asset" | "other";

export interface SkillFile {
  path: string;
  content: string;
  file_type: SkillFileType;
}

export interface Skill {
  name: string;
  display_name?: string;
  description: string;
  categories: string[];
  status: SkillStatus;
  skill_md_content: string | null;
  version: string;
  allowed_tools: string[];
  evals_json: Array<Record<string, unknown>>;
  files: SkillFile[];
  teslint_config: Record<string, unknown> | null;
  tags: string[];
  scopes: string[];
  sync: boolean;
  promoted_with_warnings: boolean;
  promotion_history: PromotionHistoryEntry[];
  usage_count: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface SkillCreate {
  name: string;
  description?: string;
  categories?: string[];
  skill_md_content?: string | null;
  evals_json?: Array<Record<string, unknown>>;
  teslint_config?: Record<string, unknown> | null;
  tags?: string[];
  scopes?: string[];
  created_by?: string | null;
}

export interface SkillUpdate {
  description?: string;
  categories?: string[];
  status?: SkillStatus;
  skill_md_content?: string | null;
  evals_json?: Array<Record<string, unknown>>;
  teslint_config?: Record<string, unknown> | null;
  tags?: string[];
  scopes?: string[];
  sync?: boolean;
}

export interface ValidationResult {
  name: string;
  valid: boolean;
  errors: string[];
  warnings: string[];
  error_count: number;
  warning_count: number;
}

export interface LintResult {
  skill_name: string;
  success: boolean;
  passed: boolean;
  error_count: number;
  warning_count: number;
  info_count: number;
  findings: TESLintFinding[];
  error_message: string | null;
}

export interface PromoteResult {
  name: string;
  status: string;
  promoted_with_warnings: boolean;
  gates: Array<{ gate: string; passed: boolean; detail: string }>;
}

export interface SkillGenerateRequest {
  description: string;
  categories?: string[];
  examples?: string[];
  style_hints?: string;
}

export interface SkillImportRequest {
  content: string;
  filename?: string;
  categories?: string[];
}

export interface BulkLintResult {
  results: Array<{
    skill_name: string;
    status: string;
    passed: boolean;
    error_count: number;
    warning_count: number;
    error_message: string | null;
  }>;
  total: number;
  passed: number;
  failed: number;
}

export interface SkillGitStatus {
  configured: boolean;
  initialized?: boolean;
  has_remote?: boolean;
  branch?: string;
  ahead?: number;
  behind?: number;
  local_changes?: string[];
  last_commit?: string;
  error?: string | null;
  message?: string;
}

export interface SkillSyncResult {
  success: boolean;
  message: string;
  files_changed?: number;
}

export interface RemoteSkill {
  name: string;
  display_name: string;
  description: string;
  categories: string[];
  status: string;
  sync: boolean;
  exists_locally: boolean;
}

export interface SkillUsageEntry {
  project: string;
  task_id: string;
  task_name: string;
  status: string;
}

export interface SkillCategoryDef {
  key: string;
  label: string;
  color: string;
  is_default: boolean;
}

// ---------------------------------------------------------------------------
// Debug Monitor
// ---------------------------------------------------------------------------

export interface DebugSessionSummary {
  session_id: string;
  timestamp: string;
  contract_id: string | null;
  provider: string;
  model: string;
  task_id: string | null;
  execution_id: string | null;
  status: "pending" | "success" | "error" | "validation_failed";
  latency_ms: number;
  token_usage: { input_tokens: number; output_tokens: number; total_tokens: number };
  error: string | null;
}

export interface DebugContextSection {
  name: string;
  header: string;
  content: string;
  token_estimate: number;
  was_truncated: boolean;
}

export interface DebugValidationResult {
  rule_id: string;
  description: string;
  passed: boolean;
  error: string | null;
}

export interface DebugSession extends DebugSessionSummary {
  contract_name: string | null;
  temperature: number;
  max_tokens: number;
  response_format: string;
  system_prompt: string;
  user_prompt: string;
  context_sections: DebugContextSection[];
  total_context_tokens: number;
  tools: Record<string, unknown>[] | null;
  raw_response: string;
  parsed_output: Record<string, unknown> | null;
  stop_reason: string;
  validation_results: DebugValidationResult[];
  validation_passed: boolean;
  error_type: string | null;
}

export interface DebugStatus {
  enabled: boolean;
  project: string;
  session_count: number;
}

// ---------------------------------------------------------------------------
// LLM Chat
// ---------------------------------------------------------------------------

export type ChatRole = "user" | "assistant" | "system" | "tool";

export interface ChatToolCall {
  id?: string;
  name: string;
  input: Record<string, unknown>;
  result?: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  toolCalls?: ChatToolCall[];
  streaming?: boolean;
  created_at: string;
  /** Original error object for rich error rendering (client-only, not serialized). */
  error?: unknown;
}

export interface ChatSession {
  session_id: string;
  context_type: string;
  context_id: string;
  project: string;
  messages: ChatMessage[];
  model_used: string;
  total_tokens_in: number;
  total_tokens_out: number;
  estimated_cost: number;
  message_count?: number;
  session_type?: string;
  session_status?: string;
  target_entity_type?: string;
  target_entity_id?: string;
  pause_reason?: string;
  blocked_by_decision_id?: string;
  created_at: string;
  updated_at: string;
}

export interface ChatFileAttachment {
  file_id: string;
  filename: string;
  size: number;
  content_preview?: string;
}

export interface ChatSendRequest {
  message: string;
  context_type?: string;
  context_id?: string;
  project?: string;
  session_id?: string | null;
  model?: string | null;
  scopes?: string[];
  disabled_capabilities?: string[];
  file_ids?: string[];
  page_context?: string;
  session_type?: string;
  target_entity_type?: string;
  target_entity_id?: string;
}

export interface ChatSendResponse {
  session_id: string;
  content: string;
  model: string;
  iterations: number;
  tool_calls: ChatToolCall[];
  total_input_tokens: number;
  total_output_tokens: number;
  stop_reason: string;
}

export interface ProviderModel {
  id: string;
  name: string;
  context_window?: number | null;
  max_output?: number | null;
  supports_vision?: boolean;
}

export interface LLMProvider {
  name: string;
  provider_type: string;
  default_model: string;
  status: string;
  has_api_key: boolean;
  api_key_source: string;
}

export interface LLMProviderTestResult {
  provider: string;
  status: string;
  model?: string | null;
  latency_ms?: number | null;
  message?: string | null;
  error?: string | null;
}

export interface LLMFeatureFlags {
  skills: boolean;
  objectives: boolean;
  ideas: boolean;
  tasks: boolean;
  knowledge: boolean;
  guidelines: boolean;
  decisions: boolean;
  lessons: boolean;
  ac_templates: boolean;
  projects: boolean;
  changes: boolean;
  research: boolean;
}

export interface LLMModulePermission {
  read: boolean;
  write: boolean;
  delete: boolean;
}

export interface LLMConfig {
  default_provider: string;
  default_model: string | null;
  feature_flags: LLMFeatureFlags;
  permissions: Record<string, LLMModulePermission>;
  api_keys: Record<string, string>;
  max_tokens_per_session: number;
  max_iterations_per_turn: number;
  session_ttl_hours: number;
  custom_app_context: string;
}

/** Backend tool contract from GET /llm/contracts. */
export interface BackendToolContract {
  name: string;
  description: string;
  scope: string | null;
  action: string;
  parameters: Record<string, unknown>;
  required_permission: string | null;
}
