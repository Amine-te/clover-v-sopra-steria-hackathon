import type { Recipient } from "@/lib/types";

/**
 * Fictional people only (constitution, rule 6). Contact details are invented
 * and use reserved/non-routable formats.
 */

export const SUBJECT = {
  id: "subject-demo-1",
  firstName: "Robert",
  lastName: "Martin",
  age: 84,
  relation: "votre père",
  bracelet: "Bracelet connecté (simulé)",
};

export const CAREGIVER = {
  id: "caregiver-demo-1",
  firstName: "Claire",
  lastName: "Martin",
};

export interface Contact {
  role: Recipient;
  name: string;
  detail: string;
  contact: string;
  initials: string;
}

export const CONTACTS: Record<Recipient, Contact> = {
  auxiliary: {
    role: "auxiliary",
    name: "Samia Benali",
    detail: "Auxiliaire de vie · passe du lundi au vendredi",
    contact: "06 00 00 00 01 (fictif)",
    initials: "SB",
  },
  family: {
    role: "family",
    name: "Julien Martin",
    detail: "Fils de Robert · vit à Lyon",
    contact: "06 00 00 00 02 (fictif)",
    initials: "JM",
  },
  doctor: {
    role: "doctor",
    name: "Dr Hélène Lefèvre",
    detail: "Médecin traitant",
    contact: "cabinet.lefevre@exemple.invalid",
    initials: "HL",
  },
  caregiver: {
    role: "caregiver",
    name: "Claire Martin",
    detail: "Aidante principale · fille de Robert",
    contact: "Cet appareil",
    initials: "CM",
  },
};

export const AUXILIARY_ID = "auxiliary-demo-1";
export const WEARABLE_ID = "wearable-demo-1";
