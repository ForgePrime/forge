import { create } from "zustand";
import {
  projects as projectsApi,
} from "../lib/api";
import type { ProjectDetail, ProjectStatus, ProjectCreate } from "../lib/types";

interface ProjectState {
  /** List of project slugs. */
  slugs: string[];
  /** Currently selected project slug. */
  currentSlug: string | null;
  /** Cached project details keyed by slug. */
  details: Record<string, ProjectDetail>;
  /** Cached project status keyed by slug. */
  statuses: Record<string, ProjectStatus>;
  /** Loading states. */
  loading: boolean;
  error: string | null;

  // Actions
  fetchProjects: () => Promise<void>;
  selectProject: (slug: string) => Promise<void>;
  fetchStatus: (slug: string) => Promise<void>;
  createProject: (data: ProjectCreate) => Promise<string>;
  clearError: () => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  slugs: [],
  currentSlug: null,
  details: {},
  statuses: {},
  loading: false,
  error: null,

  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const res = await projectsApi.list();
      set({ slugs: res.projects, loading: false });
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
    }
  },

  selectProject: async (slug: string) => {
    set({ currentSlug: slug, loading: true, error: null });
    try {
      const detail = await projectsApi.get(slug);
      // Discard if user navigated to a different project while loading
      if (get().currentSlug !== slug) return;
      set((s) => ({
        details: { ...s.details, [slug]: detail },
        loading: false,
      }));
    } catch (e) {
      if (get().currentSlug !== slug) return;
      set({ error: (e as Error).message, loading: false });
    }
  },

  fetchStatus: async (slug: string) => {
    try {
      const status = await projectsApi.status(slug);
      set((s) => ({
        statuses: { ...s.statuses, [slug]: status },
      }));
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  createProject: async (data: ProjectCreate) => {
    set({ loading: true, error: null });
    try {
      const res = await projectsApi.create(data);
      // Optimistic: add slug to list
      set((s) => ({
        slugs: [...s.slugs, res.project],
        loading: false,
      }));
      return res.project;
    } catch (e) {
      set({ error: (e as Error).message, loading: false });
      throw e;
    }
  },

  clearError: () => set({ error: null }),
}));
