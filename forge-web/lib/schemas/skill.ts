import { z } from "zod";

const skillCategory = z.enum([
  "workflow", "analysis", "generation", "validation",
  "integration", "refactoring", "testing", "deployment",
  "documentation", "custom",
]);

const skillStatus = z.enum(["DRAFT", "ACTIVE", "DEPRECATED", "ARCHIVED"]);

export const skillCreateSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
  category: skillCategory.optional(),
  skill_md_content: z.string().optional(),
  tags: z.array(z.string()).optional(),
  scopes: z.array(z.string()).optional(),
});

export const skillUpdateSchema = z.object({
  name: z.string().min(1).optional(),
  description: z.string().optional(),
  category: skillCategory.optional(),
  status: skillStatus.optional(),
  skill_md_content: z.string().optional(),
  tags: z.array(z.string()).optional(),
  scopes: z.array(z.string()).optional(),
});

export type SkillCreateForm = z.infer<typeof skillCreateSchema>;
export type SkillUpdateForm = z.infer<typeof skillUpdateSchema>;
