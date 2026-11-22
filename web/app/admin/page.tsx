"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

interface AdminStats {
  users: {
    total: number;
    free: number;
    silver: number;
    gold: number;
    student: number;
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
  plan: "free" | "silver" | "gold" | "student";
  status: "active" | "banned";
  daily_limit_override: number | null;
  devices_count: number;
  created_at: string;
  newsletter_opt_in: boolean;
  requests_today: number;
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
  const [activeTab, setActiveTab] = useState<"users" | "quotas" | "subscriptions" | "stats" | "logs" | "emails">("users");
  const [page, setPage] = useState(1);
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

      <main className="admin-layout max-w-7xl mx-auto px-4 py-8">
        <aside className="admin-sidebar" aria-label="Navigation administration">
          <button className={activeTab === "users" ? "active" : ""} onClick={() => setActiveTab("users")}>Utilisateurs</button>
          <button className={activeTab === "quotas" ? "active" : ""} onClick={() => setActiveTab("quotas")}>Quotas</button>
          <button className={activeTab === "subscriptions" ? "active" : ""} onClick={() => setActiveTab("subscriptions")}>Abonnements</button>
          <button className={activeTab === "stats" ? "active" : ""} onClick={() => setActiveTab("stats")}>Stats</button>
          <button className={activeTab === "emails" ? "active" : ""} onClick={() => setActiveTab("emails")}>Export emails</button>
          <button className={activeTab === "logs" ? "active" : ""} onClick={() => setActiveTab("logs")}>Journal d&apos;audit</button>
        </aside>
        <div className="admin-content space-y-8">
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
              <span>Silver: {stats?.users.silver}</span>
              <span>Gold: {stats?.users.gold}</span>
              <span>Étudiant: {stats?.users.student}</span>
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

          <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
            <span className="text-xs text-slate-400 block mb-1">Comptes payants</span>
            <div className="text-2xl font-bold text-purple-400">
              {(stats?.users.silver || 0) + (stats?.users.gold || 0) + (stats?.users.student || 0)}
            </div>
            <div className="mt-2 text-xs text-slate-500">Premium et illimités</div>
          </div>
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
                    <th className="px-4 py-3">Requêtes aujourd&apos;hui</th>
                    <th className="px-4 py-3">Inscription</th>
                    <th className="px-4 py-3">Statut</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {users.slice((page - 1) * 10, page * 10).map((u) => (
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
                          <option value="silver">Silver</option>
                          <option value="gold">Gold</option>
                          <option value="student">Pass étudiant</option>
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
                      <td className="px-4 py-3 text-slate-300 font-mono">
                        {u.requests_today}
                      </td>
                      <td className="px-4 py-3 text-slate-400 whitespace-nowrap">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${u.status === "banned" ? "bg-red-950 text-red-400 border border-red-800" : "bg-emerald-950 text-emerald-400 border border-emerald-800"}`}>
                          {u.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right space-x-2">
                        <details className="admin-row-menu">
                          <summary>Actions</summary>
                          <div>
                            <button onClick={() => handleUpdateUser(u.id, { status: u.status === "active" ? "banned" : "active" })}>
                              {u.status === "active" ? "Bannir" : "Débannir"}
                            </button>
                            <button onClick={() => handleUpdateUser(u.id, { role: u.role === "admin" ? "user" : "admin" })}>
                              {u.role === "admin" ? "Rétrograder" : "Promouvoir admin"}
                            </button>
                            <button onClick={() => handleUpdateUser(u.id, { plan: "silver" })}>Passer Silver</button>
                          </div>
                        </details>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="admin-pagination">
              <button disabled={page === 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>Précédent</button>
              <span>Page {page} / {Math.max(1, Math.ceil(users.length / 10))}</span>
              <button disabled={page * 10 >= users.length} onClick={() => setPage((value) => value + 1)}>Suivant</button>
            </div>
          </div>
        )}

        {activeTab === "quotas" && (
          <div className="admin-panel">
            <h2>Quotas utilisateurs</h2>
            <p>Les limites personnalisées sont modifiables depuis la colonne « Quota Override » de l&apos;onglet Utilisateurs.</p>
          </div>
        )}

        {activeTab === "subscriptions" && (
          <div className="admin-panel">
            <h2>Abonnements</h2>
            <p>{stats?.users.silver || 0} comptes Silver · {stats?.users.gold || 0} comptes Gold · {stats?.users.student || 0} pass étudiants</p>
          </div>
        )}

        {activeTab === "stats" && (
          <div className="admin-panel">
            <h2>Statistiques</h2>
            <p>{stats?.metrics_24h.total_asks || 0} requêtes sur les dernières 24 heures.</p>
          </div>
        )}

        {activeTab === "emails" && (
          <div className="admin-panel">
            <h2>Export emails</h2>
            <p>Export CSV des comptes inscrits et des visiteurs en liste d&apos;attente.</p>
            <div className="admin-export-actions">
              <a href="/api/v1/admin/emails/export">Tous les emails</a>
              <a href="/api/v1/admin/emails/export?optIn=true">Opt-in uniquement</a>
              <a href="/api/v1/admin/emails/export?optIn=false">Non opt-in</a>
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
        </div>
      </main>
    </div>
  );
}
