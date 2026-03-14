"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { objectiveCreateSchema, type ObjectiveCreateForm } from "@/lib/schemas/objective";
import { createObjective } from "@/stores/objectiveStore";
import { CreatePageLayout } from "@/components/forms/CreatePageLayout";
import { TextField } from "@/components/forms/TextField";
import { TextAreaField } from "@/components/forms/TextAreaField";
import { SelectField, type SelectOption } from "@/components/forms/SelectField";
import { DynamicListField } from "@/components/forms/DynamicListField";
import { FormErrorSummary } from "@/components/forms/FormErrorSummary";
import { parseValidationErrors } from "@/lib/utils/apiErrors";
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

interface KeyResultEntry {
  metric: string;
  baseline: number;
  target: number;
  description: string;
}

export default function NewObjectivePage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);

  const { control, handleSubmit, watch, setValue } = useForm<ObjectiveCreateForm>({
    resolver: zodResolver(objectiveCreateSchema),
    defaultValues: {
      title: "",
      description: "",
      key_results: [{ metric: "", baseline: 0, target: 0 }],
      appetite: "medium",
      scope: "project",
      assumptions: [],
      tags: [],
      scopes: [],
      guideline_ids: [],
    },
  });

  const keyResults = watch("key_results") as KeyResultEntry[];

  const addKeyResult = () => {
    setValue("key_results", [
      ...keyResults,
      { metric: "", baseline: 0, target: 0, description: "" },
    ]);
  };

  const removeKeyResult = (index: number) => {
    if (keyResults.length <= 1) return;
    setValue(
      "key_results",
      keyResults.filter((_, i) => i !== index),
    );
  };

  const updateKeyResult = (index: number, field: keyof KeyResultEntry, value: string | number) => {
    const updated = keyResults.map((kr, i) =>
      i === index ? { ...kr, [field]: value } : kr,
    );
    setValue("key_results", updated);
  };

  const onSubmit = handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      const ids = await createObjective(slug, [data]);
      router.push(`/projects/${slug}/objectives/${ids[0]}`);
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
      title="New Objective"
      backHref={`/projects/${slug}/objectives`}
      submitting={submitting}
      onSubmit={onSubmit}
    >
      <FormErrorSummary errors={apiErrors} />

      <TextField name="title" control={control} label="Title" required placeholder="Objective title" />
      <TextAreaField name="description" control={control} label="Description" required placeholder="What do we want to achieve?" />
      <SelectField name="appetite" control={control} label="Appetite" options={APPETITE_OPTIONS} />
      <SelectField name="scope" control={control} label="Scope" options={SCOPE_OPTIONS} />

      {/* Key Results */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Key Results <span className="text-red-500 ml-0.5">*</span>
        </label>
        <div className="space-y-3">
          {keyResults.map((kr, index) => (
            <div key={index} className="border border-gray-200 rounded-md p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-gray-500">KR-{index + 1}</span>
                {keyResults.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeKeyResult(index)}
                    className="text-xs text-red-500 hover:text-red-700"
                  >
                    Remove
                  </button>
                )}
              </div>
              <input
                type="text"
                value={kr.metric || ""}
                onChange={(e) => updateKeyResult(index, "metric", e.target.value)}
                placeholder="Metric (e.g., p95 latency)"
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md outline-none focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
              />
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-xs text-gray-500 mb-1">Baseline</label>
                  <input
                    type="number"
                    value={kr.baseline ?? 0}
                    onChange={(e) => updateKeyResult(index, "baseline", Number(e.target.value))}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md outline-none focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-xs text-gray-500 mb-1">Target</label>
                  <input
                    type="number"
                    value={kr.target ?? 0}
                    onChange={(e) => updateKeyResult(index, "target", Number(e.target.value))}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md outline-none focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
                  />
                </div>
              </div>
              <input
                type="text"
                value={kr.description || ""}
                onChange={(e) => updateKeyResult(index, "description", e.target.value)}
                placeholder="Description (alternative to metric)"
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md outline-none focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
              />
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={addKeyResult}
          className="mt-2 inline-flex items-center gap-1 px-3 py-1.5 text-xs text-forge-600 border border-dashed border-forge-300 rounded-md hover:bg-forge-50"
        >
          + Add Key Result
        </button>
      </div>

      <DynamicListField name="assumptions" control={control} label="Assumptions" addLabel="Add assumption" />
      <DynamicListField name="scopes" control={control} label="Scopes" addLabel="Add scope" />
      <DynamicListField name="tags" control={control} label="Tags" addLabel="Add tag" />
      <DynamicListField name="guideline_ids" control={control} label="Guideline IDs" addLabel="Add guideline" placeholder="G-001" />
    </CreatePageLayout>
  );
}
