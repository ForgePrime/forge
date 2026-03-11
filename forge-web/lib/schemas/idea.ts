import { z } from "zod";

const ideaCategory = z.enum([
  "feature", "improvement", "experiment", "migration",
  "refactor", "infrastructure", "business-opportunity", "research",
]);
const ideaStatus = z.enum(["DRAFT", "EXPLORING", "APPROVED", "REJECTED", "COMMITTED"]);
const priority = z.enum(["HIGH", "MEDIUM", "LOW"]);

export const ideaCreateSchema = z.object({
  title: z.string().min(1, "Title is required"),
  description: z.string().optional(),
  category: ideaCategory,
  priority: priority,
  tags: z.array(z.string()).optional(),
  parent_id: z.string().optional(),
  related_ideas: z.array(z.string()).optional(),
  guidelines: z.array(z.string()).optional(),
  relations: z.array(z.record(z.string(), z.unknown())).optional(),
  scopes: z.array(z.string()).optional(),
  advances_key_results: z.array(z.string()).optional(),
  knowledge_ids: z.array(z.string()).optional(),
});

export const ideaUpdateSchema = z.object({
  title: z.string().min(1).optional(),
  description: z.string().optional(),
  status: ideaStatus.optional(),
  category: ideaCategory.optional(),
  priority: priority.optional(),
  rejection_reason: z.string().optional(),
  merged_into: z.string().optional(),
  tags: z.array(z.string()).optional(),
  related_ideas: z.array(z.string()).optional(),
  guidelines: z.array(z.string()).optional(),
  exploration_notes: z.string().optional(),
  parent_id: z.string().optional(),
  relations: z.array(z.record(z.string(), z.unknown())).optional(),
  scopes: z.array(z.string()).optional(),
  advances_key_results: z.array(z.string()).optional(),
  knowledge_ids: z.array(z.string()).optional(),
});

export type IdeaCreateForm = z.infer<typeof ideaCreateSchema>;
export type IdeaUpdateForm = z.infer<typeof ideaUpdateSchema>;
