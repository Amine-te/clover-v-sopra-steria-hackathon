"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Journal } from "@/lib/api";
import { humanError, rememberMetadata } from "@/lib/demo";
import { ArrowLeft } from "lucide-react";

export default function ClarifyPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [entry, setEntry] = useState<Journal | null>(null);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    api<Journal>(`/journal/${params.id}`).then(setEntry).catch((err) => setError(humanError(err)));
  }, [params.id]);
  const questions = entry?.clarifications ?? [];
  const current = questions[index];
  async function continueFlow() {
    if (!current || !answer.trim()) return;
    const collected = { ...answers, [current.id]: answer };
    setAnswers(collected);
    if (index < questions.length - 1) {
      setIndex(index + 1); setAnswer(""); return;
    }
    setLoading(true); setError("");
    try {
      const updated = await api<Journal>(`/journal/${params.id}/clarifications`, {
        method: "POST",
        body: JSON.stringify({
          answers: questions.map((question) => ({
            clarification_id: question.id,
            answer: collected[question.id] ?? question.answer ?? "",
          })),
        }),
      });
      rememberMetadata(params.id, updated.provider_metadata);
      router.push(updated.clarification_needed ? `/journal/${params.id}/clarify` : `/journal/${params.id}/review`);
    } catch (err) { setError(err instanceof Error ? err.message : "Précisions impossibles."); setLoading(false); }
  }
  return <main className="page-shell">
    <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-semibold text-teal"><ArrowLeft size={16} /> Accueil</Link>
    <div key={current?.id ?? "loading"} className="flow-enter mt-12"><p className="eyebrow">Une petite précision</p><p className="mt-3 text-sm text-navy-soft">{questions.length ? `${index + 1} sur ${questions.length}` : "Préparation des questions…"}</p><div className="mt-4 flex gap-2" aria-hidden="true">{questions.map((question, position) => <span key={question.id} className={`h-1 flex-1 rounded-full ${position <= index ? "bg-teal" : "bg-sand"}`} />)}</div><h1 className="page-title">{current?.question}</h1><p className="mt-4 text-sm leading-relaxed text-navy-soft">{current?.reason}</p>
      <div className="mt-8 grid gap-3 sm:grid-cols-3">{["Oui", "Non", "Je ne sais pas"].map((value) => <button key={value} onClick={() => setAnswer(value)} className={`rounded-2xl px-4 py-3 font-semibold ring-1 ring-sand ${answer === value ? "bg-teal text-ivory" : "bg-white"}`}>{value}</button>)}</div>
      <label htmlFor="free-answer" className="sr-only">Réponse libre facultative</label><input id="free-answer" value={["Oui", "Non", "Je ne sais pas"].includes(answer) ? "" : answer} onChange={(event) => setAnswer(event.target.value)} placeholder="Ou écrivez une réponse" className="field mt-4" />
      <button onClick={continueFlow} disabled={loading || !answer.trim()} className="mt-8 w-full rounded-2xl bg-teal px-6 py-4 font-semibold text-ivory disabled:opacity-50">{loading ? "Karis réfléchit…" : "Continuer"}</button>{error && <p className="mt-4 text-sm text-coral">{error}</p>}
    </div>
  </main>;
}
