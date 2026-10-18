"use client";

import { useState } from "react";
import CopyButton from "./CopyButton";

const SHELLS = [
  { id: "zsh", rc: "~/.zshrc", line: 'eval "$(ezsh init zsh)"' },
  { id: "bash", rc: "~/.bashrc", line: 'eval "$(ezsh init bash)"' },
  { id: "fish", rc: "~/.config/fish/config.fish", line: "ezsh init fish | source" },
  { id: "powershell", rc: "$PROFILE", line: "Invoke-Expression (& ezsh init powershell | Out-String)" },
] as const;

type ShellId = (typeof SHELLS)[number]["id"];

export default function ShellTabs() {
  const [active, setActive] = useState<ShellId>("zsh");

  const shell = SHELLS.find((s) => s.id === active) ?? SHELLS[0];

  return (
    <div className="shell-tabs">
      <div className="tabs" role="tablist" aria-label="Choisis ton shell">
        {SHELLS.map((s) => (
          <button
            key={s.id}
            role="tab"
            type="button"
            aria-selected={s.id === active}
            className={s.id === active ? "tab active" : "tab"}
            onClick={() => setActive(s.id)}
          >
            {s.id}
          </button>
        ))}
      </div>
      <p className="rc-hint">Ajoute cette ligne à la fin de <code>{shell.rc}</code>, puis ouvre un nouveau terminal :</p>
      <div className="code-line">
        <code>{shell.line}</code>
        <CopyButton value={shell.line} label={`Copier la ligne pour ${shell.id}`} compact />
      </div>
      <p className="rc-hint subtle">
        Ou laisse ezShell le faire : <code>ezsh init --install</code> (bash, zsh et PowerShell).
      </p>
    </div>
  );
}
