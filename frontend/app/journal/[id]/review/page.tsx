"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, LockKeyhole, ChevronDown, ShieldCheck, CheckCircle2 } from "lucide-react";
import { api, type Journal, type MultimodalContext, type ProviderMetadata } from "@/lib/api";
import { humanError, categoryLabels, recallMetadata } from "@/lib/demo";
import { TechnicalCard, LLMMetadata } from "@/components/technical-card";

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>(); const router = useRouter();
  const [entry, setEntry] = useState<Journal | null>(null); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const [multimodal, setMultimodal] = useState<MultimodalContext | null>(null); const [metadata, setMetadata] = useState<ProviderMetadata | null>(null);
  useEffect(() => {
    setMetadata(recallMetadata(id));
    api<Journal>(`/journal/${id}`).then(setEntry).catch((err) => setError(humanError(err)));
    api<MultimodalContext>(`/journal/${id}/multimodal-context`).then(setMultimodal).catch(() => undefined);
  }, [id]);
  async function finalize() {
    if (busy) return; setBusy(true); setError("");
    try { await api(`/journal/${id}/finalize`, { method: "POST" }); router.push(`/journal/${id}/share`); }
    catch (err) { setError(humanError(err)); } finally { setBusy(false); }
  }
  const ser = multimodal?.caregiver_vocal_affect; const caregiver = multimodal?.caregiver_wearable; const marie = multimodal?.care_recipient_wearable;
  const fatigueClarified = entry?.clarifications.some((item) => item.question.toLocaleLowerCase("fr-FR").includes("fatigu") && item.answer?.trim().toLocaleLowerCase("fr-FR") === "oui");
  return <main className="page-shell"><Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-semibold text-teal"><ArrowLeft size={16} /> Accueil</Link><p className="eyebrow mt-8">Votre relecture</p><h1 className="page-title !mt-3">Ce que Karis a compris</h1><p className="mt-3 text-sm text-navy-soft">Vos mots, organisés pour vous aider à garder le fil.</p>
    {metadata?.fallback_used && <span className="badge mt-4">Mode démo · repli du générateur</span>}{error && <p role="alert" className="error-box">{error}</p>}
    {entry?.short_summary && <p className="card mt-6 !bg-teal/5 !border-teal/10 text-sm leading-relaxed">{entry.short_summary}</p>}
    {!entry && !error && <p className="mt-8 text-sm text-navy-soft">Votre note se prépare…</p>}
    <section className="mt-8"><h2 className="text-lg font-bold">Marie</h2><div className="mt-3 grid gap-3">{entry?.observations.map((item) => <article key={item.id} className="card !rounded-2xl !p-4"><div className="flex flex-wrap gap-2"><span className="badge badge-teal">{categoryLabels[item.category] ?? item.category}</span><span className="badge">{fatigueClarified && item.category === "fatigue" ? "Précisé" : "Rapporté"}</span></div><p className="mt-3 text-sm leading-relaxed">{item.description}</p></article>)}</div></section>
    {!!entry?.actions.length && <section className="mt-7"><h2 className="text-lg font-bold">Actions</h2><div className="mt-3 grid gap-3">{entry.actions.map((action) => <article key={action.id} className="card !rounded-2xl !p-4"><span className="badge badge-coral">Action</span><p className="mt-3 text-sm leading-relaxed">{action.description}</p></article>)}</div></section>}
    {!!entry?.caregiver_feelings.length && <section className="mt-7"><div className="flex items-center justify-between"><h2 className="text-lg font-bold">Pour vous</h2><span className="badge"><LockKeyhole size={12} /> Privé</span></div>{entry.caregiver_feelings.map((feeling) => <div key={feeling.id} className="mt-3 rounded-2xl bg-sand/70 p-5"><p className="text-sm leading-relaxed">{feeling.description}</p><p className="mt-3 flex items-center gap-2 text-xs text-navy-soft"><ShieldCheck size={14} /> Visible uniquement dans votre espace.</p></div>)}</section>}
    <details className="card mt-7 !p-5"><summary className="flex min-h-6 list-none items-center justify-between text-sm font-semibold">Contexte multimodal <ChevronDown size={17} /></summary><div className="mt-5 grid gap-4 text-sm">
      <div className="flex flex-wrap gap-2">{[["Journal", !!entry], ["SER aidant", !!ser], ["Bracelet aidant", !!caregiver], ["Bracelet Marie", !!marie]].map(([label, available]) => <span className={`badge ${available ? "badge-teal" : ""}`} key={String(label)}>{available ? "✓" : "—"} {label}</span>)}</div>
      {ser && <div className="rounded-2xl bg-ivory p-4"><div className="flex items-center justify-between"><h3 className="font-semibold">SER aidant</h3><span className="badge"><LockKeyhole size={12} /> Privé</span></div><p className="mt-3 text-navy-soft">Valence estimée {ser.valence === "negative" ? "négative" : ser.valence === "positive" ? "positive" : "neutre ou indéterminée"}<br />Activation {ser.arousal === "high" ? "élevée" : ser.arousal === "low" ? "faible" : "indéterminée"}<br />Confiance {Math.round(ser.confidence * 100)} %</p></div>}
      {caregiver && <div className="rounded-2xl bg-ivory p-4"><div className="flex items-center justify-between"><h3 className="font-semibold">Bracelet aidant</h3><span className="badge"><LockKeyhole size={12} /> Privé</span></div><p className="mt-3 text-navy-soft">FC moyenne {caregiver.metrics.heart_rate_avg_bpm ?? caregiver.metrics.heart_rate_avg} bpm<br />{caregiver.metrics.coverage_pct !== undefined && <>Couverture {caregiver.metrics.coverage_pct} %</>}</p></div>}
      {marie && <div className="rounded-2xl bg-teal/5 p-4"><h3 className="font-semibold">Bracelet Marie</h3><p className="mt-3 text-navy-soft">FC moyenne {marie.metrics.heart_rate_avg_bpm ?? marie.metrics.heart_rate_avg} bpm<br />{Number(marie.metrics.steps_total ?? marie.metrics.steps ?? 0).toLocaleString("fr-FR")} pas<br />Qualité {marie.quality === "good" ? "bonne" : "non déterminée"}</p></div>}
      {!ser && !caregiver && !marie && <p className="text-navy-soft">Ces signaux facultatifs ne sont pas disponibles. Votre journal continue normalement.</p>}
      <p className="border-t border-sand pt-4 text-xs leading-relaxed text-navy-soft">Ces signaux apportent du contexte. Ils ne constituent pas une interprétation médicale.</p>
    </div></details>
    <TechnicalCard title="Pipeline IA"><p className="font-semibold">{entry?.input_type === "voice" ? "Transcript" : "Texte"} → {metadata?.provider_used === "bedrock" ? "Bedrock" : metadata ? "Mock LLM" : "Générateur"} → Structured Output → Pydantic validé → Objets métier persistés</p><LLMMetadata metadata={metadata} /></TechnicalCard>
    {entry?.clarification_needed ? <Link href={`/journal/${id}/clarify`} className="button-primary mt-7">Compléter les précisions</Link> : entry?.status === "analyzed" ? <button onClick={finalize} disabled={busy} className="button-primary mt-7 w-full"><CheckCircle2 size={18} /> {busy ? "Validation…" : "Valider et préparer le partage"}</button> : entry?.status === "finalized" ? <Link href={`/journal/${id}/share`} className="button-primary mt-7">Voir les transmissions</Link> : entry && <Link href="/journal/new" className="button-secondary mt-7">Revenir au journal</Link>}
  </main>;
}
