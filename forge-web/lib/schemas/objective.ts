import { z } from "zod";

const objectiveStatus = z.enum(["ACTIVE", "ACHIEVED", "ABANDONED", "PAUSED"]);

export const keyResultSchema = z.object({
  metric: z.string().min(1, "Metric is required"),
  baseline: z.number().optional(),
  target: z.number({ error: "Target is required" }),
  current: z.number().optional(),
});

export const objectiveCreateSchema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().min(1, "Description is required"),
  key_results: z.array(keyResultSchema).min(1, "At least one key result is required"),
  appetite: z.enum(["small", "medium", "large"]),
  scope: z.enum(["project", "cross-project"]),
  assumptions: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  scopes: z.array(z.string()).optional(),
  derived_guidelines: z.array(z.string()).optional(),
  knowledge_ids: z.array(z.string()).optional(),
});

export const objectiveUpdateSchema = z.object({
  title: z.string().min(1).optional(),
  description: z.string().optional(),
  status: objectiveStatus.optional(),
  appetite: z.enum(["small", "medium", "large"]).optional(),
  assumptions: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  key_results: z.array(keyResultSchema).optional(),
  scopes: z.array(z.string()).optional(),
  derived_guidelines: z.array(z.string()).optional(),
  knowledge_ids: z.array(z.string()).optional(),
});

export type KeyResultForm = z.infer<typeof keyResultSchema>;
export type ObjectiveCreateForm = z.infer<typeof objectiveCreateSchema>;
export type ObjectiveUpdateForm = z.infer<typeof objectiveUpdateSchema>;
