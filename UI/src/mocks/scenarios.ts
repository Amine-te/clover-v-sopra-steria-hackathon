import type { Category, FollowUpQuestion, GuardrailNote, Severity } from "@/lib/types";

/**
 * Demo fixtures standing in for the cached-transcript fallback
 * (feature 001-AC2, constitution rule 8). The "extraction" below is written
 * by hand: no AI runs in the frontend. Every `span` is an exact substring of
 * its transcript (feature 002-AC2).
 */

export interface ScenarioFact {
  category: Category;
  /** Hour and minute of the fact, today. */
  time: [number, number];
  value: string;
  severity: Severity;
  confidence: number;
  span: string;
}

export interface Scenario {
  id: string;
  title: string;
  transcript: string;
  durationS: number;
  facts: ScenarioFact[];
  privatePassages: string[];
  guardrail: GuardrailNote[];
  followups: FollowUpQuestion[];
}

const SLEEP_Q: FollowUpQuestion = {
  id: "fu-sleep",
  category: "sleep",
  prompt: "Comment s'est passée la nuit dernière de Robert ?",
  options: [
    { label: "Nuit calme", value: "Nuit calme rapportée", severity: "info" },
    { label: "Plusieurs réveils", value: "Plusieurs réveils pendant la nuit", severity: "watch" },
    { label: "Levé la nuit", value: "Levé pendant la nuit", severity: "watch" },
  ],
};

const MOOD_Q: FollowUpQuestion = {
  id: "fu-mood",
  category: "mood_behavior",
  prompt: "Et son humeur aujourd'hui ?",
  options: [
    { label: "Calme", value: "Calme dans la journée", severity: "info" },
    { label: "Agité", value: "Agitation dans la journée", severity: "watch" },
    { label: "En retrait", value: "Peu de paroles, est resté en retrait", severity: "watch" },
  ],
};

export const SCENARIOS: Scenario[] = [
  {
    id: "scenario-refus-glissade",
    title: "Refus de traitement et glissade",
    durationS: 48,
    transcript:
      "Alors aujourd'hui, papa a refusé son traitement ce matin, il disait qu'il n'en voulait pas. Vers quinze heures, il a glissé dans la salle de bain. Il ne s'est pas fait mal, mais il a eu du mal à se relever. À midi, il a mangé la moitié de son assiette. Je crois que sa maladie s'aggrave. Et moi, honnêtement, je suis épuisée, j'ai l'impression de ne plus y arriver.",
    facts: [
      {
        category: "medication",
        time: [8, 30],
        value: "Traitement du matin non pris : refus exprimé",
        severity: "watch",
        confidence: 0.93,
        span: "papa a refusé son traitement ce matin, il disait qu'il n'en voulait pas",
      },
      {
        category: "meals_hydration",
        time: [12, 30],
        value: "Moitié du déjeuner mangée",
        severity: "info",
        confidence: 0.88,
        span: "À midi, il a mangé la moitié de son assiette",
      },
      {
        category: "mobility_falls",
        time: [15, 0],
        value: "Glissade dans la salle de bain vers 15 h, pas de blessure signalée, difficulté à se relever",
        severity: "watch",
        confidence: 0.9,
        span: "Vers quinze heures, il a glissé dans la salle de bain. Il ne s'est pas fait mal, mais il a eu du mal à se relever",
      },
    ],
    privatePassages: ["Et moi, honnêtement, je suis épuisée, j'ai l'impression de ne plus y arriver."],
    guardrail: [
      {
        original: "Je crois que sa maladie s'aggrave.",
        reason: "Il s'agit d'une interprétation médicale. Karis ne consigne que des faits observés : vous pourrez en parler directement au Dr Lefèvre.",
      },
    ],
    // Checklist gaps: sleep and mood were not mentioned (feature 003).
    followups: [SLEEP_Q, MOOD_Q],
  },
  {
    id: "scenario-genou-kine",
    title: "Douleur au genou et organisation",
    durationS: 52,
    transcript:
      "Ce soir, je voulais dire que papa a pris tous ses médicaments avec le petit-déjeuner. Il a peu bu aujourd'hui, à peine deux verres d'eau. Il s'est plaint de son genou droit quand il marchait. Il était de bonne humeur, il a regardé le match avec moi. Le kiné passe jeudi à dix heures. Il faudra racheter des protections. Je n'ai pas eu une minute à moi de la journée.",
    facts: [
      { category: "medication", time: [8, 15], value: "Traitement du matin pris avec le petit-déjeuner", severity: "info", confidence: 0.95, span: "papa a pris tous ses médicaments avec le petit-déjeuner" },
      { category: "meals_hydration", time: [18, 0], value: "Peu bu dans la journée : environ deux verres d'eau", severity: "watch", confidence: 0.91, span: "Il a peu bu aujourd'hui, à peine deux verres d'eau" },
      { category: "pain", time: [11, 0], value: "Douleur au genou droit signalée à la marche", severity: "watch", confidence: 0.89, span: "Il s'est plaint de son genou droit quand il marchait" },
      { category: "mood_behavior", time: [16, 0], value: "De bonne humeur, a regardé un match à la télévision", severity: "info", confidence: 0.84, span: "Il était de bonne humeur, il a regardé le match avec moi" },
      { category: "appointment", time: [19, 0], value: "Séance de kinésithérapie prévue jeudi à 10 h", severity: "info", confidence: 0.66, span: "Le kiné passe jeudi à dix heures" },
      { category: "logistics", time: [19, 0], value: "Protections à racheter", severity: "info", confidence: 0.92, span: "Il faudra racheter des protections" },
    ],
    privatePassages: ["Je n'ai pas eu une minute à moi de la journée."],
    guardrail: [],
    followups: [SLEEP_Q],
  },
  {
    id: "scenario-chute-salon",
    title: "Chute dans le salon",
    durationS: 37,
    transcript:
      "Papa est tombé dans le salon vers dix-huit heures, il s'est cogné la tête contre la table et il a une petite plaie au front. Il a quand même dîné, une soupe et un yaourt. Il a dormi presque toute la nuit d'après lui. Il a pris ses médicaments du soir.",
    facts: [
      { category: "sleep", time: [7, 30], value: "Nuit dernière décrite comme presque complète par Robert", severity: "info", confidence: 0.74, span: "Il a dormi presque toute la nuit d'après lui" },
      { category: "mobility_falls", time: [18, 0], value: "Chute dans le salon vers 18 h, choc à la tête contre la table, petite plaie au front", severity: "urgent", confidence: 0.96, span: "Papa est tombé dans le salon vers dix-huit heures, il s'est cogné la tête contre la table et il a une petite plaie au front" },
      { category: "meals_hydration", time: [19, 15], value: "Dîner pris : une soupe et un yaourt", severity: "info", confidence: 0.9, span: "Il a quand même dîné, une soupe et un yaourt" },
      { category: "medication", time: [19, 30], value: "Traitement du soir pris", severity: "info", confidence: 0.93, span: "Il a pris ses médicaments du soir" },
    ],
    privatePassages: [],
    guardrail: [],
    followups: [MOOD_Q],
  },
];
