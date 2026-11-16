"use client";

import { useEffect, useState, useRef } from "react";

type Scenario = {
  id: string;
  tabLabel: string;
  cwd: string;
  command: string;
  error: string;
  cause: string;
  fix: string;
  risk: "low" | "medium" | "high";
  riskLabel: string;
};

const SCENARIOS: Scenario[] = [
  {
    id: "git",
    tabLabel: "git push",
    cwd: "~/waddle/ezShell",
    command: "git push origin main",
    error: "fatal: The current branch main has no upstream branch.",
    cause: "La branche locale n'est reliée à aucune branche distante : git ignore où pousser.",
    fix: "git push --set-upstream origin main",
    risk: "low",
    riskLabel: "Risque faible",
  },
  {
    id: "docker",
    tabLabel: "docker port",
    cwd: "~/services/api",
    command: "docker run -p 8080:80 nginx",
    error: "Error response from daemon: driver failed: port 0.0.0.0:8080 is already allocated.",
    cause: "Un autre service écoute déjà sur le port 8080 de ta machine.",
    fix: "docker ps --filter publish=8080",
    risk: "low",
    riskLabel: "Risque faible",
  },
  {
    id: "npm",
    tabLabel: "port occupé",
    cwd: "~/frontend/web",
    command: "npm run dev",
    error: "Error: listen EADDRINUSE: address already in use :::3000",
    cause: "Un processus Node orphelin occupe déjà le port 3000.",
    fix: "lsof -ti:3000 | xargs kill -9",
    risk: "medium",
    riskLabel: "Risque moyen",
  },
];

// Phases :
// 0: Frappe de la commande initiale
// 1: Exécution & apparition de l'erreur
// 2: Déclenchement de Alt+E (badge en surbrillance)
// 3: Déroulement du panneau de diagnostic avec solution
// 4: Insertion de la commande dans le prompt terminal
const PHASE_DURATIONS = [1800, 1000, 600, 2400, 2600];

export default function HeroDemo() {
  const [scenarioIndex, setScenarioIndex] = useState(0);
  const [phase, setPhase] = useState(0);
  const [typedChars, setTypedChars] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const timerRef = useRef<number | null>(null);

  const scenario = SCENARIOS[scenarioIndex];

  // Réinitialisation lors du changement de scénario
  function selectScenario(index: number) {
    if (timerRef.current) clearTimeout(timerRef.current);
    setScenarioIndex(index);
    setPhase(0);
    setTypedChars(0);
  }

  // Boucle de frappe (Phase 0)
  useEffect(() => {
    if (isPaused) return;
    if (phase === 0) {
      if (typedChars < scenario.command.length) {
        timerRef.current = window.setTimeout(() => {
          setTypedChars((prev) => prev + 1);
        }, 45);
        return () => {
          if (timerRef.current) clearTimeout(timerRef.current);
        };
      } else {
        // Commande terminée, passe à la phase 1 (erreur)
        timerRef.current = window.setTimeout(() => {
          setPhase(1);
        }, 500);
        return () => {
          if (timerRef.current) clearTimeout(timerRef.current);
        };
      }
    }

    // Gestion des phases 1 à 4
    timerRef.current = window.setTimeout(() => {
      const nextPhase = (phase + 1) % PHASE_DURATIONS.length;
      if (nextPhase === 0) {
        // Tourne sur le scénario suivant si non mis en pause
        setScenarioIndex((current) => (current + 1) % SCENARIOS.length);
        setTypedChars(0);
      }
      setPhase(nextPhase);
    }, PHASE_DURATIONS[phase]);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [phase, typedChars, scenarioIndex, scenario.command.length, isPaused]);

  const showError = phase >= 1;
  const showTrigger = phase === 2;
  const showPanel = phase === 2 || phase === 3;
  const showInserted = phase === 4;

  return (
    <div
      className="terminal-wrapper"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      role="region"
      aria-label="Démonstration interactive d'ezShell dans le terminal"
    >
      <div className="terminal-glow" />

      <div className="terminal-card">
        {/* En-tête de la fenêtre façon macOS / Hyprland */}
        <div className="terminal-header">
          <div className="terminal-dots">
            <span className="terminal-dot close" />
            <span className="terminal-dot min" />
            <span className="terminal-dot max" />
          </div>

          {/* Sélecteur de scénarios interactif */}
          <div className="terminal-scenarios" role="tablist" aria-label="Scénarios de test">
            {SCENARIOS.map((s, idx) => (
              <button
                key={s.id}
                role="tab"
                aria-selected={idx === scenarioIndex}
                className={`terminal-scenario-tab ${idx === scenarioIndex ? "active" : ""}`}
                onClick={() => selectScenario(idx)}
                type="button"
              >
                {s.tabLabel}
              </button>
            ))}
          </div>

          {/* Raccourci Alt+E avec pulsation au déclenchement */}
          <div className={`terminal-key-badge ${showTrigger ? "active" : ""}`}>
            <span>Alt</span>
            <span>+</span>
            <span>E</span>
          </div>
        </div>

        {/* Corps du terminal */}
        <div className="terminal-body">
          {/* Ligne 1 : Commande initiale */}
          <div className="term-line">
            <span className="term-prompt">❯</span>{" "}
            <span className="term-path">{scenario.cwd}</span>{" "}
            <span>{scenario.command.slice(0, typedChars)}</span>
            {phase === 0 && <span className="term-cursor" />}
          </div>

          {/* Ligne 2 : Message d'erreur du terminal */}
          {showError && (
            <div className="term-line term-error" style={{ marginTop: "6px" }}>
              {scenario.error}
            </div>
          )}

          {/* Panneau contextuel de diagnostic Hyprland ezShell */}
          {showPanel && (
            <div className="diagnostic-panel">
              <div className="diagnostic-panel-head">
                <span className="diagnostic-tag">ezShell · Diagnostic</span>
                <span className={`diagnostic-risk ${scenario.risk}`}>
                  {scenario.riskLabel}
                </span>
              </div>
              <p className="diagnostic-cause">{scenario.cause}</p>
              <div className="diagnostic-cmd-box">
                <code><span style={{ color: "var(--accent)" }}>$</span> {scenario.fix}</code>
              </div>
              <div className="diagnostic-footer-keys">
                <span><kbd>↵</kbd> insérer</span>
                <span><kbd>c</kbd> copier</span>
                <span><kbd>e</kbd> modifier</span>
                <span><kbd>Esc</kbd> fermer</span>
              </div>
            </div>
          )}

          {/* Ligne 3 : Ligne de commande suivante avec correction insérée */}
          {showError && (
            <div className="term-line" style={{ marginTop: "8px" }}>
              <span className="term-prompt">❯</span>{" "}
              <span className="term-path">{scenario.cwd}</span>{" "}
              {showInserted ? (
                <span className="inserted-line">{scenario.fix}</span>
              ) : null}
              {phase !== 0 && <span className="term-cursor" />}
            </div>
          )}

          {/* Note discrète explicative en bas du terminal */}
          <div
            style={{
              position: "absolute",
              bottom: "16px",
              right: "24px",
              fontSize: "11px",
              color: "var(--text-dim)",
              fontFamily: "var(--sans)",
            }}
          >
            {isPaused ? "Démonstration en pause (survol)" : "Survolez pour mettre en pause"}
          </div>
        </div>
      </div>
    </div>
  );
}
