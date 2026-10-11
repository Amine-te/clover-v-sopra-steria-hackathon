"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, BookOpen, ArrowUpRight } from "lucide-react";
import { api, type Recipient, type WeeklyReport } from "@/lib/api";
import { frenchDate, humanError, rememberMetadata } from "@/lib/demo";

function previousWeek() {
  const now = new Date(); const end = new Date(now); end.setDate(now.getDate() - (now.getDay() || 7)); const start = new Date(end); start.setDate(end.getDate() - 6);
  const format = (day: Date) => `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
  return { period_start: format(start), period_end: format(end) };
}
export default function WeeklyReportsPage() {
  const router = useRouter(); const [recipient, setRecipient] = useState<Recipient | null>(null); const [reports, setReports] = useState<WeeklyReport[]>([]);
  const [period, setPeriod] = useState(previousWeek); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => {
    api<Recipient[]>("/care-recipients").then(async (items) => { const marie = items.find((item) => item.first_name === "Marie"); if (marie) { setRecipient(marie); setReports(await api<WeeklyReport[]>(`/care-recipients/${marie.id}/reports`)); } }).catch((err) => setError(humanError(err)));
    api<{ period_start: string; period_end: string }>("/demo/status").then((data) => setPeriod({ period_start: data.period_start, period_end: data.period_end })).catch(() => undefined);
  }, []);
  async function generate() {
    if (!recipient || busy) return; setBusy(true); setError("");
    try { const report = await api<WeeklyReport>(`/care-recipients/${recipient.id}/reports/weekly/generate`, { method: "POST", body: JSON.stringify(period) }); rememberMetadata(report.id, report.provider_metadata); router.push(`/reports/${report.id}`); }
    catch (err) { setError(humanError(err)); } finally { setBusy(false); }
  }
  return <main className="page-shell"><Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-semibold text-teal"><ArrowLeft size={16} /> Accueil</Link><p className="eyebrow mt-8">Prendre du recul</p><h1 className="page-title !mt-3">Votre semaine avec Marie</h1><p className="mt-4 text-sm leading-relaxed text-navy-soft">Un bilan clair à partir de vos notes validées. Vous gardez la main sur sa version finale.</p>
    <section className="card mt-7 !bg-sand/50"><BookOpen className="text-teal" size={26} /><h2 className="mt-4 font-bold">Du {frenchDate(period.period_start)} au {frenchDate(period.period_end)}</h2><p className="mt-2 text-xs leading-relaxed text-navy-soft">Alimentation, sommeil, organisation et actions à suivre.</p><button onClick={generate} disabled={!recipient || busy} className="button-primary mt-5 w-full">{busy ? "Préparation du bilan…" : "Préparer le bilan de la semaine"}</button></section>
    {error && <p role="alert" className="error-box">{error}</p>}
    {!!reports.length && <section className="mt-8"><h2 className="font-bold">Vos bilans</h2><div className="mt-4 grid gap-3">{reports.map((report) => <Link key={report.id} href={`/reports/${report.id}`} className="card"><div className="flex items-center justify-between"><p className="font-bold">{report.title}</p><ArrowUpRight size={18} className="text-teal" /></div><p className="mt-2 text-xs text-navy-soft">{frenchDate(report.period_start)} – {frenchDate(report.period_end)} · {report.source_entry_count} entrées</p><span className={`badge mt-3 ${report.approved ? "badge-teal" : ""}`}>{report.approved ? "Validé" : "À relire"}</span></Link>)}</div></section>}
  </main>;
}
