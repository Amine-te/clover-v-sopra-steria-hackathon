"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, type User } from "@/lib/api";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { useTechnical } from "@/components/demo-shell";

export default function DemoPage() {
  const router = useRouter();
  const technical = useTechnical();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function enterDemo() {
    setLoading(true);
    try {
      const user = await api<User>("/auth/demo", { method: "POST" });
      localStorage.setItem("karis_demo_user", JSON.stringify(user));
      router.push(`/dashboard${technical ? "?technical=1" : ""}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Impossible d’entrer en mode démo.");
      setLoading(false);
    }
  }
  return <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6">
    <p className="text-sm font-semibold uppercase tracking-[0.2em] text-teal">Karis</p>
    <div className="mt-8 flex h-20 w-20 items-center justify-center rounded-3xl bg-teal/10 text-4xl font-bold text-teal">k<span className="text-coral">.</span></div>
    <h1 className="mt-6 text-4xl font-bold tracking-tight">Un peu de clarté.<br />Un peu de répit.</h1>
    <p className="mt-4 leading-relaxed text-navy-soft">Entrez comme Thomas pour raconter la journée de Marie.</p>
    <button onClick={enterDemo} disabled={loading} className="button-primary mt-8">{loading ? "Ouverture…" : "Entrer comme Thomas"}<ArrowRight size={18} /></button><p className="mt-5 flex items-center gap-2 text-xs leading-relaxed text-navy-soft"><ShieldCheck size={17} className="shrink-0 text-teal" /> Vos mots restent les vôtres. Vous choisissez ce qui est partagé.</p>
    {error && <p className="mt-4 text-sm text-coral">{error}</p>}
  </main>;
}
