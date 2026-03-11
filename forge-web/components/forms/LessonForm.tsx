"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { lessonCreateSchema, type LessonCreateForm } from "@/lib/schemas/lesson";
import { createLesson } from "@/stores/lessonStore";
import { parseValidationErrors, fieldErrorsToRecord } from "@/lib/utils/apiErrors";
import { FormDrawer } from "./FormDrawer";
import { TextField } from "./TextField";
import { TextAreaField } from "./TextAreaField";
import { SelectField, type SelectOption } from "./SelectField";
import { FormErrorSummary } from "./FormErrorSummary";
import type { FieldError } from "@/lib/utils/apiErrors";

const CATEGORY_OPTIONS: SelectOption[] = [
  { value: "pattern-discovered", label: "Pattern Discovered" },
  { value: "mistake-avoided", label: "Mistake Avoided" },
  { value: "decision-validated", label: "Decision Validated" },
  { value: "decision-reversed", label: "Decision Reversed" },
  { value: "tool-insight", label: "Tool Insight" },
  { value: "architecture-lesson", label: "Architecture Lesson" },
  { value: "process-improvement", label: "Process Improvement" },
  { value: "market-insight", label: "Market Insight" },
];

const SEVERITY_OPTIONS: SelectOption[] = [
  { value: "critical", label: "Critical" },
  { value: "important", label: "Important" },
  { value: "minor", label: "Minor" },
];

function getDefaults(): LessonCreateForm {
  return {
    title: "",
    detail: "",
    category: "pattern-discovered",
    severity: "minor",
    task_id: "",
    tags: [],
  };
}

interface LessonFormProps {
  slug: string;
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function LessonForm({ slug, open, onClose, onSuccess }: LessonFormProps) {
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);

  const { control, handleSubmit, setError, reset } = useForm<LessonCreateForm>({
    resolver: zodResolver(lessonCreateSchema),
    defaultValues: getDefaults(),
  });

  useEffect(() => {
    if (open) {
      reset(getDefaults());
      setApiErrors([]);
    }
  }, [open, reset]);

  const onSubmit = handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      await createLesson(slug, [data]);
      reset(getDefaults());
      onSuccess?.();
      onClose();
    } catch (e) {
      const errors = parseValidationErrors(e);
      if (errors.length > 0) {
        setApiErrors(errors);
        const record = fieldErrorsToRecord(errors);
        for (const [field, message] of Object.entries(record)) {
          setError(field as keyof LessonCreateForm, { message });
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
      title="Record Lesson"
      onSubmit={onSubmit}
      submitting={submitting}
      submitLabel="Record"
    >
      <FormErrorSummary errors={apiErrors} />

      <TextField name="title" control={control} label="Title" required placeholder="What did you learn?" />
      <TextAreaField name="detail" control={control} label="Detail" required placeholder="Describe the lesson in detail..." rows={6} />
      <SelectField name="category" control={control} label="Category" options={CATEGORY_OPTIONS} />
      <SelectField name="severity" control={control} label="Severity" options={SEVERITY_OPTIONS} />
      <TextField name="task_id" control={control} label="Related Task" placeholder="T-001 (optional)" />
    </FormDrawer>
  );
}
