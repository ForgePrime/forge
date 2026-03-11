import { z } from "zod";

const acTemplateCategory = z.enum([
  "performance", "security", "quality", "functionality",
  "accessibility", "reliability", "data-integrity", "ux",
]);

const parameterSchema = z.object({
  name: z.string(),
  type: z.string(),
  default: z.unknown().optional(),
  description: z.string().optional(),
});

export const acTemplateCreateSchema = z.object({
  title: z.string().min(1, "Title is required"),
  template: z.string().min(1, "Template is required"),
  category: acTemplateCategory,
  description: z.string().optional(),
  parameters: z.array(parameterSchema).optional(),
  scopes: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  verification_method: z.string().optional(),
});

export const acTemplateUpdateSchema = z.object({
  title: z.string().min(1).optional(),
  template: z.string().optional(),
  description: z.string().optional(),
  category: z.string().optional(),
  parameters: z.array(parameterSchema).optional(),
  scopes: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  verification_method: z.string().optional(),
  status: z.enum(["ACTIVE", "DEPRECATED"]).optional(),
});

export type ACTemplateCreateForm = z.infer<typeof acTemplateCreateSchema>;
export type ACTemplateUpdateForm = z.infer<typeof acTemplateUpdateSchema>;
