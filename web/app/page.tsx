import type { Metadata, Viewport } from "next";
import CopyButton from "./CopyButton";
import Examples from "./Examples";
import HeroDemo from "./HeroDemo";
import ShellTabs from "./ShellTabs";
import BentoCard from "./BentoCard";
import FaqAccordion from "./FaqAccordion";
import FinalCta from "./_landing/FinalCta";
import PipxHelp from "./_landing/PipxHelp";

const INSTALL_COMMAND = "pipx install ezshell";
const GITHUB_URL = "https://github.com/Waddle-io/ezShell";
const SITE_URL = "https://ezshell.vercel.app";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "ezShell · Ton terminal t'explique ses erreurs",
  description:
    "Assistant terminal intelligent pour développeurs. Diagnostic instantané des erreurs shell, correction insérée directement dans votre prompt sans quitter le terminal. Zéro exécution aveugle.",
  applicationName: "ezShell",
  alternates: { canonical: "/" },
  robots: { index: true, follow: true },
  openGraph: {
    type: "website",
    url: "/",
    siteName: "ezShell",
    locale: "fr_FR",
    title: "ezShell · Ton terminal t'explique ses erreurs",
    description:
      "Une commande plante ? Alt+E : ezShell analyse la cause et glisse la correction directement dans ton prompt.",
  },
  twitter: {
    card: "summary_large_image",
    title: "ezShell · Ton terminal t'explique ses erreurs",
    description:
      "Une commande plante ? Alt+E : ezShell analyse la cause et glisse la correction directement dans ton prompt.",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#000000" },
    { media: "(prefers-color-scheme: light)", color: "#000000" },
  ],
};

function GitHubIcon() {
  return (
    <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
      />
    </svg>
  );
}

const STATS = [
  { value: "< 50ms", label: "Latence d'analyse locale" },
  { value: "0", label: "Secret ou mot de passe exposé" },
  { value: "4 shells", label: "Zsh, Bash, Fish, PowerShell" },
  { value: "100%", label: "Contrôle développeur (manuel)" },
];

const SENT_ITEMS = [
  "L'OS hôte et le shell actif (ex: Linux / zsh)",
  "Le chemin courant relatif (votre nom d'utilisateur est remplacé par ~)",
  "La dernière commande exécutée et son code de sortie",
  "La fin du flux d'erreur (4 Ko max, masqué localement)",
];

const NEVER_ITEMS = [
  "Clés privées, clés SSH, tokens d'API et mots de passe (caviardés avant tout envoi)",
  "L'historique complet de votre terminal et le contenu de vos fichiers",
  "Vos variables d'environnement système et secrets d'infrastructure",
  "Aucun stockage persistant de vos requêtes côté serveur",
];

export default function Home() {
  return (
    <>
      <a className="skip-link" href="#contenu">
        Aller au contenu
      </a>

      {/* Barre de navigation style Vercel */}
      <header className="site-header">
        <div className="shell header-inner">
          <a className="brand" href="#top" aria-label="ezShell, accueil">
            <span className="brand-symbol">❯_</span>
            <span>ezShell</span>
          </a>

          <nav aria-label="Navigation principale">
            <a href="#demonstration">Démonstration</a>
            <a href="#fonctionnalites">Fonctionnalités</a>
            <a href="#exemples">Exemples</a>
            <a href="#installation">Installation</a>
            <a href="#confidentialite">Confidentialité</a>
            <a href="#faq">Questions</a>
          </nav>

          <div className="nav-actions">
            <a
              className="nav-btn-secondary"
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer"
              aria-label="Code source GitHub"
            >
              <GitHubIcon />
              <span>GitHub</span>
            </a>
            <a className="nav-btn-primary" href="/login">
              Se connecter
            </a>
          </div>
        </div>
      </header>

      <main id="contenu">
        {/* Hero Section */}
        <section className="hero-section shell" id="top">
          {/* Titre & Proposition de valeur */}
          <div className="hero-content">
            <h1 className="hero-title">
              Ton terminal t'explique ses erreurs.
              <span className="hero-title-gradient">Sans quitter ton prompt.</span>
            </h1>

            <p className="hero-subtitle">
              Une commande échoue ? Appuie sur <kbd>Alt</kbd>+<kbd>E</kbd>. ezShell analyse la cause en
              local et place la commande corrective directement dans ton prompt. Zéro exécution aveugle.
            </p>

            <div className="hero-actions">
              <div className="command-box">
                <span className="command-box-prompt">$</span>
                <code className="command-box-code">{INSTALL_COMMAND}</code>
                <CopyButton value={INSTALL_COMMAND} label="Copier la commande d'installation" />
              </div>

              <a className="btn-secondary" href="#installation">
                Démarrage rapide ❯
              </a>
            </div>
          </div>

          {/* Démonstration interactive Vercel-style */}
          <div id="demonstration">
            <HeroDemo />
          </div>
        </section>

        {/* Métriques / Bandeau d'impact */}
        <section className="shell" aria-label="Métriques clés" style={{ margin: "48px auto 0" }}>
          <div className="stats-bar">
            {STATS.map((stat, i) => (
              <div key={i} className="stat-item">
                <span className="stat-value">{stat.value}</span>
                <span className="stat-label">{stat.label}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Bento Grid - Fonctionnalités phares */}
        <section className="section shell" id="fonctionnalites">
          <div className="section-head">
            <p className="section-eyebrow">Architecture & Principes</p>
            <h2 className="section-title">Conçu pour les développeurs exigeants.</h2>
            <p className="section-desc">
              Chaque détail d'ezShell a été pensé pour respecter votre flux de frappe, la sécurité de vos
              clés et la mémoire de votre machine.
            </p>
          </div>

          <div className="bento-grid">
            <BentoCard className="col-span-2">
              <div className="bento-number">01 / DANS LE FLUX DE TRAVAIL</div>
              <h3 className="bento-title">Zéro copier-coller. Diagnostic instantané.</h3>
              <p className="bento-desc">
                Ne basculez plus sur votre navigateur pour chercher une trace de stack sur StackOverflow.
                ezShell intercepte le code de retour et l'historique récent dans votre session pour en déduire
                la cause exacte en moins d'une seconde.
              </p>
              <div className="bento-preview">
                <span style={{ color: "var(--accent)" }}>❯</span> git push origin feature{"\n"}
                <span style={{ color: "var(--danger)" }}>! [rejected] non-fast-forward</span>{"\n"}
                <span style={{ color: "#a1a1aa" }}>↳ [Alt+E] Suggestion : git push --force-with-lease origin feature</span>
              </div>
            </BentoCard>

            <BentoCard>
              <div className="bento-number">02 / HUMAN-IN-THE-LOOP</div>
              <h3 className="bento-title">Contrôle absolu</h3>
              <p className="bento-desc">
                Rien n'est jamais exécuté automatiquement. La commande recommandée est injectée dans votre
                prompt : vous gardez le pouvoir de la modifier, de la copier ou de presser Entrée.
              </p>
            </BentoCard>

            <BentoCard>
              <div className="bento-number">03 / SÉCURITÉ PAR DÉFAUT</div>
              <h3 className="bento-title">Caviardage local des secrets</h3>
              <p className="bento-desc">
                Un moteur d'analyse statique supprime les clés API (OpenAI, AWS, GitHub), les mots de passe et
                les tokens d'autorisation avant même qu'une requête ne quitte votre machine.
              </p>
            </BentoCard>

            <BentoCard className="col-span-2">
              <div className="bento-number">04 / MULTI-ENVIRONNEMENT</div>
              <h3 className="bento-title">Zsh, Bash, Fish & Fenêtre Desktop Hyprland</h3>
              <p className="bento-desc">
                Intégration transparente dans vos shells préférés sous Linux, macOS et Windows (PowerShell).
                Profitez au choix du panneau TUI textuel natif ou de la fenêtre graphique discrète aux
                standards Wayland / Hyprland.
              </p>
              <div className="bento-preview" style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
                <span>• Hook shell léger (zéro latence au prompt)</span>
                <span>• Raccourci personnalisable (<kbd>Alt+E</kbd> ou combinaison de votre choix)</span>
                <span>• Mode hors ligne avec vos modèles locaux</span>
              </div>
            </BentoCard>
          </div>
        </section>

        {/* Exemples & Cas Concrets */}
        <section className="section shell" id="exemples">
          <div className="section-head">
            <p className="section-eyebrow">Cas d'usage concrets</p>
            <h2 className="section-title">Une erreur devient une solution immédiate.</h2>
            <p className="section-desc">
              Chaque réponse fournit la cause précise, la commande de résolution et une classification claire
              du niveau de risque d'exécution.
            </p>
          </div>

          <Examples />
        </section>

        {/* Installation & Démarrage en 3 étapes */}
        <section className="section shell" id="installation">
          <div className="section-head">
            <p className="section-eyebrow">Démarrage rapide</p>
            <h2 className="section-title">Opérationnel en deux commandes.</h2>
            <p className="section-desc">
              ezShell s'installe via pipx pour garantir l'isolation complète vis-à-vis des dépendances de
              votre système d'exploitation.
            </p>
          </div>

          <div className="install-grid">
            {/* Étape 1 */}
            <div className="install-card">
              <span className="install-step-num">Étape 01 · Paquet</span>
              <h3 className="install-card-title">Installer ezShell</h3>
              <p className="install-card-desc">
                Télécharge et isole l'exécutable dans son propre environnement virtuel Python.
              </p>
              <div className="install-code-line">
                <code>{INSTALL_COMMAND}</code>
                <CopyButton value={INSTALL_COMMAND} compact label="Copier la commande d'installation" />
              </div>
              <PipxHelp />
            </div>

            {/* Étape 2 */}
            <div className="install-card">
              <span className="install-step-num">Étape 02 · Shell</span>
              <h3 className="install-card-title">Activer le hook shell</h3>
              <p className="install-card-desc">
                Permet à votre shell de capturer l'historique récent de manière totalement transparente.
              </p>
              <ShellTabs />
            </div>

            {/* Étape 3 */}
            <div className="install-card">
              <span className="install-step-num">Étape 03 · Utilisation</span>
              <h3 className="install-card-title">Tester la première erreur</h3>
              <p className="install-card-desc">
                Lancez une commande erronée (par exemple <code>git psuh</code>), puis appuyez immédiatement
                sur <kbd>Alt</kbd>+<kbd>E</kbd>.
              </p>
              <div
                style={{
                  marginTop: "auto",
                  padding: "12px",
                  borderRadius: "6px",
                  background: "var(--code)",
                  border: "1px solid var(--border)",
                  fontFamily: "var(--mono)",
                  fontSize: "12px",
                  color: "var(--text-muted)",
                }}
              >
                <span>❯ git psuh</span>{"\n"}
                <span style={{ color: "var(--accent)" }}>[ Alt + E ]</span>{" "}
                <span style={{ color: "#ffffff" }}>→ Diagnostic immédiat</span>
              </div>
            </div>
          </div>
        </section>

        {/* Confidentialité & Transparence */}
        <section className="section shell" id="confidentialite">
          <div className="section-head">
            <p className="section-eyebrow">Vie privée & Données</p>
            <h2 className="section-title">Ce qui est analysé, ce qui reste chez vous.</h2>
            <p className="section-desc">
              Nous respectons l'intimité de votre terminal : aucune donnée ne quitte votre machine en tâche
              de fond et rien n'est conservé.
            </p>
          </div>

          <div className="privacy-grid">
            <div className="privacy-card">
              <h3 className="privacy-card-title">
                <span className="privacy-badge sent">Transmis</span>
                <span>Uniquement sur pression explicite de Alt+E</span>
              </h3>
              <ul className="privacy-list">
                {SENT_ITEMS.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>

            <div className="privacy-card">
              <h3 className="privacy-card-title">
                <span className="privacy-badge never">Jamais</span>
                <span>Exclu et filtré localement</span>
              </h3>
              <ul className="privacy-list">
                {NEVER_ITEMS.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* FAQ - Questions fréquentes */}
        <section className="section shell" id="faq">
          <div className="section-head">
            <p className="section-eyebrow">F.A.Q.</p>
            <h2 className="section-title">Questions fréquentes.</h2>
            <p className="section-desc">Tout ce que vous devez savoir avant de commencer.</p>
          </div>

          <FaqAccordion />
        </section>

        {/* Appel à l'action final */}
        <FinalCta installCommand={INSTALL_COMMAND} />
      </main>

      {/* Pied de page style Vercel */}
      <footer className="site-footer">
        <div className="shell footer-inner">
          <div className="footer-credits">
            <span style={{ color: "#ffffff", fontWeight: 600 }}>ezShell par Waddle</span>
            <span>
              © {new Date().getFullYear()} Waddle Team ·{" "}
              <a href={`${GITHUB_URL}/blob/main/LICENSE`} target="_blank" rel="noreferrer">
                Licence MIT
              </a>
            </span>
          </div>

          <div className="footer-links">
            <a href={GITHUB_URL} target="_blank" rel="noreferrer">
              GitHub
            </a>
            <a href={`${GITHUB_URL}/issues`} target="_blank" rel="noreferrer">
              Signaler un bug
            </a>
            <a href="/api/v1/health">État du service</a>
            <a href="/login">Espace compte</a>
          </div>
        </div>
      </footer>
    </>
  );
}
