"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { authClient } from "@/lib/auth-client";

// Codes d'erreur renvoyés par Better Auth dans ?error= (lien magique et GitHub).
const ERROR_MESSAGES: Record<string, string> = {
  INVALID_TOKEN: "Lien de connexion invalide, expiré ou déjà utilisé.",
  failed_to_create_session: "Impossible d'ouvrir la session : votre compte est peut-être suspendu.",
  access_denied: "GitHub a refusé la connexion.",
  state_mismatch: "La tentative de connexion GitHub a expiré. Veuillez réessayer.",
  please_restart_the_process: "La tentative de connexion GitHub a expiré. Veuillez réessayer.",
  unable_to_get_user_info: "GitHub n'a pas fourni les informations du compte.",
  email_not_found: "GitHub n'a pas fourni d'adresse e-mail pour ce compte.",
  account_not_linked: "Ce compte GitHub n'est pas lié à votre compte ezShell.",
  oauth_provider_not_found: "La connexion GitHub n'est pas encore configurée sur ce serveur.",
};

function GitHubIcon() {
  return (
    <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}

function EzShellIcon() {
  return (
    <svg viewBox="0 0 32 32" width="32" height="32" aria-hidden="true">
      <rect x="1" y="1" width="30" height="30" rx="7.5" fill="#111318" stroke="rgba(255,255,255,0.14)" strokeWidth="1"/>
      <path d="M 9.9 20.85 L 12.41 14.12 L 9.9 7.3 L 6.78 7.3 L 9.29 14.08 L 6.78 20.85 Z" fill="#38bdf8"/>
      <path d="M 16.31 23.42 L 25.22 23.42 L 25.22 21.32 L 16.31 21.32 Z" fill="#38bdf8"/>
    </svg>
  );
}

function LoginContent() {
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [userCode, setUserCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    const code = searchParams.get("user_code");
    if (code) setUserCode(code);
    const err = searchParams.get("error");
    if (err) {
      setMessage({ type: "error", text: ERROR_MESSAGES[err] || "Une erreur est survenue lors de la connexion." });
    }
  }, [searchParams]);

  const codeQuery = userCode ? `?user_code=${encodeURIComponent(userCode)}` : "";
  const callbackURL = userCode ? `/activate${codeQuery}` : "/dashboard";
  const errorCallbackURL = `/login${codeQuery}`;

  async function handleMagicLink(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      const { error } = await authClient.signIn.magicLink({ email, callbackURL, errorCallbackURL });
      if (error) {
        setMessage({ type: "error", text: error.message || "Échec de l'envoi." });
      } else {
        setSent(true);
      }
    } catch {
      setMessage({ type: "error", text: "Erreur de connexion au serveur." });
    } finally {
      setLoading(false);
    }
  }

  async function handleGithub() {
    setMessage(null);
    try {
      const { error } = await authClient.signIn.social({ provider: "github", callbackURL, errorCallbackURL });
      if (error) {
        setMessage({
          type: "error",
          text: error.status === 404
            ? ERROR_MESSAGES.oauth_provider_not_found
            : error.message || "Impossible de démarrer la connexion GitHub.",
        });
      }
    } catch {
      setMessage({ type: "error", text: "Erreur de connexion au serveur." });
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">

        {/* Logo + wordmark */}
        <div className="login-brand-block">
          <EzShellIcon />
          <Link href="/" className="login-wordmark">ezShell</Link>
        </div>

        {/* Titre */}
        <div className="login-heading">
          <h1 className="login-title">
            {userCode ? "Autoriser votre terminal" : "Connexion"}
          </h1>
          <p className="login-subtitle">
            {userCode
              ? <>Code terminal : <span className="login-code-pill">{userCode}</span></>
              : "Sans mot de passe. Connexion sécurisée en un clic."}
          </p>
        </div>

        {/* Message d'erreur */}
        {message && (
          <div className={`login-alert login-alert--${message.type}`} role="alert">
            {message.type === "error" && (
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                <path d="M8 1a7 7 0 100 14A7 7 0 008 1zM7 5a1 1 0 112 0v3a1 1 0 11-2 0V5zm1 6.5a1.25 1.25 0 110-2.5 1.25 1.25 0 010 2.5z"/>
              </svg>
            )}
            {message.text}
          </div>
        )}

        {/* Contenu principal */}
        {sent ? (
          /* État : lien envoyé */
          <div className="login-sent">
            <div className="login-sent-icon" aria-hidden="true">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="4" width="20" height="16" rx="3"/>
                <path d="M2 7l10 7 10-7"/>
              </svg>
            </div>
            <p className="login-sent-title">Lien envoyé !</p>
            <p className="login-sent-desc">
              Vérifiez <strong>{email}</strong> — le lien expire dans 10 minutes.
            </p>
            <button className="login-back-btn" onClick={() => { setSent(false); setEmail(""); }}>
              Changer d&apos;adresse
            </button>
          </div>
        ) : (
          <div className="login-options">
            {/* GitHub */}
            <button type="button" onClick={handleGithub} className="login-github-btn">
              <GitHubIcon />
              Continuer avec GitHub
            </button>

            {/* Divider */}
            <div className="login-divider">
              <span>ou par e-mail</span>
            </div>

            {/* Magic link */}
            <form onSubmit={handleMagicLink} className="login-form">
              <div className="login-field">
                <label htmlFor="email" className="login-label">Adresse e-mail</label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="vous@exemple.com"
                  className="login-input"
                  autoComplete="email"
                />
              </div>
              <button type="submit" disabled={loading} className="login-submit-btn">
                {loading ? (
                  <>
                    <svg className="login-spinner" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                      <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeOpacity="0.3" strokeWidth="2"/>
                      <path d="M7 1.5A5.5 5.5 0 0112.5 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                    Envoi en cours…
                  </>
                ) : "Recevoir le lien de connexion"}
              </button>
            </form>
          </div>
        )}

        {/* Footnote */}
        <p className="login-footnote">
          En vous connectant, vous acceptez nos{" "}
          <a href="/#confidentialite">conditions de confidentialité</a>.
          Aucune donnée de vos requêtes n&apos;est stockée.
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="login-page" />}>
      <LoginContent />
    </Suspense>
  );
}
