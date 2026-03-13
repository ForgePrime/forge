import { describe, it, expect } from "vitest";
import { deriveScopesFromElements } from "../deriveScopes";
import type { AIElementDescriptor } from "../types";

describe("deriveScopesFromElements", () => {
  it("extracts scope from project-scoped endpoint", () => {
    const elements: AIElementDescriptor[] = [
      {
        id: "task-list",
        type: "list",
        actions: [
          { label: "Get", endpoint: "/projects/{slug}/tasks", method: "GET" },
        ],
      },
    ];
    expect(deriveScopesFromElements(elements)).toEqual(["tasks"]);
  });

  it("extracts scope from direct endpoint", () => {
    const elements: AIElementDescriptor[] = [
      {
        id: "skills",
        type: "list",
        actions: [
          { label: "Get", endpoint: "/api/skills", method: "GET" },
        ],
      },
    ];
    expect(deriveScopesFromElements(elements)).toEqual(["skills"]);
  });

  it("deduplicates scopes", () => {
    const elements: AIElementDescriptor[] = [
      {
        id: "list",
        type: "list",
        actions: [
          { label: "List", endpoint: "/projects/{slug}/tasks", method: "GET" },
          { label: "Create", endpoint: "/projects/{slug}/tasks", method: "POST" },
        ],
      },
    ];
    expect(deriveScopesFromElements(elements)).toEqual(["tasks"]);
  });

  it("extracts multiple scopes from different elements", () => {
    const elements: AIElementDescriptor[] = [
      {
        id: "tasks",
        type: "list",
        actions: [
          { label: "Get", endpoint: "/projects/{slug}/tasks", method: "GET" },
        ],
      },
      {
        id: "decisions",
        type: "list",
        actions: [
          { label: "Get", endpoint: "/projects/{slug}/decisions", method: "GET" },
        ],
      },
    ];
    const scopes = deriveScopesFromElements(elements);
    expect(scopes).toContain("tasks");
    expect(scopes).toContain("decisions");
  });

  it("returns empty for elements without actions", () => {
    const elements: AIElementDescriptor[] = [
      { id: "display", type: "display", label: "Text" },
    ];
    expect(deriveScopesFromElements(elements)).toEqual([]);
  });

  it("returns empty for actions without endpoints", () => {
    const elements: AIElementDescriptor[] = [
      {
        id: "btn",
        type: "button",
        actions: [{ label: "Click", description: "Does something" }],
      },
    ];
    expect(deriveScopesFromElements(elements)).toEqual([]);
  });

  it("ignores projects and api as scopes", () => {
    const elements: AIElementDescriptor[] = [
      {
        id: "proj",
        type: "list",
        actions: [
          { label: "Get", endpoint: "/projects", method: "GET" },
          { label: "Api", endpoint: "/api", method: "GET" },
        ],
      },
    ];
    expect(deriveScopesFromElements(elements)).toEqual([]);
  });

  it("handles endpoints without /api/ prefix", () => {
    const elements: AIElementDescriptor[] = [
      {
        id: "settings",
        type: "form",
        actions: [
          { label: "Save", endpoint: "/settings/llm", method: "PUT" },
        ],
      },
    ];
    expect(deriveScopesFromElements(elements)).toEqual(["settings"]);
  });

  it("works with Map values (Iterable)", () => {
    const map = new Map<string, AIElementDescriptor>();
    map.set("tasks", {
      id: "tasks",
      type: "list",
      actions: [
        { label: "Get", endpoint: "/projects/{slug}/tasks", method: "GET" },
      ],
    });
    expect(deriveScopesFromElements(map.values())).toEqual(["tasks"]);
  });
});
