import type { InAppNotice, Observation, ReportDraft, UiMessage } from "@/lib/types";

/**
 * Integration seam between the UI and the backend.
 *
 * The UI only talks to this interface. `mock-service.ts` implements it with
 * local demo fixtures. To plug in the real backend (api.py), write another
 * implementation of `KarisService` and export it from `services/index.ts`.
 * No endpoint is assumed here on purpose: the API shape is not specified yet.
 */

export type PipelineStep = "upload" | "transcribe" | "extract" | "gaps" | "guardrail";

export interface AnalyzeInput {
  /** Real microphone recording, when one exists on the device. */
  audio?: Blob;
  durationS: number;
  reportedAt: Date;
}

export class TranscriptionError extends Error {
  constructor() {
    super("transcription_failed");
    this.name = "TranscriptionError";
  }
}

export interface KarisService {
  /** True when results come from demo fixtures, not from a real pipeline. */
  readonly isDemo: boolean;

  /**
   * Features 001 → 002 → 003 → 006: upload audio, transcribe (fr-FR), extract
   * Observations, find checklist gaps (≤ 3 follow-ups) and apply guardrails.
   * Throws `TranscriptionError` when transcription fails (001-AC3).
   */
  analyzeReport(input: AnalyzeInput, onStep?: (step: PipelineStep) => void): Promise<ReportDraft>;

  /** Feature 003-AC3: turn follow-up answers into Observations. */
  extractFollowUpAnswers(draft: ReportDraft): Promise<Observation[]>;

  /** Features 004 + 005: store confirmed Observations and route them. */
  confirmReport(observations: Observation[]): Promise<{ stored: Observation[]; messages: UiMessage[] }>;

  /** Feature 008-AC4: "send reminder now" for demos. Null when nothing should be sent. */
  sendReminderNow(missingLabels: string[], alreadyReported: boolean): Promise<InAppNotice | null>;
}
