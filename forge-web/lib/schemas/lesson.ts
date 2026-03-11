import { z } from "zod";

const lessonCategory = z.enum([
  "pattern-discovered", "mistake-avoided", "decision-validated",
  "decision-reversed", "tool-insight", "architecture-lesson",
  "process-improvement", "market-insight",
]);
const lessonSeverity = z.enum(["critical", "important", "minor"]);

export const lessonCreateSchema = z.object({
  category: lessonCategory,
  title: z.string().min(1, "Title is required"),
  detail: z.string().min(1, "Detail is required"),
  task_id: z.string().optional(),
  decision_ids: z.array(z.string()).optional(),
  severity: lessonSeverity.default("minor"),
  applies_to: z.string().optional(),
  tags: z.array(z.string()).optional(),
});

export type LessonCreateForm = z.infer<typeof lessonCreateSchema>;
