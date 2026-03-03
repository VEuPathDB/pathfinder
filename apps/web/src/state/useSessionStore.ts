/**
 * Session state store (user, selected site)
 */

import { create } from "zustand";
import { setAuthTokenGetter } from "@/lib/api/auth";

interface SessionState {
  selectedSite: string;
  selectedSiteDisplayName: string;
  strategyId: string | null;
  authToken: string | null;
  veupathdbSignedIn: boolean;
  veupathdbName: string | null;
  chatIsStreaming: boolean;

  /** Monotonic counter; bump to tell sidebar to reload chat preview. */
  chatPreviewVersion: number;
  /** Transient node selection payload from graph -> chat. */
  pendingAskNode: Record<string, unknown> | null;
  /** Prefill content for the message composer. */
  composerPrefill: { message: string } | null;

  /** Whether the VEuPathDB auth token has been refreshed in this session. */
  authRefreshed: boolean;
  /** True after the first auth status check has completed. Used to avoid showing sign-in UI before we know. */
  authStatusKnown: boolean;

  setSelectedSite: (siteId: string) => void;
  setSelectedSiteInfo: (siteId: string, displayName: string) => void;
  setStrategyId: (id: string | null) => void;
  setAuthToken: (token: string | null) => void;
  setVeupathdbAuth: (signedIn: boolean, name?: string | null) => void;
  setChatIsStreaming: (value: boolean) => void;

  // Signal setters
  bumpChatPreviewVersion: () => void;
  setPendingAskNode: (payload: Record<string, unknown> | null) => void;
  setComposerPrefill: (payload: { message: string } | null) => void;
  setAuthRefreshed: (value: boolean) => void;
  setAuthStatusKnown: (value: boolean) => void;
}

const AUTH_TOKEN_STORAGE_KEY = "pathfinder-auth-token";
const SELECTED_SITE_KEY = "pathfinder-selected-site";
const SELECTED_SITE_DISPLAY_KEY = "pathfinder-selected-site-display";
const STRATEGY_ID_KEY_PREFIX = "pathfinder-strategy-id:";

const getInitialAuthToken = () => {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
};

const getInitialSelectedSite = () => {
  if (typeof window === "undefined") return "plasmodb";
  return window.localStorage.getItem(SELECTED_SITE_KEY) || "plasmodb";
};

const getInitialSelectedSiteDisplayName = () => {
  if (typeof window === "undefined") return "PlasmoDB";
  return window.localStorage.getItem(SELECTED_SITE_DISPLAY_KEY) || "PlasmoDB";
};

const getInitialStrategyId = () => {
  if (typeof window === "undefined") return null;
  const site = getInitialSelectedSite();
  return window.localStorage.getItem(`${STRATEGY_ID_KEY_PREFIX}${site}`);
};

export const useSessionStore = create<SessionState>()((set, get) => ({
  selectedSite: getInitialSelectedSite(),
  selectedSiteDisplayName: getInitialSelectedSiteDisplayName(),
  strategyId: getInitialStrategyId(),
  authToken: getInitialAuthToken(),
  veupathdbSignedIn: false,
  veupathdbName: null,
  chatIsStreaming: false,

  // Signals
  chatPreviewVersion: 0,
  pendingAskNode: null,
  composerPrefill: null,
  authRefreshed: false,
  authStatusKnown: false,

  setSelectedSite: (siteId) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SELECTED_SITE_KEY, siteId);
    }
    set((s) => {
      if (s.selectedSite === siteId) return { selectedSite: siteId };
      // Restore last-used strategy for the new site.
      const restored =
        typeof window !== "undefined"
          ? window.localStorage.getItem(`${STRATEGY_ID_KEY_PREFIX}${siteId}`)
          : null;
      return { selectedSite: siteId, strategyId: restored };
    });
  },
  setSelectedSiteInfo: (siteId, displayName) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SELECTED_SITE_KEY, siteId);
      window.localStorage.setItem(SELECTED_SITE_DISPLAY_KEY, displayName);
    }
    set((s) => {
      if (s.selectedSite === siteId) {
        return { selectedSite: siteId, selectedSiteDisplayName: displayName };
      }
      const restored =
        typeof window !== "undefined"
          ? window.localStorage.getItem(`${STRATEGY_ID_KEY_PREFIX}${siteId}`)
          : null;
      return {
        selectedSite: siteId,
        selectedSiteDisplayName: displayName,
        strategyId: restored,
      };
    });
  },
  setStrategyId: (id) => {
    const site = get().selectedSite;
    if (typeof window !== "undefined") {
      if (id) {
        window.localStorage.setItem(`${STRATEGY_ID_KEY_PREFIX}${site}`, id);
      } else {
        window.localStorage.removeItem(`${STRATEGY_ID_KEY_PREFIX}${site}`);
      }
    }
    set({ strategyId: id });
  },
  setAuthToken: (token) => {
    if (typeof window !== "undefined") {
      if (token) {
        window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
      } else {
        window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
      }
    }
    set({ authToken: token });
  },
  setVeupathdbAuth: (signedIn, name = null) =>
    set({ veupathdbSignedIn: signedIn, veupathdbName: name }),
  setChatIsStreaming: (value) => set({ chatIsStreaming: value }),

  // Signal setters
  bumpChatPreviewVersion: () =>
    set((s) => ({ chatPreviewVersion: s.chatPreviewVersion + 1 })),
  setPendingAskNode: (payload) => set({ pendingAskNode: payload }),
  setComposerPrefill: (payload) => set({ composerPrefill: payload }),
  setAuthRefreshed: (value) => set({ authRefreshed: value }),
  setAuthStatusKnown: (value) => set({ authStatusKnown: value }),
}));

// Inject token getter for transport-layer helpers (keeps `lib/api/*` independent of `state/*`).
setAuthTokenGetter(() => useSessionStore.getState().authToken);
