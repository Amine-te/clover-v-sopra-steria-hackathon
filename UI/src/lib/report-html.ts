import { CATEGORY_LABEL, SEVERITY_LABEL, SOURCE_LABEL } from "./labels";
import { formatDate, formatDayLong, formatHoursMinutes, formatNumber, formatTime, lowerFirst } from "./format";
import type { DoctorReport } from "./report";

/**
 * Standalone HTML export of the demo report preview, generated on the device.
 * The official HTML/PDF comes from the backend renderer (feature 007).
 */

function esc(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] as string);
}

export function reportToHtml(r: DoctorReport, subject: { name: string; age: number }, doctor: string): string {
  const highlights = r.highlights.length
    ? `<ul>${r.highlights
        .map((o) => `<li><strong>${esc(formatDate(o.timestamp))}, ${esc(formatTime(o.timestamp))}</strong> — ${esc(CATEGORY_LABEL[o.category])} : ${esc(lowerFirst(o.value))} <span class="tag">${esc(SEVERITY_LABEL[o.severity])}</span> <span class="ref">[${esc(o.id)}]</span></li>`)
        .join("")}</ul>`
    : "<p>Aucun point signalé sur la période.</p>";

  const counts = r.counts.map((c) => `<tr><td>${esc(CATEGORY_LABEL[c.category])}</td><td>${c.total}</td><td>${c.flagged}</td></tr>`).join("");

  const wearable = r.wearable
    ? `<h2>Mesures du bracelet (données simulées)</h2>
<p>Valeurs mesurées, présentées séparément des faits rapportés.</p>
<table><tbody>
<tr><td>Nuits mesurées</td><td>${r.wearable.nights}</td></tr>
<tr><td>Sommeil moyen mesuré</td><td>${esc(formatHoursMinutes(r.wearable.avgAsleepMin))} par nuit, dont ${esc(formatHoursMinutes(r.wearable.avgDeepMin))} de sommeil profond</td></tr>
${r.wearable.avgNightHr ? `<tr><td>Fréquence cardiaque nocturne moyenne</td><td>${formatNumber(r.wearable.avgNightHr)} bpm</td></tr>` : ""}
${r.wearable.avgSpo2 ? `<tr><td>SpO₂ nocturne moyenne</td><td>${formatNumber(r.wearable.avgSpo2, 1)} %</td></tr>` : ""}
<tr><td>Pas par jour (moyenne)</td><td>${formatNumber(r.wearable.avgSteps)}</td></tr>
</tbody></table>`
    : "";

  const days = r.days
    .map((d) => {
      const items = d.observations
        .map((o) => `<li><span class="time">${esc(formatTime(o.timestamp))}</span> ${esc(CATEGORY_LABEL[o.category])} : ${esc(lowerFirst(o.value))}${o.severity !== "info" ? ` <span class="tag">${esc(SEVERITY_LABEL[o.severity])}</span>` : ""} <span class="src">${esc(SOURCE_LABEL[o.source])}</span> <span class="ref">[${esc(o.id)}]</span></li>`)
        .join("");
      const w = d.wearable && d.wearable.asleepMin > 0
        ? `<li class="w"><span class="time">Nuit</span> Bracelet : ${esc(formatHoursMinutes(d.wearable.asleepMin))} de sommeil mesuré, ${d.wearable.awakePeriods} période(s) d'éveil${d.wearable.steps ? `, ${formatNumber(d.wearable.steps)} pas` : ""} <span class="ref">[bracelet ${esc(d.day)}]</span></li>`
        : "";
      return `<h3>${esc(formatDayLong(d.day + "T12:00:00"))}</h3><ul>${w}${items}</ul>`;
    })
    .join("");

  return `<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rapport de suivi — ${esc(subject.name)}</title>
<style>
body{font-family:Manrope,Inter,system-ui,sans-serif;color:#25342E;max-width:760px;margin:32px auto;padding:0 20px;line-height:1.5}
h1{color:#23483C;font-size:24px;margin-bottom:4px}h2{color:#23483C;font-size:17px;margin-top:28px;border-bottom:1px solid #E6E8E1;padding-bottom:6px}
h3{font-size:14px;margin:18px 0 6px;color:#23483C}ul{padding-left:18px;margin:0}li{margin:4px 0;font-size:13.5px}
table{border-collapse:collapse;width:100%;font-size:13.5px}td,th{border-bottom:1px solid #E6E8E1;padding:6px 4px;text-align:left}
.muted{color:#778078;font-size:13px}.tag{background:#F6E9E3;color:#8A4A35;border-radius:6px;padding:1px 6px;font-size:12px}
.ref{color:#778078;font-size:11.5px}.src{color:#769783;font-size:12px}.time{display:inline-block;min-width:44px;color:#778078}
.notice{background:#E7EEE6;border-radius:10px;padding:10px 14px;font-size:13px}
</style></head><body>
<h1>Rapport de suivi factuel</h1>
<p class="muted">${esc(subject.name)}, ${subject.age} ans · Destinataire : ${esc(doctor)}<br>
Période : du ${esc(formatDate(r.from))} au ${esc(formatDate(r.to))} · Généré le ${esc(formatDate(r.generatedAt))}</p>
<p class="notice">Ce document rassemble des faits rapportés par l'entourage et des mesures du bracelet. Il ne contient ni diagnostic, ni interprétation, ni recommandation de traitement. Document de démonstration : personnes et données fictives.</p>
<h2>Points signalés</h2>${highlights}
<h2>Vue d'ensemble</h2><table><thead><tr><th>Catégorie</th><th>Observations</th><th>Signalées</th></tr></thead><tbody>${counts}</tbody></table>
${wearable}
<h2>Chronologie</h2>${days || "<p>Aucune observation sur la période.</p>"}
<p class="muted" style="margin-top:28px">Chaque ligne renvoie à l'identifiant de l'observation d'origine ou aux mesures du bracelet. Généré par Karis (version de démonstration).</p>
</body></html>`;
}

export function downloadTextFile(filename: string, content: string, mime = "text/html;charset=utf-8") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
