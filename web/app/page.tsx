import type { Metadata } from "next";
import CopyButton from "./CopyButton";

const INSTALL_COMMAND = "pipx install git+https://github.com/Waddle-io/ezShell.git";
const GITHUB_URL = "https://github.com/Waddle-io/ezShell";

export const metadata: Metadata = {
  title: "ezShell | Ton terminal t'explique ses erreurs",
  description: "ezShell explique les erreurs de ton terminal et propose une commande à relire avant insertion.",
  openGraph: {
    title: "ezShell | Ton terminal t'explique ses erreurs",
    description: "Un assistant de terminal direct, prudent et lisible.",
    type: "website",
    locale: "fr_FR",
  },
  themeColor: "#111315",
};

function ArrowIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" fill="none">
      <path d="M4 10h11m-4-4 4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" fill="none">
      <path d="m4 10 4 4 8-8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
      <path d="M12 3 19 6v5c0 4.5-2.8 8-7 10-4.2-2-7-5.5-7-10V6l7-3Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="m8.5 12 2.2 2.2 4.8-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function TerminalIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
      <rect x="3" y="4" width="18" height="16" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="m7 9 3 3-3 3m5 0h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const securityCards = [
  ["Aucune clé sur ta machine", "Les secrets restent masqués avant l'envoi au modèle.", "shield"],
  ["Tu gardes la main", "La commande est insérée dans ton prompt, jamais exécutée sans toi.", "terminal"],
  ["Un risque lisible", "Chaque suggestion porte un niveau: faible, moyen ou élevé.", "check"],
  ["Pas de stockage", "Le service ne stocke ni tes commandes ni tes messages d'erreur.", "shield"],
] as const;

export default function Home() {
  return (
    <>
      <a className="skip-link" href="#contenu">Aller au contenu</a>
      <header className="site-header">
        <div className="shell header-inner">
          <a className="brand" href="#top" aria-label="ezShell, accueil">
            <span className="brand-mark">&gt;_</span>
            <span>ezShell</span>
          </a>
          <nav aria-label="Navigation principale">
            <a href="#fonctionnement">Fonctionnement</a>
            <a href="#securite">Sécurité</a>
            <a href="#installation">Installation</a>
            <a className="nav-github" href={GITHUB_URL} target="_blank" rel="noreferrer">
              GitHub <ArrowIcon />
            </a>
          </nav>
        </div>
      </header>

      <main id="contenu">
        <section className="hero shell" id="top">
          <div className="hero-copy">
            <p className="eyebrow"><span className="status-dot" /> assistant terminal pour bash, zsh et fish</p>
            <h1>Ton terminal t'explique ses erreurs<span className="accent">.</span></h1>
            <p className="hero-lede">Une commande échoue. Tu comprends pourquoi. Tu relis la correction. C'est toi qui valides.</p>
            <div className="install-box" aria-label="Commande d'installation">
              <code><span className="prompt">$</span> {INSTALL_COMMAND}</code>
              <CopyButton value={INSTALL_COMMAND} />
            </div>
            <div className="hero-links">
              <a className="text-link" href={GITHUB_URL} target="_blank" rel="noreferrer">Voir le projet sur GitHub <ArrowIcon /></a>
              <span className="platform-note">Linux · macOS</span>
            </div>
          </div>
          <div className="hero-aside" aria-label="Aperçu d'une suggestion ezShell">
            <div className="signal-line"><span /> <span /> <span /></div>
            <p className="aside-label">dernière erreur détectée</p>
            <code className="aside-command">git push origin main</code>
            <p className="aside-error">fatal: la branche n'a pas de branche amont</p>
            <div className="aside-footer"><span className="mini-check">✓</span> correction prête à relire <span>Alt+E</span></div>
          </div>
        </section>

        <section className="demo-section shell" aria-labelledby="demo-title">
          <div className="section-intro">
            <p className="eyebrow">dans ton terminal</p>
            <h2 id="demo-title">Une erreur devient une prochaine étape.</h2>
          </div>
          <div className="terminal-window">
            <div className="window-bar"><span className="window-dots"><i /><i /><i /></span><span>~/projet · zsh</span><span className="window-key">Alt+E</span></div>
            <div className="terminal-body">
              <div><span className="terminal-prompt">➜</span> <span className="terminal-path">~/projet</span> git push origin main</div>
              <div className="terminal-dim">fatal: la branche 'main' n'a pas de branche amont</div>
              <div className="terminal-gap" />
              <div><span className="terminal-prompt">➜</span> <span className="terminal-path">~/projet</span> <span className="cursor">▌</span></div>
              <div className="suggestion-panel">
                <div className="panel-heading"><span>ezShell</span><span className="risk-low">RISQUE FAIBLE</span></div>
                <p className="panel-cause">La branche locale n'est pas encore reliée à une branche distante.</p>
                <div className="panel-command"><span>$</span> git push --set-upstream origin main</div>
                <div className="panel-hint"><kbd>Entrée</kbd> insérer <span>·</span> <kbd>e</kbd> modifier <span>·</span> <kbd>q</kbd> fermer</div>
              </div>
            </div>
          </div>
        </section>

        <section className="steps-section shell" id="fonctionnement" aria-labelledby="steps-title">
          <div className="section-intro narrow"><p className="eyebrow">le principe</p><h2 id="steps-title">Trois gestes, zéro devinette.</h2></div>
          <div className="steps-grid">
            <article className="step"><span className="step-number">01</span><h3>Une commande échoue</h3><p>ezShell repère la dernière erreur et garde le contexte utile.</p></article>
            <article className="step"><span className="step-number">02</span><h3>Tu appuies sur Alt+E</h3><p>Le panneau te montre une explication et une commande proposée.</p></article>
            <article className="step"><span className="step-number">03</span><h3>Tu relis, puis Entrée</h3><p>La commande arrive dans ton prompt. Tu décides de l'exécuter.</p></article>
          </div>
        </section>

        <section className="security-section shell" id="securite" aria-labelledby="security-title">
          <div className="section-intro narrow"><p className="eyebrow">conçu pour rester prudent</p><h2 id="security-title">Tes commandes restent à toi.</h2></div>
          <div className="security-grid">
            {securityCards.map(([title, text, icon]) => (
              <article className="security-card" key={title}>
                <span className="card-icon">{icon === "terminal" ? <TerminalIcon /> : icon === "check" ? <CheckIcon /> : <ShieldIcon />}</span>
                <h3>{title}</h3><p>{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="install-section shell" id="installation" aria-labelledby="install-title">
          <div className="install-copy"><p className="eyebrow">prêt quand tu l'es</p><h2 id="install-title">Installe-le dans ton shell.</h2><p>Linux et macOS sont pris en charge. Windows pas encore.</p></div>
          <div className="shell-commands">
            <div><span className="shell-label">bash</span><code>eval "$(ezsh init bash)"</code></div>
            <div><span className="shell-label">zsh</span><code>eval "$(ezsh init zsh)"</code></div>
            <div><span className="shell-label">fish</span><code>ezsh init fish | source</code></div>
          </div>
        </section>

        <section className="faq-section shell" aria-labelledby="faq-title">
          <div className="section-intro narrow"><p className="eyebrow">questions rapides</p><h2 id="faq-title">Avant de commencer.</h2></div>
          <div className="faq-list">
            <details><summary>Est-ce qu'ezShell exécute les corrections ?</summary><p>Non. La commande est insérée dans ton prompt; tu appuies toi-même sur Entrée.</p></details>
            <details><summary>Quels shells sont pris en charge ?</summary><p>Bash, zsh et fish, sur Linux et macOS.</p></details>
            <details><summary>Que devient mon mot de passe dans une erreur ?</summary><p>Les secrets sont masqués avant tout envoi au modèle.</p></details>
            <details><summary>Le service conserve-t-il mes commandes ?</summary><p>Non, le service ne stocke ni tes commandes ni tes messages d'erreur.</p></details>
          </div>
        </section>
      </main>

      <footer className="site-footer"><div className="shell footer-inner"><span>ezShell · ton terminal, en clair.</span><div><a href={GITHUB_URL} target="_blank" rel="noreferrer">GitHub</a><a href={`${GITHUB_URL}/blob/main/LICENSE`} target="_blank" rel="noreferrer">Licence MIT</a></div></div></footer>
    </>
  );
}
