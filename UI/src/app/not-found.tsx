"use client";

import { Compass, House } from "lucide-react";
import { EmptyState, LinkButton } from "@/components/ui";

export default function NotFound() {
  return (
    <div style={{ paddingTop: 40 }}>
      <EmptyState
        icon={Compass}
        title="Cette page n'existe pas"
        action={
          <LinkButton href="/" icon={House}>
            Revenir à l&apos;accueil
          </LinkButton>
        }
      >
        Le lien est peut-être incomplet. Tout ce que vous avez noté est toujours là.
      </EmptyState>
    </div>
  );
}
