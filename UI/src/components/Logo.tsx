/** Karis mark: two leaves sheltering a point, drawn as a single calm shape. */
export function LogoMark({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden focusable="false">
      <rect width="32" height="32" rx="10" fill="#23483C" />
      <path d="M16 24.5c-4.6-1.3-7.5-5-7.5-9.6 0-1.4.3-2.8.8-4 3.9.7 6.7 3.9 6.7 8.1v5.5Z" fill="#E7EEE6" />
      <path d="M16 24.5c4.6-1.3 7.5-5 7.5-9.6 0-1.4-.3-2.8-.8-4-3.9.7-6.7 3.9-6.7 8.1v5.5Z" fill="#769783" />
      <circle cx="16" cy="9.2" r="2.1" fill="#C88770" />
    </svg>
  );
}

export function Logo() {
  return (
    <span className="logo">
      <LogoMark />
      <span className="logo-word">Karis</span>
    </span>
  );
}
