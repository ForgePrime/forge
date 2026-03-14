"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ideaCreateSchema, type IdeaCreateForm } from "@/lib/schemas/idea";
import { createIdea } from "@/stores/ideaStore";
import { CreatePageLayout } from "@/components/forms/CreatePageLayout";
import { TextField } from "@/components/forms/TextField";
import { TextAreaField } from "@/components/forms/TextAreaField";
import { SelectField, type SelectOption } from "@/components/forms/SelectField";
import { DynamicListField } from "@/components/forms/DynamicListField";
import { EntityRefField } from "@/components/forms/EntityRefField";
import { FormErrorSummary } from "@/components/forms/FormErrorSummary";
import { parseValidationErrors } from "@/lib/utils/apiErrors";
import type { FieldError } from "@/lib/utils/apiErrors";

const CATEGORY_OPTIONS: SelectOption[] = [
  { value: "feature", label: "Feature" },
  { value: "improvement", label: "Improvement" },
  { value: "experiment", label: "Experiment" },
  { value: "migration", label: "Migration" },
  { value: "refactor", label: "Refactor" },
  { value: "infrastructure", label: "Infrastructure" },
  { value: "business-opportunity", label: "Business Opportunity" },
  { value: "research", label: "Research" },
];

const PRIORITY_OPTIONS: SelectOption[] = [
  { value: "LOW", label: "Low" },
  { value: "MEDIUM", label: "Medium" },
  { value: "HIGH", label: "High" },
];

export default function NewIdeaPage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);

  const { control, handleSubmit } = useForm<IdeaCreateForm>({
    resolver: zodResolver(ideaCreateSchema),
    defaultValues: {
      title: "",
      description: "",
      category: "feature",
      priority: "MEDIUM",
      scopes: [],
      tags: [],
      advances_key_results: [],
      parent_id: "",
    },
  });

  const onSubmit = handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      const ids = await createIdea(slug, [data]);
      router.push(`/projects/${slug}/ideas/${ids[0]}`);
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
      title="New Idea"
      backHref={`/projects/${slug}/ideas`}
      submitting={submitting}
      onSubmit={onSubmit}
    >
      <FormErrorSummary errors={apiErrors} />

      <TextField name="title" control={control} label="Title" required placeholder="Idea title" />
      <TextAreaField name="description" control={control} label="Description" placeholder="Describe the idea..." />
      <SelectField name="category" control={control} label="Category" options={CATEGORY_OPTIONS} />
      <SelectField name="priority" control={control} label="Priority" options={PRIORITY_OPTIONS} />
      <DynamicListField name="scopes" control={control} label="Scopes" addLabel="Add scope" />
      <DynamicListField name="tags" control={control} label="Tags" addLabel="Add tag" />
      <DynamicListField name="advances_key_results" control={control} label="Advances Key Results" addLabel="Add KR reference" placeholder="O-001/KR-1" />
      <EntityRefField name="parent_id" control={control} label="Parent Idea" entityTypes={["idea"]} multiple={false} placeholder="Search ideas..." />
    </CreatePageLayout>
  );
}
