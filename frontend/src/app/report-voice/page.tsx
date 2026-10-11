"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  extractObservations,
  retryTranscription,
  saveObservations,
  submitVoiceReport,
  type Observation,
  type VoiceReport,
  type VoiceReportFailure,
  type VoiceReportResult,
} from "@/lib/api";

type PageState =
  | { kind: "idle" }
  | { kind: "recording" }
  | { kind: "loading"; message: string }
  | { kind: "done"; report: VoiceReport }
  | { kind: "error"; error: VoiceReportFailure };

type ExtractState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "done"; observations: Observation[] }
  | { kind: "error"; detail: string };

type SaveState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "done"; saved: number }
  | { kind: "error"; detail: string };

// Fixed demo identities for this slice; real subject/caregiver selection comes later.
const DEMO_SUBJECT_ID = "subject-demo-1";
const DEMO_REPORTER_ID = "caregiver-demo-1";

// Recorder formats in order of preference, with the extension the backend expects.
const RECORDER_FORMATS: { mimeType: string; ext: string }[] = [
  { mimeType: "audio/webm", ext: "webm" },
  { mimeType: "audio/ogg", ext: "ogg" },
  { mimeType: "audio/mp4", ext: "m4a" },
];

function extensionFor(mimeType: string): string {
  return RECORDER_FORMATS.find((format) => mimeType.startsWith(format.mimeType))?.ext ?? "webm";
}

function canRecord(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.MediaRecorder !== "undefined" &&
    typeof navigator.mediaDevices?.getUserMedia === "function"
  );
}

/** Minimal voice report page: record or upload a French report, then show its transcript. */
export default function ReportVoicePage() {
  const [state, setState] = useState<PageState>({ kind: "idle" });
  const [extract, setExtract] = useState<ExtractState>({ kind: "idle" });
  const [save, setSave] = useState<SaveState>({ kind: "idle" });
  const [notice, setNotice] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  // Set when the page unmounts so a recording interrupted by navigation is not submitted.
  const cancelledRef = useRef(false);

  // Release the microphone if the page is left while recording, without submitting the clip.
  useEffect(() => {
    // Reset on (re)mount so React Strict Mode's mount/cleanup/mount cycle doesn't leave this stuck.
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
      const recorder = recorderRef.current;
      if (recorder) {
        recorder.onstop = null;
        if (recorder.state !== "inactive") recorder.stop();
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  const busy = state.kind === "loading";

  function show(result: VoiceReportResult) {
    setExtract({ kind: "idle" });
    setSave({ kind: "idle" });
    setState(result.ok ? { kind: "done", report: result.report } : { kind: "error", error: result.error });
  }

  async function analyse(transcript: string) {
    setExtract({ kind: "loading" });
    setSave({ kind: "idle" });
    const result = await extractObservations({
      transcript,
      subject_id: DEMO_SUBJECT_ID,
      reported_by: DEMO_REPORTER_ID,
    });
    setExtract(result.ok ? { kind: "done", observations: result.observations } : { kind: "error", detail: result.detail });
  }

  async function persist(observations: Observation[]) {
    setSave({ kind: "loading" });
    const result = await saveObservations(observations);
    setSave(result.ok ? { kind: "done", saved: result.saved } : { kind: "error", detail: result.detail });
  }

  async function send(file: Blob, filename: string) {
    setNotice(null);
    setState({ kind: "loading", message: "Transcription en cours, merci de patienter…" });
    show(await submitVoiceReport(file, filename));
  }

  async function retry(reportId: string) {
    setState({ kind: "loading", message: "Nouvelle tentative de transcription…" });
    show(await retryTranscription(reportId));
  }

  async function onFileSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem("audio-file") as HTMLInputElement | null;
    const file = input?.files?.[0];
    if (!file) {
      setNotice("Choisissez d'abord un fichier audio.");
      return;
    }
    await send(file, file.name);
  }

  async function startRecording() {
    setNotice(null);
    cancelledRef.current = false;
    if (!canRecord()) {
      setNotice("L'enregistrement n'est pas disponible dans ce navigateur. Choisissez un fichier audio.");
      return;
    }
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setNotice("Accès au micro refusé ou indisponible. Choisissez un fichier audio.");
      return;
    }
    const format = RECORDER_FORMATS.find((f) => MediaRecorder.isTypeSupported(f.mimeType));
    const recorder = format ? new MediaRecorder(stream, { mimeType: format.mimeType }) : new MediaRecorder(stream);
    chunksRef.current = [];
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };
    recorder.onstop = () => {
      stream.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      recorderRef.current = null;
      if (cancelledRef.current) return;
      const mimeType = recorder.mimeType || format?.mimeType || "audio/webm";
      const blob = new Blob(chunksRef.current, { type: mimeType });
      void send(blob, `enregistrement.${extensionFor(mimeType)}`);
    };
    streamRef.current = stream;
    recorderRef.current = recorder;
    recorder.start();
    setState({ kind: "recording" });
  }

  function stopRecording() {
    recorderRef.current?.stop();
  }

  let status = "";
  if (notice) status = notice;
  else if (state.kind === "recording") status = "Enregistrement en cours… Cliquez sur « Arrêter et envoyer ».";
  else if (state.kind === "loading") status = state.message;
  else if (save.kind === "loading") status = "Enregistrement des faits dans la chronologie…";
  else if (save.kind === "done") status = `${save.saved} fait(s) enregistré(s).`;
  else if (save.kind === "error") status = save.detail;
  else if (extract.kind === "loading") status = "Analyse des faits en cours, merci de patienter…";
  else if (extract.kind === "error") status = extract.detail;
  else if (extract.kind === "done")
    status =
      extract.observations.length > 0
        ? `${extract.observations.length} fait(s) extrait(s).`
        : "Aucun fait à signaler dans cette transcription.";
  else if (state.kind === "done")
    status = state.report.source === "cache" ? "Transcription de démonstration reçue." : "Transcription terminée.";
  else if (state.kind === "error") status = state.error.detail;

  return (
    <main>
      <p>
        <Link href="/">Retour à l&apos;accueil</Link>
      </p>
      <h1>Rapport vocal</h1>
      <p>Enregistrez votre rapport du jour ou envoyez un fichier audio (mp3, m4a, wav, ogg, webm…, 25 Mo maximum).</p>

      <section aria-labelledby="record-heading">
        <h2 id="record-heading">Enregistrer</h2>
        {state.kind === "recording" ? (
          <button type="button" onClick={stopRecording}>
            Arrêter et envoyer
          </button>
        ) : (
          <button type="button" onClick={startRecording} disabled={busy}>
            Commencer l&apos;enregistrement
          </button>
        )}
      </section>

      <section aria-labelledby="upload-heading">
        <h2 id="upload-heading">Envoyer un fichier</h2>
        <form onSubmit={onFileSubmit}>
          <label htmlFor="audio-file">Fichier audio</label>{" "}
          <input id="audio-file" name="audio-file" type="file" accept="audio/*" disabled={busy} />{" "}
          <button type="submit" disabled={busy || state.kind === "recording"}>
            Envoyer le fichier
          </button>
        </form>
      </section>

      <p aria-live="polite" role="status" data-state={state.kind}>
        {status}
      </p>

      {state.kind === "error" && state.error.retryable && state.error.report_id && (
        <button type="button" onClick={() => retry(state.error.report_id as string)}>
          Réessayer
        </button>
      )}

      {state.kind === "done" && (
        <section aria-labelledby="transcript-heading">
          <h2 id="transcript-heading">Transcription</h2>
          <blockquote lang="fr">{state.report.transcript || "(aucun texte reconnu)"}</blockquote>
          <button
            type="button"
            onClick={() => analyse(state.report.transcript)}
            disabled={extract.kind === "loading" || !state.report.transcript.trim()}
          >
            Analyser les faits
          </button>
        </section>
      )}

      {extract.kind === "done" && (
        <section aria-labelledby="facts-heading">
          <h2 id="facts-heading">Faits extraits</h2>
          {extract.observations.length > 0 ? (
            <>
              <ul lang="fr">
                {extract.observations.map((obs) => (
                  <li key={obs.id}>
                    [{obs.severity}] {obs.category} — {obs.value}
                  </li>
                ))}
              </ul>
              <button
                type="button"
                onClick={() => persist(extract.observations)}
                disabled={save.kind === "loading" || save.kind === "done"}
              >
                Enregistrer dans la chronologie
              </button>
              {save.kind === "done" && (
                <p lang="fr">
                  <Link href="/timeline">Voir la chronologie</Link>
                </p>
              )}
            </>
          ) : (
            <p lang="fr">Aucun fait à signaler.</p>
          )}
        </section>
      )}
    </main>
  );
}
