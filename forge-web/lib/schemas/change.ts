import { z } from "zod";

const changeAction = z.enum(["create", "edit", "delete", "rename", "move", "verify"]);

const reasoningStep = z.object({
  step: z.string(),
  detail: z.string(),
});

export const changeCreateSchema = z.object({
  task_id: z.string().min(1, "Task ID is required"),
  file: z.string().min(1, "File path is required"),
  action: changeAction,
  summary: z.string().min(1, "Summary is required"),
  reasoning_trace: z.array(reasoningStep).optional(),
  decision_ids: z.array(z.string()).optional(),
  lines_added: z.number().int().nonnegative().optional(),
  lines_removed: z.number().int().nonnegative().optional(),
  group_id: z.string().optional(),
  guidelines_checked: z.array(z.string()).optional(),
});

export type ChangeCreateForm = z.infer<typeof changeCreateSchema>;
