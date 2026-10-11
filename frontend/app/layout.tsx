import type { Metadata } from "next";
import "./globals.css";
import { Suspense } from "react";
import { DemoShell } from "@/components/demo-shell";

export const metadata: Metadata = {
  title: "Karis",
  description: "Un journal intelligent pour mieux accompagner au quotidien.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr">
      <body className="min-h-dvh antialiased"><Suspense fallback={<div className="page-shell">Ouverture de Karis…</div>}><DemoShell>{children}</DemoShell></Suspense></body>
    </html>
  );
}
