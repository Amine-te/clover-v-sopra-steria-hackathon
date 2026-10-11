"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  AudioLines,
  Check,
  CircleAlert,
  Lock,
  Mic,
  MicOff,
  NotebookPen,
  Pause,
  Play,
  RotateCcw,
  Send,
  Square,
  X,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Sheet } from "@/components/Sheet";
import { AudioPlayer } from "@/components/recorder/AudioPlayer";
import { MAX_RECORDING_S, useRecorder } from "@/components/recorder/useRecorder";
import { Button, Card, DemoNote, LinkButton } from "@/components/ui";
import { formatDuration } from "@/lib/format";
import { SUBJECT } from "@/mocks/people";
import { SCENARIOS } from "@/mocks/scenarios";
import { karis, mockControls, TranscriptionError, type PipelineStep } from "@/services";
import { setDeviceRecording } from "@/state/recording";
import { useStore } from "@/state/store";

const STEPS: { id: PipelineStep; label: string; note: string }[] = [
  { id: "upload", label: "Préparation de l'enregistrement", note: "Reste sur l'appareil en démonstration" },
  { id: "transcribe", label: "Transcription en français", note: "Exemple préenregistré utilisé" },
  { id: "extract", label: "Repérage des faits", note: "Résultat d'exemple, sans IA" },
  { id: "gaps", label: "Repères du jour manquants", note: "Trois questions au plus" },
  { id: "guardrail", label: "Vérification : aucun diagnostic", note: "Les interprétations sont écartées" },
];

type Phase = "record" | "processing" | "failed";

export default function RecordPage() {
  const router = useRouter();
  const { state, dispatch } = useStore();
  const rec = useRecorder();
  const [phase, setPhase] = useState<Phase>("record");
  const [step, setStep] = useState<PipelineStep | null>(null);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [confirmDiscardDraft, setConfirmDiscardDraft] = useState(false);
  const [usingDemo, setUsingDemo] = useState(false);
  const statusRef = useRef<HTMLParagraphElement>(null);

  const pendingDraft = state.draft && state.draft.stage !== "confirmed" ? state.draft : null;
  const scenario = SCENARIOS[state.scenarioIndex % SCENARIOS.length];
  const live = rec.status === "recording" || rec.status === "paused";

  useEffect(() => {
    if (phase === "processing" || phase === "failed") statusRef.current?.focus();
  }, [phase]);

  const analyze = async (demo: boolean) => {
    setUsingDemo(demo);
    setPhase("processing");
    mockControls.scenarioIndex = state.scenarioIndex;
    mockControls.failTranscription = state.settings.simulateTranscribeFailure;
    if (state.settings.simulateTranscribeFailure) dispatch({ type: "settings", patch: { simulateTranscribeFailure: false } });
    try {
      if (!demo && rec.result) setDeviceRecording(rec.result);
      if (demo) setDeviceRecording(null);
      const draft = await karis.analyzeReport(
        { audio: demo ? undefined : rec.result?.blob, durationS: demo ? 0 : rec.result?.durationS ?? 0, reportedAt: new Date() },
        setStep,
      );
      dispatch({ type: "setDraft", draft });
      router.push("/analyse/");
    } catch (e) {
      // TranscriptionError (001-AC3) or any other failure: same calm retry screen.
      if (!(e instanceof TranscriptionError)) console.error(e);
      setPhase("failed");
    }
  };

  // ----- Processing ---------------------------------------------------------
  if (phase === "processing" || phase === "failed") {
    const currentIndex = step ? STEPS.findIndex((s) => s.id === step) : 0;
    return (
      <>
        <PageHeader title={phase === "failed" ? "La transcription n'a pas abouti" : "Karis prépare votre compte rendu"} eyebrow="Journal vocal" />
        <p ref={statusRef} tabIndex={-1} className="page-subtitle" role="status" style={{ marginTop: -10, marginBottom: 18 }}>
          {phase === "failed"
            ? "Rien n'est perdu : votre enregistrement est conservé sur l'appareil. Vous pouvez réessayer."
            : "Quelques secondes. Vous pourrez tout relire avant que quoi que ce soit ne soit enregistré."}
        </p>
        <Card>
          <ol className="steps" aria-label="Étapes de préparation">
            {STEPS.map((s, i) => {
              const failedHere = phase === "failed" && s.id === "transcribe";
              const done = phase === "processing" ? i < currentIndex : i < 1;
              const current = phase === "processing" && i === currentIndex;
              return (
                <li key={s.id} className={done ? "is-done" : current ? "is-current" : ""} aria-current={current ? "step" : undefined}>
                  <span className="step-mark" aria-hidden style={failedHere ? { background: "var(--terracotta-pale)", color: "var(--terracotta-ink)" } : undefined}>
                    {failedHere ? <CircleAlert size={16} /> : done ? <Check size={15} strokeWidth={2.2} /> : current ? <span className="spinner" style={{ width: 13, height: 13 }} /> : i + 1}
                  </span>
                  <span>
                    {s.label}
                    <span className="step-note">{failedHere ? "Service indisponible pour le moment" : s.note}</span>
                  </span>
                </li>
              );
            })}
          </ol>
        </Card>
        {phase === "failed" ? (
          <div className="stack" style={{ marginTop: 18 }}>
            <Button block icon={RotateCcw} onClick={() => analyze(usingDemo)}>
              Réessayer
            </Button>
            <Button block variant="secondary" onClick={() => setPhase("record")}>
              Revenir à l&apos;enregistrement
            </Button>
          </div>
        ) : null}
        <div style={{ marginTop: 16 }}>
          <DemoNote>
            Mode démonstration : aucune analyse réelle n&apos;est effectuée. Le texte et les faits affichés ensuite proviennent d&apos;un exemple préparé à l&apos;avance.
          </DemoNote>
        </div>
      </>
    );
  }

  // ----- Pending draft --------------------------------------------------------
  if (pendingDraft && !live && rec.status !== "stopped") {
    return (
      <>
        <PageHeader title="Un compte rendu vous attend" eyebrow="Journal vocal" subtitle="Vous aviez commencé à le vérifier. Rien n'a encore été enregistré ni partagé." />
        <Card>
          <div className="card-title">
            <span className="soft-icon" aria-hidden>
              <NotebookPen size={20} strokeWidth={1.75} />
            </span>
            <div>
              <h2>{pendingDraft.observations.length} faits à relire</h2>
              <p className="row-sub">Préparé à partir de votre message vocal</p>
            </div>
          </div>
          <div className="stack" style={{ marginTop: 14 }}>
            <LinkButton href="/analyse/" block>
              Reprendre la vérification
            </LinkButton>
            <Button block variant="danger" onClick={() => setConfirmDiscardDraft(true)}>
              Abandonner et enregistrer à nouveau
            </Button>
          </div>
        </Card>
        <Sheet
          open={confirmDiscardDraft}
          onClose={() => setConfirmDiscardDraft(false)}
          tone="alert"
          title="Abandonner ce compte rendu ?"
          description="Les faits relevés et vos réponses seront effacés. Rien n'a été transmis."
          footer={
            <>
              <Button variant="ghost" onClick={() => setConfirmDiscardDraft(false)}>
                Garder
              </Button>
              <Button
                variant="danger"
                onClick={() => {
                  dispatch({ type: "setDraft", draft: null });
                  setDeviceRecording(null);
                  setConfirmDiscardDraft(false);
                }}
              >
                Abandonner
              </Button>
            </>
          }
        />
      </>
    );
  }

  // ----- Permission problems ----------------------------------------------------
  if (rec.status === "denied" || rec.status === "unsupported" || rec.status === "error") {
    const denied = rec.status === "denied";
    return (
      <>
        <PageHeader title={denied ? "Le micro n'est pas autorisé" : "Le micro n'est pas disponible"} eyebrow="Journal vocal" back={{ href: "/", label: "Accueil" }} />
        <Card className="permission">
          <div className="card-title">
            <span className="soft-icon terra" aria-hidden>
              <MicOff size={20} strokeWidth={1.75} />
            </span>
            <h2>{denied ? "Karis a besoin du micro pour vous écouter" : "Votre navigateur ne permet pas l'enregistrement"}</h2>
          </div>
          <p className="lead">
            {denied
              ? "Pour l'activer, ouvrez les réglages du site dans votre navigateur (icône à gauche de l'adresse), autorisez le micro, puis réessayez."
              : "L'enregistrement nécessite un navigateur récent et une connexion sécurisée (https ou localhost)."}
          </p>
          <div className="stack" style={{ marginTop: 16 }}>
            {denied || rec.status === "error" ? (
              <Button block icon={RotateCcw} onClick={() => rec.start()}>
                Réessayer
              </Button>
            ) : null}
            <Button block variant="secondary" icon={AudioLines} onClick={() => analyze(true)}>
              Continuer avec l&apos;exemple de démonstration
            </Button>
          </div>
        </Card>
        <div style={{ marginTop: 14 }}>
          <DemoNote>L&apos;exemple de démonstration utilise un compte rendu fictif préparé à l&apos;avance.</DemoNote>
        </div>
      </>
    );
  }

  // ----- Review the recording -------------------------------------------------------
  if (rec.status === "stopped" && rec.result) {
    return (
      <>
        <PageHeader title="Votre message est prêt" eyebrow="Journal vocal" subtitle="Réécoutez-le si vous le souhaitez, puis envoyez-le pour en extraire les faits." />
        <Card>
          <div className="card-title">
            <span className="soft-icon" aria-hidden>
              <AudioLines size={20} strokeWidth={1.75} />
            </span>
            <div>
              <h2>Message vocal · {formatDuration(rec.result.durationS)}</h2>
              <p className="row-sub">Enregistré sur cet appareil</p>
            </div>
          </div>
          <AudioPlayer src={rec.result.url} fallbackDuration={rec.result.durationS} />
        </Card>
        <div className="stack" style={{ marginTop: 18 }}>
          <Button block icon={Send} onClick={() => analyze(false)}>
            Envoyer pour analyse
          </Button>
          <Button
            block
            variant="secondary"
            icon={RotateCcw}
            onClick={() => {
              rec.cancel();
            }}
          >
            Recommencer
          </Button>
        </div>
        <div style={{ marginTop: 16 }}>
          <DemoNote>
            En démonstration, votre enregistrement ne quitte pas l&apos;appareil : il n&apos;est pas transcrit. Un exemple de transcription sera utilisé.
          </DemoNote>
        </div>
      </>
    );
  }

  // ----- Idle / recording -------------------------------------------------------------
  const remaining = MAX_RECORDING_S - rec.elapsed;
  return (
    <>
      <PageHeader
        title={live ? (rec.status === "paused" ? "En pause" : "Je vous écoute") : "Racontez la journée"}
        eyebrow="Journal vocal"
        back={live ? undefined : { href: "/", label: "Accueil" }}
        subtitle={live ? undefined : `Parlez naturellement de ${SUBJECT.firstName}. Karis retient les faits ; le reste vous appartient.`}
      />

      <div className={`recorder ${rec.status === "recording" ? "is-recording" : ""}`}>
        <p className="rec-status" aria-live="polite">
          {rec.status === "recording" ? (
            <>
              <span className="rec-dot" aria-hidden /> Enregistrement en cours
            </>
          ) : rec.status === "paused" ? (
            "Enregistrement en pause"
          ) : rec.status === "requesting" ? (
            "Autorisez l'accès au micro dans la fenêtre du navigateur…"
          ) : (
            <>
              <Lock size={14} strokeWidth={2} aria-hidden /> Votre voix reste privée
            </>
          )}
        </p>
        <p className="rec-timer" aria-label={`Durée : ${formatDuration(rec.elapsed)}`}>
          {formatDuration(rec.elapsed)}
        </p>
        <p className="rec-limit">{live && remaining <= 30 ? `Encore ${Math.ceil(remaining)} secondes` : "3 minutes au plus"}</p>

        <div className={`wave ${rec.status === "recording" ? "" : "is-idle"}`} aria-hidden>
          {rec.levels.map((l, i) => (
            <span key={i} style={{ height: `${Math.round(l * 64)}px` }} />
          ))}
        </div>

        {live ? (
          <div className="rec-controls">
            <button type="button" className="rec-side" onClick={() => (rec.elapsed > 3 ? setConfirmCancel(true) : rec.cancel())}>
              <span className="icon-btn" aria-hidden>
                <X size={22} strokeWidth={1.75} />
              </span>
              Annuler
            </button>
            <button type="button" className={`rec-button ${rec.status === "recording" ? "is-live" : ""}`} onClick={rec.stop} aria-label="Terminer l'enregistrement">
              <Square size={30} strokeWidth={1.75} fill="currentColor" aria-hidden />
            </button>
            <button type="button" className="rec-side" onClick={rec.status === "paused" ? rec.resume : rec.pause}>
              <span className="icon-btn" aria-hidden>
                {rec.status === "paused" ? <Play size={22} strokeWidth={1.75} /> : <Pause size={22} strokeWidth={1.75} />}
              </span>
              {rec.status === "paused" ? "Reprendre" : "Pause"}
            </button>
          </div>
        ) : (
          <button
            type="button"
            className="rec-button"
            onClick={() => rec.start()}
            disabled={rec.status === "requesting"}
            aria-label="Commencer l'enregistrement"
          >
            {rec.status === "requesting" ? <span className="spinner" style={{ width: 28, height: 28 }} /> : <Mic size={38} strokeWidth={1.6} aria-hidden />}
          </button>
        )}

        <p className="rec-hint">
          {live ? "Appuyez sur le carré pour terminer. Vous pourrez réécouter avant d'envoyer." : "Appuyez pour commencer. Vous pourrez réécouter, recommencer ou annuler."}
        </p>
      </div>

      <>
          {!live ? (
            <p className="rec-topics">
              Sa nuit, ses repas, son traitement, son humeur, une chute, un rendez-vous… ce qui vous vient.
            </p>
          ) : null}

          {/* Demo script, visible while recording too: what is read aloud matches the example shown afterwards. */}
          <section className="script-card" aria-labelledby="script-title">
            <div className="script-head">
              <span className="demo-badge">
                <span className="demo-dot" aria-hidden />
                Démonstration
              </span>
              <h2 id="script-title">Texte à lire à voix haute</h2>
            </div>
            <p className="script-sub">
              L&apos;enregistrement n&apos;est pas transcrit dans cette démonstration : Karis affichera cet exemple, « {scenario.title.toLowerCase()} ».
            </p>
            <blockquote className="script-text">{scenario.transcript}</blockquote>
            {!live ? (
              <div className="script-actions">
                <Button variant="ghost" size="sm" icon={RotateCcw} onClick={() => dispatch({ type: "setScenario", index: (state.scenarioIndex + 1) % SCENARIOS.length })}>
                  Autre exemple
                </Button>
                <Button variant="ghost" size="sm" icon={AudioLines} onClick={() => analyze(true)}>
                  Continuer sans micro
                </Button>
              </div>
            ) : null}
          </section>
          {!live ? (
            <p className="footer-note" style={{ marginTop: 12 }}>
              <Link href="/parametres/#demonstration" className="text-link" style={{ minHeight: 0, display: "inline" }}>
                Options de démonstration
              </Link>
            </p>
          ) : null}
      </>

      <Sheet
        open={confirmCancel}
        onClose={() => setConfirmCancel(false)}
        tone="alert"
        title="Supprimer cet enregistrement ?"
        description="Ce que vous venez de dire sera effacé de l'appareil. Rien n'a été envoyé."
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmCancel(false)}>
              Continuer
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                rec.cancel();
                setConfirmCancel(false);
              }}
            >
              Supprimer
            </Button>
          </>
        }
      />
    </>
  );
}
