"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ShieldCheck, Send, Check, LockKeyhole } from "lucide-react";
import { api, type Message, type MessageGeneration } from "@/lib/api";
import { humanError, roleLabels } from "@/lib/demo";
import { TechnicalCard } from "@/components/technical-card";

export default function SharePage() {
  const { id } = useParams<{ id: string }>();
  const [messages, setMessages] = useState<Message[]>([]); const [edits, setEdits] = useState<Record<string, string>>({});
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false); const [loading, setLoading] = useState(true);
  const request = useRef<{ id: string; promise: Promise<MessageGeneration> } | null>(null);
  useEffect(() => {
    let active = true;
    if (request.current?.id !== id) request.current = { id, promise: api<MessageGeneration>(`/journal/${id}/messages`).then((saved) => saved.drafts.length ? saved : api<MessageGeneration>(`/journal/${id}/messages/generate`, { method: "POST" })) };
    request.current.promise.then((response) => { if (active) setMessages(response.drafts); }).catch((err) => { if (active) setError(humanError(err)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);
  async function approve(message: Message, approved: boolean) {
    if (busy) return; setBusy(true); setError("");
    try {
      const updated = await api<Message>(`/messages/${message.id}`, { method: "PATCH", body: JSON.stringify({ edited_text: edits[message.id] ?? message.text, approved }) });
      setMessages((items) => items.map((item) => item.id === updated.id ? { ...item, ...updated, privacy_pipeline: item.privacy_pipeline } : item));
      setEdits((values) => { const next = { ...values }; delete next[message.id]; return next; });
    } catch (err) { setError(humanError(err)); } finally { setBusy(false); }
  }
  async function send() {
    if (busy) return; setBusy(true); setError("");
    try { const response = await api<MessageGeneration>(`/journal/${id}/messages/send`, { method: "POST" }); setMessages((old) => response.drafts.map((item) => ({ ...old.find((previous) => previous.id === item.id), ...item, privacy_pipeline: old.find((previous) => previous.id === item.id)?.privacy_pipeline }))); }
    catch (err) { setError(humanError(err)); } finally { setBusy(false); }
  }
  return <main className="page-shell"><Link href={`/journal/${id}/review`} className="inline-flex items-center gap-2 text-sm font-semibold text-teal"><ArrowLeft size={16} /> Relecture</Link><p className="eyebrow mt-8">Les bonnes informations, aux bonnes personnes</p><h1 className="page-title !mt-3">Préparer le partage</h1>
    <p className="mt-5 flex items-start gap-3 rounded-2xl bg-teal/5 p-4 text-sm leading-relaxed text-navy-soft"><ShieldCheck className="shrink-0 text-teal" size={23} /> Les informations privées ont été exclues avant la génération de ces messages.</p>
    {error && <p role="alert" className="error-box">{error}</p>}{loading && <p className="mt-6 text-sm text-navy-soft">Vos transmissions se préparent…</p>}
    <div className="mt-6 grid gap-5">{messages.map((message) => {
      const dirty = edits[message.id] !== undefined; const pipeline = message.privacy_pipeline;
      return <article key={message.id} className="card"><div className="flex items-center gap-3"><span className="avatar">{message.recipient_name[0]}</span><div className="flex-1"><h2 className="text-lg font-bold">{message.recipient_name}</h2><p className="text-xs text-navy-soft">{roleLabels[message.recipient_role] ?? message.recipient_role}</p></div><span className={`badge ${message.delivery_status === "sent" ? "badge-teal" : ""}`}>{message.delivery_status === "sent" ? "Envoyé" : message.approved && !dirty ? "Approuvé" : "Brouillon"}</span></div>
        <p className="mt-4 text-xs leading-relaxed text-navy-soft">{message.recipient_role === "family_caregiver" ? "Pour suivre le repas de Marie et préparer sa visite." : message.recipient_role === "auxiliary" ? "Pour organiser l’accompagnement au quotidien." : "Pour coordonner les informations utiles à son rôle."}</p>
        <p className="mt-2 text-[11px] text-teal">{message.allowed_item_count} informations autorisées · {message.excluded_private_count} éléments privés exclus</p>
        <label htmlFor={`message-${message.id}`} className="sr-only">Message pour {message.recipient_name}</label><textarea id={`message-${message.id}`} className="field mt-4 min-h-36 !bg-ivory text-sm" value={edits[message.id] ?? message.text} disabled={message.delivery_status === "sent" || busy} onChange={(event) => setEdits((values) => ({ ...values, [message.id]: event.target.value }))} />
        {message.provider_metadata?.fallback_used && <span className="badge mt-2">Mode démo</span>}
        {message.delivery_status !== "sent" ? <div className="mt-3 flex flex-wrap items-center gap-2"><label className="flex min-h-12 flex-1 items-center gap-3 text-sm font-semibold"><input type="checkbox" className="h-5 w-5 accent-teal" checked={message.approved && !dirty} disabled={busy} onChange={(event) => approve(message, event.target.checked)} /> Envoyer ce message</label>{dirty && <button onClick={() => approve(message, false)} disabled={busy || !edits[message.id]?.trim()} className="button-secondary !text-xs">Enregistrer le brouillon</button>}</div> : <p className="mt-4 flex items-center gap-2 text-xs text-teal"><Check size={16} /> Disponible dans la boîte de réception démo.</p>}
        <TechnicalCard title="Filtrage avant génération">{pipeline ? <><p className="font-semibold">{pipeline.structured_count} éléments structurés → {pipeline.shareable_count} observations/actions partageables → {pipeline.authorized_count} autorisés pour {message.recipient_name} → {pipeline.transmitted_count} transmis au générateur</p><p className="flex items-center gap-2 font-bold"><LockKeyhole size={14} /> Données privées transmises : {pipeline.private_transmitted_count}</p></> : <p>Compteurs de filtrage indisponibles.</p>}<p>Seul RecipientContext est transmis. Les bracelets de Marie ne font pas partie des observations/actions de cette transmission.</p></TechnicalCard>
      </article>;
    })}</div>
    {!loading && !error && !messages.length && <p className="card mt-5 text-sm">Aucune transmission pertinente pour cette note. Elle reste dans votre journal.</p>}
    {!!messages.length && <button onClick={send} disabled={busy || Object.keys(edits).length > 0 || messages.every((message) => !message.approved || message.delivery_status === "sent")} className="button-primary mt-7 w-full"><Send size={18} /> {busy ? "Préparation…" : "Envoyer les messages approuvés"}</button>}
    <Link href="/timeline" className="button-secondary mt-3">Voir la timeline</Link><p className="mt-4 text-center text-xs text-navy-soft">Vous décidez toujours de ce qui est envoyé.</p>
  </main>;
}
