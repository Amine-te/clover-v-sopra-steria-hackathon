"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, useState, type ReactNode } from "react";
import { DAILY_CHECKLIST } from "@/lib/labels";
import { dayKey, isSameDay } from "@/lib/format";
import type { CheckIn, FollowUpAnswer, InAppNotice, Observation, ReportDraft, Settings, UiMessage, WearableSample } from "@/lib/types";
import { generateDemoData, DEMO_DAYS } from "@/mocks/generator";
import { seedMessages } from "@/mocks/messages";
import { SCENARIOS } from "@/mocks/scenarios";
import { setDeviceRecording } from "./recording";

/**
 * Local UI state, persisted in localStorage. This is presentation state only:
 * once the backend exists, observations and messages come from it instead of
 * the seeded demo data.
 */

const STORAGE_KEY = "karis-ui-demo-v1";

export interface AppState {
  anchorDay: string;
  observations: Observation[];
  messages: UiMessage[];
  draft: ReportDraft | null;
  checkins: CheckIn[];
  notices: InAppNotice[];
  settings: Settings;
  scenarioIndex: number;
  /** Message ids the caregiver has already seen (for the "new" dot). */
  seenMessageIds: string[];
}

export const DEFAULT_SETTINGS: Settings = {
  reminderEnabled: true,
  reminderTime: "20:00",
  gentleRetry: true,
  lightMode: false,
  suggestLightMode: false,
  wearableInReport: true,
  simulateTranscribeFailure: false,
};

const EMPTY_STATE: AppState = {
  anchorDay: "",
  observations: [],
  messages: [],
  draft: null,
  checkins: [],
  notices: [],
  settings: DEFAULT_SETTINGS,
  scenarioIndex: 0,
  seenMessageIds: [],
};

function seedState(now: Date, keep?: Partial<AppState>): AppState {
  const { observations } = generateDemoData(now);
  const userObs = (keep?.observations ?? []).filter((o) => o.id.startsWith("obs-r"));
  const userMsgs = (keep?.messages ?? []).filter((m) => m.observation_ids.some((id) => id.startsWith("obs-r")));
  const messages = [...userMsgs, ...seedMessages(observations, now)];
  return {
    anchorDay: dayKey(now),
    observations: [...observations, ...userObs].sort((a, b) => a.timestamp.localeCompare(b.timestamp)),
    messages: messages.sort((a, b) => b.sent_at.localeCompare(a.sent_at)),
    draft: keep?.draft ?? null,
    checkins: keep?.checkins ?? [],
    notices: [],
    settings: { ...DEFAULT_SETTINGS, ...(keep?.settings ?? {}) },
    scenarioIndex: keep?.scenarioIndex ?? 0,
    seenMessageIds: messages.map((m) => m.id),
  };
}

type Action =
  | { type: "init"; state: AppState }
  | { type: "setDraft"; draft: ReportDraft | null }
  | { type: "answer"; questionId: string; answer: FollowUpAnswer | null }
  | { type: "patchDraft"; patch: Partial<ReportDraft> }
  | { type: "updateDraftObservation"; observation: Observation }
  | { type: "removeDraftObservation"; id: string }
  | { type: "confirmed"; stored: Observation[]; messages: UiMessage[] }
  | { type: "addCheckin"; checkin: CheckIn }
  | { type: "clearCheckins" }
  | { type: "settings"; patch: Partial<Settings> }
  | { type: "notice"; notice: InAppNotice }
  | { type: "dismissNotice"; id: string }
  | { type: "markMessagesSeen" }
  | { type: "setScenario"; index: number };

function reducer(s: AppState, a: Action): AppState {
  switch (a.type) {
    case "init":
      return a.state;
    case "setDraft":
      return { ...s, draft: a.draft };
    case "answer": {
      if (!s.draft) return s;
      const answers = { ...s.draft.answers };
      if (a.answer) answers[a.questionId] = a.answer;
      else delete answers[a.questionId];
      return { ...s, draft: { ...s.draft, answers } };
    }
    case "patchDraft":
      return s.draft ? { ...s, draft: { ...s.draft, ...a.patch } } : s;
    case "updateDraftObservation":
      return s.draft
        ? { ...s, draft: { ...s.draft, observations: s.draft.observations.map((o) => (o.id === a.observation.id ? a.observation : o)) } }
        : s;
    case "removeDraftObservation":
      return s.draft ? { ...s, draft: { ...s.draft, observations: s.draft.observations.filter((o) => o.id !== a.id) } } : s;
    case "confirmed":
      return {
        ...s,
        observations: [...s.observations, ...a.stored].sort((x, y) => x.timestamp.localeCompare(y.timestamp)),
        messages: [...a.messages, ...s.messages],
        // Privacy: once confirmed, the raw transcript and the caregiver's private
        // words are dropped from the device; only the stored facts remain.
        draft: s.draft
          ? { ...s.draft, transcript: "", private_passages: [], guardrail_notes: [], stage: "confirmed", confirmed_summary: { observations: a.stored.length, messages: a.messages.filter((m) => m.recipient !== "caregiver").length } }
          : null,
        scenarioIndex: (s.scenarioIndex + 1) % SCENARIOS.length,
      };
    case "addCheckin":
      return { ...s, checkins: [a.checkin, ...s.checkins].slice(0, 30) };
    case "clearCheckins":
      return { ...s, checkins: [] };
    case "settings":
      return { ...s, settings: { ...s.settings, ...a.patch } };
    case "notice":
      return { ...s, notices: [a.notice, ...s.notices] };
    case "dismissNotice":
      return { ...s, notices: s.notices.filter((n) => n.id !== a.id) };
    case "markMessagesSeen":
      return { ...s, seenMessageIds: s.messages.map((m) => m.id) };
    case "setScenario":
      return { ...s, scenarioIndex: Math.max(0, Math.min(SCENARIOS.length - 1, a.index)) };
  }
}

interface StoreValue {
  ready: boolean;
  state: AppState;
  dispatch: (a: Action) => void;
  wearable: WearableSample[];
  dataStart: Date;
  resetDemo: () => void;
  replayDemo: () => void;
  /** Today's checklist categories that have no observation yet. */
  missingToday: typeof DAILY_CHECKLIST;
  reportedToday: boolean;
  unseenMessages: number;
  toast: (message: string) => void;
  toasts: { id: number; message: string }[];
}

const StoreContext = createContext<StoreValue | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, EMPTY_STATE);
  const [ready, setReady] = useState(false);
  const [wearable, setWearable] = useState<WearableSample[]>([]);
  const [toasts, setToasts] = useState<{ id: number; message: string }[]>([]);
  const toastId = useRef(0);
  const stateRef = useRef(state);
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  // Hydrate on the client only: dates depend on the device clock.
  useEffect(() => {
    const now = new Date();
    let next: AppState;
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const saved = raw ? (JSON.parse(raw) as AppState) : null;
      if (saved && saved.anchorDay === dayKey(now)) next = { ...saved, settings: { ...DEFAULT_SETTINGS, ...saved.settings }, notices: [] };
      else next = seedState(now, saved ?? undefined);
    } catch {
      next = seedState(now);
    }
    dispatch({ type: "init", state: next });
    setWearable(generateDemoData(now).wearable);
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    try {
      const { notices: _n, ...persist } = state;
      void _n;
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(persist));
    } catch {
      /* storage full or unavailable: the demo keeps working in memory */
    }
  }, [state, ready]);

  const resetDemo = useCallback(() => {
    const now = new Date();
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
    dispatch({ type: "init", state: seedState(now) });
    setWearable(generateDemoData(now).wearable);
  }, []);

  /** Fresh history for a new run, keeping settings and the next example. */
  const replayDemo = useCallback(() => {
    const now = new Date();
    setDeviceRecording(null);
    dispatch({
      type: "init",
      state: seedState(now, { settings: stateRef.current.settings, scenarioIndex: stateRef.current.scenarioIndex }),
    });
    setWearable(generateDemoData(now).wearable);
  }, []);

  const toast = useCallback((message: string) => {
    toastId.current += 1;
    const id = toastId.current;
    // One toast at a time: a new message replaces the previous one.
    setToasts([{ id, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 2800);
  }, []);

  const value = useMemo<StoreValue>(() => {
    const now = new Date();
    const today = state.observations.filter((o) => isSameDay(o.timestamp, now) || isSameDay(o.reported_at, now));
    const missingToday = DAILY_CHECKLIST.filter((c) => !today.some((o) => o.category === c));
    const reportedToday = today.some((o) => o.source === "caregiver_voice" && isSameDay(o.reported_at, now));
    const seen = new Set(state.seenMessageIds);
    const dataStart = new Date(now);
    dataStart.setDate(dataStart.getDate() - DEMO_DAYS);
    return {
      ready,
      state,
      dispatch,
      wearable,
      dataStart,
      resetDemo,
      replayDemo,
      missingToday,
      reportedToday,
      unseenMessages: state.messages.filter((m) => !seen.has(m.id) && m.recipient !== "caregiver").length,
      toast,
      toasts,
    };
  }, [state, ready, wearable, resetDemo, replayDemo, toast, toasts]);

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): StoreValue {
  const v = useContext(StoreContext);
  if (!v) throw new Error("useStore must be used inside StoreProvider");
  return v;
}
