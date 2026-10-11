import type { Category, Observation, Recipient, RoutingCell } from "./types";

/**
 * Frontend copy of `specs/contracts/routing-matrix.md`, used ONLY to preview
 * "who will be informed" before confirmation. The backend `routing/` module is
 * the source of truth; when it is available, replace `previewRouting` with the
 * backend answer.
 *
 * Assumption (matrix is still a draft): a `medication` observation with
 * severity `info` (treatment taken normally) is not an "issue" and follows the
 * same row as sleep / meals.
 */
type Row = Record<Recipient, RoutingCell>;

const ROUTINE: Row = { auxiliary: "yes", family: "daily_summary", doctor: "monthly_report", caregiver: "yes" };
const ALERT: Row = { auxiliary: "immediate", family: "immediate", doctor: "yes", caregiver: "yes" };

export const ROUTING_MATRIX: Record<Category, Row> = {
  sleep: ROUTINE,
  meals_hydration: ROUTINE,
  medication: ALERT,
  mobility_falls: ALERT,
  incident: ALERT,
  mood_behavior: { auxiliary: "yes", family: "filtered_summary", doctor: "monthly_report", caregiver: "yes" },
  pain: { auxiliary: "yes", family: "summary", doctor: "monthly_report", caregiver: "yes" },
  vitals: { auxiliary: "yes", family: "summary", doctor: "monthly_report", caregiver: "yes" },
  appointment: { auxiliary: "yes", family: "yes", doctor: "no", caregiver: "yes" },
  logistics: { auxiliary: "yes", family: "no", doctor: "no", caregiver: "yes" },
};

export const RECIPIENTS: Recipient[] = ["auxiliary", "family", "doctor", "caregiver"];

export function routingCell(obs: Pick<Observation, "category" | "severity">, recipient: Recipient): RoutingCell {
  let row = ROUTING_MATRIX[obs.category];
  if (obs.category === "medication" && obs.severity === "info") row = ROUTINE;
  const cell = row[recipient];
  // `severity: urgent` overrides the table: every recipient who receives this
  // category at all is notified immediately.
  if (obs.severity === "urgent" && cell !== "no") return "immediate";
  return cell;
}

export interface RoutingPreview {
  recipient: Recipient;
  immediate: Observation[];
  summary: Observation[];
  report: Observation[];
  regular: Observation[];
  excluded: Observation[];
}

export function previewRouting(observations: Observation[]): RoutingPreview[] {
  return RECIPIENTS.map((recipient) => {
    const p: RoutingPreview = { recipient, immediate: [], summary: [], report: [], regular: [], excluded: [] };
    for (const o of observations) {
      const cell = routingCell(o, recipient);
      if (cell === "immediate") p.immediate.push(o);
      else if (cell === "daily_summary" || cell === "summary" || cell === "filtered_summary") p.summary.push(o);
      else if (cell === "monthly_report") p.report.push(o);
      else if (cell === "yes") p.regular.push(o);
      else p.excluded.push(o);
    }
    return p;
  });
}
