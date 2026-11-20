"use client";

import CopyButton from "../CopyButton";

export default function FinalCta({ installCommand }: { installCommand: string }) {
  return (
    <section className="section shell" aria-labelledby="cta-title">
      <div className="cta-box">
        <h2 id="cta-title" className="cta-title">
          Reprenez le contrôle de votre terminal.
        </h2>
        <p className="cta-desc">
          L'installation prend 30 secondes. Sans clé d'API obligatoire, sans compte requis et sans télémétrie intrusive.
        </p>

        <div className="cta-actions">
          <div className="command-box">
            <span className="command-box-prompt">$</span>
            <code className="command-box-code">{installCommand}</code>
            <CopyButton value={installCommand} label="Copier la commande" />
          </div>

          <a
            className="btn-secondary"
            href="https://github.com/Waddle-io/ezShell"
            target="_blank"
            rel="noreferrer"
          >
            Explorer sur GitHub
          </a>
        </div>
      </div>
    </section>
  );
}
