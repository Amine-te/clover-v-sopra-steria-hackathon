"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Mic, PenLine, LockKeyhole } from "lucide-react";
import { api, type Recipient, type Timeline } from "@/lib/api";
import { frenchDate, humanError, categoryLabels, actionLabels } from "@/lib/demo";

export default function TimelinePage() {
  const [timeline, setTimeline] = useState<Timeline | null>(null); const [error, setError] = useState("");
  useEffect(() => { api<Recipient[]>("/care-recipients").then((items) => { const marie = items.find((item) => item.first_name === "Marie"); if (marie) return api<Timeline>(`/care-recipients/${marie.id}/timeline`).then(setTimeline); }).catch((err) => setError(humanError(err))); }, []);
  const groups = new Map<string, NonNullable<Timeline>["items"]>();
  timeline?.items.forEach((item) => { const date = new Date(item.date).toLocaleDateString("fr-CA"); groups.set(date, [...(groups.get(date) ?? []), item]); });
  return <main className="page-shell"><Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-semibold text-teal"><ArrowLeft size={16} /> Accueil</Link><p className="eyebrow mt-8">Un jour après l’autre</p><h1 className="page-title !mt-3">Le fil de Marie</h1><p className="mt-3 text-sm text-navy-soft">Les notes validées et les petites choses à suivre.</p>{error && <p role="alert" className="error-box">{error}</p>}{!timeline && !error && <p className="mt-6 text-sm text-navy-soft">Ouverture de votre timeline…</p>}
    <div className="mt-7 space-y-7">{Array.from(groups.entries()).map(([date, items]) => <section key={date}><h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-navy-soft">{frenchDate(date)}</h2><div className="grid gap-3">{items.map((item) => <article key={item.id} className="card !rounded-2xl"><div className="flex items-center justify-between"><span className="inline-flex items-center gap-1.5 text-[11px] text-navy-soft">{item.source_type === "voice" ? <Mic size={13} /> : <PenLine size={13} />}{item.source_type === "voice" ? "Note vocale" : "Note écrite"}</span>{item.has_private_data && <span className="badge"><LockKeyhole size={11} /> Espace privé</span>}</div><Link href={`/journal/${item.id}/review`} className="mt-3 block text-sm font-medium leading-relaxed">{item.short_summary}</Link><div className="mt-4 flex flex-wrap gap-2">{Array.from(new Set(item.observations.map((observation) => observation.category))).map((category) => <span key={category} className="badge badge-teal">{categoryLabels[category] ?? category}</span>)}</div>{item.actions.map((action) => <div key={action.id} className="mt-3 border-t border-sand pt-3 text-xs leading-relaxed"><span className={`badge mr-2 ${action.status === "pending" ? "badge-coral" : ""}`}>{actionLabels[action.status] ?? action.status}</span>{action.description}</div>)}</article>)}</div></section>)}</div><Link href="/reports/weekly" className="button-secondary mt-8">Bilan de la semaine</Link>
  </main>;
}
