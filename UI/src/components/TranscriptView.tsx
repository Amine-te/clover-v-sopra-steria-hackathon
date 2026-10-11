import type { ReactNode } from "react";

type Kind = "fact" | "private" | "guard";

/**
 * Shows the transcript with the passages each fact came from highlighted
 * (traceability), the private passages and the passages set aside by the
 * guardrail.
 */
export function TranscriptView({ text, facts, privates, guarded }: { text: string; facts: string[]; privates: string[]; guarded: string[] }) {
  const ranges: { start: number; end: number; kind: Kind }[] = [];
  const add = (span: string, kind: Kind) => {
    if (!span) return;
    const start = text.indexOf(span);
    if (start < 0) return;
    const end = start + span.length;
    if (ranges.some((r) => start < r.end && end > r.start)) return;
    ranges.push({ start, end, kind });
  };
  guarded.forEach((s) => add(s, "guard"));
  privates.forEach((s) => add(s, "private"));
  facts.forEach((s) => add(s, "fact"));
  ranges.sort((a, b) => a.start - b.start);

  const parts: ReactNode[] = [];
  let cursor = 0;
  ranges.forEach((r, i) => {
    if (r.start > cursor) parts.push(text.slice(cursor, r.start));
    const content = text.slice(r.start, r.end);
    const label = r.kind === "fact" ? "Fait relevé" : r.kind === "private" ? "Gardé pour vous" : "Interprétation écartée";
    parts.push(
      <mark key={i} className={r.kind === "fact" ? "" : r.kind}>
        <span className="sr-only">[{label}] </span>
        {content}
      </mark>,
    );
    cursor = r.end;
  });
  if (cursor < text.length) parts.push(text.slice(cursor));

  return (
    <>
      <p className="transcript">{parts}</p>
      <div className="legend" aria-hidden>
        <span>
          <i style={{ background: "var(--sage-pale)" }} /> Fait relevé
        </span>
        <span>
          <i style={{ background: "var(--terracotta-pale)" }} /> Gardé pour vous
        </span>
        <span>
          <i style={{ border: "1px solid var(--terracotta)" }} /> Interprétation écartée
        </span>
      </div>
    </>
  );
}
