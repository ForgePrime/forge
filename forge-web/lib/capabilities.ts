/**
 * Capability Contract Registry — static definitions of what the AI can do per scope.
 *
 * Each scope (skills, tasks, etc.) has a list of capabilities with:
 * - tool mapping to backend ToolRegistry
 * - availability flag
 * - action type for permission checking
 * - contract: parameters and return description
 */

import type { LLMModulePermission } from "./types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CapabilityParam {
  name: string;
  type: "string" | "number" | "boolean" | "array" | "object";
  required: boolean;
  description: string;
  enum?: string[];
}

export interface CapabilityContract {
  params: CapabilityParam[];
  returns: string;
}

export interface CapabilityDef {
  /** Unique ID, e.g., "skills-list". */
  id: string;
  /** Display label, e.g., "List all skills". */
  label: string;
  /** Short description of what this capability does. */
  description: string;
  /** Action type — used for permission checks. */
  action: "READ" | "WRITE" | "DELETE";
  /** Scope this capability belongs to. */
  scope: string;
  /** Backend tool name, or null if not yet implemented. */
  toolName: string | null;
  /** Whether the backend tool exists. */
  available: boolean;
  /** Contract — parameter list and return description. */
  contract?: CapabilityContract;
}

export type PermissionStatus = "enabled" | "no-permission" | "coming-soon";

// ---------------------------------------------------------------------------
// Common parameter definitions (reused across scopes)
// ---------------------------------------------------------------------------

const P_PROJECT: CapabilityParam = { name: "project", type: "string", required: false, description: "Project slug (uses context if omitted)" };
const P_ENTITY_TYPE: CapabilityParam = { name: "entity_type", type: "string", required: true, description: "Entity type to query" };
const P_QUERY: CapabilityParam = { name: "query", type: "string", required: false, description: "Text search query" };
const P_FILTERS: CapabilityParam = { name: "filters", type: "object", required: false, description: "Key-value filters (e.g., {status: 'TODO'})" };
const P_ENTITY_ID: CapabilityParam = { name: "entity_id", type: "string", required: true, description: "Entity ID (e.g., T-001)" };

// ---------------------------------------------------------------------------
// Capability contracts per scope
// ---------------------------------------------------------------------------

export const CAPABILITY_CONTRACTS: Record<string, CapabilityDef[]> = {
  // ========== SKILLS ==========
  skills: [
    {
      id: "skills-list", label: "List skills", description: "View all available skills",
      action: "READ", scope: "skills", toolName: "listEntities", available: true,
      contract: { params: [P_FILTERS], returns: "List of skill objects with id, name, description, categories, scopes, status" },
    },
    {
      id: "skills-search", label: "Search skills", description: "Search skills by text query",
      action: "READ", scope: "skills", toolName: "searchEntities", available: true,
      contract: { params: [P_QUERY, P_FILTERS], returns: "Matching skill objects (max 20)" },
    },
    {
      id: "skills-get", label: "Get skill details", description: "View a single skill's full content",
      action: "READ", scope: "skills", toolName: "getEntity", available: true,
      contract: { params: [P_ENTITY_ID], returns: "Full skill object including skill_md_content" },
    },
    {
      id: "skills-get-other", label: "Get other skill", description: "Read another skill for reference",
      action: "READ", scope: "skills", toolName: "getOtherSkill", available: true,
      contract: {
        params: [{ name: "skill_id", type: "string", required: true, description: "Skill ID or name to read" }],
        returns: "Skill name, categories, content, tags",
      },
    },
    {
      id: "skills-edit-content", label: "Edit skill content", description: "Update a skill's SKILL.md body",
      action: "WRITE", scope: "skills", toolName: "updateSkillContent", available: true,
      contract: {
        params: [
          { name: "skill_id", type: "string", required: false, description: "Skill ID (uses context if omitted)" },
          { name: "content", type: "string", required: true, description: "New SKILL.md content" },
        ],
        returns: "Confirmation with skill_id",
      },
    },
    {
      id: "skills-edit-metadata", label: "Edit skill metadata", description: "Update category, tags, or scopes",
      action: "WRITE", scope: "skills", toolName: "updateSkillMetadata", available: true,
      contract: {
        params: [
          { name: "skill_id", type: "string", required: false, description: "Skill ID" },
          { name: "category", type: "string", required: false, description: "New category", enum: ["workflow", "analysis", "generation", "integration", "utility"] },
          { name: "tags", type: "array", required: false, description: "New tags list" },
          { name: "scopes", type: "array", required: false, description: "New scopes list" },
        ],
        returns: "Updated skill object",
      },
    },
    {
      id: "skills-lint", label: "Lint skill", description: "Run TESLint quality check",
      action: "READ", scope: "skills", toolName: "runSkillLint", available: true,
      contract: {
        params: [{ name: "skill_id", type: "string", required: false, description: "Skill ID to lint" }],
        returns: "Lint results: success, error_count, warning_count, findings[]",
      },
    },
    {
      id: "skills-preview", label: "Preview skill", description: "Render full markdown preview",
      action: "READ", scope: "skills", toolName: "previewSkill", available: true,
      contract: { params: [], returns: "Rendered markdown, name, description, line_count, file_count" },
    },
    {
      id: "skills-add-file", label: "Add file", description: "Add a bundled file to the skill",
      action: "WRITE", scope: "skills", toolName: "addSkillFile", available: true,
      contract: {
        params: [
          { name: "skill_id", type: "string", required: false, description: "Skill ID" },
          { name: "path", type: "string", required: true, description: "File path (e.g., scripts/helper.py)" },
          { name: "content", type: "string", required: true, description: "File content" },
          { name: "file_type", type: "string", required: false, description: "File type", enum: ["script", "reference", "asset", "other"] },
        ],
        returns: "Confirmation with skill_id and path",
      },
    },
    {
      id: "skills-remove-file", label: "Remove file", description: "Remove a bundled file from the skill",
      action: "DELETE", scope: "skills", toolName: "removeSkillFile", available: true,
      contract: {
        params: [
          { name: "skill_id", type: "string", required: false, description: "Skill ID" },
          { name: "path", type: "string", required: true, description: "Path of file to remove" },
        ],
        returns: "Confirmation with skill_id and path",
      },
    },
    {
      id: "skills-list-files", label: "List files", description: "List bundled files in the skill",
      action: "READ", scope: "skills", toolName: "listSkillFiles", available: true,
      contract: {
        params: [{ name: "skill_id", type: "string", required: false, description: "Skill ID" }],
        returns: "List of {path, file_type} with count",
      },
    },
    {
      id: "skills-get-file", label: "Get file content", description: "Read content of a bundled file",
      action: "READ", scope: "skills", toolName: "getSkillFileContent", available: true,
      contract: {
        params: [
          { name: "skill_id", type: "string", required: false, description: "Skill ID" },
          { name: "path", type: "string", required: true, description: "Path of file to read" },
        ],
        returns: "File content, path, file_type",
      },
    },
    {
      id: "skills-instantiate-ac", label: "Instantiate AC template", description: "Fill AC template with parameters",
      action: "READ", scope: "skills", toolName: "instantiateACTemplate", available: true,
      contract: {
        params: [
          { name: "template_id", type: "string", required: true, description: "AC template ID (e.g., AC-001)" },
          { name: "params", type: "object", required: true, description: "Key-value parameter map" },
          P_PROJECT,
        ],
        returns: "Rendered AC text, template ID, resolved params",
      },
    },
  ],

  // ========== TASKS ==========
  tasks: [
    {
      id: "tasks-list", label: "List tasks", description: "View all tasks in project pipeline",
      action: "READ", scope: "tasks", toolName: "listEntities", available: true,
      contract: { params: [P_PROJECT, P_FILTERS], returns: "List of task objects with id, name, status, depends_on, type" },
    },
    {
      id: "tasks-search", label: "Search tasks", description: "Search tasks by text query",
      action: "READ", scope: "tasks", toolName: "searchEntities", available: true,
      contract: { params: [P_QUERY, P_FILTERS, P_PROJECT], returns: "Matching task objects (max 20)" },
    },
    {
      id: "tasks-get", label: "Get task details", description: "View full task with all fields",
      action: "READ", scope: "tasks", toolName: "getEntity", available: true,
      contract: { params: [P_ENTITY_ID, P_PROJECT], returns: "Full task object including acceptance_criteria, scopes, instruction" },
    },
    {
      id: "tasks-context", label: "Get task context", description: "Load full execution context (guidelines, knowledge, deps, risks, business context)",
      action: "READ", scope: "tasks", toolName: "getTaskContext", available: true,
      contract: {
        params: [
          { name: "task_id", type: "string", required: true, description: "Task ID (e.g., T-001)" },
          P_PROJECT,
        ],
        returns: "Full context: scoped guidelines, knowledge, dependency chain, active risks, business context from origin",
      },
    },
    {
      id: "tasks-create", label: "Create task", description: "Add a new task to the pipeline",
      action: "WRITE", scope: "tasks", toolName: "createTask", available: true,
      contract: {
        params: [
          { name: "name", type: "string", required: true, description: "Task name in kebab-case" },
          { name: "description", type: "string", required: false, description: "What needs to be done" },
          { name: "instruction", type: "string", required: false, description: "Step-by-step how to do it" },
          { name: "depends_on", type: "array", required: false, description: "Prerequisite task IDs" },
          { name: "type", type: "string", required: false, description: "Task type", enum: ["feature", "bug", "chore", "investigation"] },
          { name: "scopes", type: "array", required: false, description: "Guideline scopes" },
          { name: "acceptance_criteria", type: "array", required: false, description: "Conditions for DONE" },
          { name: "origin", type: "string", required: false, description: "Source (I-001, O-001, or text)" },
          P_PROJECT,
        ],
        returns: "Created task with generated ID (T-NNN)",
      },
    },
    {
      id: "tasks-update", label: "Update task", description: "Modify a TODO/FAILED task's fields",
      action: "WRITE", scope: "tasks", toolName: "updateTask", available: true,
      contract: {
        params: [
          { name: "task_id", type: "string", required: true, description: "Task ID (e.g., T-001)" },
          { name: "name", type: "string", required: false, description: "New name" },
          { name: "description", type: "string", required: false, description: "New description" },
          { name: "depends_on", type: "array", required: false, description: "New dependencies" },
          { name: "scopes", type: "array", required: false, description: "New scopes" },
          P_PROJECT,
        ],
        returns: "Updated task with list of changed fields",
      },
    },
    {
      id: "tasks-complete", label: "Complete task", description: "Mark a task as DONE with reasoning",
      action: "WRITE", scope: "tasks", toolName: "completeTask", available: true,
      contract: {
        params: [
          { name: "task_id", type: "string", required: true, description: "Task ID to complete" },
          { name: "reasoning", type: "string", required: false, description: "Why this task is done" },
          P_PROJECT,
        ],
        returns: "Confirmation with task_id and DONE status",
      },
    },
  ],

  // ========== PLANNING ==========
  planning: [
    {
      id: "planning-draft", label: "Draft plan", description: "Decompose objective/idea into a task graph (draft, not yet materialized)",
      action: "WRITE", scope: "planning", toolName: "draftPlan", available: true,
      contract: {
        params: [
          { name: "tasks", type: "array", required: true, description: "Array of task definitions with id, name, depends_on, scopes, etc." },
          { name: "objective_id", type: "string", required: false, description: "Source objective ID for traceability" },
          { name: "idea_id", type: "string", required: false, description: "Source idea ID for traceability" },
          P_PROJECT,
        ],
        returns: "Draft plan stored with task count and IDs",
      },
    },
    {
      id: "planning-show", label: "Show draft", description: "Preview the current draft plan before approval",
      action: "READ", scope: "planning", toolName: "showDraft", available: true,
      contract: {
        params: [P_PROJECT],
        returns: "Draft plan with all task definitions, source idea/objective, created timestamp",
      },
    },
    {
      id: "planning-approve", label: "Approve plan", description: "Materialize draft plan into pipeline as TODO tasks",
      action: "WRITE", scope: "planning", toolName: "approvePlan", available: true,
      contract: {
        params: [P_PROJECT],
        returns: "Confirmation with materialized task count and IDs",
      },
    },
  ],

  // ========== OBJECTIVES ==========
  objectives: [
    {
      id: "objectives-list", label: "List objectives", description: "View all business objectives",
      action: "READ", scope: "objectives", toolName: "listEntities", available: true,
      contract: { params: [P_PROJECT, P_FILTERS], returns: "List of objective objects with id, title, status, key_results" },
    },
    {
      id: "objectives-search", label: "Search objectives", description: "Search objectives by text",
      action: "READ", scope: "objectives", toolName: "searchEntities", available: true,
      contract: { params: [P_QUERY, P_FILTERS, P_PROJECT], returns: "Matching objectives (max 20)" },
    },
    {
      id: "objectives-get", label: "Get objective details", description: "View objective with KR progress",
      action: "READ", scope: "objectives", toolName: "getEntity", available: true,
      contract: { params: [P_ENTITY_ID, P_PROJECT], returns: "Full objective with key_results, appetite, assumptions, scopes" },
    },
    {
      id: "objectives-create", label: "Create objective", description: "Define a business objective with key results",
      action: "WRITE", scope: "objectives", toolName: "createObjective", available: true,
      contract: {
        params: [
          { name: "title", type: "string", required: true, description: "Concise objective name" },
          { name: "description", type: "string", required: true, description: "Why this matters" },
          { name: "key_results", type: "array", required: true, description: "Measurable outcomes (metric/baseline/target or description/status)" },
          { name: "appetite", type: "string", required: false, description: "Effort budget", enum: ["small", "medium", "large"] },
          { name: "scopes", type: "array", required: false, description: "Guideline scopes" },
          P_PROJECT,
        ],
        returns: "Created objective with generated ID (O-NNN) and KR IDs",
      },
    },
    {
      id: "objectives-update", label: "Update objective", description: "Update status or KR progress",
      action: "WRITE", scope: "objectives", toolName: "updateObjective", available: true,
      contract: {
        params: [
          { name: "id", type: "string", required: true, description: "Objective ID (e.g., O-001)" },
          { name: "status", type: "string", required: false, description: "New status", enum: ["ACTIVE", "ACHIEVED", "ABANDONED", "PAUSED"] },
          { name: "key_results", type: "array", required: false, description: "KR updates [{id, current, status}]" },
          P_PROJECT,
        ],
        returns: "Updated objective with changed fields",
      },
    },
  ],

  // ========== IDEAS ==========
  ideas: [
    {
      id: "ideas-list", label: "List ideas", description: "View all ideas in staging area",
      action: "READ", scope: "ideas", toolName: "listEntities", available: true,
      contract: { params: [P_PROJECT, P_FILTERS], returns: "List of idea objects with id, title, status, category, priority" },
    },
    {
      id: "ideas-search", label: "Search ideas", description: "Search ideas by text query",
      action: "READ", scope: "ideas", toolName: "searchEntities", available: true,
      contract: { params: [P_QUERY, P_FILTERS, P_PROJECT], returns: "Matching ideas (max 20)" },
    },
    {
      id: "ideas-get", label: "Get idea details", description: "View idea with relations and hierarchy",
      action: "READ", scope: "ideas", toolName: "getEntity", available: true,
      contract: { params: [P_ENTITY_ID, P_PROJECT], returns: "Full idea with relations, parent_id, advances_key_results" },
    },
    {
      id: "ideas-create", label: "Create idea", description: "Add a new idea to staging",
      action: "WRITE", scope: "ideas", toolName: "createIdea", available: true,
      contract: {
        params: [
          { name: "title", type: "string", required: true, description: "Concise idea name" },
          { name: "description", type: "string", required: true, description: "What to achieve and why" },
          { name: "category", type: "string", required: false, description: "Idea category", enum: ["feature", "improvement", "experiment", "migration", "refactor", "infrastructure", "business-opportunity", "research"] },
          { name: "priority", type: "string", required: false, description: "Priority level", enum: ["HIGH", "MEDIUM", "LOW"] },
          { name: "parent_id", type: "string", required: false, description: "Parent idea ID for hierarchy" },
          { name: "advances_key_results", type: "array", required: false, description: "KR IDs this idea advances (O-001/KR-1)" },
          P_PROJECT,
        ],
        returns: "Created idea with generated ID (I-NNN)",
      },
    },
    {
      id: "ideas-update", label: "Update idea", description: "Update idea status, fields, or relations",
      action: "WRITE", scope: "ideas", toolName: "updateIdea", available: true,
      contract: {
        params: [
          { name: "id", type: "string", required: true, description: "Idea ID (e.g., I-001)" },
          { name: "status", type: "string", required: false, description: "New status", enum: ["DRAFT", "EXPLORING", "APPROVED", "REJECTED", "COMMITTED"] },
          { name: "exploration_notes", type: "string", required: false, description: "Notes from exploration" },
          { name: "relations", type: "array", required: false, description: "Relations to append [{type, target_id}]" },
          P_PROJECT,
        ],
        returns: "Updated idea with changed fields",
      },
    },
  ],

  // ========== DECISIONS ==========
  decisions: [
    {
      id: "decisions-list", label: "List decisions", description: "View all decisions, explorations, and risks",
      action: "READ", scope: "decisions", toolName: "listEntities", available: true,
      contract: { params: [P_PROJECT, P_FILTERS], returns: "List of decision objects with id, type, issue, status, task_id" },
    },
    {
      id: "decisions-search", label: "Search decisions", description: "Search decisions by text",
      action: "READ", scope: "decisions", toolName: "searchEntities", available: true,
      contract: { params: [P_QUERY, P_FILTERS, P_PROJECT], returns: "Matching decisions (max 20)" },
    },
    {
      id: "decisions-get", label: "Get decision details", description: "View full decision with reasoning",
      action: "READ", scope: "decisions", toolName: "getEntity", available: true,
      contract: { params: [P_ENTITY_ID, P_PROJECT], returns: "Full decision with recommendation, alternatives, reasoning" },
    },
    {
      id: "decisions-create", label: "Create decision", description: "Record a decision, exploration, or risk",
      action: "WRITE", scope: "decisions", toolName: "createDecision", available: true,
      contract: {
        params: [
          { name: "task_id", type: "string", required: true, description: "Related entity ID (T-001, I-001, PLANNING, etc.)" },
          { name: "type", type: "string", required: true, description: "Decision type", enum: ["architecture", "implementation", "dependency", "security", "performance", "testing", "naming", "convention", "other", "exploration", "risk"] },
          { name: "issue", type: "string", required: true, description: "What is being decided" },
          { name: "recommendation", type: "string", required: true, description: "Chosen approach" },
          { name: "reasoning", type: "string", required: false, description: "Why this choice" },
          { name: "alternatives", type: "array", required: false, description: "Other options considered" },
          { name: "confidence", type: "string", required: false, description: "Confidence level", enum: ["HIGH", "MEDIUM", "LOW"] },
          P_PROJECT,
        ],
        returns: "Created decision with generated ID (D-NNN)",
      },
    },
    {
      id: "decisions-update", label: "Update decision", description: "Close, defer, or mitigate a decision",
      action: "WRITE", scope: "decisions", toolName: "updateDecision", available: true,
      contract: {
        params: [
          { name: "id", type: "string", required: true, description: "Decision ID (e.g., D-001)" },
          { name: "status", type: "string", required: false, description: "New status", enum: ["OPEN", "CLOSED", "DEFERRED", "ANALYZING", "MITIGATED", "ACCEPTED"] },
          { name: "resolution_notes", type: "string", required: false, description: "How it was resolved" },
          { name: "mitigation_plan", type: "string", required: false, description: "For risks — how to mitigate" },
          P_PROJECT,
        ],
        returns: "Updated decision with changed fields",
      },
    },
  ],

  // ========== KNOWLEDGE ==========
  knowledge: [
    {
      id: "knowledge-list", label: "List knowledge", description: "View all knowledge objects",
      action: "READ", scope: "knowledge", toolName: "listEntities", available: true,
      contract: { params: [P_PROJECT, P_FILTERS], returns: "List of knowledge objects with id, title, category, status, version" },
    },
    {
      id: "knowledge-search", label: "Search knowledge", description: "Search knowledge by text",
      action: "READ", scope: "knowledge", toolName: "searchEntities", available: true,
      contract: { params: [P_QUERY, P_FILTERS, P_PROJECT], returns: "Matching knowledge objects (max 20)" },
    },
    {
      id: "knowledge-get", label: "Get knowledge details", description: "View knowledge with version history",
      action: "READ", scope: "knowledge", toolName: "getEntity", available: true,
      contract: { params: [P_ENTITY_ID, P_PROJECT], returns: "Full knowledge object with content, versions, linked_entities" },
    },
    {
      id: "knowledge-create", label: "Create knowledge", description: "Add a knowledge object (domain rules, patterns, context)",
      action: "WRITE", scope: "knowledge", toolName: "createKnowledge", available: true,
      contract: {
        params: [
          { name: "title", type: "string", required: true, description: "Concise title" },
          { name: "category", type: "string", required: true, description: "Knowledge category", enum: ["domain-rules", "api-reference", "architecture", "business-context", "technical-context", "code-patterns", "integration", "infrastructure"] },
          { name: "content", type: "string", required: true, description: "The knowledge content" },
          { name: "scopes", type: "array", required: false, description: "Areas this applies to" },
          { name: "tags", type: "array", required: false, description: "Searchable keywords" },
          P_PROJECT,
        ],
        returns: "Created knowledge with generated ID (K-NNN), version 1",
      },
    },
    {
      id: "knowledge-update", label: "Update knowledge", description: "Update content (creates new version), status, or metadata",
      action: "WRITE", scope: "knowledge", toolName: "updateKnowledge", available: true,
      contract: {
        params: [
          { name: "id", type: "string", required: true, description: "Knowledge ID (e.g., K-001)" },
          { name: "content", type: "string", required: false, description: "New content (creates version)" },
          { name: "change_reason", type: "string", required: false, description: "Why content changed" },
          { name: "status", type: "string", required: false, description: "New status", enum: ["DRAFT", "ACTIVE", "REVIEW_NEEDED", "DEPRECATED", "ARCHIVED"] },
          P_PROJECT,
        ],
        returns: "Updated knowledge with new version number",
      },
    },
  ],

  // ========== GUIDELINES ==========
  guidelines: [
    {
      id: "guidelines-list", label: "List guidelines", description: "View all project guidelines",
      action: "READ", scope: "guidelines", toolName: "listEntities", available: true,
      contract: { params: [P_PROJECT, P_FILTERS], returns: "List of guideline objects with id, title, scope, weight, status" },
    },
    {
      id: "guidelines-search", label: "Search guidelines", description: "Search guidelines by text",
      action: "READ", scope: "guidelines", toolName: "searchEntities", available: true,
      contract: { params: [P_QUERY, P_FILTERS, P_PROJECT], returns: "Matching guidelines (max 20)" },
    },
    {
      id: "guidelines-get", label: "Get guideline details", description: "View full guideline with rationale",
      action: "READ", scope: "guidelines", toolName: "getEntity", available: true,
      contract: { params: [P_ENTITY_ID, P_PROJECT], returns: "Full guideline with content, rationale, examples, weight" },
    },
    {
      id: "guidelines-create", label: "Create guideline", description: "Add a project standard or convention",
      action: "WRITE", scope: "guidelines", toolName: "createGuideline", available: true,
      contract: {
        params: [
          { name: "title", type: "string", required: true, description: "Concise guideline name" },
          { name: "scope", type: "string", required: true, description: "Area (backend, frontend, testing, etc.)" },
          { name: "content", type: "string", required: true, description: "The guideline text" },
          { name: "weight", type: "string", required: false, description: "Priority", enum: ["must", "should", "may"] },
          { name: "rationale", type: "string", required: false, description: "Why this guideline exists" },
          { name: "derived_from", type: "string", required: false, description: "Objective ID if derived (O-001)" },
          P_PROJECT,
        ],
        returns: "Created guideline with generated ID (G-NNN)",
      },
    },
    {
      id: "guidelines-update", label: "Update guideline", description: "Update content, status, or weight",
      action: "WRITE", scope: "guidelines", toolName: "updateGuideline", available: true,
      contract: {
        params: [
          { name: "id", type: "string", required: true, description: "Guideline ID (e.g., G-001)" },
          { name: "content", type: "string", required: false, description: "New guideline text" },
          { name: "status", type: "string", required: false, description: "New status", enum: ["ACTIVE", "DEPRECATED"] },
          { name: "weight", type: "string", required: false, description: "New weight", enum: ["must", "should", "may"] },
          P_PROJECT,
        ],
        returns: "Updated guideline with changed fields",
      },
    },
  ],

  // ========== LESSONS ==========
  lessons: [
    {
      id: "lessons-list", label: "List lessons", description: "View all lessons learned",
      action: "READ", scope: "lessons", toolName: "listEntities", available: true,
      contract: { params: [P_PROJECT, P_FILTERS], returns: "List of lesson objects with id, title, category, severity" },
    },
    {
      id: "lessons-search", label: "Search lessons", description: "Search lessons by text",
      action: "READ", scope: "lessons", toolName: "searchEntities", available: true,
      contract: { params: [P_QUERY, P_FILTERS, P_PROJECT], returns: "Matching lessons (max 20)" },
    },
    {
      id: "lessons-get", label: "Get lesson details", description: "View full lesson with context",
      action: "READ", scope: "lessons", toolName: "getEntity", available: true,
      contract: { params: [P_ENTITY_ID, P_PROJECT], returns: "Full lesson with detail, task_id, decision_ids, severity" },
    },
    {
      id: "lessons-create", label: "Record lesson", description: "Record a lesson learned from project execution",
      action: "WRITE", scope: "lessons", toolName: "createLesson", available: true,
      contract: {
        params: [
          { name: "category", type: "string", required: true, description: "Lesson category", enum: ["pattern-discovered", "mistake-avoided", "decision-validated", "decision-reversed", "tool-insight", "architecture-lesson", "process-improvement", "market-insight"] },
          { name: "title", type: "string", required: true, description: "Concise actionable title" },
          { name: "detail", type: "string", required: true, description: "Explain WHY this matters" },
          { name: "severity", type: "string", required: false, description: "Importance level", enum: ["critical", "important", "minor"] },
          { name: "task_id", type: "string", required: false, description: "Related task ID" },
          { name: "tags", type: "array", required: false, description: "Searchable keywords" },
          P_PROJECT,
        ],
        returns: "Created lesson with generated ID (L-NNN)",
      },
    },
  ],

  // ========== CHANGES ==========
  changes: [
    {
      id: "changes-list", label: "List changes", description: "View all recorded file changes",
      action: "READ", scope: "changes", toolName: "listEntities", available: true,
      contract: { params: [P_PROJECT, P_FILTERS], returns: "List of change records with id, task_id, file, action, summary" },
    },
    {
      id: "changes-search", label: "Search changes", description: "Search changes by text",
      action: "READ", scope: "changes", toolName: "searchEntities", available: true,
      contract: { params: [P_QUERY, P_FILTERS, P_PROJECT], returns: "Matching change records (max 20)" },
    },
    {
      id: "changes-get", label: "Get change details", description: "View full change with reasoning trace",
      action: "READ", scope: "changes", toolName: "getEntity", available: true,
      contract: { params: [P_ENTITY_ID, P_PROJECT], returns: "Full change with reasoning_trace, decision_ids, guidelines_checked" },
    },
    {
      id: "changes-record", label: "Record change", description: "Record a file change for audit trail",
      action: "WRITE", scope: "changes", toolName: "recordChange", available: true,
      contract: {
        params: [
          { name: "task_id", type: "string", required: true, description: "Related task ID (T-001)" },
          { name: "file", type: "string", required: true, description: "Relative file path" },
          { name: "action", type: "string", required: true, description: "Change type", enum: ["create", "edit", "delete", "rename", "move"] },
          { name: "summary", type: "string", required: true, description: "What was changed and why" },
          { name: "decision_ids", type: "array", required: false, description: "Related decision IDs" },
          { name: "guidelines_checked", type: "array", required: false, description: "Guideline IDs verified" },
          P_PROJECT,
        ],
        returns: "Recorded change with generated ID (C-NNN)",
      },
    },
  ],

  // ========== AC TEMPLATES ==========
  ac_templates: [
    {
      id: "ac-templates-list", label: "List AC templates", description: "View all acceptance criteria templates",
      action: "READ", scope: "ac_templates", toolName: "listEntities", available: true,
      contract: { params: [P_PROJECT, P_FILTERS], returns: "List of AC templates with id, title, category, usage_count" },
    },
    {
      id: "ac-templates-search", label: "Search AC templates", description: "Search templates by text",
      action: "READ", scope: "ac_templates", toolName: "searchEntities", available: true,
      contract: { params: [P_QUERY, P_FILTERS, P_PROJECT], returns: "Matching templates (max 20)" },
    },
    {
      id: "ac-templates-get", label: "Get AC template", description: "View template with parameters and usage",
      action: "READ", scope: "ac_templates", toolName: "getEntity", available: true,
      contract: { params: [P_ENTITY_ID, P_PROJECT], returns: "Full template with template text, parameters, usage_count" },
    },
  ],

  // ========== RESEARCH ==========
  research: [
    {
      id: "research-list", label: "List research", description: "View all research objects",
      action: "READ", scope: "research", toolName: "listEntities", available: true,
      contract: { params: [P_PROJECT, P_FILTERS], returns: "List of research objects with id, title, category, status, linked_entity" },
    },
    {
      id: "research-search", label: "Search research", description: "Search research by text",
      action: "READ", scope: "research", toolName: "searchEntities", available: true,
      contract: { params: [P_QUERY, P_FILTERS, P_PROJECT], returns: "Matching research objects (max 20)" },
    },
    {
      id: "research-get", label: "Get research details", description: "View research with findings and decisions",
      action: "READ", scope: "research", toolName: "getEntity", available: true,
      contract: { params: [P_ENTITY_ID, P_PROJECT], returns: "Full research with key_findings, decision_ids, file_path" },
    },
  ],

  // ========== PROJECTS ==========
  projects: [
    {
      id: "projects-list", label: "List projects", description: "View all projects with status",
      action: "READ", scope: "projects", toolName: "listEntities", available: true,
      contract: { params: [P_FILTERS], returns: "List of projects" },
    },
    {
      id: "projects-overview", label: "Project overview", description: "Get project goal, task counts, status breakdown",
      action: "READ", scope: "projects", toolName: "getProject", available: true,
      contract: {
        params: [{ name: "slug", type: "string", required: true, description: "Project slug" }],
        returns: "Project goal, task_count, status_counts breakdown",
      },
    },
  ],

  // ========== DASHBOARD ==========
  dashboard: [
    {
      id: "dashboard-projects", label: "List projects", description: "View all projects for dashboard",
      action: "READ", scope: "dashboard", toolName: "listEntities", available: true,
      contract: { params: [P_FILTERS], returns: "List of projects" },
    },
    {
      id: "dashboard-overview", label: "Project overview", description: "Get project status for dashboard view",
      action: "READ", scope: "dashboard", toolName: "getProject", available: true,
      contract: {
        params: [{ name: "slug", type: "string", required: true, description: "Project slug" }],
        returns: "Project goal, task_count, status_counts breakdown",
      },
    },
  ],
};

// ---------------------------------------------------------------------------
// All known scope names (used for iteration)
// ---------------------------------------------------------------------------

export const ALL_SCOPES = Object.keys(CAPABILITY_CONTRACTS);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Get merged capabilities for a list of scopes (deduped by id).
 */
export function getCapabilitiesForScopes(scopes: string[]): CapabilityDef[] {
  const seen = new Set<string>();
  const result: CapabilityDef[] = [];

  for (const scope of scopes) {
    const caps = CAPABILITY_CONTRACTS[scope];
    if (!caps) continue;
    for (const cap of caps) {
      if (!seen.has(cap.id)) {
        seen.add(cap.id);
        result.push(cap);
      }
    }
  }

  return result;
}

/**
 * Get the permission status for a capability given the current LLM permissions.
 */
export function getPermissionStatus(
  capability: CapabilityDef,
  permissions: Record<string, LLMModulePermission>,
): PermissionStatus {
  if (!capability.available) return "coming-soon";

  const modulePerms = permissions[capability.scope];
  if (!modulePerms) return "enabled"; // no restriction configured

  const actionKey = capability.action.toLowerCase() as keyof LLMModulePermission;
  if (!modulePerms[actionKey]) return "no-permission";

  return "enabled";
}
