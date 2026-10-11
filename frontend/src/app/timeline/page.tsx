"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getTimeline, type Observation } from "@/lib/api";

// Fixed demo subject for this slice; subject selection comes later.
const DEMO_SUBJECT_ID = "subject-demo-1";

type TimelineState =
  | { kind: "loading" }
  | { kind: "done"; observations: Observation[] }
  | { kind: "error"; detail: string };

/** Formats an ISO timestamp as a readable French date-time, falling back to the raw string. */
function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

/** Minimal timeline view: lists the demo subject's observations in time order. */
export default function TimelinePage() {
  const [state, setState] = useState<TimelineState>({ kind: "loading" });

  useEffect(() => {
    let active = true;
    getTimeline({ subject_id: DEMO_SUBJECT_ID }).then((result) => {
      if (!active) return;
      setState(
        result.ok
          ? { kind: "done", observations: result.observations }
          : { kind: "error", detail: result.detail },
      );
    });
    return () => {
      active = false;
    };
  }, []);

  let status = "";
  if (state.kind === "loading") status = "Chargement de la chronologie…";
  else if (state.kind === "error") status = state.detail;
  else if (state.observations.length === 0) status = "Aucun fait enregistré pour l'instant.";
  else status = `${state.observations.length} fait(s) dans la chronologie.`;

  return (
    <main>
      <p>
        <Link href="/">Retour à l&apos;accueil</Link>
      </p>
      <h1>Chronologie</h1>

      <p aria-live="polite" role="status" data-state={state.kind}>
        {status}
      </p>

      {state.kind === "done" && state.observations.length > 0 && (
        <ol lang="fr">
          {state.observations.map((obs) => (
            <li key={obs.id}>
              {formatDate(obs.timestamp)} — [{obs.severity}] {obs.category} : {obs.value}
            </li>
          ))}
        </ol>
      )}
    </main>
  );
}
