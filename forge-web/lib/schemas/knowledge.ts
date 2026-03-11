import { z } from "zod";

const knowledgeCategory = z.enum([
  "domain-rules", "api-reference", "architecture", "business-context",
  "technical-context", "code-patterns", "integration", "infrastructure",
]);
const knowledgeStatus = z.enum(["DRAFT", "ACTIVE", "REVIEW_NEEDED", "DEPRECATED", "ARCHIVED"]);

export const knowledgeCreateSchema = z.object({
  title: z.string().min(1, "Title is required"),
  category: knowledgeCategory,
  content: z.string().min(1, "Content is required"),
  scopes: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  source: z.record(z.string(), z.unknown()).nullable().optional(),
  linked_entities: z.array(z.record(z.string(), z.unknown())).optional(),
  dependencies: z.array(z.string()).optional(),
  review_interval_days: z.number().int().positive().optional(),
  created_by: z.enum(["user", "ai"]).default("user"),
});

export const knowledgeUpdateSchema = z.object({
  title: z.string().min(1).optional(),
  content: z.string().optional(),
  status: knowledgeStatus.optional(),
  category: knowledgeCategory.optional(),
  scopes: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  source: z.record(z.string(), z.unknown()).nullable().optional(),
  dependencies: z.array(z.string()).optional(),
  review_interval_days: z.number().int().positive().optional(),
  change_reason: z.string().optional(),
  changed_by: z.enum(["user", "ai"]).optional(),
});

export type KnowledgeCreateForm = z.infer<typeof knowledgeCreateSchema>;
export type KnowledgeUpdateForm = z.infer<typeof knowledgeUpdateSchema>;
