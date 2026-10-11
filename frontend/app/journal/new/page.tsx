"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Mic, PenLine, Square, Sparkles, RotateCcw, Check } from "lucide-react";
import { api, uploadAudio, type Journal, type Recipient, type MultimodalContext } from "@/lib/api";
import { DEMO_TEXT, humanError, rememberMetadata } from "@/lib/demo";
import { TechnicalCard } from "@/components/technical-card";

type Transcript = { transcript: string; provider: string; transcription_status: string };
export default function NewJournalPage() {
  const router = useRouter(); const query = useSearchParams();
  const [recipient, setRecipient] = useState<Recipient | null>(null);
  const [mode, setMode] = useState<"text" | "voice">("text");
  const [text, setText] = useState(""); const [transcript, setTranscript] = useState("");
  const [recording, setRecording] = useState(false); const [audio, setAudio] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState(""); const [entryId, setEntryId] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(0); const [status, setStatus] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const [storage, setStorage] = useState<string | null>(null); const [transcription, setTranscription] = useState<Transcript | null>(null); const [multimodal, setMultimodal] = useState<MultimodalContext | null>(null);
  const [textFallback, setTextFallback] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null); const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]); const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => { setMode(query.get("mode") === "voice" ? "voice" : "text"); }, [query]);
  useEffect(() => {
    let active = true;
    api<Recipient[]>("/care-recipients").then((items) => { if (active) setRecipient(items.find((item) => item.first_name === "Marie") ?? null); }).catch((err) => { if (active) setError(humanError(err)); });
    return () => { active = false; if (timer.current) clearInterval(timer.current); if (recorder.current?.state === "recording") recorder.current.stop(); stream.current?.getTracks().forEach((track) => track.stop()); };
  }, []);
  useEffect(() => { if (!audio) { setAudioUrl(""); return; } const url = URL.createObjectURL(audio); setAudioUrl(url); return () => URL.revokeObjectURL(url); }, [audio]);
  async function startRecording() {
    setError("");
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { setError("Le microphone n’est pas disponible. Vous pouvez utiliser l’audio de démonstration ou écrire votre note."); return; }
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"].find((type) => MediaRecorder.isTypeSupported(type));
      const instance = new MediaRecorder(stream.current, mime ? { mimeType: mime } : undefined); chunks.current = [];
      instance.ondataavailable = (event) => { if (event.data.size) chunks.current.push(event.data); };
      instance.onstop = () => { setAudio(new Blob(chunks.current, { type: instance.mimeType || "audio/webm" })); stream.current?.getTracks().forEach((track) => track.stop()); };
      recorder.current = instance; instance.start(); setRecording(true); setSeconds(0);
      timer.current = setInterval(() => setSeconds((value) => value + 1), 1000);
    } catch { stream.current?.getTracks().forEach((track) => track.stop()); setError("L’accès au microphone n’est pas disponible. Utilisez l’audio de démonstration ou écrivez votre note."); }
  }
  function stopRecording() { recorder.current?.stop(); setRecording(false); if (timer.current) clearInterval(timer.current); }
  async function ensureEntry(type: "text" | "voice") {
    if (entryId) return entryId;
    const entry = await api<Journal>("/journal", { method: "POST", body: JSON.stringify({ care_recipient_id: recipient!.id, input_type: type, original_text: type === "text" ? text : "Note vocale" }) });
    setEntryId(entry.id); return entry.id;
  }
  async function enrich(id: string) {
    const context = await api<MultimodalContext>(`/journal/${id}/multimodal/enrich`, { method: "POST" }); setMultimodal(context);
  }
  async function analyze() {
    if (!recipient || busy || !(mode === "text" ? text : transcript).trim()) return;
    setBusy(true); setStatus("Karis prépare votre relecture…"); setError("");
    try {
      const id = await ensureEntry(mode);
      if (mode === "voice") await api(`/journal/${id}`, { method: "PATCH", body: JSON.stringify({ transcript }) });
      if (!multimodal) await enrich(id);
      const analyzed = await api<Journal>(`/journal/${id}/analyze`, { method: "POST" }); rememberMetadata(id, analyzed.provider_metadata);
      router.push(analyzed.clarification_needed ? `/journal/${id}/clarify` : `/journal/${id}/review`);
    } catch (err) { setError(humanError(err)); setStatus(""); } finally { setBusy(false); }
  }
  async function transcribe(demo: boolean) {
    if (!recipient || busy || (!demo && !audio)) return;
    setBusy(true); setError(""); setStatus("Votre audio est en cours de préparation…"); setTextFallback(false);
    try {
      const id = await ensureEntry("voice");
      const uploaded = demo ? await api<{ storage_provider: string }>(`/journal/${id}/audio/demo`, { method: "POST" }) : await uploadAudio<{ storage_provider: string }>(`/journal/${id}/audio`, audio!);
      setStorage(uploaded.storage_provider); setStatus("Transcription en cours…");
      const result = await api<Transcript>(`/journal/${id}/transcribe`, { method: "POST" }); setTranscription(result); setTranscript(result.transcript);
      await enrich(id); setStatus("Votre transcription est prête à relire.");
    } catch (err) { setError(humanError(err)); setStatus(""); } finally { setBusy(false); }
  }
  function demoTextFallback() { setTranscript(DEMO_TEXT); setTextFallback(true); setError(""); setStatus("Note de démonstration · relisez avant de continuer."); }
  function restart() { setAudio(null); setTranscript(""); setEntryId(null); setMultimodal(null); setTranscription(null); setStorage(null); setStatus(""); setError(""); setTextFallback(false); }
  return <main className="page-shell"><Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-semibold text-teal"><ArrowLeft size={16} /> Accueil</Link><p className="eyebrow mt-8">Le journal de Marie</p><h1 className="page-title !mt-3">Raconter la journée</h1><p className="mt-3 text-sm leading-relaxed text-navy-soft">Parlez comme à un proche. Vous pourrez tout relire avant de partager.</p>
    <div className="mt-7 flex gap-2 rounded-2xl bg-sand/60 p-1.5">{([{ value: "voice", label: "Raconter", icon: Mic }, { value: "text", label: "Écrire", icon: PenLine }] as const).map(({ value, label, icon: Icon }) => <button key={value} disabled={busy || recording} aria-pressed={mode === value} onClick={() => { setMode(value); restart(); }} className={`flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl text-sm font-semibold ${mode === value ? "bg-white text-teal shadow-sm" : "text-navy-soft"}`}><Icon size={18} />{label}</button>)}</div>
    {mode === "text" ? <section className="mt-6"><label htmlFor="journal-text" className="sr-only">Votre journée avec Marie</label><textarea id="journal-text" value={text} disabled={busy} onChange={(event) => { setText(event.target.value); setEntryId(null); setMultimodal(null); }} placeholder="Racontez simplement comment s’est passée la journée…" className="field min-h-64 resize-y" /><button disabled={busy} onClick={() => { setText(DEMO_TEXT); setEntryId(null); setMultimodal(null); }} className="mt-3 inline-flex min-h-11 items-center gap-2 text-xs font-semibold text-teal"><Sparkles size={16} /> Utiliser la note de démonstration</button><button onClick={analyze} disabled={!text.trim() || !recipient || busy} className="button-primary mt-5 w-full">{busy ? "Préparation…" : "Comprendre ma journée"}</button></section> : <section className="card mt-6 text-center">
      {!transcript ? <><p className="text-xs text-navy-soft">Un moment pour déposer votre journée</p><button aria-label={recording ? "Arrêter l’enregistrement" : "Commencer l’enregistrement"} disabled={busy} onClick={recording ? stopRecording : startRecording} className={`mx-auto mt-7 flex h-28 w-28 items-center justify-center rounded-full ${recording ? "recording-pulse bg-coral/15 text-coral" : "bg-teal text-white shadow-lg shadow-teal/15"}`}>{recording ? <Square size={30} fill="currentColor" /> : <Mic size={40} strokeWidth={1.6} />}</button><p aria-live="polite" className="mt-6 text-sm font-medium">{recording ? `Enregistrement · ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}` : "Appuyez pour enregistrer"}</p>
        {audioUrl && <><audio controls src={audioUrl} className="mt-5 w-full" /><button disabled={busy} onClick={restart} className="mt-2 inline-flex min-h-11 items-center gap-2 text-xs font-semibold text-navy-soft"><RotateCcw size={14} /> Réenregistrer</button><button onClick={() => transcribe(false)} disabled={busy} className="button-primary mt-3 w-full">Transcrire cet audio</button></>}
        <button disabled={!recipient || busy || recording} onClick={() => transcribe(true)} className="button-secondary mt-7 w-full !text-xs"><Sparkles size={16} /> Utiliser l’audio de démonstration</button>
        {entryId && error && <button onClick={demoTextFallback} className="button-secondary mt-3 w-full !text-xs">Continuer avec la note de démonstration</button>}
      </> : <div className="text-left"><p className="mb-4 flex items-center gap-2 text-sm font-bold text-teal"><Check size={18} /> {textFallback ? "Note de démonstration" : "Votre transcription"}</p><label htmlFor="transcript" className="sr-only">Relire la transcription</label><textarea id="transcript" value={transcript} disabled={busy} onChange={(event) => setTranscript(event.target.value)} className="field min-h-52 !bg-ivory" /><p className="mt-3 text-xs leading-relaxed text-navy-soft">Corrigez un mot si besoin. Votre voix reste votre point de départ.</p><button onClick={analyze} disabled={busy || !transcript.trim()} className="button-primary mt-5 w-full">{busy ? "Préparation…" : "Continuer avec cette note"}</button><button onClick={restart} disabled={busy} className="mt-3 flex min-h-11 w-full items-center justify-center gap-2 text-xs font-semibold text-navy-soft"><RotateCcw size={14} /> Réenregistrer</button></div>}
    </section>}
    {error && <p role="alert" className="error-box">{error}{entryId && <Link href={`/journal/${entryId}/review`} className="mt-2 block font-semibold underline">Retrouver ma note enregistrée</Link>}</p>}{status && <p role="status" className="mt-4 text-center text-xs text-navy-soft">{status}</p>}
    {mode === "voice" && (storage || textFallback) && <TechnicalCard title="Pipeline de transcription"><p>{storage ? "✓ Audio stocké" : "Audio non stocké"} · {transcription ? "✓ Transcription" : "Transcription indisponible"}</p><p>{multimodal?.caregiver_vocal_affect ? "✓ SER" : "SER facultatif"} · {multimodal ? "✓ Contexte multimodal" : "Contexte en attente"}</p><dl className="metadata-grid"><dt>Stockage</dt><dd>{storage ?? "Indisponible"}</dd><dt>Transcription</dt><dd>{transcription?.provider ?? "Non utilisée"}</dd><dt>Statut</dt><dd>{transcription?.transcription_status ?? "Échec / non exécutée"}</dd><dt>provider_used</dt><dd>{textFallback ? "demo-text-fallback" : transcription?.provider ?? "En attente"}</dd><dt>Repli</dt><dd>{textFallback ? "Oui · note de démonstration choisie" : "Non"}</dd></dl></TechnicalCard>}
  </main>;
}
