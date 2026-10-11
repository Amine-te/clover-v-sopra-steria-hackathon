"use client";

import Link from "next/link";
import { ChevronLeft } from "lucide-react";
import type { ReactNode } from "react";

/** Screen title block with optional back link and trailing action. */
export function PageHeader({
  title,
  subtitle,
  back,
  action,
  eyebrow,
}: {
  title: string;
  subtitle?: ReactNode;
  back?: { href: string; label: string };
  action?: ReactNode;
  eyebrow?: string;
}) {
  return (
    <header className="page-header">
      <div className="page-header-bar">
        {back ? (
          <Link href={back.href} className="back-link">
            <ChevronLeft size={20} strokeWidth={1.75} aria-hidden />
            <span>{back.label}</span>
          </Link>
        ) : (
          <span />
        )}
        {action}
      </div>
      {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
      <h1>{title}</h1>
      {subtitle ? <p className="page-subtitle">{subtitle}</p> : null}
    </header>
  );
}
