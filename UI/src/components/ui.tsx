"use client";

import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { ICON } from "./icons";

/** Small presentational building blocks shared by every screen. */

type Variant = "primary" | "secondary" | "ghost" | "danger" | "soft";

export function Button({
  variant = "primary",
  icon: Icon,
  block,
  size = "md",
  className = "",
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; icon?: LucideIcon; block?: boolean; size?: "md" | "sm" }) {
  return (
    <button
      type="button"
      className={`btn btn-${variant} btn-${size} ${block ? "btn-block" : ""} ${className}`}
      {...rest}
    >
      {Icon ? <Icon size={size === "sm" ? 17 : 19} strokeWidth={ICON.strokeWidth} aria-hidden /> : null}
      <span>{children}</span>
    </button>
  );
}

export function LinkButton({
  href,
  variant = "primary",
  icon: Icon,
  block,
  size = "md",
  children,
  className = "",
}: {
  href: string;
  variant?: Variant;
  icon?: LucideIcon;
  block?: boolean;
  size?: "md" | "sm";
  children: ReactNode;
  className?: string;
}) {
  return (
    <Link href={href} className={`btn btn-${variant} btn-${size} ${block ? "btn-block" : ""} ${className}`}>
      {Icon ? <Icon size={size === "sm" ? 17 : 19} strokeWidth={ICON.strokeWidth} aria-hidden /> : null}
      <span>{children}</span>
    </Link>
  );
}

export function IconButton({
  icon: Icon,
  label,
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { icon: LucideIcon; label: string }) {
  return (
    <button type="button" className={`icon-btn ${className}`} aria-label={label} title={label} {...rest}>
      <Icon size={ICON.size} strokeWidth={ICON.strokeWidth} aria-hidden />
    </button>
  );
}

export function Card({ children, className = "", labelledBy }: { children: ReactNode; className?: string; labelledBy?: string }) {
  return (
    <section className={`card ${className}`} aria-labelledby={labelledBy}>
      {children}
    </section>
  );
}

export function SectionHeader({ title, action, id }: { title: string; action?: ReactNode; id?: string }) {
  return (
    <div className="section-header">
      <h2 id={id}>{title}</h2>
      {action}
    </div>
  );
}

export function Badge({ tone = "neutral", children, icon: Icon }: { tone?: "neutral" | "sage" | "watch" | "urgent" | "forest" | "outline"; children: ReactNode; icon?: LucideIcon }) {
  return (
    <span className={`badge badge-${tone}`}>
      {Icon ? <Icon size={13} strokeWidth={2} aria-hidden /> : null}
      {children}
    </span>
  );
}

export function Chip({
  selected,
  children,
  icon: Icon,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { selected?: boolean; icon?: LucideIcon }) {
  return (
    <button type="button" className={`chip ${selected ? "chip-selected" : ""}`} aria-pressed={selected} {...rest}>
      {Icon ? <Icon size={16} strokeWidth={ICON.strokeWidth} aria-hidden /> : null}
      {children}
    </button>
  );
}

export function Switch({
  checked,
  onChange,
  label,
  description,
  disabled,
  id,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description?: ReactNode;
  disabled?: boolean;
  id: string;
}) {
  return (
    <div className={`switch-row ${disabled ? "is-disabled" : ""}`}>
      <div className="switch-text">
        <label htmlFor={id} className="switch-label">
          {label}
        </label>
        {description ? (
          <p className="switch-desc" id={`${id}-desc`}>
            {description}
          </p>
        ) : null}
      </div>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        aria-describedby={description ? `${id}-desc` : undefined}
        disabled={disabled}
        className={`switch ${checked ? "is-on" : ""}`}
        onClick={() => onChange(!checked)}
      >
        <span className="switch-thumb" aria-hidden />
      </button>
    </div>
  );
}

export function Segmented<T extends string>({
  value,
  onChange,
  options,
  label,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
  label: string;
}) {
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          className={value === o.value ? "is-active" : ""}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, children, action }: { icon: LucideIcon; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty">
      <div className="empty-icon" aria-hidden>
        <Icon size={26} strokeWidth={1.5} />
      </div>
      <h3>{title}</h3>
      {children ? <p>{children}</p> : null}
      {action ? <div className="empty-action">{action}</div> : null}
    </div>
  );
}

export function DemoNote({ children }: { children: ReactNode }) {
  return (
    <p className="demo-note">
      <span className="demo-dot" aria-hidden />
      {children}
    </p>
  );
}

export function Spinner({ label }: { label: string }) {
  return <span className="spinner" role="status" aria-label={label} />;
}
