"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ChevronDown, CircleCheck, FileText, Hourglass, Inbox, Info, Scale } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Sheet } from "@/components/Sheet";
import { Badge, Button, DemoNote, EmptyState } from "@/components/ui";
import { CATEGORY_LABEL, CATEGORY_ORDER, RECIPIENT_LABEL, ROUTING_CELL_LABEL, deliveryLabel, summarySent } from "@/lib/labels";
import { lowerFirst, relativeDateTime } from "@/lib/format";
import { RECIPIENTS, ROUTING_MATRIX } from "@/lib/routing";
import type { DeliveryStatus, Recipient, UiMessage } from "@/lib/types";
import { CONTACTS } from "@/mocks/people";
import { useStore } from "@/state/store";

const RULES: Record<Recipient, { label: string; value: string }[]> = {
  auxiliary: [
    { label: "Chute, incident, traitement", value: "Tout de suite" },
    { label: "Sommeil, repas, humeur, douleur", value: "Résumé du soir" },
    { label: "Rendez-vous, organisation", value: "Résumé du soir" },
  ],
  family: [
    { label: "Chute, incident, traitement", value: "Tout de suite" },
    { label: "Sommeil, repas, douleur", value: "Résumé du soir" },
    { label: "Humeur", value: "Résumé filtré" },
    { label: "Organisation", value: "Non transmis" },
  ],
  doctor: [
    { label: "Chute, incident, traitement", value: "Pour information" },
    { label: "Sommeil, repas, humeur, douleur", value: "Rapport médical" },
    { label: "Rendez-vous, organisation", value: "Non transmis" },
  ],
  caregiver: [{ label: "Tous les faits", value: "Confirmation" }],
};

const STATUS_ICON: Record<DeliveryStatus, typeof CircleCheck> = {
  simulated_sent: CircleCheck,
  scheduled_summary: Hourglass,
  in_report: FileText,
};

function CoordinationContent() {
  const params = useSearchParams();
  const { state, dispatch } = useStore();
  const initial = (params?.get("destinataire") as Recipient | null) ?? "auxiliary";
  const [tab, setTab] = useState<Recipient>(RECIPIENTS.includes(initial) ? initial : "auxiliary");
  const [matrixOpen, setMatrixOpen] = useState(false);

  // Opening this screen marks the messages as seen (removes the nav dot).
  useEffect(() => {
    dispatch({ type: "markMessagesSeen" });
  }, [dispatch, state.messages.length]);

  const byRecipient = useMemo(() => {
    const m = new Map<Recipient, UiMessage[]>();
    for (const r of RECIPIENTS) m.set(r, []);
    for (const msg of state.messages) m.get(msg.recipient)?.push(msg);
    return m;
  }, [state.messages]);

  const contact = CONTACTS[tab];
  const list = byRecipient.get(tab) ?? [];

  return (
    <>
      <PageHeader
        title="Coordination"
        eyebrow="Échanges"
        subtitle="Ce que chaque personne reçoit, à partir de vos comptes rendus."
        action={
          <Button variant="ghost" size="sm" icon={Scale} onClick={() => setMatrixOpen(true)}>
            Qui reçoit quoi
          </Button>
        }
      />

      <div className="tabs" role="tablist" aria-label="Destinataires">
        {RECIPIENTS.map((r) => (
          <button
            key={r}
            type="button"
            role="tab"
            id={`tab-${r}`}
            aria-selected={tab === r}
            aria-controls="tab-panel"
            className="tab"
            onClick={() => setTab(r)}
          >
            {RECIPIENT_LABEL[r]}
            <span className="tab-count" aria-label={`${byRecipient.get(r)?.length ?? 0} messages`}>
              {byRecipient.get(r)?.length ?? 0}
            </span>
          </button>
        ))}
      </div>

      <div id="tab-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
        <section className="card" aria-label={`Destinataire : ${contact.name}`}>
          <div className="recipient">
            <span className="avatar avatar-lg" aria-hidden>
              {contact.initials}
            </span>
            <div className="recipient-meta">
              <strong>{contact.name}</strong>
              <span>{contact.detail}</span>
              <span>{contact.contact}</span>
            </div>
          </div>
          <div className="rules">
            {RULES[tab].map((r) => (
              <div key={r.label} className="rule">
                <span>{r.label}</span>
                <span>{r.value}</span>
              </div>
            ))}
          </div>
        </section>

        <div style={{ margin: "14px 0" }}>
          <DemoNote>Canal de démonstration : les messages sont affichés ici, aucun SMS ni e-mail n&apos;est réellement envoyé.</DemoNote>
        </div>

        {list.length ? (
          <ul className="list-plain" aria-label={`Messages pour ${contact.name}`}>
            {list.map((m) => {
              const Icon = summarySent(m) ? CircleCheck : STATUS_ICON[m.delivery];
              return (
                <li key={m.id} className="message">
                  <div className="message-head">
                    <strong>{m.title}</strong>
                    {m.title.includes("urgente") ? <Badge tone="urgent">Urgent</Badge> : null}
                  </div>
                  <p className="message-body">{m.body}</p>
                  <div className="message-foot">
                    <span className="status">
                      <Icon size={15} strokeWidth={1.9} aria-hidden />
                      {deliveryLabel(m)}
                    </span>
                    <span>{relativeDateTime(m.sent_at)}</span>
                  </div>
                  <SourceFacts ids={m.observation_ids} />
                </li>
              );
            })}
          </ul>
        ) : (
          <EmptyState icon={Inbox} title="Aucun message pour l'instant">
            {tab === "doctor"
              ? "Le médecin reçoit surtout le rapport médical. Les faits importants lui sont signalés ici."
              : "Les messages apparaîtront après votre prochain compte rendu."}
          </EmptyState>
        )}
      </div>

      <Sheet
        open={matrixOpen}
        onClose={() => setMatrixOpen(false)}
        title="Qui reçoit quoi"
        description="Ces règles sont fixes et appliquées par le programme. L'IA ne choisit jamais les destinataires : elle ne fait que rédiger les messages."
        footer={<Button onClick={() => setMatrixOpen(false)}>J&apos;ai compris</Button>}
      >
        <div className="matrix-wrap">
          <table className="matrix">
            <caption className="sr-only">Règles de transmission par catégorie et par destinataire</caption>
            <thead>
              <tr>
                <th scope="col">Catégorie</th>
                <th scope="col">Auxiliaire</th>
                <th scope="col">Famille</th>
                <th scope="col">Médecin</th>
              </tr>
            </thead>
            <tbody>
              {CATEGORY_ORDER.map((c) => (
                <tr key={c}>
                  <th scope="row" style={{ fontWeight: 650, color: "var(--text)", fontSize: 13 }}>
                    {c === "medication" ? "Traitement (problème)" : CATEGORY_LABEL[c]}
                  </th>
                  <td>{ROUTING_CELL_LABEL[ROUTING_MATRIX[c].auxiliary]}</td>
                  <td>{ROUTING_CELL_LABEL[ROUTING_MATRIX[c].family]}</td>
                  <td>{ROUTING_CELL_LABEL[ROUTING_MATRIX[c].doctor]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="row-sub" style={{ marginTop: 12, display: "flex", gap: 8 }}>
          <Info size={16} strokeWidth={1.75} aria-hidden style={{ flexShrink: 0, marginTop: 2 }} />
          Un fait urgent est transmis immédiatement à toutes les personnes concernées. La famille ne reçoit jamais vos mots personnels ni l&apos;expression de votre fatigue.
        </p>
      </Sheet>
    </>
  );
}

/** Traceability (constitution, rule 3) shown in human terms: the facts behind a message. */
function SourceFacts({ ids }: { ids: string[] }) {
  const { state } = useStore();
  const [open, setOpen] = useState(false);
  const facts = state.observations.filter((o) => ids.includes(o.id));
  const panelId = `src-${ids[0]}`;
  return (
    <div className="sources">
      <button type="button" className="sources-toggle" aria-expanded={open} aria-controls={panelId} onClick={() => setOpen((v) => !v)}>
        {ids.length > 1 ? `Voir les ${ids.length} faits d'origine` : "Voir le fait d'origine"}
        <ChevronDown size={16} strokeWidth={1.75} className={`chev ${open ? "is-open" : ""}`} aria-hidden />
      </button>
      {open ? (
        <ul id={panelId} className="sources-list">
          {facts.map((o) => (
            <li key={o.id}>
              <span className="t">{relativeDateTime(o.timestamp)}</span>
              <span>
                {CATEGORY_LABEL[o.category]} : {lowerFirst(o.value)}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export default function CoordinationPage() {
  return (
    <Suspense fallback={null}>
      <CoordinationContent />
    </Suspense>
  );
}
