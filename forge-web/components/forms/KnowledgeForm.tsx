"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { knowledgeCreateSchema, knowledgeUpdateSchema, type KnowledgeCreateForm, type KnowledgeUpdateForm } from "@/lib/schemas/knowledge";
import { createKnowledge, updateKnowledge } from "@/stores/knowledgeStore";
import { parseValidationErrors, fieldErrorsToRecord } from "@/lib/utils/apiErrors";
import { FormDrawer } from "./FormDrawer";
import { TextField } from "./TextField";
import { TextAreaField } from "./TextAreaField";
import { SelectField, type SelectOption } from "./SelectField";
import { MultiSelectField } from "./MultiSelectField";
import { FormErrorSummary } from "./FormErrorSummary";
import type { Knowledge } from "@/lib/types";
import type { FieldError } from "@/lib/utils/apiErrors";

const CATEGORY_OPTIONS: SelectOption[] = [
  { value: "domain-rules", label: "Domain Rules" },
  { value: "api-reference", label: "API Reference" },
  { value: "architecture", label: "Architecture" },
  { value: "business-context", label: "Business Context" },
  { value: "technical-context", label: "Technical Context" },
  { value: "code-patterns", label: "Code Patterns" },
  { value: "integration", label: "Integration" },
  { value: "infrastructure", label: "Infrastructure" },
];

const STATUS_OPTIONS: SelectOption[] = [
  { value: "DRAFT", label: "Draft" },
  { value: "ACTIVE", label: "Active" },
  { value: "REVIEW_NEEDED", label: "Review Needed" },
  { value: "DEPRECATED", label: "Deprecated" },
  { value: "ARCHIVED", label: "Archived" },
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

interface KnowledgeFormProps {
  slug: string;
  open: boolean;
  onClose: () => void;
  knowledge?: Knowledge;
  onSuccess?: () => void;
}

export function KnowledgeForm({ slug, open, onClose, knowledge, onSuccess }: KnowledgeFormProps) {
  const isEdit = !!knowledge;
  const [submitting, setSubmitting] = useState(false);
  const [apiErrors, setApiErrors] = useState<FieldError[]>([]);

  // Use different schemas for create vs edit
  const createForm = useForm<KnowledgeCreateForm>({
    resolver: zodResolver(knowledgeCreateSchema),
    defaultValues: {
      title: knowledge?.title || "",
      category: knowledge?.category || "domain-rules",
      content: knowledge?.content || "",
      scopes: knowledge?.scopes || [],
      tags: knowledge?.tags || [],
    },
  });

  const editForm = useForm<KnowledgeUpdateForm>({
    resolver: zodResolver(knowledgeUpdateSchema),
    defaultValues: {
      title: knowledge?.title || "",
      content: knowledge?.content || "",
      status: knowledge?.status,
      category: knowledge?.category,
      scopes: knowledge?.scopes || [],
      tags: knowledge?.tags || [],
      change_reason: "",
    },
  });

  const form = isEdit ? editForm : createForm;

  useEffect(() => {
    if (isEdit) {
      editForm.reset({
        title: knowledge?.title || "",
        content: knowledge?.content || "",
        status: knowledge?.status,
        category: knowledge?.category,
        scopes: knowledge?.scopes || [],
        tags: knowledge?.tags || [],
        change_reason: "",
      });
    } else {
      createForm.reset({
        title: "",
        category: "domain-rules",
        content: "",
        scopes: [],
        tags: [],
      });
    }
    setApiErrors([]);
  }, [knowledge, isEdit, createForm, editForm]);

  const onSubmit = form.handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      if (isEdit) {
        await updateKnowledge(slug, knowledge.id, data as KnowledgeUpdateForm);
      } else {
        await createKnowledge(slug, [data as KnowledgeCreateForm]);
      }
      form.reset();
      onSuccess?.();
      onClose();
    } catch (e) {
      const errors = parseValidationErrors(e);
      if (errors.length > 0) {
        setApiErrors(errors);
        const record = fieldErrorsToRecord(errors);
        for (const [field, message] of Object.entries(record)) {
          form.setError(field as string, { message });
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
      title={isEdit ? `Edit ${knowledge.id}` : "Create Knowledge"}
      onSubmit={onSubmit}
      submitting={submitting}
      submitLabel={isEdit ? "Update" : "Create"}
    >
      <FormErrorSummary errors={apiErrors} />

      <TextField name="title" control={form.control} label="Title" required placeholder="e.g., API rate limit rules" />
      <SelectField name="category" control={form.control} label="Category" options={CATEGORY_OPTIONS} />
      {isEdit && <SelectField name="status" control={form.control} label="Status" options={STATUS_OPTIONS} />}
      <TextAreaField name="content" control={form.control} label="Content" required={!isEdit} placeholder="Knowledge content (Markdown supported)" rows={10} />
      <MultiSelectField name="scopes" control={form.control} label="Scopes" options={SCOPE_OPTIONS} />
      {isEdit && (
        <TextField name="change_reason" control={form.control} label="Change Reason" placeholder="Why is this being updated?" />
      )}
    </FormDrawer>
  );
}
