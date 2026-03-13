/**
 * Integration test: Full AI annotations pipeline.
 *
 * Simulates: page annotations → serialization → scope derivation → chat context.
 */
import React from "react";
import { renderHook, act } from "@testing-library/react";
import { AIPageProvider, useAIPageContextSafe } from "../AIPageProvider";
import { useAIPage } from "../useAIPage";
import { useAIElement } from "../useAIElement";
import { serializePageContext } from "../serializer";
import { deriveScopesFromElements } from "../deriveScopes";
import type { AIContextSnapshot } from "../types";

// Wrapper that provides AIPageProvider + captures context for lazy snapshot access
function createTestHarness() {
  let ctxRef: ReturnType<typeof useAIPageContextSafe> = null;

  function ContextCapture() {
    ctxRef = useAIPageContextSafe();
    return null;
  }

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <AIPageProvider>
        {children}
        <ContextCapture />
      </AIPageProvider>
    );
  }

  return {
    Wrapper,
    // Call getSnapshot() lazily — after effects have run
    getSnapshot: () => ctxRef?.getSnapshot() ?? null,
  };
}

describe("AI Annotations Integration", () => {
  it("simulates TasksPage annotation flow end-to-end", () => {
    const { Wrapper, getSnapshot } = createTestHarness();

    // Simulate what TasksPage does: useAIPage + 3x useAIElement
    function useTasksPageAnnotations() {
      useAIPage({
        id: "tasks",
        title: "Tasks (25)",
        description: "Task list for project my-project",
        route: "/projects/my-project/tasks",
      });

      useAIElement({
        id: "status-filter",
        type: "filter",
        label: "Status Filter",
        value: "TODO",
        actions: [{ label: "Filter", description: "Filter tasks by status" }],
      });

      useAIElement({
        id: "task-list",
        type: "list",
        label: "Tasks",
        description: "8 shown of 25 total",
        data: {
          count: 25,
          filtered: 8,
          statuses: { TODO: 8, IN_PROGRESS: 5, DONE: 12 },
        },
        actions: [
          {
            label: "Start",
            endpoint: "/projects/{slug}/tasks/{id}",
            method: "PATCH",
            availableWhen: "status = TODO",
          },
          {
            label: "Create",
            endpoint: "/projects/{slug}/tasks",
            method: "POST",
          },
        ],
      });

      useAIElement({
        id: "task-form",
        type: "form",
        label: "Task Form",
        value: false,
        description: "closed",
        data: {
          fields: ["name*", "description", "type*"],
        },
      });
    }

    renderHook(() => useTasksPageAnnotations(), { wrapper: Wrapper });

    // Get snapshot and verify it's populated
    const snap = getSnapshot();
    expect(snap).not.toBeNull();
    expect(snap!.pageConfig).not.toBeNull();
    expect(snap!.pageConfig!.title).toBe("Tasks (25)");
    expect(snap!.elements.size).toBe(3);

    // Serialize context (what AISidebar does)
    const serialized = serializePageContext(snap!);
    expect(serialized).toContain("Page: Tasks (25)");
    expect(serialized).toContain("[filter] Status Filter");
    expect(serialized).toContain("[list] Tasks");
    expect(serialized).toContain("TODO: 8");
    expect(serialized).toContain("IN_PROGRESS: 5");
    expect(serialized).toContain("DONE: 12");
    expect(serialized).toContain("[form] Task Form");
    expect(serialized).toContain("PATCH /projects/{slug}/tasks/{id}");
    expect(serialized).toContain("POST /projects/{slug}/tasks");

    // Derive scopes (what AISidebar does)
    const scopes = deriveScopesFromElements(snap!.elements.values());
    expect(scopes).toContain("tasks");
    expect(scopes).toHaveLength(1); // only "tasks" module

    // Verify serialized output is under default limit
    expect(serialized.length).toBeLessThanOrEqual(4000);
  });

  it("simulates DecisionsPage annotation flow", () => {
    const { Wrapper, getSnapshot } = createTestHarness();

    function useDecisionsAnnotations() {
      useAIPage({
        id: "decisions",
        title: "Decisions (10)",
        description: "Decision log for project test-proj",
        route: "/projects/test-proj/decisions",
      });

      useAIElement({
        id: "decision-list",
        type: "list",
        label: "Decisions",
        description: "3 shown of 10 total",
        data: {
          count: 10,
          filtered: 3,
          statuses: { OPEN: 3, CLOSED: 5, DEFERRED: 2 },
        },
        actions: [
          { label: "Close", endpoint: "/projects/{slug}/decisions/{id}", method: "PATCH" },
          { label: "Create", endpoint: "/projects/{slug}/decisions", method: "POST" },
        ],
      });
    }

    renderHook(() => useDecisionsAnnotations(), { wrapper: Wrapper });
    const snap = getSnapshot()!;

    const serialized = serializePageContext(snap);
    expect(serialized).toContain("Page: Decisions (10)");
    expect(serialized).toContain("[list] Decisions");
    expect(serialized).toContain("OPEN: 3");

    const scopes = deriveScopesFromElements(snap.elements.values());
    expect(scopes).toContain("decisions");
  });

  it("simulates page navigation (unmount old page, mount new)", () => {
    const { Wrapper, getSnapshot } = createTestHarness();

    // First render: Tasks page
    const { unmount } = renderHook(
      () => {
        useAIPage({
          id: "tasks",
          title: "Tasks (5)",
          route: "/projects/p/tasks",
        });
        useAIElement({ id: "task-list", type: "list", label: "Tasks" });
      },
      { wrapper: Wrapper },
    );

    let snap = getSnapshot()!;
    expect(snap.pageConfig!.id).toBe("tasks");
    expect(snap.elements.size).toBe(1);
    expect(snap.elements.has("task-list")).toBe(true);

    // Navigate away — unmount tasks page
    unmount();

    // Mount ideas page
    renderHook(
      () => {
        useAIPage({
          id: "ideas",
          title: "Ideas (3)",
          route: "/projects/p/ideas",
        });
        useAIElement({ id: "idea-list", type: "list", label: "Ideas" });
      },
      { wrapper: Wrapper },
    );

    snap = getSnapshot()!;
    expect(snap.pageConfig!.id).toBe("ideas");
    // Old task-list should be cleaned up, only idea-list present
    expect(snap.elements.has("task-list")).toBe(false);
    expect(snap.elements.has("idea-list")).toBe(true);
    expect(snap.elements.size).toBe(1);
  });

  it("handles empty annotations gracefully (no crash, empty serialization)", () => {
    const { Wrapper, getSnapshot } = createTestHarness();

    renderHook(() => {}, { wrapper: Wrapper });

    const snap = getSnapshot()!;
    expect(snap.elements.size).toBe(0);
    expect(snap.pageConfig).toBeNull();

    const serialized = serializePageContext(snap);
    expect(serialized).toBe("");
  });

  it("constructs valid ChatRequest page_context payload", () => {
    const { Wrapper, getSnapshot } = createTestHarness();

    function useAnnotations() {
      useAIPage({
        id: "objectives",
        title: "Objectives (2)",
        description: "Business objectives for project forge",
        route: "/projects/forge/objectives",
      });
      useAIElement({
        id: "objective-list",
        type: "list",
        label: "Objectives",
        data: { count: 2, statuses: { ACTIVE: 1, ACHIEVED: 1 } },
        actions: [
          { label: "Update", endpoint: "/projects/{slug}/objectives/{id}", method: "PATCH" },
        ],
      });
    }

    renderHook(() => useAnnotations(), { wrapper: Wrapper });

    const snap = getSnapshot()!;
    const pageContext = snap.elements.size > 0 ? serializePageContext(snap) : undefined;

    // Simulate ChatRequest construction
    const chatRequest = {
      message: "What objectives are active?",
      context_type: "global",
      context_id: "",
      project: "forge",
      session_id: null,
      page_context: pageContext,
    };

    expect(chatRequest.page_context).toBeDefined();
    expect(chatRequest.page_context).toContain("Page: Objectives (2)");
    expect(chatRequest.page_context).toContain("ACTIVE: 1");
    // Backend max_length is 8000
    expect(chatRequest.page_context!.length).toBeLessThan(8000);
  });
});
