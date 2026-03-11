import { z } from "zod";

export const gateCreateSchema = z.object({
  name: z.string().min(1, "Gate name is required"),
  command: z.string().min(1, "Command is required"),
  required: z.boolean().default(true),
});

export type GateCreateForm = z.infer<typeof gateCreateSchema>;
