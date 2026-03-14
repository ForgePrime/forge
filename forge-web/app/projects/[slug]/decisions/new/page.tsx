"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { decisionCreateSchema, type DecisionCreateForm } from "@/lib/schemas/decision";
import { createDecision } from "@/stores/decisionStore";
import { CreatePageLayout } from "@/components/forms/CreatePageLayout";
import { TextField } from "@/components/forms/TextField";
import { TextAreaField } from "@/components/forms/TextAreaField";
import { SelectField, type SelectOption } from "@/components/forms/SelectField";
import { DynamicListField } from "@/components/forms/DynamicListField";
import { FormErrorSummary } from "@/components/forms/FormErrorSummary";
import { parseValidationErrors } from "@/lib/utils/apiErrors";
import type { FieldError } from "@/lib/utils/apiErrors";

const TYPE_OPTIONS: SelectOption[] = [
  { value: "architecture", label: "Architecture" },
  { value: "implementation", label: "Implementation" },
  { value: "dependency", label: "Dependency" },
  { value: "security", label: "Security" },
  { value: "performance", label: "Performance" },
  { value: "testing", label: "Testing" },
  { value: "naming", label: "Naming" },
  { value: "convention", label: "Convention" },
  { value: "constraint", label: "Constraint" },
  { value: "business", label: "Business" },
  { value: "strategy", label: "Strategy" },
  { value: "other", label: "Other" },
  { value: "exploration", label: "Exploration" },
  { value: "risk", label: "Risk" },
];

const CONFIDENCE_OPTIONS: SelectOption[] = [
  { value: "LOW", label: "Low" },
  { value: "MEDIUM", label: "Medium" },
  { value: "HIGH", label: "High" },
];

const STATUS_OPTIONS: SelectOption[] = [
  { value: "OPEN", label: "Open" },
  { value: "CLOSED", label: "Closed" },
  { value: "DEFERRED", label: "Deferred" },
  { value: "ANALYZING", label: "Analyzing" },
  { value: "MITIGATED", label: "Mitigated" },
  { value: "ACCEPTED", label: "Accepted" },
];

const LINKED_ENTITY_TYPE_OPTIONS: SelectOption[] = [
  { value: "", label: "None" },
  { value: "objective", label: "Objective" },
  { value: "idea", label: "Idea" },
  { value: "task", label: "Task" },
];

const SEVERITY_OPTIONS: SelectOption[] = [
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

const LIKELIHOOD_OPTIONS: SelectOption[] = [
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

export default function NewDecisionPage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);

  const { control, handleSubmit, watch } = useForm<DecisionCreateForm>({
    resolver: zodResolver(decisionCreateSchema),
    defaultValues: {
      task_id: "",
      type: "implementation",
      issue: "",
      recommendation: "",
      reasoning: "",
      alternatives: [],
      confidence: "MEDIUM",
      status: "OPEN",
      scope: "",
      tags: [],
      linked_entity_type: "",
      linked_entity_id: "",
      severity: "",
      likelihood: "",
      mitigation_plan: "",
      exploration_type: "",
      open_questions: [],
      blockers: [],
    },
  });

  const watchedType = watch("type");

  const onSubmit = handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      const ids = await createDecision(slug, [data]);
      router.push(`/projects/${slug}/decisions/${ids[0]}`);
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
      title="New Decision"
      backHref={`/projects/${slug}/decisions`}
      submitting={submitting}
      onSubmit={onSubmit}
    >
      <FormErrorSummary errors={apiErrors} />

      <TextField name="task_id" control={control} label="Task ID" required placeholder="T-001" />
      <SelectField name="type" control={control} label="Type" options={TYPE_OPTIONS} required />
      <TextAreaField name="issue" control={control} label="Issue" required placeholder="What is the issue or question?" />
      <TextAreaField name="recommendation" control={control} label="Recommendation" required placeholder="What do you recommend?" />
      <TextAreaField name="reasoning" control={control} label="Reasoning" placeholder="Why this recommendation?" />
      <DynamicListField name="alternatives" control={control} label="Alternatives" addLabel="Add alternative" placeholder="Alternative option..." />
      <SelectField name="confidence" control={control} label="Confidence" options={CONFIDENCE_OPTIONS} />
      <SelectField name="status" control={control} label="Status" options={STATUS_OPTIONS} />
      <TextField name="scope" control={control} label="Scope" placeholder="e.g., backend" />
      <DynamicListField name="tags" control={control} label="Tags" addLabel="Add tag" />
      <SelectField name="linked_entity_type" control={control} label="Linked Entity Type" options={LINKED_ENTITY_TYPE_OPTIONS} placeholder="None" />
      <TextField name="linked_entity_id" control={control} label="Linked Entity ID" placeholder="O-001" />

      {watchedType === "risk" && (
        <>
          <SelectField name="severity" control={control} label="Severity" options={SEVERITY_OPTIONS} />
          <SelectField name="likelihood" control={control} label="Likelihood" options={LIKELIHOOD_OPTIONS} />
          <TextAreaField name="mitigation_plan" control={control} label="Mitigation Plan" placeholder="How will this risk be mitigated?" />
        </>
      )}

      {watchedType === "exploration" && (
        <>
          <TextField name="exploration_type" control={control} label="Exploration Type" placeholder="e.g., domain, architecture, feasibility" />
          <DynamicListField name="open_questions" control={control} label="Open Questions" addLabel="Add question" placeholder="What needs to be answered?" />
          <DynamicListField name="blockers" control={control} label="Blockers" addLabel="Add blocker" placeholder="What blocks progress?" />
        </>
      )}
    </CreatePageLayout>
  );
}
