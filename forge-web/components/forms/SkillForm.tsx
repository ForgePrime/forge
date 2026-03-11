"use client";

import { useState, useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { skillCreateSchema, skillUpdateSchema, type SkillCreateForm, type SkillUpdateForm } from "@/lib/schemas/skill";
import { skills as skillsApi } from "@/lib/api";
import { parseValidationErrors, fieldErrorsToRecord } from "@/lib/utils/apiErrors";
import { FormDrawer } from "./FormDrawer";
import { TextField } from "./TextField";
import { TextAreaField } from "./TextAreaField";
import { SelectField, type SelectOption } from "./SelectField";
import { DynamicListField } from "./DynamicListField";
import { FormErrorSummary } from "./FormErrorSummary";
import { Badge } from "@/components/shared/Badge";
import type { Skill, TESLintFinding } from "@/lib/types";
import type { FieldError } from "@/lib/utils/apiErrors";

const CATEGORY_OPTIONS: SelectOption[] = [
  { value: "workflow", label: "Workflow" },
  { value: "analysis", label: "Analysis" },
  { value: "generation", label: "Generation" },
  { value: "validation", label: "Validation" },
  { value: "integration", label: "Integration" },
  { value: "refactoring", label: "Refactoring" },
  { value: "testing", label: "Testing" },
  { value: "deployment", label: "Deployment" },
  { value: "documentation", label: "Documentation" },
  { value: "custom", label: "Custom" },
];

const SKILL_MD_PLACEHOLDER = `# {Skill Name}

## Description
What this skill does and when to use it.

## Procedure
1. Step one
2. Step two
3. Step three

## Guidelines
- Key rules and constraints
- Quality expectations`;

interface SkillFormProps {
  open: boolean;
  onClose: () => void;
  skill?: Skill;
  onSuccess?: () => void;
}

function MonospaceTextarea({
  value,
  onChange,
  placeholder,
  error,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  error?: string;
}) {
  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        SKILL.md Content
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={14}
        className={`w-full px-3 py-2 text-sm border rounded-md outline-none transition-colors resize-y font-mono ${
          error
            ? "border-red-300 focus:border-red-500 focus:ring-1 focus:ring-red-500"
            : "border-gray-300 focus:border-forge-500 focus:ring-1 focus:ring-forge-500"
        }`}
      />
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

export function SkillForm({ open, onClose, skill, onSuccess }: SkillFormProps) {
  const isEdit = !!skill;
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);
  const [lintFindings, setLintFindings] = useState<TESLintFinding[]>([]);
  const [lintLoading, setLintLoading] = useState(false);

  const createForm = useForm<SkillCreateForm>({
    resolver: zodResolver(skillCreateSchema),
    defaultValues: {
      name: "",
      description: "",
      category: "custom",
      skill_md_content: "",
      tags: [],
      scopes: [],
    },
  });

  const editForm = useForm<SkillUpdateForm>({
    resolver: zodResolver(skillUpdateSchema),
    defaultValues: {
      name: skill?.name || "",
      description: skill?.description || "",
      category: skill?.category,
      skill_md_content: skill?.skill_md_content || "",
      tags: skill?.tags || [],
      scopes: skill?.scopes || [],
    },
  });

  useEffect(() => {
    if (isEdit && skill) {
      editForm.reset({
        name: skill.name,
        description: skill.description,
        category: skill.category,
        skill_md_content: skill.skill_md_content || "",
        tags: skill.tags,
        scopes: skill.scopes,
      });
    } else {
      createForm.reset({
        name: "",
        description: "",
        category: "custom",
        skill_md_content: "",
        tags: [],
        scopes: [],
      });
    }
    setApiErrors([]);
    setLintFindings([]);
  }, [skill, isEdit, createForm, editForm]);

  const onCreateSubmit = createForm.handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      await skillsApi.create([data as import("@/lib/types").SkillCreate]);
      createForm.reset();
      onSuccess?.();
      onClose();
    } catch (e) {
      const errors = parseValidationErrors(e);
      if (errors.length > 0) {
        setApiErrors(errors);
        const record = fieldErrorsToRecord(errors);
        for (const [field, message] of Object.entries(record)) {
          createForm.setError(field as keyof SkillCreateForm, { message });
        }
      } else {
        setApiErrors([{ field: "general", message: (e as Error).message }]);
      }
    } finally {
      setSubmitting(false);
    }
  });

  const onEditSubmit = editForm.handleSubmit(async (data) => {
    if (!skill) return;
    setSubmitting(true);
    setApiErrors([]);
    try {
      await skillsApi.update(skill.id, data);
      editForm.reset();
      onSuccess?.();
      onClose();
    } catch (e) {
      const errors = parseValidationErrors(e);
      if (errors.length > 0) {
        setApiErrors(errors);
        const record = fieldErrorsToRecord(errors);
        for (const [field, message] of Object.entries(record)) {
          editForm.setError(field as keyof SkillUpdateForm, { message });
        }
      } else {
        setApiErrors([{ field: "general", message: (e as Error).message }]);
      }
    } finally {
      setSubmitting(false);
    }
  });

  const runInlineLint = async () => {
    if (!skill) return;
    setLintLoading(true);
    try {
      const res = await skillsApi.lint(skill.id);
      setLintFindings(res.findings);
    } catch {
      setLintFindings([]);
    } finally {
      setLintLoading(false);
    }
  };

  const isActive = skill?.status === "ACTIVE";
  const usageWarning = isActive && skill.usage_count > 0;

  const lintSection = isEdit && (
    <div className="mb-4">
      <div className="flex items-center gap-2 mb-2">
        <button
          type="button"
          onClick={runInlineLint}
          disabled={lintLoading}
          className="text-xs px-3 py-1 border border-forge-300 text-forge-600 rounded-md hover:bg-forge-50 disabled:opacity-50"
        >
          {lintLoading ? "Linting..." : "Run Lint"}
        </button>
        {lintFindings.length > 0 && (
          <span className="text-xs text-gray-400">{lintFindings.length} finding(s)</span>
        )}
        <span className="text-xs text-gray-300">Lints saved content — save first</span>
      </div>
      {lintFindings.length > 0 && (
        <div className="space-y-1">
          {lintFindings.map((f, i) => (
            <div
              key={i}
              className={`text-xs px-2 py-1 rounded ${
                f.severity === "error" ? "bg-red-50 text-red-700" :
                f.severity === "warning" ? "bg-yellow-50 text-yellow-700" :
                "bg-blue-50 text-blue-700"
              }`}
            >
              <Badge
                variant={f.severity === "error" ? "danger" : f.severity === "warning" ? "warning" : "info"}
                className="mr-1"
              >
                {f.severity}
              </Badge>
              {f.rule_id}: {f.message}
            </div>
          ))}
        </div>
      )}
    </div>
  );

  if (isEdit) {
    return (
      <FormDrawer
        open={open}
        onClose={onClose}
        title={`Edit ${skill.id}`}
        onSubmit={onEditSubmit}
        submitting={submitting}
        submitLabel="Update"
      >
        <FormErrorSummary errors={apiErrors} />
        {usageWarning && (
          <div className="mb-4 rounded-md bg-amber-50 border border-amber-200 px-3 py-2">
            <p className="text-xs text-amber-700">
              This skill is ACTIVE and used by {skill.usage_count} task{skill.usage_count !== 1 ? "s" : ""}. Changes may affect running work.
            </p>
          </div>
        )}
        <TextField name="name" control={editForm.control} label="Name" />
        <TextAreaField name="description" control={editForm.control} label="Description" rows={3} />
        <SelectField name="category" control={editForm.control} label="Category" options={CATEGORY_OPTIONS} />
        <Controller
          name="skill_md_content"
          control={editForm.control}
          render={({ field, fieldState: { error } }) => (
            <MonospaceTextarea
              value={field.value ?? ""}
              onChange={field.onChange}
              placeholder={SKILL_MD_PLACEHOLDER}
              error={error?.message}
            />
          )}
        />
        {lintSection}
        <DynamicListField name="tags" control={editForm.control} label="Tags" placeholder="e.g., backend" addLabel="Add tag" />
        <DynamicListField name="scopes" control={editForm.control} label="Scopes" placeholder="e.g., backend" addLabel="Add scope" />
      </FormDrawer>
    );
  }

  return (
    <FormDrawer
      open={open}
      onClose={onClose}
      title="Create Skill"
      onSubmit={onCreateSubmit}
      submitting={submitting}
      submitLabel="Create"
    >
      <FormErrorSummary errors={apiErrors} />
      <TextField name="name" control={createForm.control} label="Name" required placeholder="e.g., Code Review Checklist" />
      <TextAreaField name="description" control={createForm.control} label="Description" rows={3} placeholder="What does this skill do?" />
      <SelectField name="category" control={createForm.control} label="Category" options={CATEGORY_OPTIONS} />
      <Controller
        name="skill_md_content"
        control={createForm.control}
        render={({ field, fieldState: { error } }) => (
          <MonospaceTextarea
            value={field.value ?? ""}
            onChange={field.onChange}
            placeholder={SKILL_MD_PLACEHOLDER}
            error={error?.message}
          />
        )}
      />
      <DynamicListField name="tags" control={createForm.control} label="Tags" placeholder="e.g., backend" addLabel="Add tag" />
      <DynamicListField name="scopes" control={createForm.control} label="Scopes" placeholder="e.g., backend" addLabel="Add scope" />
    </FormDrawer>
  );
}
