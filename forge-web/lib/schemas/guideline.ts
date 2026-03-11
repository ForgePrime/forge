import { z } from "zod";

const guidelineWeight = z.enum(["must", "should", "may"]);

export const guidelineCreateSchema = z.object({
  title: z.string().min(1, "Title is required"),
  scope: z.string().min(1, "Scope is required"),
  content: z.string().min(1, "Content is required"),
  rationale: z.string().optional(),
  examples: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  weight: guidelineWeight.default("should"),
});

export const guidelineUpdateSchema = z.object({
  title: z.string().min(1).optional(),
  content: z.string().optional(),
  status: z.enum(["ACTIVE", "DEPRECATED"]).optional(),
  rationale: z.string().optional(),
  scope: z.string().optional(),
  examples: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  weight: guidelineWeight.optional(),
  derived_from: z.string().optional(),
});

export type GuidelineCreateForm = z.infer<typeof guidelineCreateSchema>;
export type GuidelineUpdateForm = z.infer<typeof guidelineUpdateSchema>;
