"use client";
import { FlaskConical } from "lucide-react";
import { useTechnical } from "./demo-shell";
import type { ProviderMetadata } from "@/lib/api";

export function TechnicalCard({ title, children }: { title: string; children: React.ReactNode }) {
  const technical = useTechnical();
  if (!technical) return null;
  return <aside className="technical-card"><h2 className="flex items-center gap-2 text-sm font-bold"><FlaskConical size={16} />{title}</h2><div className="mt-3 space-y-2 text-xs leading-relaxed">{children}</div></aside>;
}
export function LLMMetadata({ metadata }: { metadata: ProviderMetadata | null | undefined }) {
  if (!metadata) return <p>Métadonnées de cet appel indisponibles après rechargement.</p>;
  return <dl className="metadata-grid"><dt>provider_used</dt><dd>{metadata.provider_used}</dd><dt>Validation</dt><dd>Sortie acceptée · contrat Pydantic</dd><dt>Réparations</dt><dd>{metadata.validation_retry_count}</dd><dt>Latence</dt><dd>{metadata.latency_ms} ms</dd>{metadata.model_id && <><dt>Modèle demandé</dt><dd className="break-all">{metadata.model_id}</dd></>}<dt>Repli</dt><dd>{metadata.fallback_used ? "Oui · Mode démo" : "Non"}</dd></dl>;
}
