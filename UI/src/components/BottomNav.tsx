"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarRange, FileText, House, MessagesSquare, Mic } from "lucide-react";
import { useStore } from "@/state/store";
import { ICON } from "./icons";

const ITEMS = [
  { href: "/", label: "Accueil", icon: House },
  { href: "/chronologie/", label: "Frise", icon: CalendarRange },
  { href: "/enregistrer/", label: "Raconter", icon: Mic, primary: true },
  { href: "/coordination/", label: "Échanges", icon: MessagesSquare },
  { href: "/rapport/", label: "Rapport", icon: FileText },
] as const;

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  const base = href.replace(/\/$/, "");
  if (base === "/enregistrer") return pathname.startsWith("/enregistrer") || pathname.startsWith("/analyse");
  return pathname.startsWith(base);
}

export function BottomNav() {
  const pathname = usePathname() ?? "/";
  const { unseenMessages } = useStore();

  return (
    <nav className="bottom-nav" aria-label="Navigation principale">
      <ul>
        {ITEMS.map((item) => {
          const active = isActive(pathname, item.href);
          const Icon = item.icon;
          const isPrimary = "primary" in item && item.primary;
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className={`nav-item ${active ? "is-active" : ""} ${isPrimary ? "nav-primary" : ""}`}
                aria-current={active ? "page" : undefined}
              >
                <span className="nav-icon">
                  <Icon size={isPrimary ? 24 : 22} strokeWidth={ICON.strokeWidth} aria-hidden />
                  {item.href === "/coordination/" && unseenMessages > 0 ? (
                    <span className="nav-dot" aria-label={`${unseenMessages} nouveaux messages`} />
                  ) : null}
                </span>
                <span className="nav-label">{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
