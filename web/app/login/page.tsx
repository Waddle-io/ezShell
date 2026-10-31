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

function LoginContent() {
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [userCode, setUserCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    const code = searchParams.get("user_code");
    if (code) setUserCode(code);
    const err = searchParams.get("error");
    if (err) {
      setMessage({ type: "error", text: ERROR_MESSAGES[err] || "Une erreur est survenue lors de la connexion." });
    }
  }, [searchParams]);

  // Après connexion : page d'approbation du terminal si un code est en attente, sinon le tableau de bord.
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
        setMessage({ type: "success", text: "Un lien de connexion vous a été envoyé par e-mail." });
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
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <Link href="/" className="auth-brand">
            ezShell
          </Link>
          <h1 className="auth-title">Connexion à votre espace</h1>
          {userCode && (
            <div className="auth-device-code">
              Terminal en attente : <span className="font-bold">{userCode}</span>
            </div>
          )}
        </div>

        {message && (
          <div
            className={`auth-message ${message.type}`}
          >
            {message.text}
          </div>
        )}

        <div className="auth-options">
          <button
            type="button"
            onClick={handleGithub}
            className="auth-provider"
          >
            <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
            Continuer avec GitHub
          </button>

          <div className="auth-divider">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-800"></div>
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span>Ou par e-mail</span>
            </div>
          </div>

          <form onSubmit={handleMagicLink} className="auth-form">
            <div>
              <label htmlFor="email">
                Adresse e-mail
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="nom@exemple.com"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="auth-submit"
            >
              {loading ? "Envoi en cours..." : "Recevoir un lien magique"}
            </button>
          </form>
        </div>

        <p className="auth-footnote">
          Sans mot de passe. Aucun contenu de vos requêtes n&apos;est jamais stocké.
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-950" />}>
      <LoginContent />
    </Suspense>
  );
}
