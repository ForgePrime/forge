import { z } from "zod";

const decisionType = z.enum([
  "architecture", "implementation", "dependency", "security",
  "performance", "testing", "naming", "convention", "constraint",
  "business", "strategy", "other", "exploration", "risk",
]);
const decisionStatus = z.enum(["OPEN", "CLOSED", "DEFERRED", "ANALYZING", "MITIGATED", "ACCEPTED"]);
const confidence = z.enum(["HIGH", "MEDIUM", "LOW"]);

export const decisionCreateSchema = z.object({
  task_id: z.string().min(1, "Task ID is required"),
  type: decisionType.default("implementation"),
  issue: z.string().min(1, "Issue description is required"),
  recommendation: z.string().min(1, "Recommendation is required"),
  reasoning: z.string().optional(),
  alternatives: z.array(z.string()).optional(),
  confidence: confidence.default("MEDIUM"),
  status: decisionStatus.default("OPEN"),
  decided_by: z.enum(["claude", "user", "imported"]).default("user"),
  file: z.string().optional(),
  scope: z.string().optional(),
  tags: z.array(z.string()).optional(),
  // Exploration fields
  exploration_type: z.string().optional(),
  findings: z.array(z.unknown()).optional(),
  options: z.array(z.unknown()).optional(),
  open_questions: z.array(z.string()).optional(),
  blockers: z.array(z.string()).optional(),
  ready_for_tracker: z.boolean().optional(),
  evidence_refs: z.array(z.string()).optional(),
  // Risk fields
  severity: z.string().optional(),
  likelihood: z.string().optional(),
  mitigation_plan: z.string().optional(),
  resolution_notes: z.string().optional(),
  linked_entity_type: z.string().optional(),
  linked_entity_id: z.string().optional(),
});

export const decisionUpdateSchema = z.object({
  status: decisionStatus.optional(),
  recommendation: z.string().optional(),
  reasoning: z.string().optional(),
  decided_by: z.enum(["claude", "user", "imported"]).optional(),
  resolution_notes: z.string().optional(),
});

export type DecisionCreateForm = z.infer<typeof decisionCreateSchema>;
export type DecisionUpdateForm = z.infer<typeof decisionUpdateSchema>;
