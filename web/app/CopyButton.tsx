"use client";

import { useState } from "react";

type CopyButtonProps = {
  value: string;
  label?: string;
  compact?: boolean;
};

export default function CopyButton({ value, label = "Copier la commande", compact = false }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  async function copyCommand() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <button
      className={compact ? "copy-button compact" : "copy-button"}
      type="button"
      onClick={copyCommand}
      aria-label={label}
    >
      <svg aria-hidden="true" viewBox="0 0 20 20" fill="none">
        {copied ? (
          <path d="m4 10 4 4 8-8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
        ) : (
          <>
            <rect x="6.5" y="6.5" width="9" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
            <path d="M13.5 6.5V5A1.5 1.5 0 0 0 12 3.5H5A1.5 1.5 0 0 0 3.5 5v7A1.5 1.5 0 0 0 5 13.5h1.5" stroke="currentColor" strokeWidth="1.4" />
          </>
        )}
      </svg>
      {!compact && <span aria-live="polite">{copied ? "Copié" : "Copier"}</span>}
    </button>
  );
}
