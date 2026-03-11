"use client";

import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { decisionCreateSchema, type DecisionCreateForm } from "@/lib/schemas/decision";
import { createDecision, updateDecision } from "@/stores/decisionStore";
import { parseValidationErrors, fieldErrorsToRecord } from "@/lib/utils/apiErrors";
import { FormDrawer } from "./FormDrawer";
import { TextField } from "./TextField";
import { TextAreaField } from "./TextAreaField";
import { SelectField, type SelectOption } from "./SelectField";
import { DynamicListField } from "./DynamicListField";
import { FormErrorSummary } from "./FormErrorSummary";
import type { Decision } from "@/lib/types";
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

const STATUS_OPTIONS: SelectOption[] = [
  { value: "OPEN", label: "Open" },
  { value: "CLOSED", label: "Closed" },
  { value: "DEFERRED", label: "Deferred" },
  { value: "ANALYZING", label: "Analyzing" },
  { value: "MITIGATED", label: "Mitigated" },
  { value: "ACCEPTED", label: "Accepted" },
];

const CONFIDENCE_OPTIONS: SelectOption[] = [
  { value: "HIGH", label: "High" },
  { value: "MEDIUM", label: "Medium" },
  { value: "LOW", label: "Low" },
];

const SEVERITY_OPTIONS: SelectOption[] = [
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

const LIKELIHOOD_OPTIONS: SelectOption[] = [
  { value: "certain", label: "Certain" },
  { value: "likely", label: "Likely" },
  { value: "possible", label: "Possible" },
  { value: "unlikely", label: "Unlikely" },
];

const EXPLORATION_TYPE_OPTIONS: SelectOption[] = [
  { value: "domain", label: "Domain" },
  { value: "architecture", label: "Architecture" },
  { value: "business", label: "Business" },
  { value: "risk", label: "Risk" },
  { value: "feasibility", label: "Feasibility" },
];

interface DecisionFormProps {
  slug: string;
  open: boolean;
  onClose: () => void;
  decision?: Decision;
  defaultTaskId?: string;
  onSuccess?: () => void;
}

export function DecisionForm({ slug, open, onClose, decision, defaultTaskId, onSuccess }: DecisionFormProps) {
  const isEdit = !!decision;
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);

  const { control, handleSubmit, setError, reset } = useForm<DecisionCreateForm>({
    resolver: zodResolver(decisionCreateSchema),
    defaultValues: decision
      ? {
          task_id: decision.task_id,
          type: decision.type,
          issue: decision.issue,
          recommendation: decision.recommendation,
          reasoning: decision.reasoning || "",
          alternatives: decision.alternatives || [],
          confidence: decision.confidence,
          status: decision.status,
          severity: decision.severity || "",
          likelihood: decision.likelihood || "",
          mitigation_plan: decision.mitigation_plan || "",
          exploration_type: decision.exploration_type || "",
        }
      : {
          task_id: defaultTaskId || "",
          type: "implementation",
          issue: "",
          recommendation: "",
          reasoning: "",
          alternatives: [],
          confidence: "MEDIUM",
          status: "OPEN",
        },
  });

  const watchType = useWatch({ control, name: "type" });
  const isRisk = watchType === "risk";
  const isExploration = watchType === "exploration";

  const onSubmit = handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      if (isEdit) {
        await updateDecision(slug, decision.id, {
          status: data.status,
          recommendation: data.recommendation,
          reasoning: data.reasoning,
          resolution_notes: data.resolution_notes,
        });
      } else {
        await createDecision(slug, [data]);
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
          setError(field as keyof DecisionCreateForm, { message });
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
      title={isEdit ? `Edit ${decision.id}` : "Create Decision"}
      onSubmit={onSubmit}
      submitting={submitting}
      submitLabel={isEdit ? "Update" : "Create"}
    >
      <FormErrorSummary errors={apiErrors} />

      <TextField name="task_id" control={control} label="Task ID" required placeholder="T-001" disabled={isEdit} />
      <SelectField name="type" control={control} label="Type" options={TYPE_OPTIONS} />
      <TextAreaField name="issue" control={control} label="Issue" required placeholder="What needs to be decided?" rows={3} />
      <TextAreaField name="recommendation" control={control} label="Recommendation" required placeholder="What do you recommend?" rows={3} />
      <TextAreaField name="reasoning" control={control} label="Reasoning" placeholder="Why this recommendation?" rows={3} />
      <DynamicListField name="alternatives" control={control} label="Alternatives Considered" addLabel="Add alternative" />
      <SelectField name="confidence" control={control} label="Confidence" options={CONFIDENCE_OPTIONS} />
      <SelectField name="status" control={control} label="Status" options={STATUS_OPTIONS} />

      {/* Risk-specific fields */}
      {isRisk && (
        <>
          <SelectField name="severity" control={control} label="Severity" options={SEVERITY_OPTIONS} />
          <SelectField name="likelihood" control={control} label="Likelihood" options={LIKELIHOOD_OPTIONS} />
          <TextAreaField name="mitigation_plan" control={control} label="Mitigation Plan" placeholder="How to mitigate this risk?" rows={3} />
        </>
      )}

      {/* Exploration-specific fields */}
      {isExploration && (
        <>
          <SelectField name="exploration_type" control={control} label="Exploration Type" options={EXPLORATION_TYPE_OPTIONS} />
        </>
      )}
    </FormDrawer>
  );
}
