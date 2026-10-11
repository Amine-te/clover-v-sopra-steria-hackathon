"use client";

import { useState } from "react";
import { Coffee, Feather, HeartHandshake, Lock, Phone, Sun, Wind, type LucideIcon } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Button, Card, Chip, SectionHeader } from "@/components/ui";
import { isSameDay, relativeDateTime } from "@/lib/format";
import type { CheckInMood, CheckInPause } from "@/lib/types";
import { useStore } from "@/state/store";

const MOODS: { value: CheckInMood; label: string; icon: LucideIcon }[] = [
  { value: "bien", label: "Ça va plutôt bien", icon: Sun },
  { value: "chargee", label: "Journée chargée", icon: Coffee },
  { value: "souffler", label: "Besoin de souffler", icon: Wind },
  { value: "sans_reponse", label: "Je préfère ne pas répondre", icon: Feather },
];

const PAUSES: { value: CheckInPause; label: string }[] = [
  { value: "oui", label: "Oui" },
  { value: "un_peu", label: "Un peu" },
  { value: "non", label: "Pas aujourd'hui" },
];

/** Supportive replies. Never a score, a diagnosis or a reproach. */
const REPLIES: Record<CheckInMood, string[]> = {
  bien: ["Tant mieux. Gardez ce moment pour vous.", "Karis s'occupe de transmettre les nouvelles : vous n'avez rien d'autre à faire ce soir."],
  chargee: ["Merci de l'avoir dit. Les journées comme celle-ci comptent double.", "Si vous le souhaitez, le mode allégé réduit les questions au strict minimum."],
  souffler: [
    "Merci de l'avoir dit. Vous n'avez pas à tout porter.",
    "Parler à quelqu'un qui connaît cette situation peut aider. Les lignes ci-dessous sont gratuites et anonymes.",
  ],
  sans_reponse: ["C'est tout à fait possible. Cette page reste là, quand vous voulez."],
};

export default function WellbeingPage() {
  const { state, dispatch, toast } = useStore();
  const today = state.checkins.find((c) => isSameDay(c.at, new Date()));
  const [mood, setMood] = useState<CheckInMood | null>(today?.mood ?? null);
  const [pause, setPause] = useState<CheckInPause | null>(today?.pause ?? null);
  const [saved, setSaved] = useState(Boolean(today));

  const save = (m: CheckInMood, p: CheckInPause | null) => {
    dispatch({ type: "addCheckin", checkin: { id: `ci-${Date.now().toString(36)}`, at: new Date().toISOString(), mood: m, pause: p ?? undefined } });
    setSaved(true);
  };

  const pickMood = (m: CheckInMood) => {
    setMood(m);
    setPause(null);
    save(m, null);
  };

  const pickPause = (p: CheckInPause) => {
    setPause(p);
    if (mood) save(mood, p);
  };

  const light = state.settings.lightMode;

  return (
    <>
      <PageHeader title="Et vous, comment ça va ?" eyebrow="Bien-être de l'aidant" back={{ href: "/", label: "Accueil" }} />

      <section className="calm-hero" aria-labelledby="checkin-title">
        <span className="soft-icon terra" aria-hidden>
          <HeartHandshake size={22} strokeWidth={1.75} />
        </span>
        <h2 id="checkin-title">Comment vous sentez-vous ce soir ?</h2>
        <p className="row-sub" style={{ marginTop: 6, display: "flex", gap: 6, alignItems: "flex-start" }}>
          <Lock size={14} strokeWidth={2} aria-hidden style={{ marginTop: 3, flexShrink: 0 }} />
          Votre réponse reste sur cet appareil. Elle n&apos;apparaît ni dans la frise, ni dans les messages, ni dans le rapport.
        </p>
        <div className="mood-grid" role="group" aria-labelledby="checkin-title">
          {MOODS.map((m) => {
            const Icon = m.icon;
            return (
              <button key={m.value} type="button" className="mood" aria-pressed={mood === m.value} onClick={() => pickMood(m.value)}>
                <Icon size={22} strokeWidth={1.75} aria-hidden />
                {m.label}
              </button>
            );
          })}
        </div>

        {mood && mood !== "sans_reponse" ? (
          <div style={{ marginTop: 18 }}>
            <h3 id="pause-title" style={{ fontSize: 15 }}>
              Avez-vous pu prendre un moment pour vous aujourd&apos;hui ?
            </h3>
            <div className="chip-row" role="group" aria-labelledby="pause-title" style={{ marginTop: 10 }}>
              {PAUSES.map((p) => (
                <Chip key={p.value} selected={pause === p.value} onClick={() => pickPause(p.value)}>
                  {p.label}
                </Chip>
              ))}
            </div>
          </div>
        ) : null}

        {mood && saved ? (
          <div className="reply" role="status">
            {REPLIES[mood].map((r) => (
              <p key={r}>{r}</p>
            ))}
            {pause === "non" ? <p>Même dix minutes comptent. Demain est un autre jour, sans compte à rendre.</p> : null}
            {(mood === "chargee" || mood === "souffler") && !light ? (
              <div style={{ marginTop: 12 }}>
                <Button
                  variant="primary"
                  size="sm"
                  icon={Feather}
                  onClick={() => {
                    dispatch({ type: "settings", patch: { lightMode: true } });
                    toast("Mode allégé activé.");
                  }}
                >
                  Activer le mode allégé
                </Button>
              </div>
            ) : null}
            {light && (mood === "chargee" || mood === "souffler") ? <p style={{ fontWeight: 650 }}>Le mode allégé est activé.</p> : null}
          </div>
        ) : null}
      </section>

      <SectionHeader title="Parler à quelqu'un" id="help-title" />
      <Card labelledBy="help-title">
        <a className="help-line" href="tel:+33184729472">
          <span className="soft-icon" aria-hidden>
            <Phone size={20} strokeWidth={1.75} />
          </span>
          <span>
            <strong>Avec Nos Proches</strong>
            <span>Écoute des aidants par d&apos;anciens aidants · 7 j/7, 8 h – 22 h</span>
          </span>
          <span className="help-num">01 84 72 94 72</span>
        </a>
        <a className="help-line" href="tel:3114">
          <span className="soft-icon terra" aria-hidden>
            <Phone size={20} strokeWidth={1.75} />
          </span>
          <span>
            <strong>3114</strong>
            <span>Si vous pensez au suicide ou vous inquiétez pour un proche · 24 h/24</span>
          </span>
          <span className="help-num">3114</span>
        </a>
        <p className="row-sub" style={{ marginTop: 8 }}>
          En cas d&apos;urgence vitale, appelez le <a href="tel:15">15</a> ou le <a href="tel:112">112</a>.
        </p>
      </Card>

      <SectionHeader title="Des pistes pour souffler" id="relief-title" />
      <Card labelledBy="relief-title">
        <ul className="info-list">
          <li>
            <Wind size={17} strokeWidth={1.75} aria-hidden />
            <span>Les plateformes d&apos;accompagnement et de répit proposent écoute, information et solutions de relais près de chez vous.</span>
          </li>
          <li>
            <HeartHandshake size={17} strokeWidth={1.75} aria-hidden />
            <span>Julien peut recevoir davantage d&apos;informations : vous n&apos;êtes pas seule à suivre la situation.</span>
          </li>
          <li>
            <Feather size={17} strokeWidth={1.75} aria-hidden />
            <span>Un jour sans compte rendu n&apos;est pas un oubli. Karis ne vous le reprochera jamais.</span>
          </li>
        </ul>
      </Card>

      {state.checkins.length ? (
        <div style={{ marginTop: 18, textAlign: "center" }}>
          <p className="row-sub">Dernière réponse : {relativeDateTime(state.checkins[0].at)}</p>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              dispatch({ type: "clearCheckins" });
              setMood(null);
              setPause(null);
              setSaved(false);
              toast("Vos réponses ont été effacées de l'appareil.");
            }}
          >
            Effacer mes réponses
          </Button>
        </div>
      ) : null}
    </>
  );
}
