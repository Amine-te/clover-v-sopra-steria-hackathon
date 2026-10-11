"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Mic, PenLine, ArrowUpRight, BookOpen, ShieldCheck } from "lucide-react";
import { api, type Recipient, type Timeline, type User } from "@/lib/api";
import { frenchDate, humanError } from "@/lib/demo";

export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null);
  const [recipient, setRecipient] = useState<Recipient | null>(null);
  const [timeline, setTimeline] = useState<Timeline | null>(null); const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    Promise.all([api<User>("/me"), api<Recipient[]>("/care-recipients")]).then(async ([thomas, recipients]) => {
      const marie = recipients.find((item) => item.first_name === "Marie");
      if (!active || !marie) return; setUser(thomas); setRecipient(marie);
      const items = await api<Timeline>(`/care-recipients/${marie.id}/timeline`); if (active) setTimeline(items);
    }).catch((err) => { if (active) setError(humanError(err)); });
    return () => { active = false; };
  }, []);
  return <main className="page-shell">
    <header className="flex items-center justify-between"><span className="text-2xl font-bold tracking-tight text-teal">karis<span className="text-coral">.</span></span><span className="badge badge-teal"><ShieldCheck size={13} /> Votre espace personnel</span></header>
    <section className="mt-10"><p className="text-navy-soft">Bonjour {user?.full_name.split(" ")[0] ?? "Thomas"}</p><div className="mt-5 flex items-center gap-4"><span className="avatar !h-16 !w-16 !bg-sand !text-2xl !text-navy">M</span><div><h1 className="text-3xl font-bold tracking-tight">{recipient?.first_name ?? "Marie"}</h1><p className="mt-1 text-sm text-navy-soft">82 ans · votre maman</p></div></div>
      <h2 className="mt-8 max-w-sm text-2xl font-semibold leading-snug tracking-tight">Comment s’est passée la journée avec Marie ?</h2><p className="mt-3 text-sm leading-relaxed text-navy-soft">Quelques mots suffisent. Karis vous aide à garder le fil.</p>
      <Link href="/journal/new?mode=voice" className="button-primary mt-7 !min-h-16 !rounded-3xl !text-base"><Mic size={24} /> Raconter ma journée</Link><Link href="/journal/new?mode=text" className="button-secondary mt-3"><PenLine size={19} /> Écrire</Link>
    </section>
    {error && <p role="alert" className="error-box">{error}</p>}
    <section className="mt-10"><div className="flex items-center justify-between"><h2 className="font-bold">Dernières nouvelles</h2><Link href="/timeline" className="flex items-center gap-1 text-xs font-semibold text-teal">Tout voir <ArrowUpRight size={14} /></Link></div><div className="mt-4 grid gap-3">{timeline?.items.slice(0, 2).map((item) => <Link href={`/journal/${item.id}/review`} key={item.id} className="card !rounded-2xl !p-4"><p className="text-xs text-navy-soft">{frenchDate(item.date)}</p><p className="mt-2 line-clamp-2 text-sm leading-relaxed">{item.short_summary}</p></Link>)}{!timeline && !error && <p className="text-sm text-navy-soft">Votre journal se prépare…</p>}</div></section>
    <Link href="/reports/weekly" className="mt-6 flex items-center gap-4 rounded-3xl bg-sand p-5"><span className="icon-button bg-white/70 text-teal"><BookOpen size={23} /></span><div className="flex-1"><h2 className="font-bold">Bilan de la semaine</h2><p className="mt-1 text-xs text-navy-soft">Les moments importants, simplement.</p></div><ArrowUpRight size={18} /></Link>
  </main>;
}
