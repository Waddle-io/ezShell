"use client";

import { useState } from "react";
import CopyButton from "./CopyButton";

const SHELLS = [
  { id: "zsh", name: "Zsh", rc: "~/.zshrc", line: 'eval "$(ezsh init zsh)"' },
  { id: "bash", name: "Bash", rc: "~/.bashrc", line: 'eval "$(ezsh init bash)"' },
  { id: "fish", name: "Fish", rc: "~/.config/fish/config.fish", line: "ezsh init fish | source" },
  { id: "powershell", name: "PowerShell", rc: "$PROFILE", line: "Invoke-Expression (& ezsh init powershell | Out-String)" },
] as const;

type ShellId = (typeof SHELLS)[number]["id"];

export default function ShellTabs() {
  const [active, setActive] = useState<ShellId>("zsh");
  const currentShell = SHELLS.find((s) => s.id === active) ?? SHELLS[0];

  return (
    <div className="shell-tabs-wrapper">
      {/* Sélecteur de shell style segmented control */}
      <div className="shell-tabs-nav" role="tablist" aria-label="Choisir le shell cible">
        {SHELLS.map((s) => (
          <button
            key={s.id}
            role="tab"
            aria-selected={s.id === active}
            className={`shell-tab-btn ${s.id === active ? "active" : ""}`}
            onClick={() => setActive(s.id)}
            type="button"
          >
            {s.name}
          </button>
        ))}
      </div>

      <p style={{ margin: "0 0 10px", fontSize: "13px", color: "var(--text-muted)" }}>
        Ajoute cette ligne dans ton fichier <code style={{ color: "#ffffff", padding: "1px 5px", background: "var(--surface-raised)", borderRadius: "4px" }}>{currentShell.rc}</code> :
      </p>

      <div className="install-code-line">
        <code style={{ overflowX: "auto" }}>{currentShell.line}</code>
        <CopyButton value={currentShell.line} compact label={`Copier la commande pour ${currentShell.name}`} />
      </div>

      <p style={{ margin: "10px 0 0", fontSize: "12px", color: "var(--text-dim)" }}>
        Ou exécute l'installation automatique : <code style={{ color: "var(--text-muted)" }}>ezsh init --install</code>
      </p>
    </div>
  );
}
