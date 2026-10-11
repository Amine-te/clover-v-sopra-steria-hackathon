"use client";

import Link from "next/link";
import { useMemo } from "react";
import { Check, ChevronRight, Feather, HeartHandshake, Mic, NotebookPen, Settings, Watch } from "lucide-react";
import { Logo } from "@/components/Logo";
import { CategoryIcon, SeverityBadge } from "@/components/observations";
import { Card, SectionHeader } from "@/components/ui";
import { CATEGORY_LABEL, CATEGORY_SHORT, DAILY_CHECKLIST, RECIPIENT_LABEL, deliveryLabel } from "@/lib/labels";
import { addDays, dayKey, formatDayLong, formatHoursMinutes, formatNumber, formatTime, greeting, relativeDateTime } from "@/lib/format";
import { buildDoctorReport } from "@/lib/report";
import { CAREGIVER, CONTACTS, SUBJECT } from "@/mocks/people";
import { useStore } from "@/state/store";

export default function HomePage() {
  const { state, wearable, missingToday, reportedToday, dataStart, dispatch } = useStore();
  const now = new Date();
  const draft = state.draft && state.draft.stage !== "confirmed" ? state.draft : null;

  const toFollow = useMemo(() => {
    const limit = addDays(new Date(), -3).getTime();
    return state.observations
      .filter((o) => o.severity !== "info" && new Date(o.timestamp).getTime() >= limit)
      .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
      .slice(0, 3);
  }, [state.observations]);

  const lastNight = useMemo(() => {
    // Last complete night only (a night in progress is never shown).
    const r = buildDoctorReport([], wearable, { amount: 3, unit: "days" }, { includeWearable: true, dataStart });
    const nights = (r.wearable?.perDay ?? []).filter((d) => d.asleepMin > 0);
    return nights[nights.length - 1];
  }, [wearable, dataStart]);

  const lastMessages = state.messages.filter((m) => m.recipient !== "caregiver").slice(0, 2);
  const lastCaregiverReport = state.observations
    .filter((o) => o.source === "caregiver_voice")
    .reduce<string | null>((acc, o) => (!acc || o.reported_at > acc ? o.reported_at : acc), null);

  return (
    <>
      <div className="home-top">
        <Logo />
        <Link href="/parametres/" className="icon-btn icon-btn-surface" aria-label="Rappels et paramètres" title="Rappels et paramètres">
          <Settings size={20} strokeWidth={1.75} aria-hidden />
        </Link>
      </div>

      <div className="greeting">
        <p className="date">{formatDayLong(now)}</p>
        <h1>
          {greeting(now)}, {CAREGIVER.firstName}
        </h1>
      </div>

      {state.settings.lightMode ? (
        <div className="light-banner" role="status">
          <Feather size={18} strokeWidth={1.75} aria-hidden />
          Mode allégé : réponses en un geste, deux questions au plus.
          <button type="button" onClick={() => dispatch({ type: "settings", patch: { lightMode: false } })}>
            Désactiver
          </button>
        </div>
      ) : null}

      <section className="hero" aria-labelledby="hero-title">
        <p className="hero-kicker">
          <NotebookPen size={15} strokeWidth={1.75} aria-hidden />
          {draft
            ? "Compte rendu en attente"
            : reportedToday && lastCaregiverReport
              ? `Compte rendu enregistré à ${formatTime(lastCaregiverReport)}`
              : "Compte rendu du jour"}
        </p>
        <h2 id="hero-title">
          {draft ? "Il reste à vérifier votre compte rendu" : reportedToday ? "Un détail à ajouter ?" : `Comment s'est passée la journée de ${SUBJECT.firstName} ?`}
        </h2>
        <p>
          {draft
            ? "Relisez les faits relevés avant qu'ils ne soient enregistrés et partagés."
            : reportedToday
              ? "Vous pouvez compléter à tout moment, en quelques mots."
              : "Racontez-la simplement, à voix haute. Karis en retient les faits et prévient les bonnes personnes."}
        </p>
        <Link href={draft ? "/analyse/" : "/enregistrer/"} className="hero-action">
          <span className="hero-mic" aria-hidden>
            {draft ? <NotebookPen size={22} strokeWidth={1.75} /> : <Mic size={24} strokeWidth={1.75} />}
          </span>
          <span className="hero-action-text">
            <strong>{draft ? "Reprendre la vérification" : reportedToday ? "Ajouter un message vocal" : "Raconter la journée"}</strong>
            <span>{draft ? `${draft.observations.length} faits à relire` : "Une minute suffit souvent"}</span>
          </span>
        </Link>
      </section>

      <SectionHeader title="Aujourd'hui" id="today-title" action={<Link href="/chronologie/">Voir la frise</Link>} />
      <Card labelledBy="today-title">
        <p className="lead">
          {missingToday.length === 0
            ? "Les repères du jour sont notés. Merci."
            : "Rien n'est obligatoire : notez simplement ce qui compte."}
        </p>
        <ul className="checklist">
          {DAILY_CHECKLIST.map((c) => {
            const done = !missingToday.includes(c);
            return (
              <li key={c} className={done ? "is-done" : ""}>
                <CategoryIcon category={c} />
                <span>
                  {CATEGORY_SHORT[c]}
                  <span className="state">{done ? "Noté" : "Pas encore"}</span>
                </span>
                {done ? <Check size={16} strokeWidth={2} aria-hidden style={{ marginLeft: "auto", color: "var(--forest)" }} /> : null}
              </li>
            );
          })}
        </ul>
      </Card>

      {lastNight ? (
        <Card className="card-muted" labelledBy="night-title">
          <div className="card-title">
            <span className="soft-icon" aria-hidden>
              <Watch size={20} strokeWidth={1.75} />
            </span>
            <div>
              <h3 id="night-title">{lastNight.day === dayKey(new Date()) ? "Nuit dernière" : "Dernière nuit mesurée"}</h3>
              <p className="row-sub">Mesuré par le bracelet de {SUBJECT.firstName} · données simulées</p>
            </div>
          </div>
          <div className="measure-grid">
            <div className="measure">
              <strong>{formatHoursMinutes(lastNight.asleepMin)}</strong>
              <span>de sommeil</span>
            </div>
            <div className="measure">
              <strong>{lastNight.awakePeriods}</strong>
              <span>{lastNight.awakePeriods > 1 ? "périodes d'éveil" : "période d'éveil"}</span>
            </div>
            <div className="measure">
              <strong>{lastNight.nightHr ? `${formatNumber(lastNight.nightHr)}` : "—"}</strong>
              <span>bpm la nuit</span>
            </div>
          </div>
        </Card>
      ) : null}

      <SectionHeader title="À suivre" id="follow-title" />
      <Card labelledBy="follow-title">
        {toFollow.length ? (
          <ul className="list-plain">
            {toFollow.map((o) => (
              <li key={o.id} className="row">
                <CategoryIcon category={o.category} tone={o.severity} />
                <div className="row-main">
                  <p className="row-title">{o.value}</p>
                  <p className="row-sub">
                    {CATEGORY_LABEL[o.category]} · {relativeDateTime(o.timestamp)}
                  </p>
                </div>
                <SeverityBadge severity={o.severity} />
              </li>
            ))}
          </ul>
        ) : (
          <p className="lead">Aucun point d&apos;attention ces trois derniers jours.</p>
        )}
      </Card>

      <SectionHeader title="Derniers échanges" id="msg-title" action={<Link href="/coordination/">Tout voir</Link>} />
      <Card labelledBy="msg-title">
        {lastMessages.length ? (
          <ul className="list-plain">
            {lastMessages.map((m) => (
              <li key={m.id}>
                <Link href={`/coordination/?destinataire=${m.recipient}`} className="row card-link" style={{ minHeight: 0 }}>
                  <span className="avatar" aria-hidden>
                    {CONTACTS[m.recipient].initials}
                  </span>
                  <span className="row-main">
                    <span className="row-title" style={{ display: "block" }}>
                      {m.title}
                    </span>
                    <span className="row-sub" style={{ display: "block" }}>
                      {CONTACTS[m.recipient].name} · {RECIPIENT_LABEL[m.recipient].toLowerCase()}
                    </span>
                    <span className="row-sub" style={{ display: "block" }}>
                      {relativeDateTime(m.sent_at)} · {deliveryLabel(m).toLowerCase()}
                    </span>
                  </span>
                  <ChevronRight size={18} className="chev-r" aria-hidden />
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="lead">Aucun message préparé pour le moment.</p>
        )}
      </Card>

      <SectionHeader title="Et vous ?" id="me-title" />
      <section className="card wellbeing-card" aria-labelledby="me-title">
        <Link href="/bien-etre/" className="card-link">
          <span className="soft-icon terra" aria-hidden>
            <HeartHandshake size={22} strokeWidth={1.75} />
          </span>
          <span>
            <span className="row-title" style={{ display: "block" }}>
              Un instant pour vous
            </span>
            <span className="row-sub" style={{ display: "block" }}>
              Une question, quand vous le souhaitez. Rien n&apos;est transmis.
            </span>
          </span>
          <ChevronRight size={18} className="chev-r" aria-hidden />
        </Link>
      </section>

      <p className="footer-note">
        <strong>Karis veille sur ceux qui veillent.</strong>
        Version de démonstration · personnes et données fictives
      </p>
    </>
  );
}
