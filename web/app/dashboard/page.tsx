"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface UsageData {
  account_type: "anonymous" | "registered";
  user: {
    id: string;
    email: string | null;
    github_login: string | null;
    plan: "free" | "premium" | "unlimited";
    role: "user" | "admin";
    created_at: string;
  } | null;
  devices: Array<{
    id: string;
    created_at: string;
    last_seen_at: string;
  }>;
  quota: {
    tier: string;
    daily_limit: number | null;
    used_today: number;
    remaining_today: number | null;
    reset_at: string;
  };
}

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [revoking, setRevoking] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    fetchUsage();
  }, []);

  async function fetchUsage() {
    try {
      const res = await fetch("/api/v1/usage");
      if (res.status === 401) {
        router.push("/login");
        return;
      }
      if (res.ok) {
        const json = await res.json();
        setData(json);
      }
    } catch {
      setMessage({ type: "error", text: "Impossible de charger les données du compte." });
    } finally {
      setLoading(false);
    }
  }

  async function handleRevokeDevice(deviceId: string) {
    if (!confirm("Voulez-vous vraiment révoquer l'accès pour cet appareil ?")) return;
    setRevoking(deviceId);
    try {
      const res = await fetch("/api/v1/auth/device/revoke", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_id: deviceId }),
      });
      if (res.ok) {
        setMessage({ type: "success", text: "Appareil révoqué avec succès." });
        await fetchUsage();
      } else {
        setMessage({ type: "error", text: "Échec de la révocation." });
      }
    } catch {
      setMessage({ type: "error", text: "Erreur réseau." });
    } finally {
      setRevoking(null);
    }
  }

  async function handleLogout() {
    await fetch("/api/v1/auth/logout", { method: "POST" });
    router.push("/login");
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
        <p className="text-slate-400">Chargement de votre tableau de bord...</p>
      </div>
    );
  }

  const user = data?.user;
  const quota = data?.quota;
  const used = quota?.used_today ?? 0;
  const limit = quota?.daily_limit;
  const isUnlimited = quota?.tier === "unlimited" || limit === null;
  const percentage = isUnlimited ? 0 : Math.min(100, Math.round((used / (limit || 1)) * 100));

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/" className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
              ezShell
            </Link>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              Dashboard
            </span>
            {user?.role === "admin" && (
              <Link
                href="/admin"
                className="text-xs font-semibold px-2.5 py-1 rounded-md bg-purple-950 text-purple-300 border border-purple-800 hover:bg-purple-900 transition"
              >
                ★ Console Admin
              </Link>
            )}
          </div>
          <div className="flex items-center gap-4">
            <span className="text-xs text-slate-400 hidden sm:inline">{user?.email || user?.github_login}</span>
            <button
              onClick={handleLogout}
              className="text-xs px-3 py-1.5 rounded-lg border border-slate-700 hover:bg-slate-800 text-slate-300 transition"
            >
              Déconnexion
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 space-y-8">
        {message && (
          <div
            className={`p-4 rounded-xl text-sm border ${
              message.type === "success"
                ? "bg-emerald-950/60 border-emerald-800 text-emerald-300"
                : "bg-red-950/60 border-red-800 text-red-300"
            }`}
          >
            {message.text}
          </div>
        )}

        {/* Section Quota & Consommation */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 bg-slate-900/70 border border-slate-800 rounded-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-white">Consommation journalière</h2>
                <p className="text-xs text-slate-400">Réinitialisation automatique chaque jour à minuit UTC</p>
              </div>
              <span className="text-xs font-semibold px-3 py-1 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800 capitalize">
                Plan {quota?.tier}
              </span>
            </div>

            <div className="space-y-2 pt-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Requêtes utilisées aujourd&apos;hui :</span>
                <span className="font-bold text-white">
                  {used} {isUnlimited ? "(Illimité)" : `/ ${limit}`}
                </span>
              </div>
              {!isUnlimited && (
                <div className="w-full bg-slate-800 rounded-full h-3 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 rounded-full ${
                      percentage > 85 ? "bg-red-500" : percentage > 60 ? "bg-amber-500" : "bg-cyan-500"
                    }`}
                    style={{ width: `${percentage}%` }}
                  ></div>
                </div>
              )}
              <div className="flex justify-between text-xs text-slate-500 pt-1">
                <span>Restantes : {isUnlimited ? "∞" : quota?.remaining_today}</span>
                <span>Reset UTC : {quota?.reset_at ? new Date(quota.reset_at).toLocaleTimeString() : "--"}</span>
              </div>
            </div>
          </div>

          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white mb-2">Connecter un terminal</h3>
              <p className="text-xs text-slate-400">
                Lancez <code className="text-cyan-400 font-mono bg-slate-950 px-1.5 py-0.5 rounded">ezsh login</code> dans votre terminal pour lier votre machine à ce compte.
              </p>
            </div>
            <Link
              href="/activate"
              className="mt-4 block text-center py-2 px-4 bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-900 rounded-xl text-xs font-semibold transition"
            >
              Saisir un code d&apos;activation ›
            </Link>
          </div>
        </section>

        {/* Section Appareils connectés */}
        <section className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">Appareils et terminaux autorisés</h2>
              <p className="text-xs text-slate-400">Gérez les sessions de vos machines connectées</p>
            </div>
            <span className="text-xs text-slate-500">
              {data?.devices?.length || 0} appareil(s) actif(s)
            </span>
          </div>

          <div className="divide-y divide-slate-800/60">
            {data?.devices && data.devices.length > 0 ? (
              data.devices.map((dev) => (
                <div key={dev.id} className="py-3.5 flex items-center justify-between">
                  <div className="space-y-0.5">
                    <p className="text-sm font-mono text-slate-200">ID : {dev.id}</p>
                    <p className="text-xs text-slate-500">
                      Connecté le {new Date(dev.created_at).toLocaleDateString()} • Vu pour la dernière fois : {new Date(dev.last_seen_at).toLocaleTimeString()}
                    </p>
                  </div>
                  <button
                    onClick={() => handleRevokeDevice(dev.id)}
                    disabled={revoking === dev.id}
                    className="text-xs px-3 py-1.5 rounded-lg border border-red-900/50 hover:bg-red-950/40 text-red-400 transition disabled:opacity-50"
                  >
                    {revoking === dev.id ? "Révocation..." : "Révoquer"}
                  </button>
                </div>
              ))
            ) : (
              <p className="py-4 text-xs text-slate-500">Aucun appareil lié pour le moment.</p>
            )}
          </div>
        </section>

        {/* Section Détails du compte */}
        <section className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 space-y-4">
          <h2 className="text-lg font-semibold text-white">Détails du compte</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <span className="text-slate-500 block">Identifiant :</span>
              <span className="font-mono text-slate-300 break-all">{user?.id}</span>
            </div>
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <span className="text-slate-500 block">E-mail :</span>
              <span className="text-slate-300">{user?.email || "Non renseigné"}</span>
            </div>
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
              <span className="text-slate-500 block">GitHub :</span>
              <span className="text-slate-300">{user?.github_login ? `@${user.github_login}` : "Non lié"}</span>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
