"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { knowledgeCreateSchema, type KnowledgeCreateForm } from "@/lib/schemas/knowledge";
import { createKnowledge } from "@/stores/knowledgeStore";
import { CreatePageLayout } from "@/components/forms/CreatePageLayout";
import { TextField } from "@/components/forms/TextField";
import { TextAreaField } from "@/components/forms/TextAreaField";
import { SelectField, type SelectOption } from "@/components/forms/SelectField";
import { DynamicListField } from "@/components/forms/DynamicListField";
import { FormErrorSummary } from "@/components/forms/FormErrorSummary";
import { parseValidationErrors } from "@/lib/utils/apiErrors";
import type { FieldError } from "@/lib/utils/apiErrors";

const CATEGORY_OPTIONS: SelectOption[] = [
  { value: "domain-rules", label: "Domain Rules" },
  { value: "api-reference", label: "API Reference" },
  { value: "architecture", label: "Architecture" },
  { value: "business-context", label: "Business Context" },
  { value: "technical-context", label: "Technical Context" },
  { value: "code-patterns", label: "Code Patterns" },
  { value: "integration", label: "Integration" },
  { value: "infrastructure", label: "Infrastructure" },
];

export default function NewKnowledgePage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);

  const { control, handleSubmit } = useForm<KnowledgeCreateForm>({
    resolver: zodResolver(knowledgeCreateSchema),
    defaultValues: {
      title: "",
      category: "domain-rules",
      content: "",
      scopes: [],
      tags: [],
      review_interval_days: undefined,
    },
  });

  const onSubmit = handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      const ids = await createKnowledge(slug, [data]);
      router.push(`/projects/${slug}/knowledge/${ids[0]}`);
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
      title="New Knowledge"
      backHref={`/projects/${slug}/knowledge`}
      submitting={submitting}
      onSubmit={onSubmit}
    >
      <FormErrorSummary errors={apiErrors} />

      <TextField name="title" control={control} label="Title" required placeholder="Knowledge title" />
      <SelectField name="category" control={control} label="Category" options={CATEGORY_OPTIONS} required />
      <TextAreaField name="content" control={control} label="Content" required placeholder="Knowledge content..." rows={8} />
      <DynamicListField name="scopes" control={control} label="Scopes" addLabel="Add scope" />
      <DynamicListField name="tags" control={control} label="Tags" addLabel="Add tag" />

      <Controller
        name="review_interval_days"
        control={control}
        render={({ field }) => (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Review Interval (days)</label>
            <input
              type="number"
              min={1}
              value={field.value ?? ""}
              onChange={(e) => field.onChange(e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="e.g. 30"
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md outline-none focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
            />
          </div>
        )}
      />
    </CreatePageLayout>
  );
}
