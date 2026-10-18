import type { Metadata, Viewport } from "next";
import CopyButton from "./CopyButton";
import Examples from "./Examples";
import HeroDemo from "./HeroDemo";
import ShellTabs from "./ShellTabs";

const INSTALL_COMMAND = "pipx install git+https://github.com/Waddle-io/ezShell.git";
const GITHUB_URL = "https://github.com/Waddle-io/ezShell";

const SITE_URL = "https://ezshell.vercel.app";
const TITLE = "ezShell terminal, autrement";
const DESCRIPTION =
  "Une commande plante ? Alt+E : ezShell lit l'erreur, explique ce qui s'est passé et glisse une correction dans ton prompt.";
const SHARE_DESCRIPTION =
  "Après une erreur, Alt+E : ezShell explique ce qui s'est passé et glisse une correction dans ton prompt. ";


  export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: TITLE,
  description: DESCRIPTION,
  applicationName: "ezShell",
  alternates: { canonical: "/" },
  robots: { index: true, follow: true },
  openGraph: {
    type: "website",
    url: "/",
    siteName: "ezShell",
    locale: "fr_FR",
    title: "ezShell terminal, autrement",
    description: SHARE_DESCRIPTION,
  },
  twitter: {
    card: "summary_large_image",
    title: "ezShell terminal, autrement",
    description: SHARE_DESCRIPTION,
  },
};

// themeColor ne va plus dans `metadata` depuis Next 14 : il passe par `viewport`.
export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#111315" },
    { media: "(prefers-color-scheme: light)", color: "#f4f5f1" },
  ],
};

function ArrowIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" fill="none">
      <path d="M4 10h11m-4-4 4 4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const FACTS = [
  ["Sans clé API", "essai gratuit, sans compte"],
  ["bash · zsh · fish", "dans ton terminal habituel"],
  ["Linux · macOS", "Windows pas encore"],
  ["Rien n'est exécuté", "la commande arrive dans ton prompt"],
] as const;

const SENT = [
  "ton OS et ton shell",
  "le dossier courant (avec ~ à la place de ton nom)",
  "la dernière commande et son code de sortie",
  "la fin de la sortie d'erreur (4 Ko max), si tu passes par ezsh run",
];

const NEVER = [
  "tes mots de passe, clés API, jetons et clés privées : masqués avant l'envoi, puis une seconde fois sur le serveur",
  "ton historique, tes fichiers, tes variables d'environnement",
  "le contenu de tes requêtes : le service ne garde qu'un jeton d'appareil haché et des compteurs de quota",
];

const FAQ = [
  [
    "Est-ce qu'ezShell exécute les corrections ?",
    "Non. La commande est insérée dans ta ligne de saisie ; c'est toi qui appuies sur Entrée. Les commandes à risque élevé ou sur plusieurs lignes demandent en plus une confirmation explicite (y).",
  ],
  [
    "Faut-il une clé Groq ou OpenAI ?",
    "Non. ezShell passe par son propre service, qui détient la clé. Ton appareil reçoit un jeton anonyme au premier usage, avec un quota quotidien gratuit.",
  ],
  [
    "Et si je pose une question au lieu d'avoir une erreur ?",
    "Tape ta demande dans la ligne de saisie (« trouver les fichiers de plus de 1 Go »), puis Alt+E : ezShell la traduit en commande.",
  ],
  [
    "Comment avoir un diagnostic plus précis ?",
    "Lance la commande via ezsh run -- <commande>. La fin de sa sortie d'erreur est alors gardée (et masquée) pour le diagnostic.",
  ],
  [
    "Comment le désinstaller ?",
    "Retire la ligne ezsh init de ton fichier de configuration du shell, puis pipx uninstall ezshell.",
  ],
] as const;

export default function Home() {
  return (
    <>
      <a className="skip-link" href="#contenu">Aller au contenu</a>
      <header className="site-header">
        <div className="shell header-inner">
          <a className="brand" href="#top" aria-label="ezShell, accueil">
            <img src="/assets/logos/ezshell-horizontal-original-bg.png" alt="ezShell" />
          </a>
          <nav aria-label="Navigation principale">
            <a href="#exemples">Exemples</a>
            <a href="#confidentialite">Confidentialité</a>
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
            <h1>Ton terminal t'explique ses erreurs<span className="accent">.</span></h1>
            <p className="hero-lede">
              Une commande échoue ? Appuie sur <kbd>Alt</kbd>+<kbd>E</kbd>. ezShell explique la cause et place une
              correction dans ton prompt. Tu relis, tu valides.
            </p>
            <div className="install-box" aria-label="Commande d'installation">
              <code><span className="prompt">$</span> {INSTALL_COMMAND}</code>
              <CopyButton value={INSTALL_COMMAND} label="Copier la commande d'installation" />
            </div>
            <div className="hero-links">
              <a className="button-link" href="#installation">Installer en 2 minutes <ArrowIcon /></a>
              <a className="text-link" href={GITHUB_URL} target="_blank" rel="noreferrer">Code source sur GitHub</a>
            </div>
          </div>
          <HeroDemo />
        </section>

        <section className="facts shell" aria-label="En bref">
          {FACTS.map(([title, text]) => (
            <div className="fact" key={title}>
              <strong>{title}</strong>
              <span>{text}</span>
            </div>
          ))}
        </section>

        <section className="section shell" id="exemples" aria-labelledby="examples-title">
          <div className="section-intro">
            <p className="eyebrow">exemples</p>
            <h2 id="examples-title">Une erreur devient une prochaine étape.</h2>
            <p className="section-lede">
              Chaque réponse donne la cause, une commande et son niveau de risque. Les règles d'ezShell
              relèvent ce niveau si le modèle le sous-estime.
            </p>
          </div>
          <Examples />
        </section>

        <section className="section shell" id="fonctionnement" aria-labelledby="steps-title">
          <div className="section-intro">
            <p className="eyebrow">le principe</p>
            <h2 id="steps-title">Trois gestes, zéro copier-coller.</h2>
          </div>
          <ol className="steps-grid">
            <li className="step">
              <span className="step-number">01</span>
              <h3>Une commande échoue</h3>
              <p>Le hook d'ezShell note la commande et son code de sortie. Rien n'est envoyé à ce moment-là.</p>
            </li>
            <li className="step">
              <span className="step-number">02</span>
              <h3>Tu appuies sur <kbd>Alt</kbd>+<kbd>E</kbd></h3>
              <p>Un panneau s'ouvre dans le terminal : la cause, la commande proposée, son risque.</p>
            </li>
            <li className="step">
              <span className="step-number">03</span>
              <h3>Tu relis, puis Entrée</h3>
              <p>La commande arrive dans ton prompt. Tu peux la modifier, la copier ou fermer.</p>
            </li>
          </ol>
        </section>

        <section className="section shell" id="confidentialite" aria-labelledby="privacy-title">
          <div className="section-intro">
            <p className="eyebrow">confidentialité</p>
            <h2 id="privacy-title">Ce qui part, ce qui reste chez toi.</h2>
          </div>
          <div className="privacy-grid">
            <div className="privacy-col">
              <h3><span className="pill pill-sent">envoyé</span> seulement quand tu appuies sur Alt+E</h3>
              <ul>{SENT.map((s) => <li key={s}>{s}</li>)}</ul>
            </div>
            <div className="privacy-col">
              <h3><span className="pill pill-never">jamais</span> envoyé ni conservé</h3>
              <ul>{NEVER.map((s) => <li key={s}>{s}</li>)}</ul>
            </div>
          </div>
        </section>

        <section className="section install-section shell" id="installation" aria-labelledby="install-title">
          <div className="section-intro">
            <p className="eyebrow">installation</p>
            <h2 id="install-title">Prêt en deux commandes.</h2>
            <p className="section-lede">Python 3.10 ou plus récent. <a href="https://pipx.pypa.io/stable/" target="_blank" rel="noreferrer">pipx</a> l'isole du reste de ton système.</p>
          </div>
          <div className="install-steps">
            <div className="install-step">
              <span className="step-number">1 · installer</span>
              <div className="code-line">
                <code>{INSTALL_COMMAND}</code>
                <CopyButton value={INSTALL_COMMAND} label="Copier la commande d'installation" compact />
              </div>
            </div>
            <div className="install-step">
              <span className="step-number">2 · brancher sur ton shell</span>
              <ShellTabs />
            </div>
            <div className="install-step">
              <span className="step-number">3 · essayer</span>
              <p className="rc-hint">Lance une commande qui échoue (<code>git psuh</code>, par exemple), puis <kbd>Alt</kbd>+<kbd>E</kbd>.</p>
            </div>
          </div>
        </section>

        <section className="section shell" aria-labelledby="faq-title">
          <div className="section-intro">
            <p className="eyebrow">questions</p>
            <h2 id="faq-title">Avant de commencer.</h2>
          </div>
          <div className="faq-list">
            {FAQ.map(([q, a]) => (
              <details key={q}><summary>{q}</summary><p>{a}</p></details>
            ))}
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="shell footer-inner">
          <div className="footer-credits">
            <span>Made by <a href="https://github.com/Waddle-io" target="_blank" rel="noreferrer">Waddle Team</a></span>
            <span>
              © {new Date().getFullYear()} Waddle Team ·{" "}
              <a href={`${GITHUB_URL}/blob/main/LICENSE`} target="_blank" rel="noreferrer">Licence MIT</a>
            </span>
          </div>
          <div>
            <a href={GITHUB_URL} target="_blank" rel="noreferrer">GitHub</a>
            <a href={`${GITHUB_URL}/issues`} target="_blank" rel="noreferrer">Signaler un problème</a>
            <a href="/api/v1/health">État du service</a>
          </div>
        </div>
      </footer>
    </>
  );
}
