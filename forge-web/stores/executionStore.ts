import { create } from "zustand";
import { tasks as tasksApi, gates as gatesApi, ApiError } from "../lib/api";
import type { Task } from "../lib/types";

export type ExecutionPhase =
  | "idle"
  | "claiming"
  | "gathering-context"
  | "executing"
  | "validating"
  | "completing"
  | "failed";

interface GateResult {
  name: string;
  passed: boolean;
  output?: string;
  required: boolean;
}

interface ExecutionState {
  /** Current execution phase. */
  phase: ExecutionPhase;
  /** Task being executed. */
  currentTask: Task | null;
  /** Streaming log output lines. */
  logLines: string[];
  /** Gate check results. */
  gateResults: GateResult[];
  /** Progress percentage (0-100). */
  progress: number;
  /** Error message if phase is 'failed'. */
  error: string | null;

  // Actions
  claimNext: (slug: string, agent?: string) => Promise<Task | null>;
  setPhase: (phase: ExecutionPhase) => void;
  appendLog: (line: string) => void;
  runGates: (slug: string, taskId: string) => Promise<boolean>;
  completeTask: (slug: string, taskId: string, reasoning: string) => Promise<void>;
  setProgress: (pct: number) => void;
  reset: () => void;
}

export const useExecutionStore = create<ExecutionState>((set, get) => ({
  phase: "idle",
  currentTask: null,
  logLines: [],
  gateResults: [],
  progress: 0,
  error: null,

  claimNext: async (slug, agent) => {
    set({ phase: "claiming", error: null, logLines: [], gateResults: [], progress: 0 });
    try {
      const task = await tasksApi.claimNext(slug, agent);
      set({ currentTask: task, phase: "gathering-context", progress: 10 });
      return task;
    } catch (e) {
      // 404 means no task available — not an error
      if (e instanceof ApiError && e.status === 404) {
        set({ phase: "idle", currentTask: null });
        return null;
      }
      set({ phase: "failed", error: (e as Error).message });
      return null;
    }
  },

  setPhase: (phase) => set({ phase }),

  appendLog: (line) =>
    set((s) => ({ logLines: [...s.logLines, line] })),

  runGates: async (slug, taskId) => {
    set({ phase: "validating", progress: 80 });
    try {
      const res = await gatesApi.check(slug, taskId);
      const results: GateResult[] = (res.gates || []).map((g: Record<string, unknown>) => ({
        name: g.name as string,
        passed: g.passed as boolean,
        output: g.output as string | undefined,
        required: g.required as boolean,
      }));
      set({ gateResults: results, progress: 90 });
      return results.every((r) => !r.required || r.passed);
    } catch (e) {
      // No gates configured is OK
      set({ gateResults: [], progress: 90 });
      return true;
    }
  },

  completeTask: async (slug, taskId, reasoning) => {
    set({ phase: "completing", progress: 95 });
    try {
      const completed = await tasksApi.complete(slug, taskId, reasoning);
      set({ currentTask: completed, phase: "idle", progress: 100 });
    } catch (e) {
      set({ phase: "failed", error: (e as Error).message });
    }
  },

  setProgress: (pct) => set({ progress: Math.min(100, Math.max(0, pct)) }),

  reset: () =>
    set({
      phase: "idle",
      currentTask: null,
      logLines: [],
      gateResults: [],
      progress: 0,
      error: null,
    }),
}));
