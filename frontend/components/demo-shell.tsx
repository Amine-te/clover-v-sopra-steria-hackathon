"use client";

import Link from "next/link";
import { usePathname, useSearchParams, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { Home, BookOpen, Clock3, Users, Menu, X, ShieldCheck, RotateCcw, FlaskConical, ChevronRight } from "lucide-react";
import { api, type Member, type Recipient } from "@/lib/api";
import { humanError, roleLabels } from "@/lib/demo";

const TechnicalContext = createContext(false);
export const useTechnical = () => useContext(TechnicalContext);

export function DemoShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname(); const search = useSearchParams(); const router = useRouter();
  const [technical, setTechnical] = useState(false);
  const [panel, setPanel] = useState<"menu" | "circle" | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [resetEnabled, setResetEnabled] = useState(false);
  const [confirm, setConfirm] = useState(false); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  useEffect(() => {
    const query = search.get("technical");
    if (query === "1" || query === "0") sessionStorage.setItem("karis_technical", query);
    setTechnical(sessionStorage.getItem("karis_technical") === "1");
    setPanel(null); setConfirm(false); setError("");
  }, [pathname, search]);
  useEffect(() => {
    if (!panel) return;
    if (panel === "circle") api<Recipient[]>("/care-recipients").then((recipients) => {
      const marie = recipients.find((item) => item.first_name === "Marie");
      if (marie) return api<Member[]>(`/care-recipients/${marie.id}/members`).then(setMembers);
    }).catch((err) => setError(humanError(err)));
    if (panel === "menu") api<{ reset_enabled: boolean }>("/demo/status").then((result) => setResetEnabled(result.reset_enabled)).catch(() => setResetEnabled(false));
  }, [panel]);
  useEffect(() => {
    if (!panel) return;
    function escape(event: KeyboardEvent) { if (event.key === "Escape") setPanel(null); }
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [panel]);
  function toggleTechnical() {
    const next = !technical; setTechnical(next); sessionStorage.setItem("karis_technical", next ? "1" : "0");
    const query = new URLSearchParams(search.toString()); query.set("technical", next ? "1" : "0");
    router.replace(`${pathname}?${query}`);
  }
  async function reset() {
    setBusy(true); setError("");
    try {
      await api("/demo/reset", { method: "POST", body: JSON.stringify({ confirmed: true }) });
      Object.keys(sessionStorage).filter((key) => key.startsWith("karis_metadata_")).forEach((key) => sessionStorage.removeItem(key));
      setPanel(null); setConfirm(false); window.location.assign(`/demo${technical ? "?technical=1" : ""}`);
    } catch (err) { setError(humanError(err)); } finally { setBusy(false); }
  }
  const showNav = pathname !== "/" && pathname !== "/demo";
  const linkQuery = technical ? "?technical=1" : "";
  return <TechnicalContext.Provider value={technical}>
    {technical && <div className="technical-banner"><FlaskConical size={13} /> Présentation technique · données de démonstration</div>}
    <div className={showNav ? "app-content" : ""}>{children}</div>
    {showNav && <nav aria-label="Navigation principale" className="bottom-nav">
      {[{ href: "/dashboard", label: "Accueil", icon: Home, active: pathname === "/dashboard" }, { href: "/journal/new", label: "Journal", icon: BookOpen, active: pathname.startsWith("/journal") }, { href: "/timeline", label: "Timeline", icon: Clock3, active: pathname === "/timeline" }].map(({ href, label, icon: Icon, active }) => <Link key={href} href={href + linkQuery} aria-current={active ? "page" : undefined} className={active ? "nav-item active" : "nav-item"}><Icon size={21} strokeWidth={1.8} /><span>{label}</span></Link>)}
      <button onClick={() => { setPanel("circle"); setError(""); }} className="nav-item"><Users size={21} strokeWidth={1.8} /><span>Cercle</span></button>
      <button onClick={() => { setPanel("menu"); setError(""); }} className="nav-item"><Menu size={21} strokeWidth={1.8} /><span>Menu</span></button>
    </nav>}
    {panel && <div className="sheet-backdrop" onClick={() => setPanel(null)}><section role="dialog" aria-modal="true" aria-label={panel === "menu" ? "Menu" : "Le cercle de Marie"} className="sheet" onClick={(event) => event.stopPropagation()}>
      <div className="flex items-center justify-between"><h2 className="text-2xl font-bold">{panel === "menu" ? "Votre espace" : "Le cercle de Marie"}</h2><button autoFocus aria-label="Fermer" onClick={() => setPanel(null)} className="icon-button"><X size={22} /></button></div>
      {panel === "circle" ? <><p className="mt-2 text-sm text-navy-soft">Chacun reçoit les informations utiles à son rôle.</p><div className="mt-6 grid gap-4">{members.filter((member) => member.active).map((member) => <div className="flex items-center gap-3" key={member.id}><span className="avatar">{member.name[0]}</span><div><p className="font-semibold">{member.name}</p><p className="text-sm text-navy-soft">{roleLabels[member.role] ?? member.role}</p></div></div>)}</div></> : <div className="mt-5 grid gap-3">
        <Link onClick={() => setPanel(null)} href={`/reports/weekly${linkQuery}`} className="menu-row"><BookOpen size={20} /> Bilan de la semaine <ChevronRight className="ml-auto" size={18} /></Link>
        <button onClick={toggleTechnical} className="menu-row"><FlaskConical size={20} /> Mode technique <span className="ml-auto badge">{technical ? "Activé" : "Désactivé"}</span></button>
        <p className="flex gap-2 rounded-2xl bg-teal/5 p-4 text-sm text-navy-soft"><ShieldCheck className="shrink-0 text-teal" size={20} /> Vos ressentis et vos signaux personnels restent privés.</p>
        {resetEnabled && (!confirm ? <button onClick={() => setConfirm(true)} className="menu-row text-coral"><RotateCcw size={20} /> Réinitialiser la démo</button> : <div className="rounded-2xl bg-sand p-4"><p className="text-sm">Restaurer les sept jours de la famille de démonstration ? Les nouvelles notes de Marie seront supprimées.</p><div className="mt-4 flex gap-2"><button onClick={() => setConfirm(false)} className="button-secondary flex-1">Annuler</button><button onClick={reset} disabled={busy} className="button-primary flex-1">{busy ? "Restauration…" : "Confirmer"}</button></div></div>)}
      </div>}
      {error && <p role="alert" className="error-box">{error}</p>}
    </section></div>}
  </TechnicalContext.Provider>;
}
