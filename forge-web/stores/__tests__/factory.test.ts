import { createEntityStore, withCreateLoading, withUpdate } from "../factory";
import type { ForgeEvent } from "@/lib/ws";

function wsEvent(event: string, payload: Record<string, unknown>): ForgeEvent {
  return { event, payload, project: "test", timestamp: new Date().toISOString() } as ForgeEvent;
}

interface TestItem {
  id: string;
  name: string;
  status?: string;
}

function makeStore() {
  return createEntityStore<TestItem>({
    listFn: vi.fn().mockResolvedValue({ things: [{ id: "1", name: "A" }], count: 1 }),
    responseKey: "things",
    getItemId: (item) => item.id,
    wsEvents: {
      "item.created": { op: "create" },
      "item.updated": { op: "update", idKey: "item_id" },
      "item.removed": { op: "remove" },
      "item.replaced": { op: "replace" },
    },
  });
}

describe("createEntityStore", () => {
  it("starts with empty state", () => {
    const store = makeStore();
    const state = store.getState();
    expect(state.items).toEqual([]);
    expect(state.count).toBe(0);
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it("fetchAll loads items", async () => {
    const store = makeStore();
    await store.getState().fetchAll("test-project");
    const state = store.getState();
    expect(state.items).toEqual([{ id: "1", name: "A" }]);
    expect(state.count).toBe(1);
    expect(state.loading).toBe(false);
  });

  it("fetchAll handles errors", async () => {
    const store = createEntityStore<TestItem>({
      listFn: vi.fn().mockRejectedValue(new Error("network error")),
      responseKey: "things",
      getItemId: (item) => item.id,
      wsEvents: {},
    });
    await store.getState().fetchAll("slug");
    expect(store.getState().error).toBe("network error");
    expect(store.getState().loading).toBe(false);
  });

  it("fetchAll discards stale responses", async () => {
    let resolveFirst: (v: unknown) => void;
    const firstCall = new Promise((r) => { resolveFirst = r; });
    let callCount = 0;
    const store = createEntityStore<TestItem>({
      listFn: vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount === 1) return firstCall;
        return Promise.resolve({ things: [{ id: "2", name: "B" }], count: 1 });
      }),
      responseKey: "things",
      getItemId: (item) => item.id,
      wsEvents: {},
    });
    // Start first fetch (will be stale)
    const p1 = store.getState().fetchAll("slug");
    // Start second fetch (supersedes first)
    const p2 = store.getState().fetchAll("slug");
    await p2;
    // Resolve first after second completes
    resolveFirst!({ things: [{ id: "1", name: "stale" }], count: 1 });
    await p1;
    // Should have second result, not stale first
    expect(store.getState().items).toEqual([{ id: "2", name: "B" }]);
  });

  it("handleWsEvent create adds item", () => {
    const store = makeStore();
    store.getState().handleWsEvent(wsEvent("item.created", { id: "2", name: "B" }));
    expect(store.getState().items).toEqual([{ id: "2", name: "B" }]);
    expect(store.getState().count).toBe(1);
  });

  it("handleWsEvent create skips duplicates", () => {
    const store = makeStore();
    store.setState({ items: [{ id: "1", name: "A" }], count: 1 });
    store.getState().handleWsEvent(wsEvent("item.created", { id: "1", name: "A2" }));
    expect(store.getState().items).toHaveLength(1);
    expect(store.getState().items[0].name).toBe("A");
  });

  it("handleWsEvent update merges payload", () => {
    const store = makeStore();
    store.setState({ items: [{ id: "1", name: "A" }], count: 1 });
    store.getState().handleWsEvent(wsEvent("item.updated", { item_id: "1", name: "A-updated" }));
    expect(store.getState().items[0].name).toBe("A-updated");
  });

  it("handleWsEvent update maps new_status to status", () => {
    const store = makeStore();
    store.setState({
      items: [{ id: "1", name: "A", status: "TODO" }],
      count: 1,
    });
    store.getState().handleWsEvent(
      wsEvent("item.updated", { item_id: "1", new_status: "DONE", old_status: "TODO" }),
    );
    expect(store.getState().items[0].status).toBe("DONE");
  });

  it("handleWsEvent remove filters out item", () => {
    const store = makeStore();
    store.setState({
      items: [{ id: "1", name: "A" }, { id: "2", name: "B" }],
      count: 2,
    });
    store.getState().handleWsEvent(wsEvent("item.removed", { id: "1" }));
    expect(store.getState().items).toEqual([{ id: "2", name: "B" }]);
    expect(store.getState().count).toBe(1);
  });

  it("handleWsEvent replace swaps entire array", () => {
    const store = makeStore();
    store.setState({ items: [{ id: "1", name: "A" }], count: 1 });
    store.getState().handleWsEvent(
      wsEvent("item.replaced", { things: [{ id: "3", name: "C" }, { id: "4", name: "D" }] }),
    );
    expect(store.getState().items).toHaveLength(2);
    expect(store.getState().count).toBe(2);
  });

  it("handleWsEvent ignores unknown events", () => {
    const store = makeStore();
    store.setState({ items: [{ id: "1", name: "A" }], count: 1 });
    store.getState().handleWsEvent(wsEvent("unknown.event", {}));
    expect(store.getState().items).toHaveLength(1);
  });

  it("clear resets state", () => {
    const store = makeStore();
    store.setState({ items: [{ id: "1", name: "A" }], count: 1, loading: true, error: "x" });
    store.getState().clear();
    expect(store.getState().items).toEqual([]);
    expect(store.getState().count).toBe(0);
    expect(store.getState().loading).toBe(false);
    expect(store.getState().error).toBeNull();
  });
});

describe("withCreateLoading", () => {
  it("sets loading and returns added IDs", async () => {
    const store = makeStore();
    const result = await withCreateLoading(store, () =>
      Promise.resolve({ added: ["x1", "x2"], total: 2 }),
    );
    expect(result).toEqual(["x1", "x2"]);
    expect(store.getState().loading).toBe(false);
  });

  it("sets error on failure", async () => {
    const store = makeStore();
    await expect(
      withCreateLoading(store, () => Promise.reject(new Error("fail"))),
    ).rejects.toThrow("fail");
    expect(store.getState().error).toBe("fail");
    expect(store.getState().loading).toBe(false);
  });
});

describe("withUpdate", () => {
  it("replaces item in-place", async () => {
    const store = makeStore();
    store.setState({ items: [{ id: "1", name: "old" }], count: 1 });
    await withUpdate(
      store,
      (item) => item.id,
      "1",
      () => Promise.resolve({ id: "1", name: "new" }),
    );
    expect(store.getState().items[0].name).toBe("new");
  });
});
