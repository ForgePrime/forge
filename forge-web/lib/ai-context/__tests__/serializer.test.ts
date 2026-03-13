import { describe, it, expect } from "vitest";
import { serializePageContext } from "../serializer";
import type { AIContextSnapshot, AIElementDescriptor, AIPageConfig } from "../types";

function makeSnapshot(
  elements: AIElementDescriptor[],
  pageConfig?: AIPageConfig | null,
): AIContextSnapshot {
  const map = new Map<string, AIElementDescriptor>();
  for (const el of elements) {
    map.set(el.id, el);
  }
  return { pageConfig: pageConfig ?? null, elements: map };
}

describe("serializePageContext", () => {
  it("serializes page header", () => {
    const result = serializePageContext(
      makeSnapshot([], { id: "tasks", title: "Tasks", description: "Task list" }),
    );
    expect(result).toContain("Page: Tasks — Task list");
  });

  it("serializes page without description", () => {
    const result = serializePageContext(
      makeSnapshot([], { id: "tasks", title: "Tasks" }),
    );
    expect(result).toContain("Page: Tasks");
    expect(result).not.toContain("—");
  });

  it("serializes filter element with value", () => {
    const result = serializePageContext(
      makeSnapshot([
        { id: "status-filter", type: "filter", label: "Status", value: "TODO" },
      ]),
    );
    expect(result).toContain('[filter] Status = "TODO"');
  });

  it("serializes button element", () => {
    const result = serializePageContext(
      makeSnapshot([
        {
          id: "new-task",
          type: "button",
          label: "New Task",
          actions: [
            { label: "Create", endpoint: "/projects/{slug}/tasks", method: "POST" },
          ],
        },
      ]),
    );
    expect(result).toContain("[button] New Task");
    expect(result).toContain("actions: Create (POST /projects/{slug}/tasks)");
  });

  it("serializes list with data summary", () => {
    const result = serializePageContext(
      makeSnapshot([
        {
          id: "task-list",
          type: "list",
          label: "Tasks",
          description: "42 items",
          data: {
            count: 42,
            statuses: { TODO: 10, DONE: 20, IN_PROGRESS: 12 },
          },
        },
      ]),
    );
    expect(result).toContain("[list] Tasks");
    expect(result).toContain("42 items");
    expect(result).toContain("count: 42");
    expect(result).toContain("TODO: 10");
  });

  it("serializes form element", () => {
    const result = serializePageContext(
      makeSnapshot([
        {
          id: "task-form",
          type: "form",
          label: "Task Form",
          value: false,
          description: "closed",
          actions: [
            { label: "Submit", endpoint: "/projects/{slug}/tasks", method: "POST" },
          ],
        },
      ]),
    );
    expect(result).toContain("[form] Task Form");
    expect(result).toContain("closed");
    expect(result).toContain("Submit (POST");
  });

  it("serializes actions with availability", () => {
    const result = serializePageContext(
      makeSnapshot([
        {
          id: "task-actions",
          type: "action",
          label: "Task Actions",
          actions: [
            {
              label: "Start",
              endpoint: "/projects/{slug}/tasks/{id}",
              method: "PATCH",
              available: true,
              availableWhen: "status = TODO",
            },
            {
              label: "Done",
              endpoint: "/projects/{slug}/tasks/{id}",
              method: "PATCH",
              available: false,
            },
          ],
        },
      ]),
    );
    expect(result).toContain("Start (PATCH");
    expect(result).toContain("[when: status = TODO]");
    expect(result).toContain("Done (PATCH");
    expect(result).toContain("[disabled]");
  });

  it("truncates at maxChars", () => {
    const elements: AIElementDescriptor[] = [];
    for (let i = 0; i < 100; i++) {
      elements.push({
        id: `el-${i}`,
        type: "display",
        label: `Element ${i} with a very long description that takes up space`,
        description: "This is a detailed description that adds more characters",
      });
    }
    const result = serializePageContext(makeSnapshot(elements), {
      maxChars: 500,
    });
    expect(result.length).toBeLessThanOrEqual(500);
    expect(result).toContain("truncated");
  });

  it("serializes empty snapshot", () => {
    const result = serializePageContext(makeSnapshot([]));
    expect(result).toBe("");
  });

  it("serializes data arrays with maxItems limit", () => {
    const result = serializePageContext(
      makeSnapshot([
        {
          id: "items",
          type: "list",
          label: "Items",
          data: {
            ids: ["A", "B", "C", "D", "E", "F"],
          },
        },
      ]),
      { maxItems: 3 },
    );
    expect(result).toContain("A, B, C");
    expect(result).toContain("+3 more");
  });

  it("omits zero values in data objects", () => {
    const result = serializePageContext(
      makeSnapshot([
        {
          id: "stats",
          type: "display",
          label: "Stats",
          data: {
            statuses: { TODO: 5, DONE: 0, FAILED: 0 },
          },
        },
      ]),
    );
    expect(result).toContain("TODO: 5");
    expect(result).not.toContain("DONE: 0");
    expect(result).not.toContain("FAILED: 0");
  });

  it("handles element with no value, actions, or data", () => {
    const result = serializePageContext(
      makeSnapshot([
        { id: "simple", type: "display", label: "Just Text" },
      ]),
    );
    expect(result).toContain("[display] Just Text");
    expect(result).not.toContain("actions:");
  });

  it("uses id as fallback when label is missing", () => {
    const result = serializePageContext(
      makeSnapshot([{ id: "my-element", type: "section" }]),
    );
    expect(result).toContain("[section] my-element");
  });

  it("full integration: tasks page snapshot", () => {
    const result = serializePageContext(
      makeSnapshot(
        [
          { id: "status-filter", type: "filter", label: "Status", value: "TODO" },
          {
            id: "task-list",
            type: "list",
            label: "Tasks",
            description: "Project task list",
            data: {
              count: 42,
              filtered: 10,
              statuses: { TODO: 10, IN_PROGRESS: 8, DONE: 20, FAILED: 4 },
            },
            actions: [
              { label: "Start", endpoint: "/projects/{slug}/tasks/{id}", method: "PATCH", availableWhen: "status = TODO" },
              { label: "Done", endpoint: "/projects/{slug}/tasks/{id}", method: "PATCH", availableWhen: "status = IN_PROGRESS" },
              { label: "Create", endpoint: "/projects/{slug}/tasks", method: "POST" },
            ],
          },
          {
            id: "task-form",
            type: "form",
            label: "Task Form",
            value: false,
            description: "closed",
            data: { fields: ["name*", "description", "type*", "scopes"] },
            actions: [
              { label: "Submit", endpoint: "/projects/{slug}/tasks", method: "POST" },
            ],
          },
        ],
        { id: "tasks", title: "Tasks", description: "Task management for project" },
      ),
    );

    expect(result).toContain("Page: Tasks — Task management for project");
    expect(result).toContain('[filter] Status = "TODO"');
    expect(result).toContain("[list] Tasks");
    expect(result).toContain("count: 42");
    expect(result).toContain("TODO: 10");
    expect(result).toContain("Start (PATCH");
    expect(result).toContain("[form] Task Form");
  });
});
