"use client";

import { useState } from "react";
import { ChevronDown, Pencil, Quote, Trash, Watch } from "lucide-react";
import { CATEGORY_LABEL, CATEGORY_ORDER, SEVERITY_LABEL, SOURCE_LABEL, confidenceLabel } from "@/lib/labels";
import { formatTime, relativeDateTime, toLocalIso } from "@/lib/format";
import type { Category, Observation, Severity } from "@/lib/types";
import { CATEGORY_ICON, ICON } from "./icons";
import { Badge, Button, IconButton, Segmented } from "./ui";
import { Sheet } from "./Sheet";

export function CategoryIcon({ category, tone }: { category: Category; tone?: Severity }) {
  const Icon = CATEGORY_ICON[category];
  return (
    <span className={`cat-icon cat-${tone ?? "info"}`} aria-hidden>
      <Icon size={18} strokeWidth={ICON.strokeWidth} />
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  if (severity === "info") return null;
  return <Badge tone={severity === "urgent" ? "urgent" : "watch"}>{SEVERITY_LABEL[severity]}</Badge>;
}

/** One fact in the timeline. Tap to reveal its origin (traceability). */
export function TimelineItem({ o }: { o: Observation }) {
  const [open, setOpen] = useState(false);
  const panelId = `trace-${o.id}`;
  return (
    <li className={`tl-item tl-${o.severity}`}>
      <div className="tl-time">{formatTime(o.timestamp)}</div>
      <div className="tl-rail" aria-hidden>
        <CategoryIcon category={o.category} tone={o.severity} />
      </div>
      <div className="tl-body">
        <button type="button" className="tl-toggle" aria-expanded={open} aria-controls={panelId} onClick={() => setOpen((v) => !v)}>
          <span className="tl-cat">{CATEGORY_LABEL[o.category]}</span>
          <span className="tl-value">{o.value}</span>
          <span className="tl-meta">
            <SeverityBadge severity={o.severity} />
            <span className={`src src-${o.source}`}>
              {o.source === "wearable" ? <Watch size={13} strokeWidth={2} aria-hidden /> : null}
              {SOURCE_LABEL[o.source]}
            </span>
            <ChevronDown size={16} strokeWidth={1.75} className={`chev ${open ? "is-open" : ""}`} aria-hidden />
          </span>
        </button>
        {open ? (
          <div id={panelId} className="trace">
            {o.transcript_span ? (
              <p className="trace-quote">
                <Quote size={14} strokeWidth={1.75} aria-hidden />« {o.transcript_span} »
              </p>
            ) : (
              <p className="trace-quote">Valeur mesurée automatiquement, sans transcription.</p>
            )}
            <dl className="trace-dl">
              <div>
                <dt>Signalé</dt>
                <dd>{relativeDateTime(o.reported_at)}</dd>
              </div>
              <div>
                <dt>Référence</dt>
                <dd className="mono">{o.id}</dd>
              </div>
            </dl>
          </div>
        ) : null}
      </div>
    </li>
  );
}

/** Editable fact card used while reviewing a report draft. */
export function DraftObservationCard({ o, onEdit, onRemove }: { o: Observation; onEdit: () => void; onRemove: () => void }) {
  const conf = confidenceLabel(o.confidence);
  return (
    <li className={`fact fact-${o.severity}`}>
      <div className="fact-head">
        <CategoryIcon category={o.category} tone={o.severity} />
        <div className="fact-title">
          <span className="fact-cat">{CATEGORY_LABEL[o.category]}</span>
          <span className="fact-time">vers {formatTime(o.timestamp)}</span>
        </div>
        <div className="fact-actions">
          <IconButton icon={Pencil} label={`Modifier : ${CATEGORY_LABEL[o.category]}`} onClick={onEdit} />
          <IconButton icon={Trash} label={`Retirer : ${CATEGORY_LABEL[o.category]}`} onClick={onRemove} />
        </div>
      </div>
      <p className="fact-value">{o.value}</p>
      {o.transcript_span ? (
        <p className="fact-span">
          <Quote size={13} strokeWidth={1.75} aria-hidden />
          <span>« {o.transcript_span} »</span>
        </p>
      ) : null}
      <div className={`fact-foot ${o.severity === "info" && !conf.low ? "is-empty" : ""}`}>
        <SeverityBadge severity={o.severity} />
        {/* Only an uncertain extraction is worth the caregiver's attention. */}
        {conf.low ? <Badge tone="outline">{conf.label}</Badge> : null}
      </div>
    </li>
  );
}

function toTimeInput(iso: string) {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

/** Bottom sheet to correct a fact before it is stored. */
export function ObservationEditor({
  observation,
  onClose,
  onSave,
}: {
  observation: Observation | null;
  onClose: () => void;
  onSave: (o: Observation) => void;
}) {
  return (
    <Sheet open={!!observation} onClose={onClose} title="Corriger ce fait">
      {observation ? <EditorForm key={observation.id} observation={observation} onClose={onClose} onSave={onSave} /> : null}
    </Sheet>
  );
}

function EditorForm({ observation, onClose, onSave }: { observation: Observation; onClose: () => void; onSave: (o: Observation) => void }) {
  const [value, setValue] = useState(observation.value);
  const [category, setCategory] = useState<Category>(observation.category);
  const [severity, setSeverity] = useState<Severity>(observation.severity);
  const [time, setTime] = useState(toTimeInput(observation.timestamp));
  const trimmed = value.trim();

  const save = () => {
    if (!trimmed) return;
    const [h, m] = time.split(":").map(Number);
    const ts = new Date(observation.timestamp);
    if (!Number.isNaN(h) && !Number.isNaN(m)) ts.setHours(h, m, 0, 0);
    // A corrected fact is confirmed by the caregiver: full confidence.
    onSave({ ...observation, value: trimmed, category, severity, timestamp: toLocalIso(ts), confidence: 1 });
  };

  return (
    <form
      className="form"
      onSubmit={(e) => {
        e.preventDefault();
        save();
      }}
    >
      <div className="field">
        <label htmlFor="obs-value">Ce qui s&apos;est passé</label>
        <textarea id="obs-value" rows={3} value={value} onChange={(e) => setValue(e.target.value)} aria-invalid={!trimmed} aria-describedby="obs-value-help" />
        <p id="obs-value-help" className="field-help">
          {trimmed ? "Décrivez le fait simplement, sans interprétation." : "Ce champ ne peut pas rester vide."}
        </p>
      </div>
      <div className="field-row">
        <div className="field">
          <label htmlFor="obs-cat">Catégorie</label>
          <select id="obs-cat" value={category} onChange={(e) => setCategory(e.target.value as Category)}>
            {CATEGORY_ORDER.map((c) => (
              <option key={c} value={c}>
                {CATEGORY_LABEL[c]}
              </option>
            ))}
          </select>
        </div>
        <div className="field field-narrow">
          <label htmlFor="obs-time">Heure</label>
          <input id="obs-time" type="time" value={time} onChange={(e) => setTime(e.target.value)} />
        </div>
      </div>
      <div className="field">
        <span className="label" id="obs-sev-label">
          Niveau d&apos;attention
        </span>
        <Segmented<Severity>
          label="Niveau d'attention"
          value={severity}
          onChange={setSeverity}
          options={[
            { value: "info", label: "Information" },
            { value: "watch", label: "À surveiller" },
            { value: "urgent", label: "Urgent" },
          ]}
        />
      </div>
      {observation.transcript_span ? (
        <p className="fact-span">
          <Quote size={13} strokeWidth={1.75} aria-hidden />
          <span>D&apos;après vos mots : « {observation.transcript_span} »</span>
        </p>
      ) : null}
      <div className="sheet-actions">
        <Button variant="ghost" onClick={onClose}>
          Annuler
        </Button>
        <Button type="submit" disabled={!trimmed}>
          Enregistrer la correction
        </Button>
      </div>
    </form>
  );
}
