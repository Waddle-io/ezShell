"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface AdminStats {
  users: {
    total: number;
    free: number;
    premium: number;
    unlimited: number;
    banned: number;
  };
  devices: {
    total: number;
    registered: number;
    anonymous: number;
  };
  metrics_24h: {
    total_asks: number;
    successful_asks: number;
    avg_latency_ms: number | null;
  };
  kill_switch: boolean;
}

interface UserRow {
  id: string;
  email: string | null;
  github_login: string | null;
  role: "user" | "admin";
  plan: "free" | "premium" | "unlimited";
  status: "active" | "banned";
  daily_limit_override: number | null;
  devices_count: number;
  created_at: string;
}

interface AuditLog {
  id: string;
  at: string;
  actor_id: string;
  actor_email: string | null;
  action: string;
  target_id: string | null;
  details: Record<string, unknown>;
}

export default function AdminPage() {
  const router = useRouter();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<"users" | "logs" | "settings">("users");
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const [resStats, resUsers, resLogs] = await Promise.all([
        fetch("/api/v1/admin/stats"),
        fetch(`/api/v1/admin/users?q=${encodeURIComponent(searchQuery)}`),
        fetch("/api/v1/admin/audit-logs"),
      ]);

      if (resStats.status === 403 || resStats.status === 401) {
        alert("Accès réservé aux administrateurs.");
        router.push("/dashboard");
        return;
      }

      if (resStats.ok) setStats(await resStats.json());
      if (resUsers.ok) {
        const uData = await resUsers.json();
        setUsers(uData.users || []);
      }
      if (resLogs.ok) {
        const lData = await resLogs.json();
        setLogs(lData.logs || []);
      }
    } catch {
      setMessage({ type: "error", text: "Erreur lors du chargement des données d'administration." });
    } finally {
      setLoading(false);
    }
  }

  async function handleUpdateUser(userId: string, updates: Record<string, unknown>) {
    try {
      const res = await fetch("/api/v1/admin/users", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, ...updates }),
      });
      const data = await res.json();
      if (res.ok) {
        setMessage({ type: "success", text: "Utilisateur mis à jour." });
        await loadAll();
      } else {
        setMessage({ type: "error", text: data.message || "Échec de mise à jour." });
      }
    } catch {
      setMessage({ type: "error", text: "Erreur réseau." });
    }
  }

  async function handleToggleKillSwitch(enable: boolean) {
    if (!confirm(enable ? "ATTENTION : Activer le Kill Switch bloquera toutes les requêtes LLM du service !" : "Réactiver le service LLM ?")) return;
    try {
      const res = await fetch("/api/v1/admin/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kill_switch: enable }),
      });
      if (res.ok) {
        setMessage({ type: "success", text: `Kill Switch ${enable ? "activé" : "désactivé"}.` });
        await loadAll();
      }
    } catch {
      setMessage({ type: "error", text: "Erreur lors de la modification du Kill Switch." });
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
        <p className="text-slate-400">Chargement de la console d&apos;administration...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header Admin */}
      <header className="border-b border-purple-900/60 bg-slate-900/90 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-xl font-bold bg-gradient-to-r from-purple-400 to-cyan-400 bg-clip-text text-transparent">
              ezShell
            </Link>
            <span className="text-xs font-semibold px-2.5 py-1 rounded bg-purple-950 text-purple-300 border border-purple-800">
              Console Admin
            </span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-xs text-slate-400 hover:text-white transition">
              ← Mon Dashboard
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 space-y-8">
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

        {/* Cartes Statistiques Globales */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
            <span className="text-xs text-slate-400 block mb-1">Utilisateurs inscrits</span>
            <div className="text-2xl font-bold text-white">{stats?.users.total || 0}</div>
            <div className="mt-2 text-xs text-slate-500 space-x-2">
              <span>Free: {stats?.users.free}</span>
              <span>Premium: {stats?.users.premium}</span>
              <span>Illimité: {stats?.users.unlimited}</span>
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
            <span className="text-xs text-slate-400 block mb-1">Appareils actifs</span>
            <div className="text-2xl font-bold text-cyan-400">{stats?.devices.total || 0}</div>
            <div className="mt-2 text-xs text-slate-500">
              <span>{stats?.devices.registered} liés à un compte • {stats?.devices.anonymous} anonymes</span>
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
            <span className="text-xs text-slate-400 block mb-1">Requêtes (24h)</span>
            <div className="text-2xl font-bold text-emerald-400">{stats?.metrics_24h.total_asks || 0}</div>
            <div className="mt-2 text-xs text-slate-500">
              <span>Latence moy. : {stats?.metrics_24h.avg_latency_ms || "--"} ms</span>
            </div>
          </div>

          <div className={`p-5 rounded-2xl border ${stats?.kill_switch ? "bg-red-950/50 border-red-800" : "bg-slate-900/80 border-slate-800"}`}>
            <span className="text-xs text-slate-400 block mb-1">Statut du Service</span>
            <div className={`text-xl font-bold ${stats?.kill_switch ? "text-red-400" : "text-emerald-400"}`}>
              {stats?.kill_switch ? "⛔ KILL SWITCH ACTIF" : "✔ Opérationnel"}
            </div>
            <button
              onClick={() => handleToggleKillSwitch(!stats?.kill_switch)}
              className={`mt-2 text-xs px-2.5 py-1 rounded font-semibold transition ${
                stats?.kill_switch ? "bg-emerald-800 hover:bg-emerald-700 text-white" : "bg-red-900 hover:bg-red-800 text-red-200"
              }`}
            >
              {stats?.kill_switch ? "Désactiver Kill Switch" : "Activer Kill Switch"}
            </button>
          </div>
        </div>

        {/* Onglets */}
        <div className="border-b border-slate-800 flex gap-6 text-sm font-medium">
          <button
            onClick={() => setActiveTab("users")}
            className={`pb-3 border-b-2 transition ${activeTab === "users" ? "border-cyan-400 text-cyan-400" : "border-transparent text-slate-400 hover:text-white"}`}
          >
            Gestion des Utilisateurs ({users.length})
          </button>
          <button
            onClick={() => setActiveTab("logs")}
            className={`pb-3 border-b-2 transition ${activeTab === "logs" ? "border-cyan-400 text-cyan-400" : "border-transparent text-slate-400 hover:text-white"}`}
          >
            Journal d&apos;Audit ({logs.length})
          </button>
        </div>

        {/* Onglet Utilisateurs */}
        {activeTab === "users" && (
          <div className="space-y-4">
            <div className="flex gap-3">
              <input
                type="text"
                placeholder="Rechercher par email ou github..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && loadAll()}
                className="w-full max-w-sm px-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
              <button
                onClick={loadAll}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-sm font-medium transition"
              >
                Rechercher
              </button>
            </div>

            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/60 text-slate-400 uppercase border-b border-slate-800 font-medium">
                  <tr>
                    <th className="px-4 py-3">Utilisateur</th>
                    <th className="px-4 py-3">Rôle</th>
                    <th className="px-4 py-3">Plan</th>
                    <th className="px-4 py-3">Quota Override</th>
                    <th className="px-4 py-3">Appareils</th>
                    <th className="px-4 py-3">Statut</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-800/30 transition">
                      <td className="px-4 py-3">
                        <div className="font-semibold text-white">{u.email || "Sans email"}</div>
                        <div className="text-slate-500 font-mono text-[10px]">{u.github_login ? `@${u.github_login}` : u.id}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${u.role === "admin" ? "bg-purple-950 text-purple-300 border border-purple-800" : "text-slate-400"}`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value={u.plan}
                          onChange={(e) => handleUpdateUser(u.id, { plan: e.target.value })}
                          className="bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white"
                        >
                          <option value="free">Free</option>
                          <option value="premium">Premium</option>
                          <option value="unlimited">Unlimited</option>
                        </select>
                      </td>
                      <td className="px-4 py-3">
                        <input
                          type="number"
                          placeholder="Défaut"
                          defaultValue={u.daily_limit_override ?? ""}
                          onBlur={(e) => {
                            const val = e.target.value.trim();
                            handleUpdateUser(u.id, { daily_limit_override: val ? Number(val) : null });
                          }}
                          className="w-20 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs text-white"
                        />
                      </td>
                      <td className="px-4 py-3 text-slate-300 font-mono">
                        {u.devices_count}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${u.status === "banned" ? "bg-red-950 text-red-400 border border-red-800" : "bg-emerald-950 text-emerald-400 border border-emerald-800"}`}>
                          {u.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right space-x-2">
                        {u.status === "active" ? (
                          <button
                            onClick={() => handleUpdateUser(u.id, { status: "banned" })}
                            className="px-2 py-1 text-[11px] rounded bg-red-950 text-red-300 border border-red-800 hover:bg-red-900 transition"
                          >
                            Bannir
                          </button>
                        ) : (
                          <button
                            onClick={() => handleUpdateUser(u.id, { status: "active" })}
                            className="px-2 py-1 text-[11px] rounded bg-emerald-950 text-emerald-300 border border-emerald-800 hover:bg-emerald-900 transition"
                          >
                            Débannir
                          </button>
                        )}
                        <button
                          onClick={() => handleUpdateUser(u.id, { role: u.role === "admin" ? "user" : "admin" })}
                          className="px-2 py-1 text-[11px] rounded bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition"
                        >
                          {u.role === "admin" ? "Rétrograder" : "Promouvoir Admin"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Onglet Logs d'Audit */}
        {activeTab === "logs" && (
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 uppercase border-b border-slate-800 font-medium">
                <tr>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Acteur</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Cible</th>
                  <th className="px-4 py-3">Détails</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/30">
                    <td className="px-4 py-2.5 text-slate-400 whitespace-nowrap">
                      {new Date(log.at).toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-cyan-300">
                      {log.actor_email || log.actor_id}
                    </td>
                    <td className="px-4 py-2.5 font-bold text-white">
                      {log.action}
                    </td>
                    <td className="px-4 py-2.5 text-slate-400">
                      {log.target_id || "--"}
                    </td>
                    <td className="px-4 py-2.5 text-slate-500 truncate max-w-xs">
                      {JSON.stringify(log.details)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
