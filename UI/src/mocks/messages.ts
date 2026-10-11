import { CATEGORY_LABEL } from "@/lib/labels";
import { formatTime, toLocalIso } from "@/lib/format";
import { previewRouting } from "@/lib/routing";
import type { Observation, Recipient, UiMessage } from "@/lib/types";
import { CAREGIVER, CONTACTS, SUBJECT } from "./people";

/**
 * Simulated message wording. In the real system the routing decision comes
 * from the backend matrix and Haiku writes the wording (feature 005); here a
 * fixed French template stands in. Messages are never really sent.
 * Messages only use the factual `value` field: no raw caregiver words and no
 * private passages ever reach a recipient ("filtered summary" rule).
 */

function firstName(r: Recipient): string {
  const n = CONTACTS[r].name;
  return r === "doctor" ? n : n.split(" ")[0];
}

function lower(s: string): string {
  return s.charAt(0).toLowerCase() + s.slice(1);
}

function bullet(o: Observation): string {
  return `• ${CATEGORY_LABEL[o.category]} : ${lower(o.value)}`;
}

let counter = 0;
function nextId(at: Date): string {
  counter += 1;
  return `msg-${at.getTime().toString(36)}-${counter}`;
}

export function composeMessages(observations: Observation[], at: Date): UiMessage[] {
  const sentAt = toLocalIso(at);
  const messages: UiMessage[] = [];
  const who = CAREGIVER.firstName;
  const subject = SUBJECT.firstName;

  for (const p of previewRouting(observations)) {
    const r = p.recipient;

    if (r === "caregiver") {
      if (observations.length === 0) continue;
      messages.push({
        id: nextId(at),
        recipient: r,
        channel: "mock",
        delivery: "simulated_sent",
        title: "Compte rendu enregistré",
        body: `Votre compte rendu est enregistré : ${observations.length} ${observations.length > 1 ? "faits ajoutés" : "fait ajouté"} à la frise de ${subject}.\n${observations.map(bullet).join("\n")}`,
        observation_ids: observations.map((o) => o.id),
        sent_at: sentAt,
      });
      continue;
    }

    for (const o of p.immediate) {
      messages.push({
        id: nextId(at),
        recipient: r,
        channel: "mock",
        delivery: "simulated_sent",
        title: o.severity === "urgent" ? "Information urgente" : "Information immédiate",
        body: `Bonjour ${firstName(r)},\n${who} signale pour ${subject} (${formatTime(o.timestamp)}) : ${lower(o.value)}.\nMessage préparé par Karis à partir du compte rendu de ${who}.`,
        observation_ids: [o.id],
        sent_at: sentAt,
      });
    }

    const regularOrSummary = [...p.regular, ...p.summary];
    if (r === "doctor") {
      if (p.regular.length) {
        messages.push({
          id: nextId(at),
          recipient: r,
          channel: "mock",
          delivery: "simulated_sent",
          title: "Point d'information",
          body: `Bonjour ${firstName(r)},\nPour information, concernant ${SUBJECT.firstName} ${SUBJECT.lastName} :\n${p.regular.map(bullet).join("\n")}\nFaits rapportés par l'aidante, sans interprétation.`,
          observation_ids: p.regular.map((o) => o.id),
          sent_at: sentAt,
        });
      }
      if (p.report.length) {
        messages.push({
          id: nextId(at),
          recipient: r,
          channel: "mock",
          delivery: "in_report",
          title: "Repris dans le rapport médical",
          body: `${p.report.length} ${p.report.length > 1 ? "observations seront reprises" : "observation sera reprise"} dans le prochain rapport :\n${p.report.map(bullet).join("\n")}`,
          observation_ids: p.report.map((o) => o.id),
          sent_at: sentAt,
        });
      }
      continue;
    }

    if (regularOrSummary.length) {
      messages.push({
        id: nextId(at),
        recipient: r,
        channel: "mock",
        delivery: "scheduled_summary",
        title: "Résumé du soir",
        body: `Bonsoir ${firstName(r)},\nVoici la journée de ${subject} :\n${regularOrSummary.map(bullet).join("\n")}`,
        observation_ids: regularOrSummary.map((o) => o.id),
        sent_at: sentAt,
      });
    }
  }
  return messages;
}

/** Seed history: messages for the caregiver reports of the last few days. */
export function seedMessages(observations: Observation[], now: Date, days = 4): UiMessage[] {
  const limit = now.getTime() - days * 86400000;
  const byReport = new Map<string, Observation[]>();
  for (const o of observations) {
    if (o.source !== "caregiver_voice") continue;
    const list = byReport.get(o.reported_at) ?? [];
    list.push(o);
    byReport.set(o.reported_at, list);
  }
  const all: UiMessage[] = [];
  for (const [reportedAt, list] of byReport) {
    const recent = new Date(reportedAt).getTime() >= limit;
    // Older reports are only kept in the history when they contained an urgent fact.
    if (recent || list.some((o) => o.severity === "urgent")) all.push(...composeMessages(list, new Date(reportedAt)));
  }
  return all.sort((a, b) => b.sent_at.localeCompare(a.sent_at));
}
