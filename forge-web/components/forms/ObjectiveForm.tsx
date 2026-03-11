"use client";

import { useState, useEffect } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { objectiveCreateSchema, type ObjectiveCreateForm } from "@/lib/schemas/objective";
import { createObjective, updateObjective } from "@/stores/objectiveStore";
import { parseValidationErrors, fieldErrorsToRecord } from "@/lib/utils/apiErrors";
import { FormDrawer } from "./FormDrawer";
import { TextField } from "./TextField";
import { TextAreaField } from "./TextAreaField";
import { SelectField, type SelectOption } from "./SelectField";
import { MultiSelectField } from "./MultiSelectField";
import { DynamicListField } from "./DynamicListField";
import { FormErrorSummary } from "./FormErrorSummary";
import type { Objective } from "@/lib/types";
import type { FieldError } from "@/lib/utils/apiErrors";

const APPETITE_OPTIONS: SelectOption[] = [
  { value: "small", label: "Small (days)" },
  { value: "medium", label: "Medium (weeks)" },
  { value: "large", label: "Large (months)" },
];

const SCOPE_OPTIONS: SelectOption[] = [
  { value: "project", label: "Project" },
  { value: "cross-project", label: "Cross-project" },
];

const TAG_SCOPE_OPTIONS: SelectOption[] = [
  { value: "frontend", label: "Frontend" },
  { value: "backend", label: "Backend" },
  { value: "database", label: "Database" },
  { value: "infrastructure", label: "Infrastructure" },
  { value: "performance", label: "Performance" },
  { value: "security", label: "Security" },
  { value: "ux", label: "UX" },
];

function getDefaults(objective?: Objective): ObjectiveCreateForm {
  return objective
    ? {
        title: objective.title,
        description: objective.description || "",
        key_results: objective.key_results?.map((kr) => ({
          metric: kr.metric,
          baseline: kr.baseline,
          target: kr.target,
          current: kr.current,
        })) || [{ metric: "", target: 0 }],
        appetite: (objective as Record<string, unknown>).appetite as "small" | "medium" | "large" || "medium",
        scope: "project",
        assumptions: (objective as Record<string, unknown>).assumptions as string[] || [],
        scopes: objective.scopes || [],
      }
    : {
        title: "",
        description: "",
        key_results: [{ metric: "", target: 0 }],
        appetite: "medium",
        scope: "project",
        assumptions: [],
        scopes: [],
      };
}

interface ObjectiveFormProps {
  slug: string;
  open: boolean;
  onClose: () => void;
  objective?: Objective;
  onSuccess?: () => void;
}

export function ObjectiveForm({ slug, open, onClose, objective, onSuccess }: ObjectiveFormProps) {
  const isEdit = !!objective;
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);

  const { control, handleSubmit, setError, reset } = useForm<ObjectiveCreateForm>({
    resolver: zodResolver(objectiveCreateSchema),
    defaultValues: getDefaults(objective),
  });

  const { fields, append, remove } = useFieldArray({ control, name: "key_results" });

  useEffect(() => {
    reset(getDefaults(objective));
    setApiErrors([]);
  }, [objective, reset]);

  const onSubmit = handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      if (isEdit) {
        await updateObjective(slug, objective.id, {
          title: data.title,
          description: data.description,
          appetite: data.appetite,
          key_results: data.key_results,
          assumptions: data.assumptions,
          scopes: data.scopes,
        });
      } else {
        await createObjective(slug, [data]);
      }
      reset(getDefaults());
      onSuccess?.();
      onClose();
    } catch (e) {
      const errors = parseValidationErrors(e);
      if (errors.length > 0) {
        setApiErrors(errors);
        const record = fieldErrorsToRecord(errors);
        for (const [field, message] of Object.entries(record)) {
          setError(field as keyof ObjectiveCreateForm, { message });
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
      title={isEdit ? `Edit ${objective.id}` : "Create Objective"}
      onSubmit={onSubmit}
      submitting={submitting}
      submitLabel={isEdit ? "Update" : "Create"}
    >
      <FormErrorSummary errors={apiErrors} />

      <TextField name="title" control={control} label="Title" required placeholder="e.g., Reduce API response time" />
      <TextAreaField name="description" control={control} label="Description" required placeholder="What is the business goal?" />
      <SelectField name="appetite" control={control} label="Appetite" options={APPETITE_OPTIONS} />
      {!isEdit && <SelectField name="scope" control={control} label="Scope" options={SCOPE_OPTIONS} />}
      <MultiSelectField name="scopes" control={control} label="Guideline Scopes" options={TAG_SCOPE_OPTIONS} />
      <DynamicListField name="assumptions" control={control} label="Assumptions" addLabel="Add assumption" placeholder="What must hold true?" />

      {/* Key Results */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Key Results <span className="text-red-500">*</span>
        </label>
        <div className="space-y-3">
          {fields.map((field, idx) => (
            <div key={field.id} className="p-3 border rounded-md bg-gray-50 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-gray-500">KR-{idx + 1}</span>
                {fields.length > 1 && (
                  <button
                    type="button"
                    onClick={() => remove(idx)}
                    className="text-xs text-red-500 hover:text-red-700"
                  >
                    Remove
                  </button>
                )}
              </div>
              <TextField name={`key_results.${idx}.metric`} control={control} label="Metric" required placeholder="e.g., p95 latency (ms)" />
              <div className="grid grid-cols-3 gap-2">
                <TextField name={`key_results.${idx}.baseline`} control={control} label="Baseline" placeholder="500" />
                <TextField name={`key_results.${idx}.target`} control={control} label="Target" required placeholder="200" />
                <TextField name={`key_results.${idx}.current`} control={control} label="Current" placeholder="320" />
              </div>
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() => append({ metric: "", target: 0 })}
          className="mt-2 inline-flex items-center gap-1 px-3 py-1.5 text-xs text-forge-600 border border-dashed border-forge-300 rounded-md hover:bg-forge-50"
        >
          + Add Key Result
        </button>
      </div>
    </FormDrawer>
  );
}
