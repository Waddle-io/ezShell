"use client";

import { useEffect, useState } from "react";

const COMMAND = "git push origin main";
const ERROR = "fatal: The current branch main has no upstream branch.";
const FIX = "git push --set-upstream origin main";

// 0 tape la commande · 1 erreur · 2 Alt+E · 3 panneau · 4 commande insérée dans le prompt
const DURATIONS = [1900, 1100, 700, 2600, 2600];

export default function HeroDemo() {
  const [phase, setPhase] = useState(4);
  const [typed, setTyped] = useState(COMMAND.length);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    setPhase(0);
    setTyped(0);
  }, []);

  useEffect(() => {
    if (phase === 0 && typed < COMMAND.length) {
      const id = window.setTimeout(() => setTyped((n) => n + 1), 55);
      return () => window.clearTimeout(id);
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const id = window.setTimeout(() => {
      const next = (phase + 1) % DURATIONS.length;
      if (next === 0) setTyped(0);
      setPhase(next);
    }, DURATIONS[phase]);
    return () => window.clearTimeout(id);
  }, [phase, typed]);

  const showError = phase >= 1;
  const showPanel = phase === 2 || phase === 3;

  return (
    <div className="demo-window" role="img" aria-label="Démonstration : git push échoue, Alt+E propose git push --set-upstream origin main, la commande est insérée dans le prompt.">
      <div className="window-bar">
        <span className="window-dots"><i /><i /><i /></span>
        <span>~/projet · zsh</span>
        <span className={phase === 2 ? "window-key pressed" : "window-key"}>Alt+E</span>
      </div>
      <div className="demo-body" aria-hidden="true">
        <div className="line">
          <span className="t-prompt">➜</span> <span className="t-path">~/projet</span>{" "}
          {COMMAND.slice(0, typed)}
          {phase === 0 && <span className="cursor">▌</span>}
        </div>
        <div className={showError ? "line t-error reveal" : "line t-error hidden"}>{ERROR}</div>
        <div className={showError ? "line reveal" : "line hidden"}>
          <span className="t-prompt">➜</span> <span className="t-path">~/projet</span>{" "}
          {phase === 4 ? <span className="t-inserted">{FIX}</span> : null}
          {phase !== 0 && <span className="cursor">▌</span>}
        </div>

        <div className={showPanel ? "panel reveal" : "panel hidden"}>
          <div className="panel-head">
            <span>ezShell</span>
            <span className="risk risk-low">risque faible</span>
          </div>
          <p className="panel-cause">
            La branche locale n'est reliée à aucune branche distante : git ne sait pas où pousser.
          </p>
          <div className="panel-command"><span>$</span> {FIX}</div>
          <div className="panel-keys">
            <kbd>Entrée</kbd> insérer <kbd>e</kbd> modifier <kbd>c</kbd> copier <kbd>q</kbd> fermer
          </div>
        </div>

        <p className={phase === 4 ? "demo-note reveal" : "demo-note hidden"}>
          Insérée dans ton prompt. Rien n'est exécuté tant que tu n'appuies pas sur Entrée.
        </p>
      </div>
    </div>
  );
}
