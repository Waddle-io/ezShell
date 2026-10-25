"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

export default function LoginPage() {
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
        user_banned: "Votre compte est suspendu.",
        github_not_configured: "La connexion GitHub n'est pas encore configurée sur ce serveur.",
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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center px-4 py-12">
      <div className="w-full max-w-md bg-slate-900/90 border border-slate-800 rounded-2xl p-8 shadow-2xl backdrop-blur">
        <div className="text-center mb-8">
          <Link href="/" className="inline-block text-2xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
            ezShell
          </Link>
          <h1 className="text-xl font-semibold mt-4 text-white">Connexion à votre espace</h1>
          {userCode && (
            <div className="mt-3 inline-block px-3 py-1 bg-cyan-950/80 border border-cyan-800 text-cyan-300 rounded-full text-xs font-mono">
              Terminal en attente : <span className="font-bold">{userCode}</span>
            </div>
          )}
        </div>

        {message && (
          <div
            className={`mb-6 p-4 rounded-xl text-sm border ${
              message.type === "success"
                ? "bg-emerald-950/60 border-emerald-800 text-emerald-300"
                : "bg-red-950/60 border-red-800 text-red-300"
            }`}
          >
            {message.text}
            {debugUrl && (
              <div className="mt-3 pt-3 border-t border-emerald-900/50">
                <p className="text-xs text-slate-400 mb-1">Lien direct de développement :</p>
                <a href={debugUrl} className="text-xs font-mono text-cyan-400 underline break-all hover:text-cyan-300">
                  {debugUrl}
                </a>
              </div>
            )}
          </div>
        )}

        <div className="space-y-4">
          <a
            href={githubUrl}
            className="w-full flex items-center justify-center gap-3 py-3 px-4 bg-slate-800 hover:bg-slate-700 text-white rounded-xl font-medium border border-slate-700 transition"
          >
            <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
            Continuer avec GitHub
          </a>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-800"></div>
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-slate-900 px-3 text-slate-500 font-medium">Ou par e-mail</span>
            </div>
          </div>

          <form onSubmit={handleMagicLink} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-xs font-medium text-slate-400 mb-1.5">
                Adresse e-mail
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="nom@exemple.com"
                className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500 transition text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white rounded-xl font-medium transition shadow-lg shadow-cyan-950/50 disabled:opacity-50 text-sm"
            >
              {loading ? "Envoi en cours..." : "Recevoir un lien magique"}
            </button>
          </form>
        </div>

        <p className="mt-8 text-center text-xs text-slate-500">
          Sans mot de passe. Aucun contenu de vos requêtes n&apos;est jamais stocké.
        </p>
      </div>
    </div>
  );
}
