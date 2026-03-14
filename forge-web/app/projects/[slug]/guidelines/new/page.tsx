"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { guidelineCreateSchema, type GuidelineCreateForm } from "@/lib/schemas/guideline";
import { createGuideline } from "@/stores/guidelineStore";
import { CreatePageLayout } from "@/components/forms/CreatePageLayout";
import { TextField } from "@/components/forms/TextField";
import { TextAreaField } from "@/components/forms/TextAreaField";
import { SelectField, type SelectOption } from "@/components/forms/SelectField";
import { DynamicListField } from "@/components/forms/DynamicListField";
import { FormErrorSummary } from "@/components/forms/FormErrorSummary";
import { parseValidationErrors } from "@/lib/utils/apiErrors";
import type { FieldError } from "@/lib/utils/apiErrors";

const SCOPE_OPTIONS: SelectOption[] = [
  { value: "general", label: "General" },
  { value: "backend", label: "Backend" },
  { value: "frontend", label: "Frontend" },
  { value: "database", label: "Database" },
  { value: "api", label: "API" },
  { value: "testing", label: "Testing" },
  { value: "security", label: "Security" },
  { value: "performance", label: "Performance" },
  { value: "devops", label: "DevOps" },
  { value: "documentation", label: "Documentation" },
];

const WEIGHT_OPTIONS: SelectOption[] = [
  { value: "must", label: "Must" },
  { value: "should", label: "Should" },
  { value: "may", label: "May" },
];

export default function NewGuidelinePage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);

  const { control, handleSubmit } = useForm<GuidelineCreateForm>({
    resolver: zodResolver(guidelineCreateSchema),
    defaultValues: {
      title: "",
      scope: "general",
      content: "",
      rationale: "",
      weight: "should",
      examples: [],
      tags: [],
    },
  });

  const onSubmit = handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      const ids = await createGuideline(slug, [data]);
      router.push(`/projects/${slug}/guidelines/${ids[0]}`);
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
      title="New Guideline"
      backHref={`/projects/${slug}/guidelines`}
      submitting={submitting}
      onSubmit={onSubmit}
    >
      <FormErrorSummary errors={apiErrors} />

      <TextField name="title" control={control} label="Title" required placeholder="Guideline title" />
      <SelectField name="scope" control={control} label="Scope" options={SCOPE_OPTIONS} required />
      <SelectField name="weight" control={control} label="Weight" options={WEIGHT_OPTIONS} />
      <TextAreaField name="content" control={control} label="Content" required placeholder="Describe the guideline..." rows={6} />
      <TextAreaField name="rationale" control={control} label="Rationale" placeholder="Why is this guideline important?" />
      <DynamicListField name="examples" control={control} label="Examples" addLabel="Add example" />
      <DynamicListField name="tags" control={control} label="Tags" addLabel="Add tag" />
    </CreatePageLayout>
  );
}
