"use client";

import { useEffect, useState } from "react";

import { getApiBaseUrl, getHealth } from "@/lib/api";

type HealthState =
  | { kind: "loading" }
  | { kind: "connected"; version: string }
  | { kind: "error" };

/** Shows whether the backend answers GET /health. User-facing text is French. */
export default function HealthIndicator() {
  const [state, setState] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    let active = true;
    getHealth().then(
      (health) => {
        if (!active) return;
        setState(
          health.status === "ok"
            ? { kind: "connected", version: health.version }
            : { kind: "error" },
        );
      },
      () => {
        if (active) setState({ kind: "error" });
      },
    );
    return () => {
      active = false;
    };
  }, []);

  let message: string;
  if (state.kind === "loading") {
    message = "Vérification de la connexion au serveur…";
  } else if (state.kind === "connected") {
    message = `Connecté au serveur (version ${state.version})`;
  } else {
    message = `Impossible de joindre le serveur à ${getApiBaseUrl()}`;
  }

  return (
    <p aria-live="polite" data-state={state.kind}>
      {message}
    </p>
  );
}
