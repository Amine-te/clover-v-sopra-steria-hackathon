"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { BellRing, X } from "lucide-react";
import { useStore } from "@/state/store";
import { BottomNav } from "./BottomNav";
import { LogoMark } from "./Logo";

/** Mobile frame: content column, in-app notices, toasts and bottom navigation. */
export function AppShell({ children }: { children: ReactNode }) {
  const { ready, state, dispatch, toasts } = useStore();

  return (
    <div className="app">
      <a className="skip-link" href="#contenu">
        Aller au contenu
      </a>
      {ready ? (
        <>
          {state.notices.length > 0 ? (
            <div className="notice-stack" role="region" aria-label="Notifications">
              {state.notices.slice(0, 1).map((n) => (
                <div key={n.id} className="notice" role="status">
                  <span className="notice-icon" aria-hidden>
                    <BellRing size={18} strokeWidth={1.75} />
                  </span>
                  <Link href="/enregistrer/" className="notice-text" onClick={() => dispatch({ type: "dismissNotice", id: n.id })}>
                    <span className="notice-app">Karis · maintenant</span>
                    <strong>{n.title}</strong>
                    <span>{n.body}</span>
                  </Link>
                  <button type="button" className="icon-btn icon-btn-sm" aria-label="Fermer la notification" onClick={() => dispatch({ type: "dismissNotice", id: n.id })}>
                    <X size={18} strokeWidth={1.75} aria-hidden />
                  </button>
                </div>
              ))}
            </div>
          ) : null}
          <main id="contenu" className="main" tabIndex={-1}>
            {children}
          </main>
          <BottomNav />
        </>
      ) : (
        <div className="splash" role="status" aria-label="Chargement de Karis">
          <LogoMark size={48} />
          <p>Karis veille sur ceux qui veillent.</p>
        </div>
      )}
      <div className="toast-region" aria-live="polite" aria-atomic="false">
        {toasts.map((t) => (
          <div key={t.id} className="toast">
            {t.message}
          </div>
        ))}
      </div>
    </div>
  );
}
