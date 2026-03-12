/**
 * Task List Page — manifest definition
 *
 * This is the proof-of-concept manifest that defines the Tasks list page.
 * It demonstrates all major patterns: filters, card list, status transitions,
 * form drawer, and data binding.
 *
 * Derived scopes: ["tasks"] (from /projects/{slug}/tasks endpoint)
 */

import type { PageManifest } from "../types";

export const taskListManifest: PageManifest = {
  id: "task-list",
  title: "Tasks",
  description: "Pipeline task list with status management, filtering, and task creation",

  layout: {
    type: "list",
    areas: ["toolbar", "filters", "list", "sidebar?"],
  },

  requires: {
    params: ["slug"],
    websocket: true,
  },

  dataSources: [
    {
      id: "tasks",
      endpoint: "/projects/{slug}/tasks",
      itemsField: "tasks",
      countField: "count",
      refreshOnEvents: ["task.created", "task.updated", "task.completed"],
    },
  ],

  elements: [
    // ── Toolbar ─────────────────────────────────────────────────────
    {
      id: "page-title",
      type: "text",
      content: "Tasks ({tasks.count})",
      variant: "h2",
      position: { area: "toolbar", order: 1 },
    },
    {
      id: "add-task-btn",
      type: "button",
      label: "New Task",
      variant: "primary",
      icon: "plus",
      position: { area: "toolbar", order: 2, group: "actions" },
      action: { type: "open-form", formId: "task-form" },
    },

    // ── Filters ─────────────────────────────────────────────────────
    {
      id: "status-filter",
      type: "select",
      label: "Status",
      position: { area: "filters", order: 1 },
      options: [
        { label: "All", value: "" },
        { label: "TODO", value: "TODO" },
        { label: "In Progress", value: "IN_PROGRESS" },
        { label: "Done", value: "DONE" },
        { label: "Failed", value: "FAILED" },
        { label: "Skipped", value: "SKIPPED" },
      ],
      defaultValue: "",
      action: { type: "filter", target: "task-list", field: "status" },
    },
    {
      id: "type-filter",
      type: "select",
      label: "Type",
      position: { area: "filters", order: 2 },
      options: [
        { label: "All", value: "" },
        { label: "Feature", value: "feature" },
        { label: "Bug", value: "bug" },
        { label: "Chore", value: "chore" },
        { label: "Investigation", value: "investigation" },
      ],
      defaultValue: "",
      action: { type: "filter", target: "task-list", field: "type" },
    },

    // ── Card List ───────────────────────────────────────────────────
    {
      id: "task-list",
      type: "card-list",
      position: { area: "list", order: 1 },
      dataSource: "tasks",
      emptyMessage: "No tasks yet. Create one to get started.",
      filters: [
        { controlId: "status-filter", field: "status", match: "equals" },
        { controlId: "type-filter", field: "type", match: "equals" },
      ],
      card: {
        id: "task-card",
        type: "card",
        onClick: {
          type: "navigate",
          path: "/projects/{slug}/tasks/{row.id}",
        },
        header: [
          {
            id: "task-id-badge",
            type: "badge",
            bind: "id",
            variantMap: {},
          },
          {
            id: "task-status-badge",
            type: "badge",
            bind: "status",
            variantMap: {
              TODO: "warning",
              IN_PROGRESS: "info",
              DONE: "success",
              FAILED: "danger",
              SKIPPED: "default",
              CLAIMING: "info",
            },
          },
          {
            id: "task-type-badge",
            type: "badge",
            bind: "type",
            variantMap: {
              feature: "info",
              bug: "danger",
              chore: "default",
              investigation: "warning",
            },
          },
        ],
        body: [
          {
            id: "task-name",
            type: "text",
            bind: "name",
            variant: "h3",
          },
          {
            id: "task-description",
            type: "text",
            bind: "description",
            variant: "body",
            truncate: 2,
          },
          {
            id: "task-scopes",
            type: "text",
            bind: "scopes",
            variant: "caption",
            description: "Scope tags for this task",
          },
          {
            id: "task-deps",
            type: "text",
            bind: "depends_on",
            variant: "caption",
            description: "Task dependencies",
            visibleWhen: {
              type: "field",
              field: "depends_on",
              operator: "truthy",
            },
          },
        ],
        actions: [
          // Status transition: TODO → IN_PROGRESS
          {
            id: "start-task",
            type: "button",
            label: "Start",
            variant: "primary",
            visibleWhen: {
              type: "field",
              field: "status",
              operator: "equals",
              value: "TODO",
            },
            action: {
              type: "api-call",
              method: "PATCH",
              endpoint: "/projects/{slug}/tasks/{row.id}",
              body: { status: "IN_PROGRESS" },
              onSuccess: "refresh-data",
            },
          },
          // Status transition: IN_PROGRESS → DONE
          {
            id: "complete-task",
            type: "button",
            label: "Done",
            variant: "primary",
            visibleWhen: {
              type: "field",
              field: "status",
              operator: "equals",
              value: "IN_PROGRESS",
            },
            action: {
              type: "api-call",
              method: "POST",
              endpoint: "/projects/{slug}/tasks/{row.id}/complete",
              body: { reasoning: "Completed via UI" },
              onSuccess: "refresh-data",
            },
          },
          // Status transition: IN_PROGRESS → FAILED
          {
            id: "fail-task",
            type: "button",
            label: "Fail",
            variant: "danger",
            visibleWhen: {
              type: "field",
              field: "status",
              operator: "equals",
              value: "IN_PROGRESS",
            },
            action: {
              type: "api-call",
              method: "PATCH",
              endpoint: "/projects/{slug}/tasks/{row.id}",
              body: { status: "FAILED" },
              onSuccess: "refresh-data",
            },
          },
          // Edit button — always visible
          {
            id: "edit-task",
            type: "button",
            label: "Edit",
            variant: "ghost",
            icon: "pencil",
            visibleWhen: {
              type: "field",
              field: "status",
              operator: "in",
              value: ["TODO", "FAILED"],
            },
            action: {
              type: "open-form",
              formId: "task-form",
              prefill: "row",
            },
          },
        ],
      },
    },

    // ── Form Drawer ─────────────────────────────────────────────────
    {
      id: "task-form",
      type: "form-drawer",
      title: "Task",
      position: { area: "sidebar?", order: 1 },
      submitAction: {
        type: "api-call",
        method: "POST",
        endpoint: "/projects/{slug}/tasks",
        onSuccess: "close-form",
        successMessage: "Task created",
      },
      fields: [
        {
          id: "field-name",
          type: "form-field",
          fieldType: "text",
          name: "name",
          label: "Name",
          required: true,
          placeholder: "Task name",
        },
        {
          id: "field-description",
          type: "form-field",
          fieldType: "textarea",
          name: "description",
          label: "Description",
          rows: 4,
          placeholder: "What needs to be done",
        },
        {
          id: "field-instruction",
          type: "form-field",
          fieldType: "textarea",
          name: "instruction",
          label: "Instruction",
          rows: 6,
          placeholder: "Detailed implementation instructions",
        },
        {
          id: "field-type",
          type: "form-field",
          fieldType: "select",
          name: "type",
          label: "Type",
          required: true,
          options: [
            { label: "Feature", value: "feature" },
            { label: "Bug", value: "bug" },
            { label: "Chore", value: "chore" },
            { label: "Investigation", value: "investigation" },
          ],
          defaultValue: "feature",
        },
        {
          id: "field-scopes",
          type: "form-field",
          fieldType: "multi-select",
          name: "scopes",
          label: "Scopes",
          placeholder: "Add scope tags",
        },
        {
          id: "field-depends-on",
          type: "form-field",
          fieldType: "entity-ref",
          name: "depends_on",
          label: "Depends On",
          entityType: "task",
        },
        {
          id: "field-acceptance-criteria",
          type: "form-field",
          fieldType: "dynamic-list",
          name: "acceptance_criteria",
          label: "Acceptance Criteria",
          placeholder: "Add criterion",
        },
      ],
    },
  ],
};
