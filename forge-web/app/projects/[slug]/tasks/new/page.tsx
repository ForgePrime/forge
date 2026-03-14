"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { taskCreateSchema, type TaskCreateForm } from "@/lib/schemas/task";
import { createTask } from "@/stores/taskStore";
import { skills as skillsApi } from "@/lib/api";
import type { Skill } from "@/lib/types";
import { CreatePageLayout } from "@/components/forms/CreatePageLayout";
import { TextField } from "@/components/forms/TextField";
import { TextAreaField } from "@/components/forms/TextAreaField";
import { SelectField, type SelectOption } from "@/components/forms/SelectField";
import { MultiSelectField } from "@/components/forms/MultiSelectField";
import { DynamicListField } from "@/components/forms/DynamicListField";
import { EntityRefField } from "@/components/forms/EntityRefField";
import { FormErrorSummary } from "@/components/forms/FormErrorSummary";
import { parseValidationErrors } from "@/lib/utils/apiErrors";
import type { FieldError } from "@/lib/utils/apiErrors";

const TYPE_OPTIONS: SelectOption[] = [
  { value: "feature", label: "Feature" },
  { value: "bug", label: "Bug" },
  { value: "chore", label: "Chore" },
  { value: "investigation", label: "Investigation" },
];

const SCOPE_OPTIONS: SelectOption[] = [
  { value: "frontend", label: "Frontend" },
  { value: "backend", label: "Backend" },
  { value: "database", label: "Database" },
  { value: "infrastructure", label: "Infrastructure" },
  { value: "testing", label: "Testing" },
  { value: "ux", label: "UX" },
  { value: "performance", label: "Performance" },
  { value: "security", label: "Security" },
];

export default function NewTaskPage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);
  const [activeSkills, setActiveSkills] = useState<Skill[]>([]);
  const [allActiveSkills, setAllActiveSkills] = useState<Skill[]>([]);

  const { control, handleSubmit, watch } = useForm<TaskCreateForm>({
    resolver: zodResolver(taskCreateSchema),
    defaultValues: {
      name: "",
      description: "",
      instruction: "",
      type: "feature",
      depends_on: [],
      blocked_by_decisions: [],
      conflicts_with: [],
      acceptance_criteria: [],
      scopes: [],
      parallel: false,
      skill_id: null,
    },
  });

  const watchedScopes = watch("scopes");

  useEffect(() => {
    const params: Record<string, string> = { status: "ACTIVE" };
    if (watchedScopes && watchedScopes.length > 0) {
      params.scopes = watchedScopes.join(",");
    }
    skillsApi.list(params)
      .then((res) => setActiveSkills(res.skills))
      .catch(() => setActiveSkills([]));
    if (watchedScopes && watchedScopes.length > 0) {
      skillsApi.list({ status: "ACTIVE" })
        .then((res) => setAllActiveSkills(res.skills))
        .catch(() => setAllActiveSkills([]));
    } else {
      setAllActiveSkills([]);
    }
  }, [watchedScopes]);

  const onSubmit = handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      const ids = await createTask(slug, [data]);
      router.push(`/projects/${slug}/tasks/${ids[0]}`);
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

  const hasScopes = watchedScopes && watchedScopes.length > 0;
  const matchedIds = new Set(activeSkills.map((s) => s.name));
  const otherSkills = allActiveSkills.filter((s) => !matchedIds.has(s.name));

  return (
    <CreatePageLayout
      title="New Task"
      backHref={`/projects/${slug}/tasks`}
      submitting={submitting}
      onSubmit={onSubmit}
    >
      <FormErrorSummary errors={apiErrors} />

      <TextField name="name" control={control} label="Name" required placeholder="Task name" />
      <TextAreaField name="description" control={control} label="Description" placeholder="What needs to be done?" />
      <TextAreaField name="instruction" control={control} label="Instruction" placeholder="Step-by-step instructions" rows={6} />
      <SelectField name="type" control={control} label="Type" options={TYPE_OPTIONS} required />
      <MultiSelectField name="scopes" control={control} label="Scopes" options={SCOPE_OPTIONS} />

      {(activeSkills.length > 0 || allActiveSkills.length > 0) && (
        <Controller
          name="skill_id"
          control={control}
          render={({ field }) => (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Linked Skill
              </label>
              <select
                value={field.value ?? ""}
                onChange={(e) => field.onChange(e.target.value || null)}
                className="w-full rounded-md border px-2 py-1.5 text-sm focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
              >
                <option value="">None</option>
                {hasScopes && activeSkills.length > 0 && (
                  <optgroup label="Recommended (matching scopes)">
                    {activeSkills.map((s) => (
                      <option key={s.name} value={s.name}>{s.name}</option>
                    ))}
                  </optgroup>
                )}
                {hasScopes && otherSkills.length > 0 && (
                  <optgroup label="All skills">
                    {otherSkills.map((s) => (
                      <option key={s.name} value={s.name}>{s.name}</option>
                    ))}
                  </optgroup>
                )}
                {!hasScopes && activeSkills.map((s) => (
                  <option key={s.name} value={s.name}>{s.name}</option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-400">
                {hasScopes ? "Skills matching task scopes shown first" : "All ACTIVE skills shown"}
              </p>
            </div>
          )}
        />
      )}

      <DynamicListField name="acceptance_criteria" control={control} label="Acceptance Criteria" addLabel="Add criterion" placeholder="When X, then Y" />
      <EntityRefField name="depends_on" control={control} label="Depends On" entityTypes={["task"]} placeholder="Search tasks..." />
      <EntityRefField name="blocked_by_decisions" control={control} label="Blocked By Decisions" entityTypes={["decision"]} placeholder="Search decisions..." />
      <EntityRefField name="conflicts_with" control={control} label="Conflicts With" entityTypes={["task"]} placeholder="Search tasks..." />

      <Controller
        name="parallel"
        control={control}
        render={({ field }) => (
          <div className="mb-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={field.value || false}
                onChange={(e) => field.onChange(e.target.checked)}
                className="rounded border-gray-300 text-forge-600 focus:ring-forge-500"
              />
              <span className="text-gray-700">Can run in parallel</span>
            </label>
          </div>
        )}
      />
    </CreatePageLayout>
  );
}
