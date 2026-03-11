"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { taskCreateSchema, type TaskCreateForm } from "@/lib/schemas/task";
import { createTask, updateTask } from "@/stores/taskStore";
import { parseValidationErrors, fieldErrorsToRecord } from "@/lib/utils/apiErrors";
import { FormDrawer } from "./FormDrawer";
import { TextField } from "./TextField";
import { TextAreaField } from "./TextAreaField";
import { SelectField, type SelectOption } from "./SelectField";
import { MultiSelectField } from "./MultiSelectField";
import { EntityRefField } from "./EntityRefField";
import { DynamicListField } from "./DynamicListField";
import { FormErrorSummary } from "./FormErrorSummary";
import type { Task } from "@/lib/types";
import type { FieldError } from "@/lib/utils/apiErrors";

const TYPE_OPTIONS: SelectOption[] = [
  { value: "feature", label: "Feature" },
  { value: "bug", label: "Bug" },
  { value: "chore", label: "Chore" },
  { value: "investigation", label: "Investigation" },
];

const SCOPE_OPTIONS: SelectOption[] = [
  { value: "frontend", label: "Frontend" },
  { value: "backend", label: "Backend" },
  { value: "database", label: "Database" },
  { value: "infrastructure", label: "Infrastructure" },
  { value: "testing", label: "Testing" },
  { value: "ux", label: "UX" },
  { value: "performance", label: "Performance" },
  { value: "security", label: "Security" },
];

interface TaskFormProps {
  slug: string;
  open: boolean;
  onClose: () => void;
  task?: Task;
  onSuccess?: () => void;
}

export function TaskForm({ slug, open, onClose, task, onSuccess }: TaskFormProps) {
  const isEdit = !!task;
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);

  const { control, handleSubmit, setError, reset } = useForm<TaskCreateForm>({
    resolver: zodResolver(taskCreateSchema),
    defaultValues: task
      ? {
          name: task.name,
          description: task.description || "",
          instruction: task.instruction || "",
          type: task.type,
          depends_on: task.depends_on || [],
          blocked_by_decisions: task.blocked_by_decisions || [],
          conflicts_with: task.conflicts_with || [],
          acceptance_criteria: task.acceptance_criteria || [],
          scopes: task.scopes || [],
          parallel: task.parallel || false,
        }
      : {
          name: "",
          description: "",
          instruction: "",
          type: "feature",
          depends_on: [],
          blocked_by_decisions: [],
          conflicts_with: [],
          acceptance_criteria: [],
          scopes: [],
          parallel: false,
        },
  });

  const onSubmit = handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      if (isEdit) {
        await updateTask(slug, task.id, {
          name: data.name,
          description: data.description,
          instruction: data.instruction,
          blocked_by_decisions: data.blocked_by_decisions,
        });
      } else {
        await createTask(slug, [data]);
      }
      reset();
      onSuccess?.();
      onClose();
    } catch (e) {
      const errors = parseValidationErrors(e);
      if (errors.length > 0) {
        setApiErrors(errors);
        const record = fieldErrorsToRecord(errors);
        for (const [field, message] of Object.entries(record)) {
          setError(field as keyof TaskCreateForm, { message });
        }
      } else {
        setApiErrors([{ field: "general", message: (e as Error).message }]);
      }
    } finally {
      setSubmitting(false);
    }
  });

  return (
    <FormDrawer
      open={open}
      onClose={onClose}
      title={isEdit ? `Edit ${task.id}` : "Create Task"}
      onSubmit={onSubmit}
      submitting={submitting}
      submitLabel={isEdit ? "Update" : "Create"}
    >
      <FormErrorSummary errors={apiErrors} />

      <TextField name="name" control={control} label="Name" required placeholder="Task name" />
      <TextAreaField name="description" control={control} label="Description" placeholder="What needs to be done?" />
      <TextAreaField name="instruction" control={control} label="Instruction" placeholder="Step-by-step instructions" rows={6} />
      <SelectField name="type" control={control} label="Type" options={TYPE_OPTIONS} />
      <MultiSelectField name="scopes" control={control} label="Scopes" options={SCOPE_OPTIONS} />
      <DynamicListField name="acceptance_criteria" control={control} label="Acceptance Criteria" addLabel="Add criterion" placeholder="When X, then Y" />

      {!isEdit && (
        <>
          <EntityRefField name="depends_on" control={control} label="Depends On" entityTypes={["task"]} placeholder="Search tasks..." />
          <EntityRefField name="blocked_by_decisions" control={control} label="Blocked By Decisions" entityTypes={["decision"]} placeholder="Search decisions..." />
          <EntityRefField name="conflicts_with" control={control} label="Conflicts With" entityTypes={["task"]} placeholder="Search tasks..." />

          <div className="mb-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-forge-600 focus:ring-forge-500"
                onChange={(e) => {
                  const form = control._formValues as TaskCreateForm;
                  form.parallel = e.target.checked;
                }}
              />
              <span className="text-gray-700">Can run in parallel</span>
            </label>
          </div>
        </>
      )}
    </FormDrawer>
  );
}
