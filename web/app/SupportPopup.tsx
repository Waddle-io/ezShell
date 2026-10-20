"use client";

import { useEffect, useState } from "react";

const GITHUB_URL = "https://github.com/Waddle-io/ezShell";
const STORAGE_KEY = "ezshell:support-popup-dismissed";
const DELAY_MS = 8000;

function StarIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor">
      <path d="M10 1.8l2.4 5 5.4.7-4 3.8 1 5.4L10 14.1l-4.8 2.6 1-5.4-4-3.8 5.4-.7L10 1.8z" />
    </svg>
  );
}

export default function SupportPopup() {
  const [open, setOpen] = useState(false);

  // Affiche le message après quelques secondes, une seule fois par visiteur.
  useEffect(() => {
    try {
      if (window.localStorage.getItem(STORAGE_KEY)) return;
    } catch {
      /* stockage indisponible : on affiche quand même */
    }
    const timer = window.setTimeout(() => setOpen(true), DELAY_MS);
    return () => window.clearTimeout(timer);
  }, []);

  function dismiss() {
    setOpen(false);
    try {
      window.localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      /* ignoré */
    }
  }

  // Échap ferme le message.
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") dismiss();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  if (!open) return null;

  return (
    <aside className="support-popup" role="dialog" aria-modal="false" aria-labelledby="support-title">
      <button className="support-close" type="button" onClick={dismiss} aria-label="Fermer">
        <svg aria-hidden="true" viewBox="0 0 20 20" fill="none">
          <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      </button>
      <p className="eyebrow">merci</p>
      <h2 id="support-title">Un petit coup de pouce ?</h2>
      <p className="support-text">
        ezShell est un projet open source, fait avec passion par la Waddle Team. Si l'outil te fait gagner du
        temps, une étoile sur GitHub nous encourage énormément et aide d'autres développeurs à le découvrir.
        Merci pour ton soutien !
      </p>
      <div className="support-actions">
        <a className="button-link" href={GITHUB_URL} target="_blank" rel="noreferrer" onClick={dismiss}>
          <StarIcon /> Mettre une étoile
        </a>
        <button className="text-link support-later" type="button" onClick={dismiss}>
          Plus tard
        </button>
      </div>
    </aside>
  );
}