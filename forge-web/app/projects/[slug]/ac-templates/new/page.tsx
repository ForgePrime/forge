"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { acTemplateCreateSchema, type ACTemplateCreateForm } from "@/lib/schemas/ac-template";
import { createACTemplate } from "@/stores/acTemplateStore";
import { CreatePageLayout } from "@/components/forms/CreatePageLayout";
import { TextField } from "@/components/forms/TextField";
import { TextAreaField } from "@/components/forms/TextAreaField";
import { SelectField, type SelectOption } from "@/components/forms/SelectField";
import { DynamicListField } from "@/components/forms/DynamicListField";
import { FormErrorSummary } from "@/components/forms/FormErrorSummary";
import { parseValidationErrors } from "@/lib/utils/apiErrors";
import type { FieldError } from "@/lib/utils/apiErrors";

const CATEGORY_OPTIONS: SelectOption[] = [
  { value: "performance", label: "Performance" },
  { value: "security", label: "Security" },
  { value: "quality", label: "Quality" },
  { value: "functionality", label: "Functionality" },
  { value: "accessibility", label: "Accessibility" },
  { value: "reliability", label: "Reliability" },
  { value: "data-integrity", label: "Data Integrity" },
  { value: "ux", label: "UX" },
];

export default function NewACTemplatePage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);

  const { control, handleSubmit } = useForm<ACTemplateCreateForm>({
    resolver: zodResolver(acTemplateCreateSchema),
    defaultValues: {
      title: "",
      template: "",
      category: "quality",
      description: "",
      parameters: [],
      scopes: [],
      tags: [],
      verification_method: "",
    },
  });

  const onSubmit = handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      const cleanData = { ...data };
      if (!cleanData.description) delete cleanData.description;
      if (!cleanData.verification_method) delete cleanData.verification_method;
      const ids = await createACTemplate(slug, [cleanData]);
      router.push(`/projects/${slug}/ac-templates/${ids[0]}`);
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
      title="New AC Template"
      backHref={`/projects/${slug}/ac-templates`}
      submitting={submitting}
      onSubmit={onSubmit}
    >
      <FormErrorSummary errors={apiErrors} />

      <TextField name="title" control={control} label="Title" required placeholder="Template title" />
      <SelectField name="category" control={control} label="Category" options={CATEGORY_OPTIONS} required />
      <TextAreaField name="description" control={control} label="Description" placeholder="What this template checks for" />
      <TextAreaField name="template" control={control} label="Template Text" required placeholder="When {action} is performed, then {expected_result}" rows={6} />

      <Controller
        name="parameters"
        control={control}
        render={({ field }) => {
          const params = field.value ?? [];
          const addParam = () => field.onChange([...params, { name: "", type: "string", default: "", description: "" }]);
          const removeParam = (idx: number) => field.onChange(params.filter((_, i) => i !== idx));
          const updateParam = (idx: number, key: string, val: string) => {
            const next = [...params];
            next[idx] = { ...next[idx], [key]: val };
            field.onChange(next);
          };
          return (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Parameters</label>
              <div className="space-y-2">
                {params.map((p, idx) => (
                  <div key={idx} className="flex gap-2 items-start">
                    <input type="text" value={p.name} onChange={(e) => updateParam(idx, "name", e.target.value)} placeholder="name" className="flex-1 px-2 py-1.5 text-sm border border-gray-300 rounded-md" />
                    <select value={p.type} onChange={(e) => updateParam(idx, "type", e.target.value)} className="px-2 py-1.5 text-sm border border-gray-300 rounded-md bg-white">
                      <option value="string">string</option>
                      <option value="number">number</option>
                      <option value="boolean">boolean</option>
                    </select>
                    <input type="text" value={String(p.default ?? "")} onChange={(e) => updateParam(idx, "default", e.target.value)} placeholder="default" className="flex-1 px-2 py-1.5 text-sm border border-gray-300 rounded-md" />
                    <input type="text" value={p.description ?? ""} onChange={(e) => updateParam(idx, "description", e.target.value)} placeholder="description" className="flex-1 px-2 py-1.5 text-sm border border-gray-300 rounded-md" />
                    <button type="button" onClick={() => removeParam(idx)} className="p-1.5 text-gray-400 hover:text-red-500">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                    </button>
                  </div>
                ))}
              </div>
              <button type="button" onClick={addParam} className="mt-2 inline-flex items-center gap-1 px-3 py-1.5 text-xs text-forge-600 border border-dashed border-forge-300 rounded-md hover:bg-forge-50">
                + Add parameter
              </button>
            </div>
          );
        }}
      />

      <TextAreaField name="verification_method" control={control} label="Verification Method" placeholder="How to verify this criterion is met" />
      <DynamicListField name="scopes" control={control} label="Scopes" addLabel="Add scope" />
      <DynamicListField name="tags" control={control} label="Tags" addLabel="Add tag" />
    </CreatePageLayout>
  );
}
