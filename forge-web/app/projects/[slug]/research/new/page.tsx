"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { researchCreateSchema, type ResearchCreateForm } from "@/lib/schemas/research";
import { createResearch } from "@/stores/researchStore";
import { CreatePageLayout } from "@/components/forms/CreatePageLayout";
import { TextField } from "@/components/forms/TextField";
import { TextAreaField } from "@/components/forms/TextAreaField";
import { SelectField, type SelectOption } from "@/components/forms/SelectField";
import { DynamicListField } from "@/components/forms/DynamicListField";
import { FormErrorSummary } from "@/components/forms/FormErrorSummary";
import { parseValidationErrors } from "@/lib/utils/apiErrors";
import type { FieldError } from "@/lib/utils/apiErrors";

const CATEGORY_OPTIONS: SelectOption[] = [
  { value: "architecture", label: "Architecture" },
  { value: "business", label: "Business" },
  { value: "domain", label: "Domain" },
  { value: "feasibility", label: "Feasibility" },
  { value: "risk", label: "Risk" },
  { value: "technical", label: "Technical" },
];

const LINKED_ENTITY_TYPE_OPTIONS: SelectOption[] = [
  { value: "objective", label: "Objective" },
  { value: "idea", label: "Idea" },
];

export default function NewResearchPage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);

  const { control, handleSubmit } = useForm<ResearchCreateForm>({
    resolver: zodResolver(researchCreateSchema),
    defaultValues: {
      title: "",
      topic: "",
      category: "technical",
      summary: "",
      linked_entity_type: undefined,
      linked_entity_id: "",
      content: "",
      key_findings: [],
      decision_ids: [],
      scopes: [],
      tags: [],
    },
  });

  const onSubmit = handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      const cleanData = { ...data };
      if (!cleanData.linked_entity_type) delete cleanData.linked_entity_type;
      if (!cleanData.linked_entity_id) delete cleanData.linked_entity_id;
      const ids = await createResearch(slug, [cleanData]);
      router.push(`/projects/${slug}/research/${ids[0]}`);
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
      title="New Research"
      backHref={`/projects/${slug}/research`}
      submitting={submitting}
      onSubmit={onSubmit}
    >
      <FormErrorSummary errors={apiErrors} />

      <TextField name="title" control={control} label="Title" required placeholder="Research title" />
      <TextField name="topic" control={control} label="Topic" required placeholder="Research topic" />
      <SelectField name="category" control={control} label="Category" options={CATEGORY_OPTIONS} />
      <TextAreaField name="summary" control={control} label="Summary" required placeholder="Brief summary of the research" rows={4} />
      <TextAreaField name="content" control={control} label="Content (Markdown)" placeholder="Detailed research content..." rows={8} />
      <DynamicListField name="key_findings" control={control} label="Key Findings" addLabel="Add finding" />
      <DynamicListField name="decision_ids" control={control} label="Decision IDs" addLabel="Add decision ID" placeholder="D-001" />
      <SelectField name="linked_entity_type" control={control} label="Linked Entity Type" options={LINKED_ENTITY_TYPE_OPTIONS} placeholder="None" />
      <TextField name="linked_entity_id" control={control} label="Linked Entity ID" placeholder="O-001 or I-001" />
      <DynamicListField name="scopes" control={control} label="Scopes" addLabel="Add scope" />
      <DynamicListField name="tags" control={control} label="Tags" addLabel="Add tag" />
    </CreatePageLayout>
  );
}
