"use client";

import { useState } from "react";

type Risk = "low" | "medium" | "high";

const EXAMPLES: Array<{
  id: string;
  tab: string;
  command: string;
  error: string;
  cause: string;
  fix: string;
  risk: Risk;
  note: string;
}> = [
  {
    id: "docker",
    tab: "Port occupé",
    command: "docker run -p 8080:80 nginx",
    error: "Bind for 0.0.0.0:8080 failed: port is already allocated.",
    cause: "Un autre conteneur écoute déjà sur le port 8080 de ta machine.",
    fix: "docker ps --filter publish=8080",
    risk: "low",
    note: "Commence par identifier le conteneur : ezShell ne propose pas de l'arrêter à l'aveugle.",
  },
  {
    id: "perm",
    tab: "Permission refusée",
    command: "npm install -g typescript",
    error: "EACCES: permission denied, mkdir '/usr/lib/node_modules/typescript'",
    cause: "npm essaie d'écrire dans un dossier système qui appartient à root.",
    fix: "npm config set prefix ~/.npm-global",
    risk: "low",
    note: "Plutôt que sudo, un préfixe dans ton dossier personnel : rien de système n'est modifié.",
  },
  {
    id: "force",
    tab: "Push refusé",
    command: "git push origin feature",
    error: "! [rejected] feature -> feature (non-fast-forward)",
    cause: "Après ton rebase, l'historique local ne suit plus celui du serveur.",
    fix: "git push --force origin feature",
    risk: "high",
    note: "Réécrit l'historique distant : ezShell le classe en risque élevé et exige une confirmation (y).",
  },
];

const RISK_LABEL: Record<Risk, string> = { low: "risque faible", medium: "risque moyen", high: "risque élevé" };

export default function Examples() {
  const [active, setActive] = useState(EXAMPLES[0].id);
  const ex = EXAMPLES.find((e) => e.id === active) ?? EXAMPLES[0];

  return (
    <div className="examples">
      <div className="tabs" role="tablist" aria-label="Exemples d'erreurs">
        {EXAMPLES.map((e) => (
          <button
            key={e.id}
            role="tab"
            type="button"
            id={`tab-${e.id}`}
            aria-selected={e.id === active}
            aria-controls="example-panel"
            className={e.id === active ? "tab active" : "tab"}
            onClick={() => setActive(e.id)}
          >
            <span className={`dot risk-dot-${e.risk}`} />
            {e.tab}
          </button>
        ))}
      </div>
      <div className="example-card" role="tabpanel" id="example-panel" aria-labelledby={`tab-${ex.id}`}>
        <div className="example-terminal">
          <div className="line"><span className="t-prompt">$</span> {ex.command}</div>
          <div className="line t-error">{ex.error}</div>
        </div>
        <div className="example-answer">
          <div className="panel-head">
            <span>Cause</span>
            <span className={`risk risk-${ex.risk}`}>{RISK_LABEL[ex.risk]}</span>
          </div>
          <p className="example-cause">{ex.cause}</p>
          <div className="panel-command"><span>$</span> {ex.fix}</div>
          <p className="example-note">{ex.note}</p>
          <div className="panel-keys">
            {ex.risk === "high" ? (
              <><kbd>y</kbd> insérer quand même <kbd>e</kbd> modifier <kbd>q</kbd> fermer</>
            ) : (
              <><kbd>Entrée</kbd> insérer <kbd>e</kbd> modifier <kbd>q</kbd> fermer</>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
