import { z } from "zod";

const taskType = z.enum(["feature", "bug", "chore", "investigation"]);
const taskStatus = z.enum(["TODO", "IN_PROGRESS", "DONE", "FAILED", "SKIPPED", "CLAIMING"]);

export const taskCreateSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
  instruction: z.string().optional(),
  type: taskType.default("feature"),
  depends_on: z.array(z.string()).optional(),
  blocked_by_decisions: z.array(z.string()).optional(),
  conflicts_with: z.array(z.string()).optional(),
  acceptance_criteria: z.array(z.string()).optional(),
  scopes: z.array(z.string()).optional(),
  parallel: z.boolean().optional(),
  skill: z.string().nullable().optional(),
});

export const taskUpdateSchema = z.object({
  name: z.string().min(1).optional(),
  description: z.string().optional(),
  instruction: z.string().optional(),
  status: taskStatus.optional(),
  failed_reason: z.string().optional(),
  blocked_by_decisions: z.array(z.string()).optional(),
});

export type TaskCreateForm = z.infer<typeof taskCreateSchema>;
export type TaskUpdateForm = z.infer<typeof taskUpdateSchema>;
