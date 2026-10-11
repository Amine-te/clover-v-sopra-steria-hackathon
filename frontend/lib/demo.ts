import type { ProviderMetadata } from "./api";

export const DEMO_TEXT = "Maman était plus fatiguée aujourd’hui. Elle a pris son traitement mais elle n’a presque rien mangé. Sophie passe ce soir. Moi je suis vraiment crevé.";
export const categoryLabels: Record<string, string> = { fatigue: "Fatigue", nutrition: "Alimentation", medication: "Traitement rapporté", sleep: "Sommeil", appointment: "Organisation", mood: "Humeur", general: "Quotidien", practical: "Vie pratique", administrative: "Administratif", logistics: "Organisation" };
export const roleLabels: Record<string, string> = { primary_caregiver: "Aidant principal", family_caregiver: "Aidante familiale", auxiliary: "Auxiliaire de vie", administrative_helper: "Aide administrative", family_informed: "Famille informée" };
export const actionLabels: Record<string, string> = { pending: "À suivre", done: "Terminée", cancelled: "Annulée" };
export function humanError(error: unknown) { return error instanceof Error ? error.message : "Une erreur est survenue. Les données enregistrées sont conservées."; }
export function frenchDate(date: string) { return new Date(date.length === 10 ? `${date}T12:00:00` : date).toLocaleDateString("fr-FR", { day: "numeric", month: "long" }); }
export function rememberMetadata(id: string, metadata?: ProviderMetadata | null) {
  if (metadata) sessionStorage.setItem(`karis_metadata_${id}`, JSON.stringify(metadata));
}
export function recallMetadata(id: string): ProviderMetadata | null {
  try { return JSON.parse(sessionStorage.getItem(`karis_metadata_${id}`) ?? "null"); } catch { return null; }
}
