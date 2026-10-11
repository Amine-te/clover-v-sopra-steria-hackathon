const PILLARS = [
  {
    title: "Journal",
    text: "Notez le quotidien en quelques mots, à l’écrit ou à la voix.",
  },
  {
    title: "Cercle de soin",
    text: "Chaque proche reçoit ce qui le concerne — rien de plus.",
  },
  {
    title: "Bilans",
    text: "Une vue claire de la semaine, pour vous et pour le médecin.",
  },
];

export default function Home() {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-6 pb-10 pt-14 sm:max-w-2xl">
      <header className="flex items-center gap-3">
        <span
          aria-hidden
          className="flex h-10 w-10 items-center justify-center rounded-2xl bg-teal text-lg font-bold text-ivory"
        >
          K
        </span>
        <span className="text-xl font-semibold tracking-tight">Karis</span>
      </header>

      <section className="mt-16 flex flex-1 flex-col">
        <h1 className="text-3xl font-bold leading-tight tracking-tight sm:text-4xl">
          Un journal intelligent pour mieux accompagner au quotidien.
        </h1>
        <p className="mt-4 text-base leading-relaxed text-navy-soft">
          Karis aide les aidants familiaux à noter l’essentiel, à partager la
          bonne information aux bonnes personnes, et à garder le cap.
        </p>

        <div className="mt-8">
          <Link
            href="/demo"
            className="w-full rounded-2xl bg-teal px-6 py-4 text-center text-base font-semibold text-ivory shadow-sm transition hover:bg-teal-dark sm:w-auto"
          >
            Entrer en mode démo
          </Link>
        </div>

        <div className="mt-12 grid gap-4 sm:grid-cols-3">
          {PILLARS.map((pillar) => (
            <div
              key={pillar.title}
              className="rounded-2xl bg-white/70 p-5 shadow-sm ring-1 ring-sand"
            >
              <h2 className="text-sm font-semibold">{pillar.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-navy-soft">
                {pillar.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      <footer className="mt-12 text-center text-xs text-navy-soft">
        Karis — prototype de démonstration
      </footer>
    </main>
  );
}
import Link from "next/link";
