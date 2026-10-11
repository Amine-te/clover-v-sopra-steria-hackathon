import { CATEGORY_ORDER } from "./labels";
import { addDays, dayKey, startOfDay } from "./format";
import type { Category, Observation, WearableSample } from "./types";

/**
 * Pure "merge by date" step of the report flow (feature 007), reproduced on
 * the device for the demo preview. It only reorganises stored facts and
 * measured values: no summarising, no interpretation. The real report text is
 * produced by the backend (Sonnet 4 + guardrail) and rendered to HTML/PDF.
 */

export type PeriodUnit = "days" | "months";

export interface ReportPeriod {
  amount: number;
  unit: PeriodUnit;
}

export interface DayWearable {
  day: string;
  asleepMin: number;
  deepMin: number;
  awakePeriods: number;
  nightHr?: number;
  spo2?: number;
  steps: number;
  sampleIds: string[];
}

export interface DayBlock {
  day: string;
  observations: Observation[];
  wearable?: DayWearable;
}

export interface CategoryCount {
  category: Category;
  total: number;
  flagged: number;
}

export interface DoctorReport {
  id: string;
  generatedAt: string;
  period: ReportPeriod;
  from: string;
  to: string;
  /** True when the requested period starts before the available data. */
  truncated: boolean;
  observationCount: number;
  counts: CategoryCount[];
  highlights: Observation[];
  days: DayBlock[];
  wearable?: {
    nights: number;
    avgAsleepMin: number;
    avgDeepMin: number;
    avgNightHr?: number;
    avgSpo2?: number;
    avgSteps: number;
    perDay: DayWearable[];
  };
}

export function periodStart(period: ReportPeriod, now: Date): Date {
  const end = startOfDay(now);
  if (period.unit === "days") return addDays(end, -(period.amount - 1));
  const d = new Date(end);
  d.setMonth(d.getMonth() - period.amount);
  return addDays(d, 1);
}

/** Simulated bracelet: one reading every 30 min from 22:30 to 07:30. */
const FULL_NIGHT_READINGS = 19;

function mean(values: number[]): number | undefined {
  if (!values.length) return undefined;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

/** Bracelet nights are attributed to the day they end (wake-up day). */
function wearableByDay(samples: WearableSample[]): Map<string, DayWearable> {
  const map = new Map<string, DayWearable>();
  const hrs = new Map<string, number[]>();
  const spo2 = new Map<string, number[]>();
  const nightCount = new Map<string, number>();
  for (const s of samples) {
    const t = new Date(s.timestamp);
    // Night readings after 20:00 belong to the following day.
    const owner = s.sleep_state && t.getHours() >= 20 ? dayKey(addDays(t, 1)) : dayKey(t);
    const entry = map.get(owner) ?? { day: owner, asleepMin: 0, deepMin: 0, awakePeriods: 0, steps: 0, sampleIds: [] };
    if (s.sleep_state) {
      nightCount.set(owner, (nightCount.get(owner) ?? 0) + 1);
      if (s.sleep_state !== "awake") entry.asleepMin += 30;
      if (s.sleep_state === "deep") entry.deepMin += 30;
      // Bed time (22:30) and wake-up (07:30) readings are not counted as night awakenings.
      const edge = t.getMinutes() === 30 && (t.getHours() === 22 || t.getHours() === 7);
      if (s.sleep_state === "awake" && !edge) entry.awakePeriods += 1;
      if (s.heart_rate_bpm) hrs.set(owner, [...(hrs.get(owner) ?? []), s.heart_rate_bpm]);
      if (s.spo2_pct) spo2.set(owner, [...(spo2.get(owner) ?? []), s.spo2_pct]);
    }
    if (s.steps) entry.steps += s.steps;
    entry.sampleIds.push(`bracelet@${s.timestamp}`);
    map.set(owner, entry);
  }
  for (const [k, e] of map) {
    // A night still in progress (or cut by the period start) is not reported:
    // partial sleep totals would be misleading.
    if ((nightCount.get(k) ?? 0) < FULL_NIGHT_READINGS) {
      e.asleepMin = 0;
      e.deepMin = 0;
      e.awakePeriods = 0;
      continue;
    }
    e.nightHr = mean(hrs.get(k) ?? []);
    e.spo2 = mean(spo2.get(k) ?? []);
  }
  return map;
}

export function buildDoctorReport(
  observations: Observation[],
  wearable: WearableSample[],
  period: ReportPeriod,
  options: { includeWearable: boolean; dataStart: Date },
  now = new Date(),
): DoctorReport {
  const requestedStart = periodStart(period, now);
  const start = requestedStart < startOfDay(options.dataStart) ? startOfDay(options.dataStart) : requestedStart;
  const end = now;
  const inRange = (iso: string) => {
    const t = new Date(iso);
    return t >= start && t <= end;
  };

  const obs = observations.filter((o) => inRange(o.timestamp)).sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  const samples = options.includeWearable ? wearable.filter((s) => inRange(s.timestamp)) : [];
  const wByDay = wearableByDay(samples);

  const dayMap = new Map<string, DayBlock>();
  for (const o of obs) {
    const k = dayKey(o.timestamp);
    const b = dayMap.get(k) ?? { day: k, observations: [] };
    b.observations.push(o);
    dayMap.set(k, b);
  }
  for (const [k, w] of wByDay) {
    if (!inRange(`${k}T12:00:00`) && k !== dayKey(now)) continue;
    const b = dayMap.get(k) ?? { day: k, observations: [] };
    b.wearable = w;
    dayMap.set(k, b);
  }
  const days = [...dayMap.values()].sort((a, b) => a.day.localeCompare(b.day));

  const counts: CategoryCount[] = CATEGORY_ORDER.map((category) => {
    const list = obs.filter((o) => o.category === category);
    return { category, total: list.length, flagged: list.filter((o) => o.severity !== "info").length };
  }).filter((c) => c.total > 0);

  const perDay = [...wByDay.values()].filter((w) => w.asleepMin > 0 || w.steps > 0).sort((a, b) => a.day.localeCompare(b.day));
  const nights = perDay.filter((w) => w.asleepMin > 0);

  return {
    id: `rapport-${dayKey(now)}-${period.amount}${period.unit === "days" ? "j" : "m"}`,
    generatedAt: now.toISOString(),
    period,
    from: start.toISOString(),
    to: end.toISOString(),
    truncated: requestedStart < start,
    observationCount: obs.length,
    counts,
    highlights: obs.filter((o) => o.severity !== "info"),
    days,
    wearable: options.includeWearable && perDay.length
      ? {
          nights: nights.length,
          avgAsleepMin: mean(nights.map((n) => n.asleepMin)) ?? 0,
          avgDeepMin: mean(nights.map((n) => n.deepMin)) ?? 0,
          avgNightHr: mean(nights.map((n) => n.nightHr ?? 0).filter(Boolean)),
          avgSpo2: mean(nights.map((n) => n.spo2 ?? 0).filter(Boolean)),
          avgSteps: mean(perDay.filter((d) => d.steps > 0).map((d) => d.steps)) ?? 0,
          perDay,
        }
      : undefined,
  };
}
