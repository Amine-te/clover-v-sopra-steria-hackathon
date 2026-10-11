/** Date helpers, French locale, local time zone of the device. */

const LOCALE = "fr-FR";

export function startOfDay(d: Date): Date {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

export function addDays(d: Date, n: number): Date {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}

export function dayKey(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function isSameDay(a: string | Date, b: string | Date): boolean {
  return dayKey(a) === dayKey(b);
}

/** ISO string with the local offset, e.g. 2026-10-10T08:30:00+02:00 */
export function toLocalIso(d: Date): string {
  const pad = (n: number) => String(Math.abs(n)).padStart(2, "0");
  const off = -d.getTimezoneOffset();
  const sign = off >= 0 ? "+" : "-";
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}` +
    `${sign}${pad(Math.floor(Math.abs(off) / 60))}:${pad(Math.abs(off) % 60)}`
  );
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(LOCALE, { hour: "2-digit", minute: "2-digit" });
}

export function formatDayLong(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return capitalize(d.toLocaleDateString(LOCALE, { weekday: "long", day: "numeric", month: "long" }));
}

export function formatDate(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return d.toLocaleDateString(LOCALE, { day: "numeric", month: "long", year: "numeric" });
}

export function formatDateShort(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return d.toLocaleDateString(LOCALE, { day: "numeric", month: "short" });
}

/** "Aujourd'hui", "Hier" or the long date. */
export function relativeDay(iso: string | Date, now = new Date()): string {
  const k = dayKey(iso);
  if (k === dayKey(now)) return "Aujourd'hui";
  if (k === dayKey(addDays(now, -1))) return "Hier";
  if (k === dayKey(addDays(now, 1))) return "Demain";
  return formatDayLong(iso);
}

export function relativeDateTime(iso: string, now = new Date()): string {
  const rd = relativeDay(iso, now);
  const prefix = rd === "Aujourd'hui" || rd === "Hier" || rd === "Demain" ? rd : formatDateShort(iso);
  return `${prefix} · ${formatTime(iso)}`;
}

export function formatDuration(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

export function formatHoursMinutes(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return m === 0 ? `${h} h` : `${h} h ${String(m).padStart(2, "0")}`;
}

export function greeting(now = new Date()): string {
  const h = now.getHours();
  if (h < 5 || h >= 18) return "Bonsoir";
  return "Bonjour";
}

/** French typography: lowercase after a colon ("Repas : moitié du déjeuner"). */
export function lowerFirst(s: string): string {
  return s.charAt(0).toLowerCase() + s.slice(1);
}

export function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function plural(n: number, one: string, many: string): string {
  return `${n} ${n > 1 ? many : one}`;
}

export function formatNumber(n: number, digits = 0): string {
  return n.toLocaleString(LOCALE, { maximumFractionDigits: digits, minimumFractionDigits: digits });
}
