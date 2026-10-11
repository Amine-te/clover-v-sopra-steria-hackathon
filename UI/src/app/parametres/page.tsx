"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { BellRing, EyeOff, Lock, Play, RotateCcw, ShieldCheck, UserRound, Watch } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Sheet } from "@/components/Sheet";
import { Button, Card, DemoNote, SectionHeader, Switch } from "@/components/ui";
import { CATEGORY_SHORT, RECIPIENT_LABEL } from "@/lib/labels";
import { relativeDateTime } from "@/lib/format";
import { RECIPIENTS } from "@/lib/routing";
import { CONTACTS, SUBJECT } from "@/mocks/people";
import { SCENARIOS } from "@/mocks/scenarios";
import { karis } from "@/services";
import { useStore } from "@/state/store";

export default function SettingsPage() {
  const { state, dispatch, missingToday, reportedToday, wearable, resetDemo, replayDemo, toast } = useStore();
  const router = useRouter();
  const s = state.settings;
  const [sending, setSending] = useState(false);
  const [reminderInfo, setReminderInfo] = useState<string | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const set = (patch: Partial<typeof s>) => dispatch({ type: "settings", patch });
  const lastSample = wearable.length ? wearable[wearable.length - 1].timestamp : null;

  const sendReminder = async () => {
    setSending(true);
    setReminderInfo(null);
    const notice = await karis.sendReminderNow(missingToday.map((c) => CATEGORY_SHORT[c]), reportedToday);
    setSending(false);
    if (notice) {
      dispatch({ type: "notice", notice });
      setReminderInfo("Rappel affiché en haut de l'écran (notification simulée).");
    } else {
      setReminderInfo("Un compte rendu a déjà été fait aujourd'hui : aucun rappel ne serait envoyé.");
    }
  };

  return (
    <>
      <PageHeader title="Rappels et paramètres" back={{ href: "/", label: "Accueil" }} />

      <SectionHeader title="Rappel du soir" id="reminder-title" />
      <Card className="settings-group" labelledBy="reminder-title">
        <Switch
          id="reminder"
          checked={s.reminderEnabled}
          onChange={(v) => set({ reminderEnabled: v })}
          label="Me proposer de raconter la journée"
          description="Seulement si aucun compte rendu n'a été fait ce jour-là."
        />
        <div className={`row ${s.reminderEnabled ? "" : "is-disabled"}`} style={{ opacity: s.reminderEnabled ? 1 : 0.5 }}>
          <label htmlFor="reminder-time" className="row-main row-title">
            Heure du rappel
          </label>
          <input
            id="reminder-time"
            type="time"
            className="time-input"
            value={s.reminderTime}
            disabled={!s.reminderEnabled}
            onChange={(e) => e.target.value && set({ reminderTime: e.target.value })}
          />
        </div>
        <Switch
          id="retry"
          checked={s.gentleRetry}
          disabled={!s.reminderEnabled}
          onChange={(v) => set({ gentleRetry: v })}
          label="Une seule relance douce"
          description="Une heure plus tard, jamais davantage."
        />
        <div style={{ padding: "6px 0 16px" }}>
          <Button block variant="soft" icon={BellRing} onClick={sendReminder} disabled={sending}>
            {sending ? "Envoi…" : "Envoyer le rappel maintenant (démo)"}
          </Button>
          {reminderInfo ? (
            <p className="field-help" role="status" style={{ textAlign: "center" }}>
              {reminderInfo}
            </p>
          ) : null}
        </div>
      </Card>

      <SectionHeader title="Simplicité" id="simple-title" />
      <Card className="settings-group" labelledBy="simple-title">
        <Switch
          id="light"
          checked={s.lightMode}
          onChange={(v) => set({ lightMode: v })}
          label="Mode allégé"
          description="Réponses en un geste et deux questions au plus après chaque compte rendu."
        />
        <Switch
          id="suggest-light"
          checked={false}
          disabled
          onChange={() => undefined}
          label="Me suggérer le mode allégé · bientôt"
          description="Prévu plus tard : Karis comparerait le rythme de vos messages à vos habitudes, sans jamais interpréter vos émotions ni votre santé."
        />
      </Card>

      <SectionHeader title="Destinataires" id="recipients-title" />
      <Card className="settings-group" labelledBy="recipients-title">
        <ul className="list-plain">
          {RECIPIENTS.filter((r) => r !== "caregiver").map((r) => (
            <li key={r} className="row">
              <span className="avatar" aria-hidden>
                {CONTACTS[r].initials}
              </span>
              <div className="row-main">
                <p className="row-title">{CONTACTS[r].name}</p>
                <p className="row-sub">
                  {RECIPIENT_LABEL[r]} · {CONTACTS[r].contact}
                </p>
              </div>
            </li>
          ))}
        </ul>
        <p className="row-sub" style={{ padding: "0 0 14px" }}>
          Canal : démonstration (aucun envoi réel). Les règles de transmission sont fixes et visibles dans l&apos;onglet Échanges.
        </p>
      </Card>

      <SectionHeader title="Bracelet" id="wearable-title" />
      <Card className="settings-group" labelledBy="wearable-title">
        <div className="row">
          <span className="soft-icon" aria-hidden>
            <Watch size={20} strokeWidth={1.75} />
          </span>
          <div className="row-main">
            <p className="row-title">Bracelet de {SUBJECT.firstName}</p>
            <p className="row-sub">Données simulées · dernière mesure {lastSample ? relativeDateTime(lastSample).toLowerCase() : "indisponible"}</p>
          </div>
        </div>
        <Switch
          id="wearable-report"
          checked={s.wearableInReport}
          onChange={(v) => set({ wearableInReport: v })}
          label="Inclure les mesures dans le rapport médical"
          description="Toujours présentées à part des faits que vous rapportez."
        />
      </Card>

      <SectionHeader title="Confidentialité" id="privacy-title" />
      <Card labelledBy="privacy-title">
        <ul className="info-list">
          <li>
            <ShieldCheck size={17} strokeWidth={1.75} aria-hidden />
            <span>Karis consigne des faits, jamais de diagnostic ni de conseil médical.</span>
          </li>
          <li>
            <EyeOff size={17} strokeWidth={1.75} aria-hidden />
            <span>Ce que vous dites de vous-même n&apos;est ni enregistré dans la frise, ni transmis.</span>
          </li>
          <li>
            <Lock size={17} strokeWidth={1.75} aria-hidden />
            <span>Chaque fait garde la trace des mots dont il provient et de la personne qui l&apos;a rapporté.</span>
          </li>
          <li>
            <UserRound size={17} strokeWidth={1.75} aria-hidden />
            <span>Démonstration : toutes les personnes et données sont fictives et restent sur cet appareil.</span>
          </li>
        </ul>
      </Card>

      <SectionHeader title="Démonstration" id="demonstration" />
      <Card className="settings-group" labelledBy="demonstration">
        <Switch
          id="fail"
          checked={s.simulateTranscribeFailure}
          onChange={(v) => set({ simulateTranscribeFailure: v })}
          label="Simuler un échec de transcription"
          description="Le prochain envoi échouera une fois, pour montrer l'écran de reprise."
        />
        <div className="row">
          <label htmlFor="scenario" className="row-main row-title">
            Prochain exemple
          </label>
          <select
            id="scenario"
            className="input"
            style={{ width: "auto", maxWidth: 210 }}
            value={state.scenarioIndex}
            onChange={(e) => dispatch({ type: "setScenario", index: Number(e.target.value) })}
          >
            {SCENARIOS.map((sc, i) => (
              <option key={sc.id} value={i}>
                {sc.title}
              </option>
            ))}
          </select>
        </div>
        <div style={{ padding: "6px 0 16px" }} className="stack-sm">
          <Button
            block
            variant="soft"
            icon={Play}
            onClick={() => {
              replayDemo();
              toast("Démonstration prête : historique fictif recréé.");
              router.push("/");
            }}
          >
            Rejouer la démonstration
          </Button>
          <Button block variant="danger" icon={RotateCcw} onClick={() => setConfirmReset(true)}>
            Réinitialiser les données de démonstration
          </Button>
        </div>
      </Card>

      <div style={{ marginTop: 16 }}>
        <DemoNote>Version de démonstration de l&apos;interface. Aucune donnée n&apos;est envoyée à un serveur.</DemoNote>
      </div>
      <p className="footer-note">
        <strong>Karis veille sur ceux qui veillent.</strong>
        Interface de démonstration · v0.1
      </p>

      <Sheet
        open={confirmReset}
        onClose={() => setConfirmReset(false)}
        tone="alert"
        title="Réinitialiser la démonstration ?"
        description="Les comptes rendus ajoutés, les messages et vos réponses seront effacés, puis l'historique fictif de 30 jours sera recréé."
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmReset(false)}>
              Annuler
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                resetDemo();
                setConfirmReset(false);
                toast("Données de démonstration réinitialisées.");
              }}
            >
              Réinitialiser
            </Button>
          </>
        }
      />
    </>
  );
}
