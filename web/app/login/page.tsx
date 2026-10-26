"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

function LoginContent() {
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [userCode, setUserCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [debugUrl, setDebugUrl] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("user_code");
    if (code) setUserCode(code);
    const err = searchParams.get("error");
    if (err) {
      const msgs: Record<string, string> = {
        token_missing: "Lien de connexion invalide.",
        token_invalid: "Lien de connexion introuvable ou déjà utilisé.",
        token_expired: "Ce lien de connexion a expiré.",
        token_already_used: "Ce lien de connexion a déjà été utilisé.",
        device_approval_failed: "Le code du terminal est invalide, expiré ou déjà utilisé.",
        user_banned: "Votre compte est suspendu.",
        github_not_configured: "La connexion GitHub n'est pas encore configurée sur ce serveur.",
        github_code_missing: "La réponse de GitHub est incomplète.",
        github_state_invalid: "La tentative de connexion GitHub a expiré. Veuillez réessayer.",
        github_token_exchange_failed: "GitHub n'a pas accepté la connexion.",
        github_internal_error: "Une erreur interne a interrompu la connexion GitHub.",
      };
      setMessage({ type: "error", text: msgs[err] || "Une erreur est survenue lors de la connexion." });
    }
  }, [searchParams]);

  async function handleMagicLink(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setMessage(null);
    setDebugUrl(null);

    try {
      const res = await fetch("/api/v1/auth/magic-link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, user_code: userCode || undefined }),
      });
      const data = await res.json();
      if (res.ok) {
        setMessage({ type: "success", text: data.message || "Lien de connexion envoyé !" });
        if (data.debug_url) setDebugUrl(data.debug_url);
      } else {
        setMessage({ type: "error", text: data.message || data.error || "Échec de l'envoi." });
      }
    } catch {
      setMessage({ type: "error", text: "Erreur de connexion au serveur." });
    } finally {
      setLoading(false);
    }
  }

  const githubUrl = `/api/v1/auth/github${userCode ? `?user_code=${encodeURIComponent(userCode)}` : ""}`;

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
            {debugUrl && (
              <div className="auth-debug-url">
                <p>Lien direct de développement :</p>
                <a href={debugUrl}>
                  {debugUrl}
                </a>
              </div>
            )}
          </div>
        )}

        <div className="auth-options">
          <a
            href={githubUrl}
            className="auth-provider"
          >
            <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
            Continuer avec GitHub
          </a>

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
