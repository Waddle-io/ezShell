"use client";

import CopyButton from "../CopyButton";

const PIPX_COMMANDS = [
  ["Debian / Ubuntu", "sudo apt install pipx && pipx ensurepath"],
  ["macOS (Homebrew)", "brew install pipx && pipx ensurepath"],
  ["Fedora", "sudo dnf install pipx && pipx ensurepath"],
  ["Arch Linux", "sudo pacman -S python-pipx && pipx ensurepath"],
  ["Windows (PowerShell)", "py -m pip install --user pipx; py -m pipx ensurepath"],
] as const;

export default function PipxHelp() {
  return (
    <details style={{ marginTop: "16px", fontSize: "13px", color: "var(--text-muted)" }}>
      <summary style={{ cursor: "pointer", color: "var(--text-dim)", userSelect: "none" }}>
        <span>pipx n'est pas encore installé ?</span>
      </summary>

      <div style={{ marginTop: "12px", padding: "16px", borderRadius: "8px", background: "var(--surface)", border: "1px solid var(--border)" }}>
        <p style={{ margin: "0 0 12px", fontSize: "13px" }}>
          Installez pipx sur votre système en une commande :
        </p>

        <div style={{ display: "grid", gap: "8px" }}>
          {PIPX_COMMANDS.map(([sys, cmd]) => (
            <div key={sys} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", padding: "6px 10px", background: "var(--code)", border: "1px solid var(--border)", borderRadius: "6px" }}>
              <span style={{ fontSize: "12px", color: "var(--text-dim)", minWidth: "140px" }}>{sys}</span>
              <code style={{ fontSize: "12px", color: "var(--code-text)", flex: 1, overflowX: "auto" }}>{cmd}</code>
              <CopyButton value={cmd} compact label={`Copier pour ${sys}`} />
            </div>
          ))}
        </div>
      </div>
    </details>
  );
}
