import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "@fontsource-variable/manrope";
import "./globals.css";
import { StoreProvider } from "@/state/store";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: "Karis — veille sur ceux qui veillent",
  description: "Karis aide les aidants à consigner les faits du quotidien et à informer les bonnes personnes. Version de démonstration.",
  applicationName: "Karis",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#F8F7F2",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <StoreProvider>
          <AppShell>{children}</AppShell>
        </StoreProvider>
      </body>
    </html>
  );
}
