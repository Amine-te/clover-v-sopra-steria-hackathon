"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import {
  ArrowRight,
  AudioLines,
  CalendarRange,
  Check,
  ChevronDown,
  CircleCheck,
  EyeOff,
  HeartHandshake,
  Inbox,
  MessagesSquare,
  Mic,
  Pencil,
  RotateCcw,
  ShieldCheck,
  TriangleAlert,
  Undo2,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Sheet } from "@/components/Sheet";
import { TranscriptView } from "@/components/TranscriptView";
import { CategoryIcon, DraftObservationCard, ObservationEditor } from "@/components/observations";
import { AudioPlayer } from "@/components/recorder/AudioPlayer";
import { Badge, Button, Card, Chip, DemoNote, EmptyState, LinkButton, SectionHeader } from "@/components/ui";
import { CATEGORY_SHORT, RECIPIENT_LABEL } from "@/lib/labels";
import { formatDuration, formatTime, plural } from "@/lib/format";
import { previewRouting } from "@/lib/routing";
import type { FollowUpQuestion, Observation, ReportDraft } from "@/lib/types";
import { CONTACTS, SUBJECT } from "@/mocks/people";
import { karis } from "@/services";
import { getDeviceRecording, setDeviceRecording } from "@/state/recording";
import { useStore } from "@/state/store";

export default function AnalysePage() {
  const { state } = useStore();
  const draft = state.draft;

  if (!draft) {
    return (
      <>
        <PageHeader title="Analyse et vérification" eyebrow="Compte rendu" back={{ href: "/", label: "Accueil" }} />
        <EmptyState
          icon={Inbox}
          title="Aucun compte rendu à vérifier"
          action={
            <LinkButton href="/enregistrer/" icon={Mic}>
              Raconter la journée
            </LinkButton>
          }
        >
          Après un message vocal, vous retrouverez ici les faits relevés, à relire avant tout enregistrement.
        </EmptyState>
      </>
    );
  }

  if (draft.stage === "confirmed") return <Confirmed draft={draft} />;
  if (draft.stage === "followups") return <FollowUps draft={draft} />;
  return <Review draft={draft} />;
}

/** Always visible: these results come from a prepared example, not from AI. */
function DemoBadge() {
  return (
    <span className="demo-badge" title="Résultats issus d'un exemple préparé, sans analyse par IA">
      <span className="demo-dot" aria-hidden />
      Exemple de démonstration
    </span>
  );
}

function Stepper({ step }: { step: 1 | 2 }) {
  return (
    <div className="stepper" role="img" aria-label={`Étape ${step} sur 2`}>
      <span className="is-on" />
      <span className={step === 2 ? "is-on" : ""} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 1: completeness follow-ups (feature 003, at most 3; 2 in light mode)
// ---------------------------------------------------------------------------

function FollowUps({ draft }: { draft: ReportDraft }) {
  const { state, dispatch } = useStore();
  const light = state.settings.lightMode;
  const questions = draft.followups.slice(0, light ? 2 : 3);
  const [busy, setBusy] = useState(false);
  const answeredCount = questions.filter((q) => draft.answers[q.id]?.status === "answered").length;

  const proceed = async (skipAll: boolean) => {
    setBusy(true);
    const answers = { ...draft.answers };
    for (const q of draft.followups) {
      if (skipAll || !answers[q.id] || !questions.includes(q)) answers[q.id] = { status: "skipped" };
    }
    const updated = { ...draft, answers };
    const extra = await karis.extractFollowUpAnswers(updated);
    dispatch({ type: "patchDraft", patch: { answers, observations: [...draft.observations, ...extra], stage: "review" } });
    setBusy(false);
    window.scrollTo({ top: 0 });
  };

  return (
    <>
      <PageHeader
        title={questions.length > 1 ? `${questions.length === 2 ? "Deux" : "Trois"} précisions, si vous voulez bien` : "Une précision, si vous voulez bien"}
        eyebrow="Compte rendu · étape 1 sur 2"
        back={{ href: "/", label: "Accueil" }}
        action={<DemoBadge />}
        subtitle="Ces repères du jour n'ont pas été mentionnés. Répondez d'un geste ou passez : le compte rendu sera complet quand même."
      />
      <Stepper step={1} />
      {questions.map((q, i) => (
        <QuestionCard key={q.id} q={q} index={i} total={questions.length} draft={draft} light={light} />
      ))}
      <div className="secondary-action">
        <Button variant="ghost" size="sm" onClick={() => proceed(true)} disabled={busy}>
          Passer toutes les questions
        </Button>
      </div>
      <div className="sticky-actions">
        <Button block onClick={() => proceed(false)} disabled={busy} icon={busy ? undefined : ArrowRight}>
          {busy ? "Un instant…" : answeredCount ? "Continuer" : "Continuer sans répondre"}
        </Button>
      </div>
    </>
  );
}

function QuestionCard({ q, index, total, draft, light }: { q: FollowUpQuestion; index: number; total: number; draft: ReportDraft; light: boolean }) {
  const { dispatch } = useStore();
  const answer = draft.answers[q.id];
  const [writing, setWriting] = useState(false);
  const [text, setText] = useState("");
  const headingId = `q-${q.id}`;

  if (answer) {
    const label = answer.status === "skipped" ? "Question passée" : answer.text ? `« ${answer.text} »` : answer.option?.label;
    return (
      <section className="card question" aria-labelledby={headingId}>
        <div className="question-head">
          <CategoryIcon category={q.category} />
          <div>
            <p className="question-count">
              {CATEGORY_SHORT[q.category]} · {index + 1}/{total}
            </p>
            <h3 id={headingId}>{q.prompt}</h3>
          </div>
        </div>
        <div className="question-done" role="status">
          {answer.status === "answered" ? <Check size={17} strokeWidth={2} aria-hidden /> : null}
          <span>{label}</span>
          <Button variant="ghost" size="sm" icon={Pencil} onClick={() => dispatch({ type: "answer", questionId: q.id, answer: null })}>
            Modifier
          </Button>
        </div>
      </section>
    );
  }

  return (
    <section className="card question" aria-labelledby={headingId}>
      <div className="question-head">
        <CategoryIcon category={q.category} />
        <div>
          <p className="question-count">
            {CATEGORY_SHORT[q.category]} · {index + 1}/{total}
          </p>
          <h3 id={headingId}>{q.prompt}</h3>
        </div>
      </div>
      <div className="chip-row" role="group" aria-labelledby={headingId}>
        {q.options.map((o) => (
          <Chip key={o.label} onClick={() => dispatch({ type: "answer", questionId: q.id, answer: { status: "answered", option: o } })}>
            {o.label}
          </Chip>
        ))}
      </div>
      {writing && !light ? (
        <form
          className="form"
          style={{ marginTop: 14 }}
          onSubmit={(e) => {
            e.preventDefault();
            if (text.trim()) dispatch({ type: "answer", questionId: q.id, answer: { status: "answered", text: text.trim() } });
          }}
        >
          <div className="field">
            <label htmlFor={`txt-${q.id}`}>Votre réponse</label>
            <textarea id={`txt-${q.id}`} rows={2} value={text} onChange={(e) => setText(e.target.value)} placeholder="Quelques mots suffisent" autoFocus />
          </div>
          <div className="sheet-actions" style={{ marginTop: 10 }}>
            <Button variant="ghost" size="sm" onClick={() => setWriting(false)}>
              Annuler
            </Button>
            <Button type="submit" size="sm" disabled={!text.trim()}>
              Valider
            </Button>
          </div>
        </form>
      ) : (
        <div style={{ display: "flex", gap: 4, marginTop: 10, flexWrap: "wrap" }}>
          {!light ? (
            <Button variant="ghost" size="sm" icon={Pencil} onClick={() => setWriting(true)}>
              Répondre autrement
            </Button>
          ) : null}
          <Button variant="ghost" size="sm" onClick={() => dispatch({ type: "answer", questionId: q.id, answer: { status: "skipped" } })}>
            Passer
          </Button>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Step 2: review facts, private passages, guardrail notes, routing preview
// ---------------------------------------------------------------------------

function Review({ draft }: { draft: ReportDraft }) {
  const router = useRouter();
  const { dispatch, toast } = useStore();
  const [editing, setEditing] = useState<Observation | null>(null);
  const [removed, setRemoved] = useState<{ o: Observation; index: number } | null>(null);
  const [showTranscript, setShowTranscript] = useState(false);
  const [showRouting, setShowRouting] = useState(false);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const [busy, setBusy] = useState(false);
  const recording = getDeviceRecording();

  const facts = useMemo(() => [...draft.observations].sort((a, b) => a.timestamp.localeCompare(b.timestamp)), [draft.observations]);
  const routing = useMemo(() => previewRouting(facts), [facts]);
  const hasUrgent = facts.some((o) => o.severity === "urgent");
  const informed = routing.filter((r) => r.recipient !== "caregiver" && r.excluded.length < facts.length);
  const immediateCount = informed.filter((r) => r.immediate.length > 0).length;
  const routingSummary = informed.length
    ? `${plural(informed.length, "personne informée", "personnes informées")}${immediateCount ? `, dont ${immediateCount} immédiatement` : ""}`
    : "Personne d'autre que vous";

  const remove = (o: Observation) => {
    setRemoved({ o, index: draft.observations.findIndex((x) => x.id === o.id) });
    dispatch({ type: "removeDraftObservation", id: o.id });
  };

  const undo = () => {
    if (!removed) return;
    const list = [...draft.observations];
    list.splice(removed.index, 0, removed.o);
    dispatch({ type: "patchDraft", patch: { observations: list } });
    setRemoved(null);
  };

  const confirm = async () => {
    setBusy(true);
    const { stored, messages } = await karis.confirmReport(facts);
    dispatch({ type: "confirmed", stored, messages });
    setBusy(false);
    window.scrollTo({ top: 0 });
  };

  return (
    <>
      <PageHeader
        title="Vérifiez avant d'enregistrer"
        eyebrow="Compte rendu · étape 2 sur 2"
        back={{ href: "/", label: "Accueil" }}
        action={<DemoBadge />}
        subtitle="Corrigez ou retirez ce qui ne convient pas. Rien n'est enregistré ni partagé sans votre accord."
      />
      <Stepper step={2} />

      {hasUrgent ? (
        <div className="urgent-banner" role="alert">
          <TriangleAlert size={20} strokeWidth={1.75} aria-hidden style={{ flexShrink: 0, marginTop: 2 }} />
          <span>
            Un fait est marqué urgent : l&apos;auxiliaire et la famille seront prévenus immédiatement. En cas d&apos;urgence vitale, appelez le <a href="tel:15">15</a>.
          </span>
        </div>
      ) : null}

      {/* The "words → facts" moment comes first: highlighted transcript, then the facts. */}
      <section className="card words-card" aria-labelledby="transcript-title">
        <div className="words-head">
          <AudioLines size={18} strokeWidth={1.75} aria-hidden />
          <h2 id="transcript-title">Vos mots</h2>
          <span className="row-sub">· {formatDuration(draft.audio_duration_s)}</span>
        </div>
        <div className={`clamp ${showTranscript ? "is-open" : ""}`} id="transcript-panel">
          <TranscriptView
            text={draft.transcript}
            facts={draft.observations.map((o) => o.transcript_span)}
            privates={draft.private_passages}
            guarded={draft.guardrail_notes.map((g) => g.original)}
          />
        </div>
        <button type="button" className="text-link clamp-toggle" aria-expanded={showTranscript} aria-controls="transcript-panel" onClick={() => setShowTranscript((v) => !v)}>
          {showTranscript ? "Réduire" : "Lire tout"}
        </button>
        {recording && draft.has_device_audio ? <AudioPlayer src={recording.url} fallbackDuration={recording.durationS} /> : null}
        <p className="words-note">
          <span className="demo-dot" aria-hidden />
          {draft.has_device_audio
            ? "Démonstration : votre enregistrement n'est pas transcrit, ce texte d'exemple le remplace."
            : "Démonstration : compte rendu fictif préparé à l'avance, sans analyse par IA."}
        </p>
      </section>

      <SectionHeader title="Les faits relevés" id="facts-title" action={<Badge tone="sage">{plural(facts.length, "fait", "faits")}</Badge>} />
      {removed ? (
        <div className="light-banner" role="status">
          Fait retiré : {CATEGORY_SHORT[removed.o.category].toLowerCase()}.
          <button type="button" onClick={undo}>
            <Undo2 size={15} strokeWidth={2} aria-hidden style={{ verticalAlign: "-2px", marginRight: 4 }} />
            Annuler
          </button>
        </div>
      ) : null}
      {facts.length ? (
        <ul className="facts" aria-labelledby="facts-title">
          {facts.map((o) => (
            <DraftObservationCard key={o.id} o={o} onEdit={() => setEditing(o)} onRemove={() => remove(o)} />
          ))}
        </ul>
      ) : (
        <EmptyState icon={Inbox} title="Aucun fait à enregistrer">
          Vous avez retiré tous les faits. Vous pouvez annuler le dernier retrait ou abandonner ce compte rendu.
        </EmptyState>
      )}

      {draft.private_passages.length ? (
        <section className="card private-card" aria-labelledby="private-title" style={{ marginTop: 14 }}>
          <div className="card-title">
            <span className="soft-icon terra" aria-hidden>
              <EyeOff size={20} strokeWidth={1.75} />
            </span>
            <h3 id="private-title">Gardé pour vous</h3>
          </div>
          <p style={{ fontSize: 14.5 }}>Ces mots parlent de vous. Ils ne sont ni ajoutés à la frise, ni transmis à personne.</p>
          {draft.private_passages.map((p) => (
            <blockquote key={p}>« {p} »</blockquote>
          ))}
          <Link href="/bien-etre/" className="text-link" style={{ marginTop: 6 }}>
            <HeartHandshake size={16} strokeWidth={1.75} aria-hidden style={{ marginRight: 6 }} />
            Prendre un instant pour vous
          </Link>
        </section>
      ) : null}

      {draft.guardrail_notes.length ? (
        <section className="card guard-card" aria-labelledby="guard-title">
          <div className="card-title">
            <span className="soft-icon" aria-hidden>
              <ShieldCheck size={20} strokeWidth={1.75} />
            </span>
            <h3 id="guard-title">Formulation non retenue</h3>
          </div>
          {draft.guardrail_notes.map((g) => (
            <div key={g.original}>
              <p className="fact-span" style={{ marginTop: 0 }}>
                <span>« {g.original} »</span>
              </p>
              <p style={{ fontSize: 14, marginTop: 6 }}>{g.reason}</p>
            </div>
          ))}
        </section>
      ) : null}

      <section className="card" aria-labelledby="routing-title" style={{ marginTop: 14 }}>
        <button type="button" className="disclosure" aria-expanded={showRouting} aria-controls="routing-panel" onClick={() => setShowRouting((v) => !v)}>
          <MessagesSquare size={18} strokeWidth={1.75} aria-hidden />
          <span>
            <span id="routing-title" style={{ display: "block" }}>
              Qui sera informé
            </span>
            <span className="row-sub" style={{ display: "block", fontWeight: 500 }}>
              {routingSummary}
            </span>
          </span>
          <ChevronDown size={18} className={`chev ${showRouting ? "is-open" : ""}`} style={{ marginLeft: "auto" }} aria-hidden />
        </button>
        {showRouting ? (
          <div id="routing-panel">
            <p className="row-sub" style={{ margin: "4px 0 6px" }}>
              Décidé par des règles fixes, pas par l&apos;IA. Seuls les faits sont partagés, jamais vos mots personnels.
            </p>
            <ul className="route-list">
              {routing
                .filter((r) => r.recipient !== "caregiver")
                .map((r) => (
                  <li key={r.recipient} className="route">
                    <div className="route-head">
                      <span className="avatar" aria-hidden>
                        {CONTACTS[r.recipient].initials}
                      </span>
                      <div className="row-main">
                        <p className="row-title">{CONTACTS[r.recipient].name}</p>
                        <p className="row-sub">{RECIPIENT_LABEL[r.recipient]}</p>
                      </div>
                      {r.immediate.length ? <Badge tone={r.immediate.some((o) => o.severity === "urgent") ? "urgent" : "watch"}>Immédiat</Badge> : null}
                    </div>
                    <div className="route-lines">
                      {r.immediate.length ? <RouteLine k="Tout de suite" list={r.immediate} /> : null}
                      {r.recipient === "doctor" && r.regular.length ? <RouteLine k="Pour information" list={r.regular} /> : null}
                      {r.recipient !== "doctor" && r.regular.length + r.summary.length ? (
                        <RouteLine k={r.recipient === "family" && r.summary.some((o) => o.category === "mood_behavior") ? "Résumé du soir, filtré" : "Résumé du soir"} list={[...r.regular, ...r.summary]} />
                      ) : null}
                      {r.report.length ? <RouteLine k="Rapport médical" list={r.report} /> : null}
                      {r.excluded.length === facts.length ? <p className="route-line v">Rien à transmettre.</p> : null}
                    </div>
                  </li>
                ))}
            </ul>
          </div>
        ) : null}
      </section>

      <div className="secondary-action">
        <Button variant="ghost" size="sm" onClick={() => setConfirmDiscard(true)} disabled={busy}>
          Abandonner ce compte rendu
        </Button>
      </div>
      <div className="sticky-actions">
        <Button block onClick={confirm} disabled={busy || facts.length === 0} icon={busy ? undefined : Check}>
          {busy ? "Enregistrement…" : facts.length ? `Valider ${plural(facts.length, "fait", "faits")} et partager` : "Aucun fait à valider"}
        </Button>
      </div>

      <ObservationEditor
        observation={editing}
        onClose={() => setEditing(null)}
        onSave={(o) => {
          dispatch({ type: "updateDraftObservation", observation: o });
          setEditing(null);
          toast("Correction enregistrée.");
        }}
      />

      <Sheet
        open={confirmDiscard}
        onClose={() => setConfirmDiscard(false)}
        tone="alert"
        title="Abandonner ce compte rendu ?"
        description="Les faits relevés et vos réponses seront effacés. Rien n'a été enregistré ni transmis."
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmDiscard(false)}>
              Garder
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                dispatch({ type: "setDraft", draft: null });
                setDeviceRecording(null);
                setConfirmDiscard(false);
                router.push("/");
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

function RouteLine({ k, list }: { k: string; list: Observation[] }) {
  return (
    <p className="route-line">
      <span className="k">{k}</span>
      <span className="v">{list.map((o) => CATEGORY_SHORT[o.category].toLowerCase()).join(", ")}</span>
    </p>
  );
}

// ---------------------------------------------------------------------------
// Done
// ---------------------------------------------------------------------------

function Confirmed({ draft }: { draft: ReportDraft }) {
  const router = useRouter();
  const { dispatch, replayDemo, toast } = useStore();
  const summary = draft.confirmed_summary ?? { observations: draft.observations.length, messages: 0 };
  const finish = (href: string) => {
    dispatch({ type: "setDraft", draft: null });
    setDeviceRecording(null);
    router.push(href);
  };

  return (
    <div className="success">
      <div className="success-mark" aria-hidden>
        <CircleCheck size={38} strokeWidth={1.5} />
      </div>
      <h1>C&apos;est noté.</h1>
      <p>
        Merci. Le compte rendu de {SUBJECT.firstName} est enregistré à {formatTime(draft.created_at)}. Les bonnes personnes seront informées, sans que vous ayez à le faire.
      </p>
      <div className="summary-tiles">
        <div>
          <strong>{summary.observations}</strong>
          <span>{summary.observations > 1 ? "faits ajoutés à la frise" : "fait ajouté à la frise"}</span>
        </div>
        <div>
          <strong>{summary.messages}</strong>
          <span>{summary.messages > 1 ? "messages préparés" : "message préparé"} (envoi simulé)</span>
        </div>
      </div>
      <div className="stack">
        <Button block icon={CalendarRange} onClick={() => finish("/chronologie/")}>
          Voir la frise
        </Button>
        <Button block variant="secondary" icon={MessagesSquare} onClick={() => finish("/coordination/")}>
          Voir les échanges
        </Button>
        <Button block variant="ghost" onClick={() => finish("/")}>
          Retour à l&apos;accueil
        </Button>
      </div>
      <div style={{ marginTop: 18, textAlign: "left" }}>
        <DemoNote>Aucun message n&apos;a réellement été envoyé : le canal de démonstration affiche les messages dans l&apos;onglet Échanges.</DemoNote>
      </div>
      <div style={{ marginTop: 10 }}>
        <Button
          variant="ghost"
          size="sm"
          icon={RotateCcw}
          onClick={() => {
            replayDemo();
            toast("Démonstration prête : exemple suivant sélectionné.");
            router.push("/");
          }}
        >
          Rejouer la démonstration
        </Button>
      </div>
    </div>
  );
}
