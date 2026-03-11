"use client";

import { useState, useEffect } from "react";
import { useForm, useFieldArray, useWatch } from "react-hook-form";
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
import type { Objective, ObjectiveRelation } from "@/lib/types";
import type { FieldError } from "@/lib/utils/apiErrors";
import useSWR from "swr";
import { guidelines as guidelinesApi, objectives as objectivesApi } from "@/lib/api";

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
  { value: "ai", label: "AI" },
];

const RELATION_TYPE_OPTIONS: SelectOption[] = [
  { value: "depends_on", label: "Depends on" },
  { value: "related_to", label: "Related to" },
  { value: "supersedes", label: "Supersedes" },
  { value: "duplicates", label: "Duplicates" },
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
          description: kr.description,
        })) || [{ metric: "", target: 0 }],
        appetite: objective.appetite || "medium",
        scope: objective.scope || "project",
        assumptions: objective.assumptions || [],
        scopes: objective.scopes || [],
        guideline_ids: objective.guideline_ids || [],
        relations: objective.relations?.map((r) => ({
          type: r.type,
          target_id: r.target_id,
          notes: r.notes,
        })) || [],
      }
    : {
        title: "",
        description: "",
        key_results: [{ metric: "", target: 0 }],
        appetite: "medium",
        scope: "project",
        assumptions: [],
        scopes: [],
        guideline_ids: [],
        relations: [],
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
  const [expandedKRs, setExpandedKRs] = useState<Set<number>>(new Set());

  const { control, handleSubmit, setError, reset, setValue, getValues } = useForm<ObjectiveCreateForm>({
    resolver: zodResolver(objectiveCreateSchema),
    defaultValues: getDefaults(objective),
  });

  const { fields, append, remove } = useFieldArray({ control, name: "key_results" });
  const { fields: relationFields, append: appendRelation, remove: removeRelation } = useFieldArray({ control, name: "relations" as any });

  // Watch guideline_ids for the picker
  const selectedGuidelineIds = useWatch({ control, name: "guideline_ids" }) || [];

  // Load guidelines for picker
  const { data: guidelinesData } = useSWR(
    open ? `guidelines-${slug}` : null,
    () => guidelinesApi.list(slug)
  );

  // Load objectives for relation target picker (exclude self)
  const { data: objectivesData } = useSWR(
    open ? `objectives-${slug}` : null,
    () => objectivesApi.list(slug)
  );

  const availableGuidelines = guidelinesData?.guidelines?.filter(
    (g: any) => g.status === "ACTIVE"
  ) || [];

  const availableObjectives = objectivesData?.objectives?.filter(
    (o: any) => !objective || o.id !== objective.id
  ) || [];

  useEffect(() => {
    reset(getDefaults(objective));
    setApiErrors([]);
    setExpandedKRs(new Set());
  }, [objective, reset]);

  const toggleKRDetails = (idx: number) => {
    setExpandedKRs((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const toggleGuideline = (gId: string) => {
    const current = getValues("guideline_ids") || [];
    if (current.includes(gId)) {
      setValue("guideline_ids", current.filter((id: string) => id !== gId));
    } else {
      setValue("guideline_ids", [...current, gId]);
    }
  };

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
          guideline_ids: data.guideline_ids,
          relations: data.relations,
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
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => toggleKRDetails(idx)}
                    className="text-xs text-forge-600 hover:text-forge-800"
                  >
                    {expandedKRs.has(idx) ? "Hide details" : "Details"}
                  </button>
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
              </div>
              <TextField name={`key_results.${idx}.metric`} control={control} label="Metric" placeholder="e.g., p95 latency (ms) — leave empty for descriptive KR" />
              <div className="grid grid-cols-3 gap-2">
                <TextField name={`key_results.${idx}.baseline`} control={control} label="Baseline" placeholder="500" />
                <TextField name={`key_results.${idx}.target`} control={control} label="Target" placeholder="200" />
                <TextField name={`key_results.${idx}.current`} control={control} label="Current" placeholder="320" />
              </div>
              {/* Progressive disclosure: description field */}
              {expandedKRs.has(idx) && (
                <div className="mt-2 pt-2 border-t border-gray-200">
                  <TextAreaField
                    name={`key_results.${idx}.description`}
                    control={control}
                    label="Description"
                    placeholder="Why does this KR matter? What qualitative outcome?"
                  />
                </div>
              )}
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() => append({ metric: "", target: 0, description: "" })}
          className="mt-2 inline-flex items-center gap-1 px-3 py-1.5 text-xs text-forge-600 border border-dashed border-forge-300 rounded-md hover:bg-forge-50"
        >
          + Add Key Result
        </button>
      </div>

      {/* Guidelines Picker */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Assigned Guidelines
        </label>
        {availableGuidelines.length === 0 ? (
          <p className="text-xs text-gray-400">No active guidelines in this project</p>
        ) : (
          <div className="max-h-40 overflow-y-auto border rounded-md p-2 space-y-1">
            {availableGuidelines.map((g: any) => (
              <label
                key={g.id}
                className={`flex items-center gap-2 p-1.5 rounded cursor-pointer text-xs hover:bg-gray-50 ${
                  selectedGuidelineIds.includes(g.id) ? "bg-forge-50 border border-forge-200" : ""
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedGuidelineIds.includes(g.id)}
                  onChange={() => toggleGuideline(g.id)}
                  className="rounded border-gray-300 text-forge-600 focus:ring-forge-500"
                />
                <span className="font-mono text-gray-500">{g.id}</span>
                <span className="truncate">{g.title}</span>
                <span className={`ml-auto px-1.5 py-0.5 rounded text-[10px] font-medium ${
                  g.weight === "must" ? "bg-red-100 text-red-700" :
                  g.weight === "should" ? "bg-yellow-100 text-yellow-700" :
                  "bg-gray-100 text-gray-600"
                }`}>
                  {g.weight}
                </span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Relations Editor */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Relations
        </label>
        <div className="space-y-2">
          {relationFields.map((field, idx) => (
            <div key={field.id} className="flex items-start gap-2 p-2 border rounded-md bg-gray-50">
              <select
                {...(control as any).register(`relations.${idx}.type`)}
                className="text-xs border rounded px-2 py-1.5 bg-white"
              >
                {RELATION_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <select
                {...(control as any).register(`relations.${idx}.target_id`)}
                className="text-xs border rounded px-2 py-1.5 bg-white flex-1"
              >
                <option value="">Select objective...</option>
                {availableObjectives.map((o: any) => (
                  <option key={o.id} value={o.id}>{o.id}: {o.title?.slice(0, 40)}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => removeRelation(idx)}
                className="text-xs text-red-500 hover:text-red-700 px-1 py-1"
              >
                x
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() => appendRelation({ type: "related_to", target_id: "" })}
          className="mt-2 inline-flex items-center gap-1 px-3 py-1.5 text-xs text-forge-600 border border-dashed border-forge-300 rounded-md hover:bg-forge-50"
        >
          + Add Relation
        </button>
      </div>
    </FormDrawer>
  );
}
