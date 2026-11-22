"use client";

import { useState } from "react";
import CopyButton from "./CopyButton";

type ExampleItem = {
  id: string;
  tabLabel: string;
  command: string;
  error: string;
  cause: string;
  fix: string;
  risk: "low" | "medium" | "high";
  riskLabel: string;
  note: string;
};

const EXAMPLES: ExampleItem[] = [
  {
    id: "docker",
    tabLabel: "Port alloué",
    command: "docker run -p 8080:80 nginx",
    error: "docker: Error response from daemon: driver failed programming external connectivity on endpoint: Bind for 0.0.0.0:8080 failed: port is already allocated.",
    cause: "Un autre processus ou conteneur local est déjà en écoute sur le port 8080.",
    fix: "docker ps --filter publish=8080",
    risk: "low",
    riskLabel: "Risque faible",
    note: "ezShell cible le conteneur en conflit plutôt que de forcer un kill aveugle.",
  },
  {
    id: "perm",
    tabLabel: "Permission refusée",
    command: "npm install -g typescript",
    error: "npm ERR! code EACCES\nnpm ERR! syscall mkdir\nnpm ERR! path /usr/lib/node_modules/typescript\nnpm ERR! errno -13\nnpm ERR! Error: EACCES: permission denied",
    cause: "npm essaie d'écrire dans un répertoire système appartenant à root.",
    fix: "npm config set prefix ~/.npm-global",
    risk: "low",
    riskLabel: "Risque faible",
    note: "Configure un préfixe dans ton dossier utilisateur sans jamais polluer le système avec sudo.",
  },
  {
    id: "git",
    tabLabel: "Push rejeté (force)",
    command: "git push origin main",
    error: "To origin:mon-projet.git\n ! [rejected]        main -> main (non-fast-forward)\nerror: failed to push some refs to 'origin:mon-projet.git'",
    cause: "L'historique distant a divergé suite à un rebase local.",
    fix: "git push --force-with-lease origin main",
    risk: "medium",
    riskLabel: "Risque moyen",
    note: "--force-with-lease protège les commits distants créés par d'autres collègues.",
  },
  {
    id: "python",
    tabLabel: "Module introuvable",
    command: "python3 app.py",
    error: "ModuleNotFoundError: No module named 'fastapi'\nTraceback (most recent call last):\n  File \"/home/user/app.py\", line 1, in <module>",
    cause: "La dépendance fastapi n'est pas installée dans l'environnement virtuel actif.",
    fix: "pip install fastapi uvicorn",
    risk: "low",
    riskLabel: "Risque faible",
    note: "Détecte automatiquement l'arborescence Python et propose l'installation adéquate.",
  },
];

export default function Examples() {
  const [activeId, setActiveId] = useState(EXAMPLES[0].id);
  const activeEx = EXAMPLES.find((e) => e.id === activeId) ?? EXAMPLES[0];

  return (
    <div className="examples-wrapper">
      {/* Onglets épurés style Vercel */}
      <div className="examples-tabs" role="tablist" aria-label="Cas d'usage concrets">
        {EXAMPLES.map((ex) => (
          <button
            key={ex.id}
            role="tab"
            aria-selected={ex.id === activeId}
            className={`examples-tab ${ex.id === activeId ? "active" : ""}`}
            onClick={() => setActiveId(ex.id)}
            type="button"
          >
            <span>{ex.tabLabel}</span>
          </button>
        ))}
      </div>

      {/* Conteneur terminal split : Erreur à gauche / Diagnostic à droite */}
      <div className="examples-container">
        {/* Volet gauche : Commande et sortie d'erreur brute */}
        <div className="examples-terminal">
          <div style={{ color: "var(--text-dim)", fontSize: "11px", marginBottom: "12px", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Terminal brut
          </div>
          <div className="term-line">
            <span className="term-prompt">❯</span> {activeEx.command}
          </div>
          <div className="term-line term-error" style={{ marginTop: "10px", whiteSpace: "pre-wrap" }}>
            {activeEx.error}
          </div>
        </div>

        {/* Volet droit : Analyse ezShell et commande recommandée */}
        <div className="examples-analysis">
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Diagnostic ezShell
              </span>
              <span className={`diagnostic-risk ${activeEx.risk}`}>
                {activeEx.riskLabel}
              </span>
            </div>

            <p style={{ margin: "0 0 16px", color: "var(--text)", fontSize: "14px", lineHeight: "1.55" }}>
              {activeEx.cause}
            </p>

            <div className="diagnostic-cmd-box" style={{ marginBottom: "12px" }}>
              <code><span style={{ color: "var(--accent)" }}>$</span> {activeEx.fix}</code>
              <CopyButton value={activeEx.fix} compact label="Copier la commande recommandée" />
            </div>

            <p style={{ margin: "0", color: "var(--text-muted)", fontSize: "12.5px", lineHeight: "1.5" }}>
              {activeEx.note}
            </p>
          </div>

          <div style={{ marginTop: "24px", paddingTop: "14px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", gap: "10px", fontSize: "11px", color: "var(--text-dim)" }}>
            <span><kbd>Alt+E</kbd> déclencher</span>
            <span><kbd>↵</kbd> insérer dans le prompt</span>
            <span><kbd>Esc</kbd> annuler</span>
          </div>
        </div>
      </div>
    </div>
  );
}
