import { addDays, startOfDay, toLocalIso } from "@/lib/format";
import type { Category, Observation, Severity, SleepState, Source, WearableSample } from "@/lib/types";
import { AUXILIARY_ID, CAREGIVER, SUBJECT, WEARABLE_ID } from "./people";

/**
 * Simulated 30-day history (feature 004-AC3) with matching bracelet data
 * (contracts/wearable-sample.md). Deterministic for a given anchor day so the
 * demo looks identical on every reload. Everything here is fictional.
 */

export const DEMO_DAYS = 30;

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function at(day: Date, h: number, m = 0): Date {
  const d = new Date(day);
  d.setHours(h, m, 0, 0);
  return d;
}

type Draft = Omit<Observation, "id">;

interface Ctx {
  rand: () => number;
  out: Draft[];
}

function pick<T>(rand: () => number, items: T[]): T {
  return items[Math.floor(rand() * items.length)];
}

function push(
  ctx: Ctx,
  when: Date,
  reported: Date,
  category: Category,
  value: string,
  span: string,
  severity: Severity = "info",
  source: Source = "caregiver_voice",
) {
  ctx.out.push({
    timestamp: toLocalIso(when),
    reported_at: toLocalIso(reported),
    subject_id: SUBJECT.id,
    category,
    value,
    severity,
    source,
    reported_by: source === "caregiver_voice" ? CAREGIVER.id : source === "auxiliary_report" ? AUXILIARY_ID : WEARABLE_ID,
    confidence: source === "wearable" ? 1 : Math.round((0.78 + ctx.rand() * 0.2) * 100) / 100,
    transcript_span: source === "wearable" ? "" : span,
  });
}

/** Number of awake periods in the night that ends on `dayOffset` (0 = last night). */
function nightWakeups(rand: () => number, dayOffset: number): number {
  if (dayOffset === 12) return 4; // night of the fall
  if (dayOffset === 8 || dayOffset === 7) return 3; // knee pain nights
  const r = rand();
  return r < 0.45 ? 0 : r < 0.75 ? 1 : r < 0.9 ? 2 : 3;
}

const REFUSED_TREATMENT_DAYS = new Set([27, 16, 5]);
const NO_REPORT_DAYS = new Set([22, 9]);

export interface DemoData {
  observations: Observation[];
  wearable: WearableSample[];
}

export function generateDemoData(now: Date): DemoData {
  const today = startOfDay(now);
  const seed = Number(`${today.getFullYear()}${today.getMonth() + 1}${today.getDate()}`);
  const rand = mulberry32(seed);
  const ctx: Ctx = { rand, out: [] };
  const wearable: WearableSample[] = [];

  for (let d = DEMO_DAYS; d >= 0; d--) {
    const day = addDays(today, -d);
    const isToday = d === 0;
    const weekday = day.getDay();
    const isWeekday = weekday >= 1 && weekday <= 5;
    const wakeups = nightWakeups(rand, d);

    // --- Bracelet: night readings every 30 min, 22:30 → 07:30 ---------------
    const nightStart = at(addDays(day, -1), 22, 30);
    const awakeSlots = new Set<number>();
    while (awakeSlots.size < wakeups) awakeSlots.add(2 + Math.floor(rand() * 15));
    for (let i = 0; i < 19; i++) {
      const t = new Date(nightStart.getTime() + i * 30 * 60000);
      if (t > now) break;
      let state: SleepState;
      if (i === 0 || i === 18 || awakeSlots.has(i)) state = "awake";
      else if ((i >= 4 && i <= 7) || (i >= 11 && i <= 12)) state = "deep";
      else state = "light";
      const hr = state === "awake" ? 70 + Math.round(rand() * 9) : state === "light" ? 60 + Math.round(rand() * 6) : 55 + Math.round(rand() * 5);
      wearable.push({
        timestamp: toLocalIso(t),
        subject_id: SUBJECT.id,
        heart_rate_bpm: hr,
        sleep_state: state,
        spo2_pct: Math.round((94 + rand() * 3) * 10) / 10,
      });
    }
    // --- Bracelet: daytime activity ----------------------------------------
    const lowActivity = d === 12 || d === 11 || d === 8 || d === 7;
    for (const h of [10, 14, 18]) {
      const t = at(day, h);
      if (t > now) break;
      const steps = Math.round((lowActivity ? 180 : 450) + rand() * (lowActivity ? 220 : 520));
      wearable.push({ timestamp: toLocalIso(t), subject_id: SUBJECT.id, heart_rate_bpm: 68 + Math.round(rand() * 12), steps });
    }

    if (wakeups >= 3 && !isToday) {
      push(ctx, at(day, 7, 30), at(day, 7, 45), "sleep", `${wakeups} périodes d'éveil mesurées entre 22 h 30 et 7 h 30`, "", "info", "wearable");
    } else if (isToday && wakeups >= 3 && now > at(day, 7, 45)) {
      push(ctx, at(day, 7, 30), at(day, 7, 45), "sleep", `${wakeups} périodes d'éveil mesurées entre 22 h 30 et 7 h 30`, "", "info", "wearable");
    }

    // --- Auxiliary visit, weekday mornings ---------------------------------
    if (isWeekday && (!isToday || now > at(day, 10))) {
      const visit = at(day, 9, 30);
      const reported = at(day, 10, 15);
      push(
        ctx,
        visit,
        reported,
        "meals_hydration",
        pick(rand, ["Petit-déjeuner pris en entier", "Petit-déjeuner pris en partie : café et une biscotte", "Petit-déjeuner pris en entier, un grand verre d'eau bu"]),
        pick(rand, ["petit-déjeuner pris en entier", "a pris son café et une biscotte", "petit-déjeuner complet, a bien bu"]),
        "info",
        "auxiliary_report",
      );
      if (rand() < 0.35) {
        push(ctx, at(day, 9, 50), reported, "mobility_falls", "Marche dans le couloir avec le déambulateur, une dizaine de minutes", "marche avec le déambulateur dans le couloir, 10 minutes", "info", "auxiliary_report");
      }
    }
    if (d === 15) {
      push(ctx, at(day, 10, 0), at(day, 10, 15), "vitals", "Tension relevée à 13/8 lors du passage de l'infirmière", "tension prise par l'infirmière : 13/8", "info", "auxiliary_report");
    }

    if (isToday || NO_REPORT_DAYS.has(d)) continue;

    // --- Caregiver evening report -----------------------------------------
    const rep = at(day, 20, Math.floor(rand() * 40));

    if (wakeups >= 3) {
      push(ctx, at(day, 7, 30), rep, "sleep", "Nuit agitée, plusieurs réveils", "il a mal dormi, il s'est réveillé plusieurs fois", "watch");
    } else {
      push(ctx, at(day, 7, 30), rep, "sleep", pick(rand, ["Nuit calme, levé vers 8 h", "Nuit calme rapportée", "Nuit complète, levé vers 7 h 30"]), pick(rand, ["il a bien dormi, il s'est levé vers huit heures", "la nuit a été calme", "il a fait sa nuit, levé vers sept heures et demie"]));
    }

    if (REFUSED_TREATMENT_DAYS.has(d)) {
      push(ctx, at(day, 8, 30), rep, "medication", "Traitement du matin non pris : refus exprimé", "il a refusé son traitement ce matin", "watch");
    } else {
      push(ctx, at(day, 8, 30), rep, "medication", "Traitement du matin pris", pick(rand, ["il a pris ses médicaments ce matin", "il a bien pris son traitement", "les médicaments du matin, c'est fait"]));
    }

    const meal = rand();
    if (meal < 0.15) {
      push(ctx, at(day, 16, 0), rep, "meals_hydration", "Peu bu dans la journée : environ deux verres d'eau", "il n'a presque pas bu, à peine deux verres", "watch");
    } else if (meal < 0.45) {
      push(ctx, at(day, 12, 30), rep, "meals_hydration", "Moitié du déjeuner mangée", "il a mangé la moitié de son assiette");
    } else {
      push(ctx, at(day, 12, 30), rep, "meals_hydration", "Déjeuner mangé en entier", pick(rand, ["il a tout mangé à midi", "il a fini son assiette ce midi"]));
    }

    const mood = rand();
    if (d === 12 || mood < 0.18) {
      push(ctx, at(day, 17, 0), rep, "mood_behavior", "Agitation en fin d'après-midi, a voulu sortir seul", "il était agité vers dix-sept heures, il voulait sortir", "watch");
    } else if (mood < 0.35) {
      push(ctx, at(day, 11, 0), rep, "mood_behavior", "A demandé plusieurs fois quel jour on était", "il m'a demandé plusieurs fois quel jour on était");
    } else if (weekday === 0) {
      push(ctx, at(day, 15, 0), rep, "mood_behavior", "Souriant pendant la visite de Julien", "il a souri tout l'après-midi quand Julien est venu");
    } else {
      push(ctx, at(day, 15, 0), rep, "mood_behavior", pick(rand, ["Calme, a regardé la télévision", "Calme, a feuilleté le journal", "Calme, a fait une courte sieste"]), pick(rand, ["il était calme, il a regardé la télé", "il était tranquille, il a lu le journal", "il était calme, il a fait une petite sieste"]));
    }

    // --- Notable events -----------------------------------------------------
    if (d === 12) {
      push(ctx, at(day, 6, 0), rep, "mobility_falls", "Retrouvé assis au sol dans sa chambre vers 6 h, pas de saignement constaté", "je l'ai retrouvé par terre dans sa chambre vers six heures, assis, il ne saignait pas", "urgent");
    }
    if (d === 8 || d === 7) {
      push(ctx, at(day, 10, 30), rep, "pain", "Douleur au genou droit signalée à la marche", "il s'est plaint de son genou droit quand il marchait", "watch");
    }
    if (d === 14) {
      push(ctx, at(day, 11, 0), rep, "appointment", "Consultation au cabinet du Dr Lefèvre", "on est allés chez le docteur Lefèvre ce matin");
    }
    if (d === 10 || d === 3) {
      push(ctx, at(day, 10, 0), rep, "appointment", "Séance de kinésithérapie à domicile", "le kiné est passé à dix heures");
    }
    if (d === 20) {
      push(ctx, at(day, 14, 0), rep, "incident", "Robinet de la salle de bain laissé ouvert, petite inondation sans conséquence", "il a laissé le robinet ouvert, il y avait de l'eau partout dans la salle de bain", "watch");
    }
    if (d === 18) {
      push(ctx, at(day, 16, 30), rep, "logistics", "Renouvellement de l'ordonnance récupéré à la pharmacie", "j'ai récupéré le renouvellement à la pharmacie");
    }
    if (d === 6) {
      push(ctx, at(day, 18, 0), rep, "logistics", "Protections à racheter", "il faudra racheter des protections");
    }
    if (d === 2) {
      push(ctx, at(day, 18, 30), rep, "appointment", "Consultation d'ophtalmologie à reprogrammer, date à confirmer", "il faut reprendre rendez-vous chez l'ophtalmo");
    }
  }

  ctx.out.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  const observations: Observation[] = ctx.out.map((o, i) => ({ id: `obs-${String(i + 1).padStart(4, "0")}`, ...o }));
  return { observations, wearable };
}

/** Regenerates only the bracelet data (not persisted, cheap to rebuild). */
export function generateWearable(now: Date): WearableSample[] {
  return generateDemoData(now).wearable;
}
