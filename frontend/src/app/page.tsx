import Link from "next/link";
import HealthIndicator from "@/components/HealthIndicator";

export default function Home() {
  return (
    <main>
      <h1>Karis</h1>
      <HealthIndicator />
      <p>
        <Link href="/report-voice">Enregistrer un rapport vocal</Link>
      </p>
      <p>
        <Link href="/timeline">Voir la chronologie</Link>
      </p>
    </main>
  );
}
