"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

function ActivateContent() {
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
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <Link href="/" className="auth-brand">
            ezShell
          </Link>
          <h1 className="auth-title">Connexion d&apos;un terminal</h1>
          <p className="auth-subtitle">Autorisation sécurisée (RFC 8628 Device Flow)</p>
        </div>

        {message && (
          <div
            className={`auth-message ${message.type}`}
          >
            {message.text}
          </div>
        )}

        {checkingAuth ? (
          <div className="auth-loading">Vérification de session...</div>
        ) : currentUser ? (
          <form onSubmit={handleApprove} className="auth-form">
            <div className="auth-user">
              <p>Connecté en tant que :</p>
              <strong>{currentUser.email || currentUser.id}</strong>
            </div>

            <div>
              <label htmlFor="userCode">
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
                className="auth-code-input"
              />
            </div>

            <button
              type="submit"
              disabled={approving || !userCode.trim()}
              className="auth-submit"
            >
              {approving ? "Approbation en cours..." : "Approuver ce terminal"}
            </button>
          </form>
        ) : (
          <div className="auth-options">
            <div className="auth-explanation">
              Pour associer votre terminal à votre compte et débloquer vos quotas, veuillez vous connecter :
            </div>

            {userCode && (
              <div className="auth-device-code">
                Code : {userCode}
              </div>
            )}

            <div>
              <Link
                href={`/login${userCode ? `?user_code=${encodeURIComponent(userCode)}` : ""}`}
                className="auth-submit auth-link"
              >
                Se connecter pour approuver
              </Link>
            </div>
          </div>
        )}

        <div className="auth-dashboard-link">
          <Link href="/dashboard">
            Accéder à mon tableau de bord
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ActivatePage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-950" />}>
      <ActivateContent />
    </Suspense>
  );
}
