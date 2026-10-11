import { toLocalIso } from "@/lib/format";
import type { Category, Observation, ReportDraft } from "@/lib/types";
import { composeMessages } from "@/mocks/messages";
import { CAREGIVER, SUBJECT } from "@/mocks/people";
import { SCENARIOS } from "@/mocks/scenarios";
import { TranscriptionError, type AnalyzeInput, type KarisService, type PipelineStep } from "./karis-service";

/**
 * Local demo implementation. Nothing leaves the device: no network call, no
 * AI inference. Results come from hand-written fixtures in `mocks/`.
 */

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

export interface MockControls {
  /** Index of the next fixture scenario to use. */
  scenarioIndex: number;
  /** Fail the transcription step (to show the retry state). */
  failTranscription: boolean;
}

export const mockControls: MockControls = { scenarioIndex: 0, failTranscription: false };

const FOLLOWUP_TIME: Partial<Record<Category, [number, number]>> = {
  sleep: [7, 30],
  meals_hydration: [12, 30],
  medication: [8, 30],
  mood_behavior: [16, 0],
};

/**
 * Day the demo report describes. The fixture facts carry fixed times of day
 * ("vers 15 h"); if some of them are still in the future (morning demo, just
 * after midnight), the report describes the previous day instead of
 * squashing every time to "now".
 */
function reportDayBase(times: [number, number][], reportedAt: Date): Date {
  const latest = times.reduce((acc, [h, m]) => Math.max(acc, h * 60 + m), 0);
  const nowMin = reportedAt.getHours() * 60 + reportedAt.getMinutes();
  const base = new Date(reportedAt);
  base.setHours(0, 0, 0, 0);
  if (latest > nowMin) base.setDate(base.getDate() - 1);
  return base;
}

let seq = 0;
function newObsId(): string {
  seq += 1;
  return `obs-r${Date.now().toString(36)}-${seq}`;
}

export const mockService: KarisService = {
  isDemo: true,

  async analyzeReport(input: AnalyzeInput, onStep?: (step: PipelineStep) => void): Promise<ReportDraft> {
    const steps: [PipelineStep, number][] = [
      ["upload", 700],
      ["transcribe", 1300],
      ["extract", 1200],
      ["gaps", 700],
      ["guardrail", 700],
    ];
    for (const [step, ms] of steps) {
      onStep?.(step);
      await wait(ms);
      if (step === "transcribe" && mockControls.failTranscription) {
        mockControls.failTranscription = false; // fail once, then succeed on retry
        throw new TranscriptionError();
      }
    }

    const scenario = SCENARIOS[mockControls.scenarioIndex % SCENARIOS.length];
    const reportedAt = input.reportedAt;
    const reportedIso = toLocalIso(reportedAt);
    const base = reportDayBase(scenario.facts.map((f) => f.time), reportedAt);
    const observations: Observation[] = scenario.facts.map((f) => {
      const when = new Date(base);
      when.setHours(f.time[0], f.time[1], 0, 0);
      return {
        id: newObsId(),
        timestamp: toLocalIso(when),
        reported_at: reportedIso,
        subject_id: SUBJECT.id,
        category: f.category,
        value: f.value,
        severity: f.severity,
        source: "caregiver_voice",
        reported_by: CAREGIVER.id,
        confidence: f.confidence,
        transcript_span: f.span,
      };
    });

    return {
      id: `draft-${reportedAt.getTime().toString(36)}`,
      created_at: reportedIso,
      day: toLocalIso(base),
      transcript_origin: "demo_cached",
      transcript: scenario.transcript,
      audio_duration_s: input.audio ? input.durationS : scenario.durationS,
      has_device_audio: Boolean(input.audio),
      observations,
      private_passages: scenario.privatePassages,
      guardrail_notes: scenario.guardrail,
      followups: scenario.followups.slice(0, 3),
      answers: {},
      stage: scenario.followups.length ? "followups" : "review",
    };
  },

  async extractFollowUpAnswers(draft: ReportDraft): Promise<Observation[]> {
    await wait(600);
    const reportedAt = new Date(draft.created_at);
    const day = new Date(draft.day ?? draft.created_at);
    const out: Observation[] = [];
    for (const q of draft.followups) {
      const a = draft.answers[q.id];
      if (!a || a.status !== "answered") continue;
      const text = a.text?.trim();
      const value = text ? text.charAt(0).toUpperCase() + text.slice(1) : a.option?.value;
      if (!value) continue;
      // Fixed, plausible time of day per category, never after the report itself.
      const [h, m] = FOLLOWUP_TIME[q.category] ?? [17, 0];
      const when = new Date(day);
      when.setHours(h, m, 0, 0);
      if (when > reportedAt) when.setTime(reportedAt.getTime() - 15 * 60000);
      out.push({
        id: newObsId(),
        timestamp: toLocalIso(when),
        reported_at: draft.created_at,
        subject_id: SUBJECT.id,
        category: q.category,
        value,
        severity: text ? "info" : a.option?.severity ?? "info",
        source: "caregiver_voice",
        reported_by: CAREGIVER.id,
        confidence: text ? 0.8 : 1,
        // Traceability: the exact answer given by the caregiver.
        transcript_span: text ?? a.option?.label ?? "",
      });
    }
    return out;
  },

  async confirmReport(observations: Observation[]) {
    await wait(900);
    const now = new Date();
    return { stored: observations, messages: composeMessages(observations, now) };
  },

  async sendReminderNow(missingLabels: string[], alreadyReported: boolean) {
    await wait(400);
    if (alreadyReported) return null; // feature 008-AC2
    const missing = missingLabels.length
      ? ` Il manque encore : ${missingLabels.join(", ").toLowerCase()}.`
      : "";
    return {
      id: `notice-${Date.now().toString(36)}`,
      at: new Date().toISOString(),
      title: `Comment s'est passée la journée de ${SUBJECT.firstName} ?`,
      body: `Quelques mots suffisent, quand vous voulez.${missing}`,
    };
  },
};
