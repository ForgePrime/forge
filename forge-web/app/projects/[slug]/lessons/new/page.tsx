"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { lessonCreateSchema, type LessonCreateForm } from "@/lib/schemas/lesson";
import { createLesson } from "@/stores/lessonStore";
import { CreatePageLayout } from "@/components/forms/CreatePageLayout";
import { TextField } from "@/components/forms/TextField";
import { TextAreaField } from "@/components/forms/TextAreaField";
import { SelectField, type SelectOption } from "@/components/forms/SelectField";
import { DynamicListField } from "@/components/forms/DynamicListField";
import { FormErrorSummary } from "@/components/forms/FormErrorSummary";
import { parseValidationErrors } from "@/lib/utils/apiErrors";
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

export default function NewLessonPage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);

  const { control, handleSubmit } = useForm<LessonCreateForm>({
    resolver: zodResolver(lessonCreateSchema),
    defaultValues: {
      title: "",
      detail: "",
      category: "pattern-discovered",
      severity: "important",
      task_id: "",
      applies_to: "",
      decision_ids: [],
      tags: [],
    },
  });

  const onSubmit = handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      const ids = await createLesson(slug, [data]);
      router.push(`/projects/${slug}/lessons/${ids[0]}`);
    } catch (e) {
      const errors = parseValidationErrors(e);
      if (errors.length > 0) {
        setApiErrors(errors);
      } else {
        setApiErrors([{ field: "general", message: (e as Error).message }]);
      }
    } finally {
      setSubmitting(false);
    }
  });

  return (
    <CreatePageLayout
      title="New Lesson"
      backHref={`/projects/${slug}/lessons`}
      submitting={submitting}
      onSubmit={onSubmit}
    >
      <FormErrorSummary errors={apiErrors} />

      <TextField name="title" control={control} label="Title" required placeholder="Lesson title" />
      <TextAreaField name="detail" control={control} label="Detail" required placeholder="What was learned?" rows={6} />
      <SelectField name="category" control={control} label="Category" options={CATEGORY_OPTIONS} />
      <SelectField name="severity" control={control} label="Severity" options={SEVERITY_OPTIONS} />
      <TextField name="task_id" control={control} label="Task ID" placeholder="T-001" />
      <DynamicListField name="decision_ids" control={control} label="Decision IDs" addLabel="Add decision ID" placeholder="D-001" />
      <TextField name="applies_to" control={control} label="Applies To" placeholder="e.g., all backend services" />
      <DynamicListField name="tags" control={control} label="Tags" addLabel="Add tag" />
    </CreatePageLayout>
  );
}
