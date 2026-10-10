import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Karis",
  description: "Karis : suivi factuel pour les aidants",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
