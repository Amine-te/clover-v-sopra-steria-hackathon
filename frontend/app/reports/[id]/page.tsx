"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, PenLine, CheckCircle2 } from "lucide-react";
import { api, type WeeklyReport, type ProviderMetadata } from "@/lib/api";
import { frenchDate, humanError, recallMetadata } from "@/lib/demo";
import { TechnicalCard, LLMMetadata } from "@/components/technical-card";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>(); const [report, setReport] = useState<WeeklyReport | null>(null);
  const [editing, setEditing] = useState(false); const [content, setContent] = useState(""); const [error, setError] = useState(""); const [busy, setBusy] = useState(false); const [metadata, setMetadata] = useState<ProviderMetadata | null>(null);
  useEffect(() => { setMetadata(recallMetadata(id)); api<WeeklyReport>(`/reports/${id}`).then((item) => { setReport(item); setContent(item.content); }).catch((err) => setError(humanError(err))); }, [id]);
  async function save() {
    if (busy) return; setBusy(true); setError("");
    try { const updated = await api<WeeklyReport>(`/reports/${id}`, { method: "PATCH", body: JSON.stringify({ edited_markdown: content }) }); setReport(updated); setEditing(false); }
    catch (err) { setError(humanError(err)); } finally { setBusy(false); }
  }
  async function approve() {
    if (busy) return; setBusy(true); setError("");
    try { setReport(await api<WeeklyReport>(`/reports/${id}/approve`, { method: "POST" })); }
    catch (err) { setError(humanError(err)); } finally { setBusy(false); }
  }
  // Render plain text sections. No HTML evaluation or unsafe Markdown renderer.
  const sections = (report?.content ?? "").split("## ").filter((section) => section.trim()).map((section) => {
    const newline = section.indexOf("\n"); return { title: newline < 0 ? "Synthèse" : section.slice(0, newline).trim(), text: newline < 0 ? section.trim() : section.slice(newline + 1).trim() };
  });
  return <main className="page-shell"><Link href="/reports/weekly" className="inline-flex items-center gap-2 text-sm font-semibold text-teal"><ArrowLeft size={16} /> Bilans</Link><p className="eyebrow mt-8">Le bilan hebdomadaire</p><h1 className="page-title !mt-3">Votre semaine avec Marie</h1>
    {report && <><p className="mt-4 text-sm text-navy-soft">Du {frenchDate(report.period_start)} au {frenchDate(report.period_end)}</p><div className="mt-3 flex flex-wrap gap-2"><span className="badge badge-teal">{report.source_entry_count} entrées validées utilisées</span><span className="badge">{report.approved ? "Bilan validé" : "À relire"}</span>{metadata?.fallback_used && <span className="badge">Mode démo</span>}</div></>}
    {error && <p role="alert" className="error-box">{error}</p>}{!report && !error && <p className="mt-6 text-sm text-navy-soft">Ouverture du bilan…</p>}
    {editing ? <><label htmlFor="report-content" className="sr-only">Modifier le bilan</label><textarea id="report-content" value={content} onChange={(event) => setContent(event.target.value)} className="field mt-7 min-h-96" /></> : <div className="mt-6">{sections.map((section, index) => <section key={`${section.title}-${index}`} className={`card report-section ${section.title === "Alimentation" ? "!border-teal/15 !bg-teal/5" : ""}`}><h2>{section.title}</h2><p>{section.text}</p></section>)}</div>}
    {report && !report.approved && <div className="mt-6 grid gap-3 sm:grid-cols-2">{editing ? <button onClick={save} disabled={busy || !content.trim()} className="button-secondary">Enregistrer</button> : <button onClick={() => setEditing(true)} disabled={busy} className="button-secondary"><PenLine size={17} /> Modifier</button>}<button onClick={approve} disabled={busy || editing} className="button-primary"><CheckCircle2 size={17} /> Valider le bilan</button></div>}
    <p className="mt-6 text-xs leading-relaxed text-navy-soft">Ce document résume les informations consignées dans Karis. Il ne constitue pas un avis médical.</p>
    {report && <TechnicalCard title="Construction du rapport"><p className="font-semibold">{report.structured_item_count} objets structurés PostgreSQL → {report.reportable_item_count} reportables → agrégation déterministe → génération du texte</p><dl className="metadata-grid"><dt>source_entry_count</dt><dd>{report.source_entry_count}</dd><dt>reportable_item_count</dt><dd>{report.reportable_item_count}</dd><dt>excluded_private_count</dt><dd>{report.excluded_private_count}</dd></dl><p>Le générateur reçoit WeeklyReportContext. Il ne compte pas les événements et ne déduit aucun diagnostic.</p><LLMMetadata metadata={metadata} /></TechnicalCard>}
  </main>;
}
