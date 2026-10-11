/**
 * Frontend mirror of the shared contracts in `specs/contracts/`.
 * Field names follow the contracts exactly so the backend payloads can be
 * plugged in without mapping. UI-only extensions are grouped and commented.
 */

// --- specs/contracts/observation.md -------------------------------------

export type Category =
  | "sleep"
  | "meals_hydration"
  | "medication"
  | "mood_behavior"
  | "mobility_falls"
  | "pain"
  | "vitals"
  | "incident"
  | "appointment"
  | "logistics";

export type Severity = "info" | "watch" | "urgent";

export type Source = "caregiver_voice" | "wearable" | "auxiliary_report";

export interface Observation {
  id: string;
  /** When it happened (ISO 8601). */
  timestamp: string;
  /** When the report was made (ISO 8601). */
  reported_at: string;
  subject_id: string;
  category: Category;
  /** Plain factual words. Never a diagnosis, cause or advice. */
  value: string;
  severity: Severity;
  source: Source;
  reported_by: string;
  /** 0 to 1. */
  confidence: number;
  /** Exact words the fact came from; empty for wearable facts. */
  transcript_span: string;
}

// --- specs/contracts/wearable-sample.md ---------------------------------

export type SleepState = "awake" | "light" | "deep";

export interface WearableSample {
  timestamp: string;
  subject_id: string;
  heart_rate_bpm?: number;
  sleep_state?: SleepState;
  spo2_pct?: number;
  steps?: number;
}

// --- specs/contracts/routing-matrix.md + karis_architecture.md ----------

export type Recipient = "auxiliary" | "family" | "doctor" | "caregiver";

export type Channel = "mock" | "sns" | "ses" | "telegram";

/** SentMessage as described in karis_architecture.md (section 3). */
export interface SentMessage {
  id: string;
  recipient: Recipient;
  channel: Channel;
  body: string;
  observation_ids: string[];
  sent_at: string;
}

/**
 * Value of one routing-matrix cell.
 * - immediate: sent right away
 * - yes: included in the recipient's regular feed
 * - daily_summary / summary / filtered_summary: grouped into the evening summary
 * - monthly_report: only appears in the doctor report
 * - no: never sent
 */
export type RoutingCell =
  | "immediate"
  | "yes"
  | "daily_summary"
  | "summary"
  | "filtered_summary"
  | "monthly_report"
  | "no";

// --- UI-only types (not part of the backend contracts) ------------------

/** Delivery status shown in the UI. All deliveries are simulated. */
export type DeliveryStatus = "simulated_sent" | "scheduled_summary" | "in_report";

export interface UiMessage extends SentMessage {
  /** UI-only: how the message is delivered (derived from the routing cell). */
  delivery: DeliveryStatus;
  /** UI-only: short headline for list views. */
  title: string;
}

export interface FollowUpOption {
  label: string;
  /** Factual value stored if this option is chosen. */
  value: string;
  severity: Severity;
}

/** A completeness follow-up question (feature 003, at most 3 per report). */
export interface FollowUpQuestion {
  id: string;
  category: Category;
  prompt: string;
  options: FollowUpOption[];
}

export type FollowUpAnswer =
  | { status: "answered"; option?: FollowUpOption; text?: string }
  | { status: "skipped" };

/** A guardrail intervention (feature 006): wording that was not kept. */
export interface GuardrailNote {
  original: string;
  reason: string;
}

export type DraftStage = "followups" | "review" | "confirmed";

/** A voice report being reviewed by the caregiver before it is stored. */
export interface ReportDraft {
  id: string;
  created_at: string;
  /** Day the report describes (start of day, ISO). Usually the report day. */
  day?: string;
  /** "demo_cached" = fixture transcript; "backend" reserved for integration. */
  transcript_origin: "demo_cached" | "backend";
  transcript: string;
  audio_duration_s: number;
  /** True when a real microphone recording exists on this device. */
  has_device_audio: boolean;
  observations: Observation[];
  /** Words about the caregiver themself: never stored as facts, never sent. */
  private_passages: string[];
  guardrail_notes: GuardrailNote[];
  followups: FollowUpQuestion[];
  answers: Record<string, FollowUpAnswer>;
  stage: DraftStage;
  confirmed_summary?: { observations: number; messages: number };
}

export type CheckInMood = "bien" | "chargee" | "souffler" | "sans_reponse";
export type CheckInPause = "oui" | "un_peu" | "non";

/** Caregiver check-in. Private: stays on the device, never transmitted. */
export interface CheckIn {
  id: string;
  at: string;
  mood: CheckInMood;
  pause?: CheckInPause;
}

export interface Settings {
  reminderEnabled: boolean;
  /** Mirrors CHECKIN_TIME (contracts/config.md), local time "HH:MM". */
  reminderTime: string;
  gentleRetry: boolean;
  lightMode: boolean;
  /** Feature 011 (optional): suggest light mode from the engagement signal. */
  suggestLightMode: boolean;
  wearableInReport: boolean;
  /** Demo only: force the transcription step to fail once. */
  simulateTranscribeFailure: boolean;
}

export interface InAppNotice {
  id: string;
  at: string;
  title: string;
  body: string;
}
