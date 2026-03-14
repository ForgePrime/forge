/**
 * Zustand store for workflow execution state (O-001).
 *
 * Manages workflow executions, handles WebSocket events for real-time
 * updates, and provides actions for start/resume/cancel.
 */
import { create } from "zustand";
import { workflows as workflowsApi, ApiError } from "@/lib/api";
import type { WorkflowExecution, WorkflowExecutionStatus } from "@/lib/types";
import type { ForgeEvent } from "@/lib/ws";

interface WorkflowState {
  /** All loaded executions, keyed by ext_id. */
  executions: Record<string, WorkflowExecution>;
  /** Currently selected/active execution ext_id. */
  activeExtId: string | null;
  /** Loading state. */
  loading: boolean;
  /** Last error message. */
  error: string | null;

  // Actions
  fetchList: (slug: string, status?: string) => Promise<void>;
  fetchOne: (slug: string, extId: string) => Promise<void>;
  startWorkflow: (
    slug: string,
    definitionId: string,
    objectiveId?: string,
    variables?: Record<string, unknown>,
  ) => Promise<WorkflowExecution | null>;
  resumeWorkflow: (slug: string, extId: string, userResponse: unknown) => Promise<void>;
  cancelWorkflow: (slug: string, extId: string) => Promise<void>;
  setActive: (extId: string | null) => void;
  handleWsEvent: (event: ForgeEvent) => void;
  reset: () => void;
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  executions: {},
  activeExtId: null,
  loading: false,
  error: null,

  fetchList: async (slug, status) => {
    set({ loading: true, error: null });
    try {
      const params = status ? { status } : undefined;
      const res = await workflowsApi.list(slug, params);
      const map: Record<string, WorkflowExecution> = {};
      for (const ex of res.workflows) {
        map[ex.ext_id] = ex;
      }
      set({ executions: map, loading: false });
    } catch (e) {
      set({ loading: false, error: (e as Error).message });
    }
  },

  fetchOne: async (slug, extId) => {
    try {
      const ex = await workflowsApi.get(slug, extId);
      set((s) => ({
        executions: { ...s.executions, [ex.ext_id]: ex },
      }));
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return;
      set({ error: (e as Error).message });
    }
  },

  startWorkflow: async (slug, definitionId, objectiveId, variables) => {
    set({ loading: true, error: null });
    try {
      const ex = await workflowsApi.start(slug, {
        definition_id: definitionId,
        objective_id: objectiveId,
        variables,
      });
      set((s) => ({
        executions: { ...s.executions, [ex.ext_id]: ex },
        activeExtId: ex.ext_id,
        loading: false,
      }));
      return ex;
    } catch (e) {
      set({ loading: false, error: (e as Error).message });
      return null;
    }
  },

  resumeWorkflow: async (slug, extId, userResponse) => {
    set({ error: null });
    try {
      const ex = await workflowsApi.resume(slug, extId, userResponse);
      set((s) => ({
        executions: { ...s.executions, [ex.ext_id]: ex },
      }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  cancelWorkflow: async (slug, extId) => {
    set({ error: null });
    try {
      const ex = await workflowsApi.cancel(slug, extId);
      set((s) => ({
        executions: { ...s.executions, [ex.ext_id]: ex },
      }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  setActive: (extId) => set({ activeExtId: extId }),

  handleWsEvent: (event) => {
    const payload = event.payload as Record<string, unknown>;
    const extId = payload.execution_id as string | undefined;
    if (!extId) return;

    const current = get().executions[extId];
    if (!current) return;

    const status = payload.status as WorkflowExecutionStatus | undefined;
    const stepId = payload.step_id as string | undefined;
    const error = payload.error as string | undefined;
    const pauseReason = payload.pause_reason as string | undefined;

    // Build partial update
    const updated: WorkflowExecution = { ...current };
    if (status) updated.status = status;
    if (stepId) updated.current_step = stepId;
    if (error !== undefined) updated.error = error;
    if (pauseReason !== undefined) updated.pause_reason = pauseReason;
    updated.updated_at = payload.timestamp as string ?? new Date().toISOString();

    // Update step result status from step events
    if (stepId && (
      event.event === "workflow.step_started" ||
      event.event === "workflow.step_completed"
    )) {
      const stepStatus = event.event === "workflow.step_completed" ? "completed" : "running";
      const existingStep = current.step_results[stepId];
      updated.step_results = {
        ...current.step_results,
        [stepId]: {
          step_id: stepId,
          status: stepStatus,
          started_at: existingStep?.started_at ?? new Date().toISOString(),
          completed_at: stepStatus === "completed" ? new Date().toISOString() : null,
          output: existingStep?.output ?? null,
          session_id: existingStep?.session_id ?? null,
          error: null,
          decision_ids: existingStep?.decision_ids ?? [],
          retries: existingStep?.retries ?? 0,
        },
      };
    }

    // Terminal states
    if (status === "completed" || status === "failed" || status === "cancelled") {
      updated.completed_at = new Date().toISOString();
    }

    set((s) => ({
      executions: { ...s.executions, [extId]: updated },
    }));
  },

  reset: () => set({ executions: {}, activeExtId: null, loading: false, error: null }),
}));
