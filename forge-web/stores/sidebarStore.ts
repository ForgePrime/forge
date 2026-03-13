/**
 * Sidebar store — persistent state for the AI sidebar.
 *
 * Manages scope overrides, disabled capabilities, active tab,
 * and route visibility. Persisted to localStorage.
 */
import { create } from "zustand";

const STORAGE_KEY = "forge-ai-sidebar";

type SidebarTab = "chat" | "tools" | "scopes" | "conversations" | "debug";

interface SidebarState {
  /** Extra scopes added by user (beyond auto-detected). */
  addedScopes: string[];
  /** Scopes removed by user (overriding auto-detection). */
  removedScopes: string[];
  /** Capability IDs toggled off by user. */
  disabledCapabilities: string[];
  /** Currently active tab. */
  activeTab: SidebarTab;
  /** Route prefixes where sidebar is hidden. */
  hiddenRoutes: string[];
  /** Whether localStorage has been read. */
  _hydrated: boolean;
}

interface SidebarActions {
  hydrate: () => void;
  addScope: (scope: string) => void;
  removeScope: (scope: string) => void;
  resetScopes: () => void;
  toggleCapability: (capabilityId: string, enabled: boolean) => void;
  setActiveTab: (tab: SidebarTab) => void;
  toggleRouteVisibility: (route: string) => void;
  isRouteHidden: (pathname: string) => boolean;
}

function persist(state: SidebarState) {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        addedScopes: state.addedScopes,
        removedScopes: state.removedScopes,
        disabledCapabilities: state.disabledCapabilities,
        activeTab: state.activeTab,
        hiddenRoutes: state.hiddenRoutes,
      }),
    );
  } catch {
    // localStorage unavailable (SSR)
  }
}

export const useSidebarStore = create<SidebarState & SidebarActions>((set, get) => ({
  addedScopes: [],
  removedScopes: [],
  disabledCapabilities: [],
  activeTab: "chat",
  hiddenRoutes: [],
  _hydrated: false,

  hydrate: () => {
    if (get()._hydrated) return;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const data = JSON.parse(raw);
        set({
          addedScopes: data.addedScopes ?? [],
          removedScopes: data.removedScopes ?? [],
          disabledCapabilities: data.disabledCapabilities ?? [],
          activeTab: data.activeTab ?? "chat",
          hiddenRoutes: data.hiddenRoutes ?? [],
          _hydrated: true,
        });
        return;
      }
    } catch {
      // ignore
    }
    set({ _hydrated: true });
  },

  addScope: (scope) => {
    set((s) => {
      const next = {
        ...s,
        addedScopes: s.addedScopes.includes(scope) ? s.addedScopes : [...s.addedScopes, scope],
        removedScopes: s.removedScopes.filter((r) => r !== scope),
      };
      persist(next);
      return next;
    });
  },

  removeScope: (scope) => {
    set((s) => {
      const next = {
        ...s,
        removedScopes: s.removedScopes.includes(scope) ? s.removedScopes : [...s.removedScopes, scope],
        addedScopes: s.addedScopes.filter((a) => a !== scope),
      };
      persist(next);
      return next;
    });
  },

  resetScopes: () => {
    set((s) => {
      const next = { ...s, addedScopes: [], removedScopes: [] };
      persist(next);
      return next;
    });
  },

  toggleCapability: (capabilityId, enabled) => {
    set((s) => {
      const next = {
        ...s,
        disabledCapabilities: enabled
          ? s.disabledCapabilities.filter((id) => id !== capabilityId)
          : s.disabledCapabilities.includes(capabilityId)
            ? s.disabledCapabilities
            : [...s.disabledCapabilities, capabilityId],
      };
      persist(next);
      return next;
    });
  },

  setActiveTab: (tab) => {
    set((s) => {
      const next = { ...s, activeTab: tab };
      persist(next);
      return next;
    });
  },

  toggleRouteVisibility: (route) => {
    set((s) => {
      const hidden = s.hiddenRoutes.includes(route)
        ? s.hiddenRoutes.filter((r) => r !== route)
        : [...s.hiddenRoutes, route];
      const next = { ...s, hiddenRoutes: hidden };
      persist(next);
      return next;
    });
  },

  isRouteHidden: (pathname) => {
    return get().hiddenRoutes.some((prefix) => pathname.startsWith(prefix));
  },
}));
