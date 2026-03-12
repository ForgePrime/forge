import { create } from "zustand";
import { createEntityStore, withCreateLoading, withUpdate } from "./factory";
import { skills as skillsApi } from "@/lib/api";
import type { Skill, SkillCreate, SkillUpdate, SkillGitStatus } from "@/lib/types";
import { trackMutation } from "@/lib/mutationTracker";

// ---------------------------------------------------------------------------
// Main entity store (skills list)
// ---------------------------------------------------------------------------

export const useSkillStore = createEntityStore<Skill>({
  // Skills are global — slug is ignored by the API client
  listFn: (_slug, params) => skillsApi.list(params),
  responseKey: "skills",
  getItemId: (item) => item.name,
  wsEvents: {
    "skill.created": { op: "create", idKey: "name" },
    "skill.updated": { op: "update", idKey: "name" },
    "skill.deleted": { op: "remove", idKey: "name" },
    "skill.promoted": { op: "update", idKey: "name" },
    "skill.synced": { op: "replace" },
  },
});

// ---------------------------------------------------------------------------
// Git sync state (separate store)
// ---------------------------------------------------------------------------

interface GitSyncState {
  status: SkillGitStatus | null;
  syncing: boolean;
  lastSynced: string | null;
  error: string | null;
  fetchStatus: () => Promise<void>;
  setSyncing: (v: boolean) => void;
}

export const useGitSyncStore = create<GitSyncState>((set) => ({
  status: null,
  syncing: false,
  lastSynced: null,
  error: null,

  fetchStatus: async () => {
    try {
      const status = await skillsApi.gitStatus();
      set({ status, error: null });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  setSyncing: (v: boolean) => set({ syncing: v }),
}));

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

/** Fetch all skills (global — no slug needed). */
export async function fetchSkills(params?: Record<string, string>): Promise<void> {
  return useSkillStore.getState().fetchAll("_global", params);
}

export async function createSkill(data: SkillCreate): Promise<Skill> {
  const result = await skillsApi.create(data);
  // Refresh list
  await fetchSkills();
  return result;
}

export async function updateSkill(name: string, data: SkillUpdate): Promise<void> {
  return withUpdate(
    useSkillStore,
    (item) => item.name,
    name,
    () => skillsApi.update(name, data),
    data,
  );
}

export async function removeSkill(name: string): Promise<void> {
  const prev = useSkillStore.getState().items;
  const filtered = prev.filter((item) => item.name !== name);
  useSkillStore.setState({ items: filtered, count: filtered.length });
  try {
    await skillsApi.remove(name);
    trackMutation(name);
  } catch (e) {
    useSkillStore.setState({ items: prev, count: prev.length, error: (e as Error).message });
  }
}

// ---------------------------------------------------------------------------
// Git sync actions
// ---------------------------------------------------------------------------

export async function gitPull(): Promise<void> {
  const store = useGitSyncStore.getState();
  store.setSyncing(true);
  try {
    await skillsApi.gitPull();
    await fetchSkills();
    useGitSyncStore.setState({
      syncing: false,
      lastSynced: new Date().toISOString(),
    });
  } catch (e) {
    useGitSyncStore.setState({
      syncing: false,
      error: (e as Error).message,
    });
    throw e;
  }
}

export async function gitPush(message?: string): Promise<void> {
  const store = useGitSyncStore.getState();
  store.setSyncing(true);
  try {
    await skillsApi.gitPush(message);
    useGitSyncStore.setState({
      syncing: false,
      lastSynced: new Date().toISOString(),
    });
  } catch (e) {
    useGitSyncStore.setState({
      syncing: false,
      error: (e as Error).message,
    });
    throw e;
  }
}

export async function gitScan(): Promise<void> {
  await skillsApi.gitScan();
  await fetchSkills();
}
