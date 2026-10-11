"use client";

import { useEffect, useMemo, useState } from "react";
import { Download, FileText, Info, Minus, Plus, Printer, ShieldCheck, Watch } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Badge, Button, Card, Chip, DemoNote, Segmented, Switch } from "@/components/ui";
import { CATEGORY_LABEL, SEVERITY_LABEL, SOURCE_SHORT } from "@/lib/labels";
import { dayKey, lowerFirst, formatDate, formatDateShort, formatDayLong, formatHoursMinutes, formatNumber, formatTime, plural } from "@/lib/format";
import { buildDoctorReport, type DoctorReport, type PeriodUnit, type ReportPeriod } from "@/lib/report";
import { downloadTextFile, reportToHtml } from "@/lib/report-html";
import { CONTACTS, SUBJECT } from "@/mocks/people";
import { useStore } from "@/state/store";

const PRESETS: { label: string; period: ReportPeriod }[] = [
  { label: "7 jours", period: { amount: 7, unit: "days" } },
  { label: "30 jours", period: { amount: 30, unit: "days" } },
  { label: "3 mois", period: { amount: 3, unit: "months" } },
];

const MAX: Record<PeriodUnit, number> = { days: 90, months: 12 };
const HIGHLIGHTS_SHOWN = 6;

export default function ReportPage() {
  const { state, wearable, dataStart, dispatch, toast } = useStore();
  const [period, setPeriod] = useState<ReportPeriod>({ amount: 30, unit: "days" });
  const [report, setReport] = useState<DoctorReport | null>(null);
  const [busy, setBusy] = useState(false);
  const includeWearable = state.settings.wearableInReport;

  const samePeriod = (a: ReportPeriod, b: ReportPeriod) => a.amount === b.amount && a.unit === b.unit;

  const generate = () => {
    setBusy(true);
    setReport(null);
    // Simulated generation delay; the real report is produced by the backend.
    window.setTimeout(() => {
      setReport(buildDoctorReport(state.observations, wearable, period, { includeWearable, dataStart }));
      setBusy(false);
    }, 900);
  };

  const download = () => {
    if (!report) return;
    const html = reportToHtml(report, { name: `${SUBJECT.firstName} ${SUBJECT.lastName}`, age: SUBJECT.age }, CONTACTS.doctor.name);
    downloadTextFile(`rapport-karis-${dayKey(new Date())}.html`, html);
    toast("Rapport téléchargé sur cet appareil.");
  };

  const changeAmount = (delta: number) => {
    setPeriod((p) => ({ ...p, amount: Math.min(MAX[p.unit], Math.max(1, p.amount + delta)) }));
    setReport(null);
  };

  return (
    <>
      <PageHeader title="Rapport médical" eyebrow="Pour le Dr Lefèvre" subtitle="Un document factuel et daté, à partager lors d'une consultation." />

      <Card className="no-print" labelledBy="period-title">
        <h2 id="period-title" style={{ fontSize: 16, marginBottom: 12 }}>
          Période couverte
        </h2>
        <div className="period-presets" role="group" aria-label="Périodes fréquentes">
          {PRESETS.map((p) => (
            <Chip
              key={p.label}
              selected={samePeriod(p.period, period)}
              onClick={() => {
                setPeriod(p.period);
                setReport(null);
              }}
            >
              {p.label}
            </Chip>
          ))}
        </div>
        <div className="custom-period">
          <div className="stepper-input" role="group" aria-label="Durée personnalisée">
            <button type="button" className="icon-btn icon-btn-surface" aria-label="Diminuer la durée" onClick={() => changeAmount(-1)} disabled={period.amount <= 1}>
              <Minus size={18} strokeWidth={1.75} aria-hidden />
            </button>
            <output aria-live="polite" aria-label={`${period.amount} ${period.unit === "days" ? "jours" : "mois"}`}>
              {period.amount}
            </output>
            <button type="button" className="icon-btn icon-btn-surface" aria-label="Augmenter la durée" onClick={() => changeAmount(1)} disabled={period.amount >= MAX[period.unit]}>
              <Plus size={18} strokeWidth={1.75} aria-hidden />
            </button>
          </div>
          <Segmented<PeriodUnit>
            label="Unité"
            value={period.unit}
            onChange={(u) => {
              setPeriod((p) => ({ unit: u, amount: Math.min(p.amount, MAX[u]) }));
              setReport(null);
            }}
            options={[
              { value: "days", label: "jours" },
              { value: "months", label: "mois" },
            ]}
          />
        </div>
        <div style={{ marginTop: 6 }}>
          <Switch
            id="wearable-in-report"
            checked={includeWearable}
            onChange={(v) => {
              dispatch({ type: "settings", patch: { wearableInReport: v } });
              setReport(null);
            }}
            label="Inclure les mesures du bracelet"
            description="Sommeil, fréquence cardiaque, oxygénation et pas, présentés à part."
          />
        </div>
        <Button block icon={FileText} onClick={generate} disabled={busy}>
          {busy ? "Préparation du rapport…" : report ? "Mettre à jour le rapport" : "Préparer le rapport"}
        </Button>
      </Card>

      {busy ? (
        <p className="row-sub" role="status" style={{ textAlign: "center", marginTop: 18, display: "flex", gap: 10, justifyContent: "center", alignItems: "center" }}>
          <span className="spinner" aria-hidden /> Rassemblement des faits par date…
        </p>
      ) : null}

      {report ? <ReportPreview report={report} onDownload={download} /> : null}

      {!report && !busy ? (
        <div style={{ marginTop: 14 }}>
          <DemoNote>Rapport de démonstration assemblé sur l&apos;appareil à partir des données fictives. La version officielle (HTML et PDF) sera produite par le serveur Karis.</DemoNote>
        </div>
      ) : null}
    </>
  );
}

function ReportPreview({ report, onDownload }: { report: DoctorReport; onDownload: () => void }) {
  const [showAllDays, setShowAllDays] = useState(false);
  const [showAllHighlights, setShowAllHighlights] = useState(false);
  const allHighlights = useMemo(() => [...report.highlights].reverse(), [report.highlights]);
  const highlights = showAllHighlights ? allHighlights : allHighlights.slice(0, HIGHLIGHTS_SHOWN);
  // The printed / PDF version always contains the full content.
  useEffect(() => {
    const onBeforePrint = () => {
      setShowAllDays(true);
      setShowAllHighlights(true);
    };
    window.addEventListener("beforeprint", onBeforePrint);
    return () => window.removeEventListener("beforeprint", onBeforePrint);
  }, []);
  const days = useMemo(() => [...report.days].reverse(), [report.days]);
  const shownDays = showAllDays ? days : days.slice(0, 5);
  const maxSleep = report.wearable ? Math.max(...report.wearable.perDay.map((d) => d.asleepMin), 1) : 1;

  return (
    <article className="doc" style={{ marginTop: 16 }} aria-labelledby="doc-title">
      <div className="doc-head">
        <div>
          <h2 id="doc-title">Rapport de suivi factuel</h2>
          <p className="doc-meta">
            {SUBJECT.firstName} {SUBJECT.lastName}, {SUBJECT.age} ans
            <br />
            Du {formatDate(report.from)} au {formatDate(report.to)}
          </p>
        </div>
        <Badge tone="sage">{plural(report.observationCount, "fait", "faits")}</Badge>
      </div>

      <p className="doc-notice">
        <ShieldCheck size={16} strokeWidth={1.75} aria-hidden />
        Faits rapportés et mesures uniquement : ce document ne contient ni diagnostic, ni interprétation, ni recommandation.
      </p>
      {report.truncated ? (
        <p className="doc-notice" style={{ background: "var(--terracotta-pale)" }}>
          <Info size={16} strokeWidth={1.75} aria-hidden style={{ color: "var(--terracotta-ink)" }} />
          Les données de démonstration commencent le {formatDate(report.from)} : la période demandée est plus longue.
        </p>
      ) : null}

      <h3>Points signalés</h3>
      {report.highlights.length ? (
        <ul>
          {highlights.map((o) => (
            <li key={o.id} className="doc-line">
              <span className="t">{formatDateShort(o.timestamp)}</span>
              <span>
                {CATEGORY_LABEL[o.category]} : {lowerFirst(o.value)}{" "}
                <Badge tone={o.severity === "urgent" ? "urgent" : "watch"}>{SEVERITY_LABEL[o.severity]}</Badge> <span className="doc-ref">{o.id}</span>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="row-sub">Aucun point signalé sur la période.</p>
      )}
      {report.highlights.length > HIGHLIGHTS_SHOWN ? (
        <div className="no-print">
          <Button variant="ghost" size="sm" onClick={() => setShowAllHighlights((v) => !v)}>
            {showAllHighlights ? "Afficher moins" : `Afficher les ${report.highlights.length} points signalés`}
          </Button>
        </div>
      ) : null}

      <h3>Vue d&apos;ensemble</h3>
      <table className="count-table">
        <thead>
          <tr>
            <th scope="col">Catégorie</th>
            <th scope="col">Faits</th>
            <th scope="col">Signalés</th>
          </tr>
        </thead>
        <tbody>
          {report.counts.map((c) => (
            <tr key={c.category}>
              <td>{CATEGORY_LABEL[c.category]}</td>
              <td>{c.total}</td>
              <td>{c.flagged}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {report.wearable ? (
        <>
          <h3 style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Watch size={16} strokeWidth={1.75} aria-hidden /> Mesures du bracelet · données simulées
          </h3>
          <div className="measure-grid" style={{ marginTop: 0 }}>
            <div className="measure">
              <strong>{formatHoursMinutes(report.wearable.avgAsleepMin)}</strong>
              <span>sommeil moyen</span>
            </div>
            <div className="measure">
              <strong>{report.wearable.avgNightHr ? `${formatNumber(report.wearable.avgNightHr)} bpm` : "—"}</strong>
              <span>pouls la nuit</span>
            </div>
            <div className="measure">
              <strong>{formatNumber(report.wearable.avgSteps)}</strong>
              <span>pas par jour</span>
            </div>
          </div>
          <p className="row-sub" style={{ marginTop: 8 }}>
            {plural(report.wearable.nights, "nuit mesurée", "nuits mesurées")}, dont {formatHoursMinutes(report.wearable.avgDeepMin)} de sommeil profond en moyenne
            {report.wearable.avgSpo2 ? ` · SpO₂ nocturne moyenne ${formatNumber(report.wearable.avgSpo2, 1)} %` : ""}.
          </p>
          <div className="bars" role="img" aria-label="Durée de sommeil mesurée chaque nuit sur la période">
            {report.wearable.perDay
              .filter((d) => d.asleepMin > 0)
              .map((d) => (
                <span key={d.day} className={d.asleepMin < 360 ? "low" : ""} style={{ height: `${(d.asleepMin / maxSleep) * 100}%` }} title={`${formatDateShort(d.day + "T12:00:00")} : ${formatHoursMinutes(d.asleepMin)}`} />
              ))}
          </div>
          <div className="bars-legend" aria-hidden>
            <span>Sommeil par nuit</span>
            <span>en terracotta : moins de 6 h</span>
          </div>
        </>
      ) : null}

      <h3>Chronologie</h3>
      {shownDays.length ? (
        shownDays.map((d) => (
          <div key={d.day}>
            <p className="doc-day">{formatDayLong(`${d.day}T12:00:00`)}</p>
            <ul>
              {d.wearable && d.wearable.asleepMin > 0 ? (
                <li className="doc-line">
                  <span className="t">Nuit</span>
                  <span>
                    Bracelet : {formatHoursMinutes(d.wearable.asleepMin)} de sommeil mesuré, {plural(d.wearable.awakePeriods, "période", "périodes")} d&apos;éveil
                    {d.wearable.steps ? `, ${formatNumber(d.wearable.steps)} pas` : ""} <span className="doc-ref">bracelet</span>
                  </span>
                </li>
              ) : null}
              {d.observations.map((o) => (
                <li key={o.id} className="doc-line">
                  <span className="t">{formatTime(o.timestamp)}</span>
                  <span>
                    {CATEGORY_LABEL[o.category]} : {lowerFirst(o.value)} <span className="src">· {SOURCE_SHORT[o.source]}</span> <span className="doc-ref">{o.id}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))
      ) : (
        <p className="row-sub">Aucune observation sur la période.</p>
      )}
      {days.length > 5 ? (
        <div className="no-print" style={{ marginTop: 12 }}>
          <Button block variant="ghost" onClick={() => setShowAllDays((v) => !v)}>
            {showAllDays ? "Afficher moins" : `Afficher les ${days.length} jours`}
          </Button>
        </div>
      ) : null}

      <div className="doc-actions no-print">
        <Button icon={Download} onClick={onDownload}>
          Télécharger
        </Button>
        <Button variant="secondary" icon={Printer} onClick={() => window.print()}>
          Imprimer / PDF
        </Button>
      </div>
      <p className="row-sub no-print" style={{ marginTop: 10, textAlign: "center" }}>
        Fichier HTML généré sur l&apos;appareil. Rien n&apos;est envoyé au médecin.
      </p>
    </article>
  );
}
