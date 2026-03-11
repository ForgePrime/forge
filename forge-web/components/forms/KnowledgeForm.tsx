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

  const handleError = (e: unknown) => {
    const errors = parseValidationErrors(e);
    if (errors.length > 0) {
      setApiErrors(errors);
      const record = fieldErrorsToRecord(errors);
      for (const [field, message] of Object.entries(record)) {
        if (isEdit) {
          editForm.setError(field as keyof KnowledgeUpdateForm, { message });
        } else {
          createForm.setError(field as keyof KnowledgeCreateForm, { message });
        }
      }
    } else {
      setApiErrors([{ field: "general", message: (e as Error).message }]);
    }
  };

  const onCreateSubmit = createForm.handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      await createKnowledge(slug, [data]);
      createForm.reset();
      onSuccess?.();
      onClose();
    } catch (e) {
      handleError(e);
    } finally {
      setSubmitting(false);
    }
  });

  const onEditSubmit = editForm.handleSubmit(async (data) => {
    setSubmitting(true);
    setApiErrors([]);
    try {
      await updateKnowledge(slug, knowledge!.id, data);
      editForm.reset();
      onSuccess?.();
      onClose();
    } catch (e) {
      handleError(e);
    } finally {
      setSubmitting(false);
    }
  });

  if (isEdit) {
    return (
      <FormDrawer
        open={open}
        onClose={onClose}
        title={`Edit ${knowledge.id}`}
        onSubmit={onEditSubmit}
        submitting={submitting}
        submitLabel="Update"
      >
        <FormErrorSummary errors={apiErrors} />
        <TextField name="title" control={editForm.control} label="Title" placeholder="e.g., API rate limit rules" />
        <SelectField name="category" control={editForm.control} label="Category" options={CATEGORY_OPTIONS} />
        <SelectField name="status" control={editForm.control} label="Status" options={STATUS_OPTIONS} />
        <TextAreaField name="content" control={editForm.control} label="Content" placeholder="Knowledge content (Markdown supported)" rows={10} />
        <MultiSelectField name="scopes" control={editForm.control} label="Scopes" options={SCOPE_OPTIONS} />
        <TextField name="change_reason" control={editForm.control} label="Change Reason" placeholder="Why is this being updated?" />
      </FormDrawer>
    );
  }

  return (
    <FormDrawer
      open={open}
      onClose={onClose}
      title="Create Knowledge"
      onSubmit={onCreateSubmit}
      submitting={submitting}
      submitLabel="Create"
    >
      <FormErrorSummary errors={apiErrors} />
      <TextField name="title" control={createForm.control} label="Title" required placeholder="e.g., API rate limit rules" />
      <SelectField name="category" control={createForm.control} label="Category" options={CATEGORY_OPTIONS} />
      <TextAreaField name="content" control={createForm.control} label="Content" required placeholder="Knowledge content (Markdown supported)" rows={10} />
      <MultiSelectField name="scopes" control={createForm.control} label="Scopes" options={SCOPE_OPTIONS} />
    </FormDrawer>
  );
}
