"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ideaCreateSchema, type IdeaCreateForm } from "@/lib/schemas/idea";
import { createIdea, updateIdea } from "@/stores/ideaStore";
import { parseValidationErrors, fieldErrorsToRecord } from "@/lib/utils/apiErrors";
import { FormDrawer } from "./FormDrawer";
import { TextField } from "./TextField";
import { TextAreaField } from "./TextAreaField";
import { SelectField, type SelectOption } from "./SelectField";
import { MultiSelectField } from "./MultiSelectField";
import { EntityRefField } from "./EntityRefField";
import { FormErrorSummary } from "./FormErrorSummary";
import type { Idea } from "@/lib/types";
import type { FieldError } from "@/lib/utils/apiErrors";

const CATEGORY_OPTIONS: SelectOption[] = [
  { value: "feature", label: "Feature" },
  { value: "improvement", label: "Improvement" },
  { value: "experiment", label: "Experiment" },
  { value: "migration", label: "Migration" },
  { value: "refactor", label: "Refactor" },
  { value: "infrastructure", label: "Infrastructure" },
  { value: "business-opportunity", label: "Business Opportunity" },
  { value: "research", label: "Research" },
];

const PRIORITY_OPTIONS: SelectOption[] = [
  { value: "HIGH", label: "High" },
  { value: "MEDIUM", label: "Medium" },
  { value: "LOW", label: "Low" },
];

const SCOPE_OPTIONS: SelectOption[] = [
  { value: "frontend", label: "Frontend" },
  { value: "backend", label: "Backend" },
  { value: "database", label: "Database" },
  { value: "infrastructure", label: "Infrastructure" },
  { value: "performance", label: "Performance" },
  { value: "security", label: "Security" },
  { value: "ux", label: "UX" },
];

function getDefaults(idea?: Idea): IdeaCreateForm {
  return idea
    ? {
        title: idea.title,
        description: idea.description || "",
        category: idea.category,
        priority: idea.priority,
        parent_id: idea.parent_id || "",
        scopes: idea.scopes || [],
        advances_key_results: idea.advances_key_results || [],
        tags: idea.tags || [],
      }
    : {
        title: "",
        description: "",
        category: "feature",
        priority: "MEDIUM",
        parent_id: "",
        scopes: [],
        advances_key_results: [],
        tags: [],
      };
}

interface IdeaFormProps {
  slug: string;
  open: boolean;
  onClose: () => void;
  idea?: Idea;
  onSuccess?: () => void;
}

export function IdeaForm({ slug, open, onClose, idea, onSuccess }: IdeaFormProps) {
  const isEdit = !!idea;
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);

  const { control, handleSubmit, setError, reset } = useForm<IdeaCreateForm>({
    resolver: zodResolver(ideaCreateSchema),
    defaultValues: getDefaults(idea),
  });

  useEffect(() => {
    reset(getDefaults(idea));
    setApiErrors([]);
  }, [idea, reset]);

  const onSubmit = handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      if (isEdit) {
        await updateIdea(slug, idea.id, {
          title: data.title,
          description: data.description,
          category: data.category,
          priority: data.priority,
          scopes: data.scopes,
          advances_key_results: data.advances_key_results,
          tags: data.tags,
        });
      } else {
        await createIdea(slug, [data]);
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
          setError(field as keyof IdeaCreateForm, { message });
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
      title={isEdit ? `Edit ${idea.id}` : "Create Idea"}
      onSubmit={onSubmit}
      submitting={submitting}
      submitLabel={isEdit ? "Update" : "Create"}
    >
      <FormErrorSummary errors={apiErrors} />

      <TextField name="title" control={control} label="Title" required placeholder="e.g., Redis caching layer" />
      <TextAreaField name="description" control={control} label="Description" placeholder="What and why?" />
      <SelectField name="category" control={control} label="Category" options={CATEGORY_OPTIONS} />
      <SelectField name="priority" control={control} label="Priority" options={PRIORITY_OPTIONS} />
      <MultiSelectField name="scopes" control={control} label="Scopes" options={SCOPE_OPTIONS} />
      {!isEdit && (
        <EntityRefField name="parent_id" control={control} label="Parent Idea" entityTypes={["idea"]} multiple={false} placeholder="Search parent idea..." />
      )}
    </FormDrawer>
  );
}
