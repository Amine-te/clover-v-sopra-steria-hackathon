"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return <main className="page-shell"><h1 className="page-title">Reprenons tranquillement</h1><p className="mt-5 text-navy-soft">Une erreur est survenue. Les notes déjà enregistrées dans Karis sont conservées.</p><button onClick={reset} className="button-primary mt-6 w-full">Réessayer</button></main>;
}
