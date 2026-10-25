"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

export default function ActivatePage() {
  const searchParams = useSearchParams();
  const [userCode, setUserCode] = useState("");
  const [currentUser, setCurrentUser] = useState<{ id: string; email: string | null } | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [approving, setApproving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    const code = searchParams.get("user_code");
    if (code) setUserCode(code);
    if (searchParams.get("approved")) {
      setMessage({ type: "success", text: "Votre terminal a été connecté avec succès ! Vous pouvez revenir à votre invite de commande." });
    }

    // Vérifier si une session web est déjà active
    fetch("/api/v1/usage")
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data?.user) {
          setCurrentUser(data.user);
        }
      })
      .catch(() => {})
      .finally(() => setCheckingAuth(false));
  }, [searchParams]);

  async function handleApprove(e: React.FormEvent) {
    e.preventDefault();
    if (!userCode.trim()) return;
    setApproving(true);
    setMessage(null);

    try {
      const res = await fetch("/api/v1/auth/device/approve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_code: userCode }),
      });
      const data = await res.json();
      if (res.ok) {
        setMessage({
          type: "success",
          text: "Terminal approuvé ! La commande 'ezsh login' dans votre terminal va finaliser la connexion automatiquement.",
        });
      } else {
        setMessage({
          type: "error",
          text: data.message || data.error || "Impossible d'approuver cet appareil.",
        });
      }
    } catch {
      setMessage({ type: "error", text: "Erreur de communication avec le serveur." });
    } finally {
      setApproving(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center px-4 py-12">
      <div className="w-full max-w-md bg-slate-900/90 border border-slate-800 rounded-2xl p-8 shadow-2xl backdrop-blur">
        <div className="text-center mb-8">
          <Link href="/" className="inline-block text-2xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
            ezShell
          </Link>
          <h1 className="text-xl font-semibold mt-4 text-white">Connexion d&apos;un terminal</h1>
          <p className="text-xs text-slate-400 mt-1">Autorisation sécurisée (RFC 8628 Device Flow)</p>
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
          </div>
        )}

        {checkingAuth ? (
          <div className="text-center py-8 text-slate-500 text-sm">Vérification de session...</div>
        ) : currentUser ? (
          <form onSubmit={handleApprove} className="space-y-6">
            <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl text-xs space-y-1">
              <p className="text-slate-400">Connecté en tant que :</p>
              <p className="font-semibold text-white">{currentUser.email || currentUser.id}</p>
            </div>

            <div>
              <label htmlFor="userCode" className="block text-xs font-medium text-slate-400 mb-2">
                Code d&apos;activation affiché dans votre terminal
              </label>
              <input
                id="userCode"
                type="text"
                required
                value={userCode}
                onChange={(e) => setUserCode(e.target.value.toUpperCase())}
                placeholder="Ex : WDLE-8492"
                maxLength={10}
                className="w-full text-center tracking-widest font-mono text-lg font-bold px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-cyan-300 placeholder-slate-700 focus:outline-none focus:border-cyan-500 transition"
              />
            </div>

            <button
              type="submit"
              disabled={approving || !userCode.trim()}
              className="w-full py-3 px-4 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white rounded-xl font-medium transition shadow-lg shadow-cyan-950/50 disabled:opacity-50 text-sm"
            >
              {approving ? "Approbation en cours..." : "Approuver ce terminal"}
            </button>
          </form>
        ) : (
          <div className="space-y-6">
            <div className="text-sm text-slate-300 text-center">
              Pour associer votre terminal à votre compte et débloquer vos quotas, veuillez vous connecter :
            </div>

            {userCode && (
              <div className="text-center p-3 bg-slate-950 border border-slate-800 rounded-xl font-mono text-cyan-400 text-sm font-bold">
                Code : {userCode}
              </div>
            )}

            <div className="space-y-3">
              <Link
                href={`/login${userCode ? `?user_code=${encodeURIComponent(userCode)}` : ""}`}
                className="block text-center w-full py-3 px-4 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white rounded-xl font-medium transition shadow-lg shadow-cyan-950/50 text-sm"
              >
                Se connecter pour approuver
              </Link>
            </div>
          </div>
        )}

        <div className="mt-8 text-center">
          <Link href="/dashboard" className="text-xs text-slate-500 hover:text-slate-400 underline">
            Accéder à mon tableau de bord
          </Link>
        </div>
      </div>
    </div>
  );
}
