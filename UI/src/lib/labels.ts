import type { Category, DeliveryStatus, Recipient, RoutingCell, Severity, Source, UiMessage } from "./types";

/** French user-facing labels. Code identifiers stay in English (constitution, rule 10). */

export const CATEGORY_LABEL: Record<Category, string> = {
  sleep: "Sommeil",
  meals_hydration: "Repas et hydratation",
  medication: "Traitement",
  mood_behavior: "Humeur et comportement",
  mobility_falls: "Mobilité et chutes",
  pain: "Douleur",
  vitals: "Constantes",
  incident: "Incident",
  appointment: "Rendez-vous",
  logistics: "Organisation",
};

export const CATEGORY_SHORT: Record<Category, string> = {
  sleep: "Sommeil",
  meals_hydration: "Repas",
  medication: "Traitement",
  mood_behavior: "Humeur",
  mobility_falls: "Mobilité",
  pain: "Douleur",
  vitals: "Constantes",
  incident: "Incident",
  appointment: "Rendez-vous",
  logistics: "Organisation",
};

export const CATEGORY_ORDER: Category[] = [
  "sleep",
  "meals_hydration",
  "medication",
  "mood_behavior",
  "mobility_falls",
  "pain",
  "vitals",
  "incident",
  "appointment",
  "logistics",
];

/** Default daily checklist (feature 003, open question 10). */
export const DAILY_CHECKLIST: Category[] = ["sleep", "meals_hydration", "medication", "mood_behavior"];

export const SEVERITY_LABEL: Record<Severity, string> = {
  info: "Information",
  watch: "À surveiller",
  urgent: "Urgent",
};

export const SOURCE_LABEL: Record<Source, string> = {
  caregiver_voice: "Votre compte rendu",
  wearable: "Mesuré par le bracelet",
  auxiliary_report: "Transmis par l'auxiliaire",
};

export const SOURCE_SHORT: Record<Source, string> = {
  caregiver_voice: "Vous",
  wearable: "Bracelet",
  auxiliary_report: "Auxiliaire",
};

export const RECIPIENT_LABEL: Record<Recipient, string> = {
  auxiliary: "Auxiliaire de vie",
  family: "Famille",
  doctor: "Médecin traitant",
  caregiver: "Vous",
};

export const ROUTING_CELL_LABEL: Record<RoutingCell, string> = {
  immediate: "Immédiatement",
  yes: "Oui",
  daily_summary: "Résumé du soir",
  summary: "Résumé",
  filtered_summary: "Résumé filtré",
  monthly_report: "Rapport mensuel",
  no: "Non",
};

export const DELIVERY_LABEL: Record<DeliveryStatus, string> = {
  simulated_sent: "Envoi simulé",
  scheduled_summary: "Prévu pour le résumé de 20 h 30",
  in_report: "Ajouté au rapport médical",
};

/** Evening summaries are considered sent (simulated) at this local time. */
const SUMMARY_SENT_AT: [number, number] = [20, 30];

/** True once a scheduled evening summary has (virtually) gone out. */
export function summarySent(m: Pick<UiMessage, "delivery" | "sent_at">, now = new Date()): boolean {
  if (m.delivery !== "scheduled_summary") return false;
  const due = new Date(m.sent_at);
  due.setHours(SUMMARY_SENT_AT[0], SUMMARY_SENT_AT[1], 0, 0);
  // A report made after the summary time is included in a summary sent right away.
  return now >= due || new Date(m.sent_at) >= due;
}

/** Status shown to the user; every delivery is simulated. */
export function deliveryLabel(m: Pick<UiMessage, "delivery" | "sent_at">, now = new Date()): string {
  if (summarySent(m, now)) return "Résumé envoyé (simulé)";
  return DELIVERY_LABEL[m.delivery];
}

export function confidenceLabel(c: number): { label: string; low: boolean } {
  if (c >= 0.85) return { label: "Certitude élevée", low: false };
  if (c >= 0.7) return { label: "Certitude moyenne", low: false };
  return { label: "À vérifier", low: true };
}
