"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ANONYMOUS_PLAN, PLANS, type PlanId } from "@/lib/plans";
import styles from "./admin.module.css";

/* ------------------------------------------------------------------ Types */

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
  plan: PlanId;
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

type Tab = "users" | "quotas" | "subscriptions" | "stats" | "emails" | "logs";
type IconName = "users" | "gauge" | "card" | "chart" | "mail" | "scroll" | "search" | "refresh" | "download";

interface Toast {
  type: "success" | "error";
  text: string;
}

/* -------------------------------------------------------------- Constantes */

const PAGE_SIZE = 10;
const PLAN_IDS: PlanId[] = ["free", "silver", "gold", "student"];

const PLAN_LABEL: Record<PlanId, string> = {
  free: "Free",
  silver: "Silver",
  gold: "Gold",
  student: "Pass étudiant",
};

const PLAN_BADGE: Record<PlanId, string> = {
  free: "",
  silver: styles.badgeSilver,
  gold: styles.badgeWarn,
  student: styles.badgeAccent,
};

const TABS: { id: Tab; label: string; title: string; subtitle: string; icon: IconName }[] = [
  { id: "users", label: "Utilisateurs", title: "Utilisateurs", subtitle: "Gérez les comptes, les plans et les quotas individuels.", icon: "users" },
  { id: "quotas", label: "Quotas", title: "Quotas", subtitle: "Limites quotidiennes par plan et dérogations en cours.", icon: "gauge" },
  { id: "subscriptions", label: "Abonnements", title: "Abonnements", subtitle: "Répartition des comptes par plan et revenu estimé.", icon: "card" },
  { id: "stats", label: "Stats", title: "Statistiques", subtitle: "Activité des dernières 24 heures et état du service.", icon: "chart" },
  { id: "emails", label: "Export emails", title: "Export emails", subtitle: "Téléchargez les adresses au format CSV.", icon: "mail" },
  { id: "logs", label: "Journal d’audit", title: "Journal d’audit", subtitle: "Historique des actions effectuées par les administrateurs.", icon: "scroll" },
];

/* ---------------------------------------------------------------- Helpers */

const fmtNumber = (n: number) => n.toLocaleString("fr-FR");

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });

const fmtDateTime = (iso: string) =>
  new Date(iso).toLocaleString("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

const initials = (u: UserRow) => (u.email || u.github_login || "?").slice(0, 2);

function Icon({ name, className }: { name: IconName; className?: string }) {
  const common = {
    className,
    width: 18,
    height: 18,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  switch (name) {
    case "users":
      return (
        <svg {...common}>
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    case "gauge":
      return (
        <svg {...common}>
          <path d="M12 14l4-4" />
          <path d="M3.3 17a10 10 0 1 1 17.4 0" />
        </svg>
      );
    case "card":
      return (
        <svg {...common}>
          <rect x="2" y="5" width="20" height="14" rx="2" />
          <path d="M2 10h20" />
        </svg>
      );
    case "chart":
      return (
        <svg {...common}>
          <path d="M3 3v18h18" />
          <path d="M7 15l4-4 3 3 5-6" />
        </svg>
      );
    case "mail":
      return (
        <svg {...common}>
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <path d="M22 7l-10 6L2 7" />
        </svg>
      );
    case "scroll":
      return (
        <svg {...common}>
          <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
          <path d="M14 3v6h6M8 13h8M8 17h5" />
        </svg>
      );
    case "search":
      return (
        <svg {...common}>
          <circle cx="11" cy="11" r="7" />
          <path d="M21 21l-4.3-4.3" />
        </svg>
      );
    case "refresh":
      return (
        <svg {...common}>
          <path d="M21 12a9 9 0 0 1-15.5 6.2L3 16" />
          <path d="M3 21v-5h5M3 12a9 9 0 0 1 15.5-6.2L21 8" />
          <path d="M21 3v5h-5" />
        </svg>
      );
    case "download":
      return (
        <svg {...common}>
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <path d="M7 10l5 5 5-5M12 15V3" />
        </svg>
      );
  }
}

/* ------------------------------------------------------------------- Page */

export default function AdminPage() {
  const router = useRouter();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<Tab>("users");
  const [page, setPage] = useState(1);
  const [message, setMessage] = useState<Toast | null>(null);

  const loadAll = useCallback(
    async (query: string) => {
      setRefreshing(true);
      try {
        const [resStats, resUsers, resLogs] = await Promise.all([
          fetch("/api/v1/admin/stats"),
          fetch(`/api/v1/admin/users?q=${encodeURIComponent(query)}`),
          fetch("/api/v1/admin/audit-logs"),
        ]);

        if (resStats.status === 403 || resStats.status === 401) {
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
        setMessage({ type: "error", text: "Erreur lors du chargement des données d’administration." });
      } finally {
        setInitialLoading(false);
        setRefreshing(false);
      }
    },
    [router],
  );

  useEffect(() => {
    void loadAll("");
  }, [loadAll]);

  // Les notifications disparaissent toutes seules.
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(() => setMessage(null), 4000);
    return () => clearTimeout(t);
  }, [message]);

  async function handleUpdateUser(userId: string, updates: Record<string, unknown>) {
    try {
      const res = await fetch("/api/v1/admin/users", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, ...updates }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setMessage({ type: "success", text: "Utilisateur mis à jour." });
        await loadAll(searchQuery);
      } else {
        setMessage({ type: "error", text: data.message || "Échec de la mise à jour." });
      }
    } catch {
      setMessage({ type: "error", text: "Erreur réseau." });
    }
  }

  async function handleToggleKillSwitch(enable: boolean) {
    const ok = confirm(
      enable
        ? "ATTENTION : activer le Kill Switch bloquera toutes les requêtes LLM du service !"
        : "Réactiver le service LLM ?",
    );
    if (!ok) return;
    try {
      const res = await fetch("/api/v1/admin/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kill_switch: enable }),
      });
      if (res.ok) {
        setMessage({ type: "success", text: `Kill Switch ${enable ? "activé" : "désactivé"}.` });
        await loadAll(searchQuery);
      } else {
        setMessage({ type: "error", text: "Impossible de modifier le Kill Switch." });
      }
    } catch {
      setMessage({ type: "error", text: "Erreur lors de la modification du Kill Switch." });
    }
  }

  function handleSearch() {
    setPage(1);
    void loadAll(searchQuery);
  }

  function handleOverrideCommit(u: UserRow, input: HTMLInputElement) {
    const raw = input.value.trim();
    const next = raw === "" ? null : Number(raw);
    if (next !== null && (!Number.isInteger(next) || next < 0)) {
      setMessage({ type: "error", text: "Le quota doit être un entier positif." });
      input.value = u.daily_limit_override?.toString() ?? "";
      return;
    }
    if (next === u.daily_limit_override) return; // rien n’a changé : pas d’appel, pas de ligne d’audit
    void handleUpdateUser(u.id, { daily_limit_override: next });
  }

  function handleToggleBan(u: UserRow) {
    const banning = u.status === "active";
    if (banning && !confirm(`Suspendre ${u.email || u.github_login || u.id} ?`)) return;
    void handleUpdateUser(u.id, { status: banning ? "banned" : "active" });
  }

  function handleToggleRole(u: UserRow) {
    const promoting = u.role !== "admin";
    const who = u.email || u.github_login || u.id;
    if (!confirm(promoting ? `Donner les droits administrateur à ${who} ?` : `Retirer les droits administrateur à ${who} ?`)) return;
    void handleUpdateUser(u.id, { role: promoting ? "admin" : "user" });
  }

  /* ------------------------------------------------------------- Dérivés */

  const totalPages = Math.max(1, Math.ceil(users.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageUsers = users.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);
  const overrides = useMemo(() => users.filter((u) => u.daily_limit_override !== null), [users]);
  const meta = TABS.find((t) => t.id === activeTab)!;

  const paying = (stats?.users.silver || 0) + (stats?.users.gold || 0) + (stats?.users.student || 0);
  const totalAsks = stats?.metrics_24h.total_asks || 0;
  const successRate = totalAsks > 0 ? Math.round(((stats?.metrics_24h.successful_asks || 0) / totalAsks) * 100) : null;
  const latency = stats?.metrics_24h.avg_latency_ms;
  const killSwitch = stats?.kill_switch ?? false;

  const planCounts: Record<PlanId, number> = {
    free: stats?.users.free || 0,
    silver: stats?.users.silver || 0,
    gold: stats?.users.gold || 0,
    student: stats?.users.student || 0,
  };
  const totalUsers = stats?.users.total || 0;
  const monthlyRevenue = PLAN_IDS.reduce(
    (sum, id) => sum + planCounts[id] * (PLANS[id].priceFcfa / (PLANS[id].durationMonths ?? 1)),
    0,
  );

  /* ---------------------------------------------------------------- Rendu */

  if (initialLoading) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} role="status" aria-label="Chargement" />
        <span>Chargement de la console d’administration…</span>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div className={styles.brand}>
            <Link href="/" className={styles.logo}>
              ezShell
            </Link>
            <span className={styles.adminBadge}>Console admin</span>
          </div>
          <div className={styles.headerActions}>
            <span className={styles.statusPill} title="État du service LLM">
              <span className={`${styles.dot} ${killSwitch ? styles.dotDanger : ""}`} />
              {killSwitch ? "Service suspendu" : "Service actif"}
            </span>
            <Link href="/dashboard" className={styles.backLink}>
              ← Mon dashboard
            </Link>
          </div>
        </div>
      </header>

      <main className={styles.shell}>
        <nav className={styles.sidebar} aria-label="Navigation administration">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`${styles.navItem} ${activeTab === t.id ? styles.navItemActive : ""}`}
              aria-current={activeTab === t.id ? "page" : undefined}
              onClick={() => setActiveTab(t.id)}
            >
              <Icon name={t.icon} className={styles.navIcon} />
              {t.label}
            </button>
          ))}
        </nav>

        <div className={styles.content}>
          {killSwitch && (
            <div className={styles.banner} role="alert">
              <strong>Kill Switch actif.</strong> Toutes les requêtes LLM sont bloquées. Réactivez le service depuis l’onglet Stats.
            </div>
          )}

          <div className={styles.pageTitle}>
            <div>
              <h1>{meta.title}</h1>
              <p>{meta.subtitle}</p>
            </div>
            <button type="button" className={styles.btn} onClick={() => void loadAll(searchQuery)} disabled={refreshing}>
              <Icon name="refresh" />
              {refreshing ? "Actualisation…" : "Actualiser"}
            </button>
          </div>

          {/* ------------------------------------------------ Utilisateurs */}
          {activeTab === "users" && (
            <>
              <section className={styles.kpis} aria-label="Indicateurs clés">
                <div className={styles.kpi}>
                  <span className={styles.kpiLabel}>Utilisateurs inscrits</span>
                  <div className={styles.kpiValue}>{fmtNumber(totalUsers)}</div>
                  <div className={styles.kpiSub}>
                    <span><b>{planCounts.free}</b> Free</span>
                    <span><b>{planCounts.silver}</b> Silver</span>
                    <span><b>{planCounts.gold}</b> Gold</span>
                    <span><b>{planCounts.student}</b> Étudiant</span>
                  </div>
                </div>

                <div className={styles.kpi}>
                  <span className={styles.kpiLabel}>Appareils actifs</span>
                  <div className={styles.kpiValue}>{fmtNumber(stats?.devices.total || 0)}</div>
                  <div className={styles.kpiSub}>
                    <span><b>{stats?.devices.registered || 0}</b> liés à un compte</span>
                    <span><b>{stats?.devices.anonymous || 0}</b> anonymes</span>
                  </div>
                </div>

                <div className={styles.kpi}>
                  <span className={styles.kpiLabel}>Requêtes (24 h)</span>
                  <div className={styles.kpiValue}>{fmtNumber(totalAsks)}</div>
                  <div className={styles.kpiSub}>
                    <span>Latence moy. <b>{latency ? `${Math.round(latency)} ms` : "—"}</b></span>
                  </div>
                </div>

                <div className={styles.kpi}>
                  <span className={styles.kpiLabel}>Comptes payants</span>
                  <div className={styles.kpiValue}>{paying}</div>
                  <div className={styles.kpiSub}>
                    <span>Silver, Gold et Pass étudiant</span>
                  </div>
                </div>
              </section>

              <div className={styles.toolbar}>
                <div className={styles.searchBox}>
                  <Icon name="search" className={styles.searchIcon} />
                  <input
                    type="text"
                    aria-label="Rechercher un utilisateur"
                    placeholder="Rechercher par email ou GitHub…"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                    className={styles.input}
                  />
                </div>
                <button type="button" className={styles.btn} onClick={handleSearch}>
                  Rechercher
                </button>
              </div>

              <section className={styles.card}>
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Utilisateur</th>
                        <th>Rôle</th>
                        <th>Plan</th>
                        <th>Quota / jour</th>
                        <th>Appareils</th>
                        <th>Req. aujourd’hui</th>
                        <th>Inscription</th>
                        <th>Statut</th>
                        <th className={styles.right}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pageUsers.length === 0 && (
                        <tr>
                          <td colSpan={9} className={styles.empty}>
                            Aucun utilisateur trouvé.
                          </td>
                        </tr>
                      )}
                      {pageUsers.map((u) => (
                        <tr key={u.id}>
                          <td>
                            <div className={styles.user}>
                              <span className={styles.avatar}>{initials(u)}</span>
                              <div className={styles.userMain}>
                                <div className={styles.userEmail}>{u.email || "Sans email"}</div>
                                <div className={styles.userSub}>{u.github_login ? `@${u.github_login}` : u.id}</div>
                              </div>
                            </div>
                          </td>
                          <td>
                            <span className={`${styles.badge} ${u.role === "admin" ? styles.badgeAccent : ""}`}>
                              {u.role === "admin" ? "Admin" : "Utilisateur"}
                            </span>
                          </td>
                          <td>
                            <select
                              aria-label={`Plan de ${u.email || u.id}`}
                              value={u.plan}
                              onChange={(e) => void handleUpdateUser(u.id, { plan: e.target.value })}
                              className={styles.select}
                            >
                              {PLAN_IDS.map((id) => (
                                <option key={id} value={id}>
                                  {PLAN_LABEL[id]}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <input
                              key={`${u.id}-${u.daily_limit_override ?? ""}`}
                              type="number"
                              min={0}
                              aria-label={`Quota personnalisé de ${u.email || u.id}`}
                              placeholder={String(PLANS[u.plan].dailyQuota)}
                              defaultValue={u.daily_limit_override ?? ""}
                              onBlur={(e) => handleOverrideCommit(u, e.currentTarget)}
                              onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
                              className={`${styles.input} ${styles.inputSm} ${styles.numInput}`}
                            />
                          </td>
                          <td className={styles.num}>{u.devices_count}</td>
                          <td className={styles.num}>{u.requests_today}</td>
                          <td className={`${styles.nowrap} ${styles.num}`}>{fmtDate(u.created_at)}</td>
                          <td>
                            <span className={`${styles.badge} ${u.status === "banned" ? styles.badgeDanger : styles.badgeSuccess}`}>
                              {u.status === "banned" ? "Suspendu" : "Actif"}
                            </span>
                          </td>
                          <td className={styles.right}>
                            <div className={styles.rowActions}>
                              <button
                                type="button"
                                className={`${styles.btn} ${styles.btnSm} ${u.status === "active" ? styles.btnDanger : ""}`}
                                onClick={() => handleToggleBan(u)}
                              >
                                {u.status === "active" ? "Bannir" : "Débannir"}
                              </button>
                              <button type="button" className={`${styles.btn} ${styles.btnSm}`} onClick={() => handleToggleRole(u)}>
                                {u.role === "admin" ? "Rétrograder" : "Promouvoir"}
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className={styles.pagination}>
                  <span>
                    {users.length} utilisateur{users.length > 1 ? "s" : ""} · Page {currentPage} / {totalPages}
                  </span>
                  <div className={styles.pagerBtns}>
                    <button type="button" className={`${styles.btn} ${styles.btnSm}`} disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>
                      Précédent
                    </button>
                    <button type="button" className={`${styles.btn} ${styles.btnSm}`} disabled={currentPage >= totalPages} onClick={() => setPage(currentPage + 1)}>
                      Suivant
                    </button>
                  </div>
                </div>
              </section>
            </>
          )}

          {/* ---------------------------------------------------- Quotas */}
          {activeTab === "quotas" && (
            <>
              <section className={styles.card}>
                <div className={styles.cardHead}>
                  <h2>Limites par plan</h2>
                </div>
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Plan</th>
                        <th>Requêtes / jour</th>
                        <th>Comptes</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Sans compte (anonyme)</td>
                        <td className={styles.num}>{ANONYMOUS_PLAN.dailyQuota}</td>
                        <td className={styles.num}>{stats?.devices.anonymous || 0} appareils</td>
                      </tr>
                      {PLAN_IDS.map((id) => (
                        <tr key={id}>
                          <td>
                            <span className={`${styles.badge} ${PLAN_BADGE[id]}`}>{PLAN_LABEL[id]}</span>
                          </td>
                          <td className={styles.num}>{PLANS[id].dailyQuota}</td>
                          <td className={styles.num}>{planCounts[id]}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className={styles.card}>
                <div className={styles.cardHead}>
                  <h2>Dérogations actives</h2>
                  <span className={styles.badge}>{overrides.length}</span>
                </div>
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Utilisateur</th>
                        <th>Plan</th>
                        <th>Quota par défaut</th>
                        <th>Quota personnalisé</th>
                      </tr>
                    </thead>
                    <tbody>
                      {overrides.length === 0 && (
                        <tr>
                          <td colSpan={4} className={styles.empty}>
                            Aucune dérogation. Définissez un quota personnalisé depuis l’onglet Utilisateurs.
                          </td>
                        </tr>
                      )}
                      {overrides.map((u) => (
                        <tr key={u.id}>
                          <td>{u.email || u.github_login || u.id}</td>
                          <td>
                            <span className={`${styles.badge} ${PLAN_BADGE[u.plan]}`}>{PLAN_LABEL[u.plan]}</span>
                          </td>
                          <td className={styles.num}>{PLANS[u.plan].dailyQuota}</td>
                          <td className={styles.num}>{u.daily_limit_override}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}

          {/* ---------------------------------------------- Abonnements */}
          {activeTab === "subscriptions" && (
            <>
              <section className={styles.grid4}>
                {PLAN_IDS.map((id) => (
                  <div key={id} className={styles.planCard}>
                    <div className={styles.planName}>
                      <span>{PLAN_LABEL[id]}</span>
                      <span className={`${styles.badge} ${PLAN_BADGE[id]}`}>{PLANS[id].dailyQuota}/jour</span>
                    </div>
                    <div className={styles.planCount}>{planCounts[id]}</div>
                    <div className={styles.planMeta}>
                      {PLANS[id].priceFcfa === 0
                        ? "Gratuit"
                        : `${fmtNumber(PLANS[id].priceFcfa)} FCFA / ${PLANS[id].period === "month" ? "mois" : "3 mois"}`}
                    </div>
                  </div>
                ))}
              </section>

              <section className={`${styles.card} ${styles.cardPad}`}>
                <div className={styles.cardHead} style={{ margin: "-22px -22px 20px" }}>
                  <h2>Répartition des comptes</h2>
                  <span className={styles.muted}>{totalUsers} au total</span>
                </div>
                <div className={styles.bars}>
                  {PLAN_IDS.map((id) => (
                    <div key={id} className={styles.barRow}>
                      <span className={styles.barLabel}>{PLAN_LABEL[id]}</span>
                      <div className={styles.barTrack}>
                        <div className={styles.barFill} style={{ width: `${totalUsers ? (planCounts[id] / totalUsers) * 100 : 0}%` }} />
                      </div>
                      <span className={styles.barValue}>{planCounts[id]}</span>
                    </div>
                  ))}
                </div>
              </section>

              <section className={`${styles.card} ${styles.cardPad}`}>
                <div className={styles.switchRow}>
                  <div>
                    <h2 className={styles.cardTitle}>Revenu mensuel estimé</h2>
                    <p className={styles.muted}>Calculé à partir des prix publics ; le Pass étudiant est ramené au mois.</p>
                  </div>
                  <div className={styles.kpiValue}>{fmtNumber(Math.round(monthlyRevenue))} FCFA</div>
                </div>
              </section>
            </>
          )}

          {/* ------------------------------------------------------ Stats */}
          {activeTab === "stats" && (
            <>
              <section className={styles.grid4}>
                <div className={styles.kpi}>
                  <span className={styles.kpiLabel}>Requêtes (24 h)</span>
                  <div className={styles.kpiValue}>{fmtNumber(totalAsks)}</div>
                </div>
                <div className={styles.kpi}>
                  <span className={styles.kpiLabel}>Taux de succès</span>
                  <div className={styles.kpiValue}>{successRate === null ? "—" : `${successRate} %`}</div>
                </div>
                <div className={styles.kpi}>
                  <span className={styles.kpiLabel}>Latence moyenne</span>
                  <div className={styles.kpiValue}>{latency ? `${Math.round(latency)} ms` : "—"}</div>
                </div>
                <div className={styles.kpi}>
                  <span className={styles.kpiLabel}>Comptes suspendus</span>
                  <div className={styles.kpiValue}>{stats?.users.banned || 0}</div>
                </div>
              </section>

              <section className={`${styles.card} ${styles.cardPad}`}>
                <h2 className={styles.cardTitle} style={{ marginBottom: 18 }}>Appareils</h2>
                <div className={styles.bars}>
                  {[
                    { label: "Liés à un compte", value: stats?.devices.registered || 0 },
                    { label: "Anonymes", value: stats?.devices.anonymous || 0 },
                  ].map((row) => (
                    <div key={row.label} className={styles.barRow}>
                      <span className={styles.barLabel}>{row.label}</span>
                      <div className={styles.barTrack}>
                        <div className={styles.barFill} style={{ width: `${stats?.devices.total ? (row.value / stats.devices.total) * 100 : 0}%` }} />
                      </div>
                      <span className={styles.barValue}>{row.value}</span>
                    </div>
                  ))}
                </div>
              </section>

              <section className={`${styles.card} ${styles.cardPad}`}>
                <div className={styles.switchRow}>
                  <div>
                    <h2 className={styles.cardTitle}>Service LLM</h2>
                    <p className={styles.muted}>
                      {killSwitch
                        ? "Le Kill Switch est actif : toutes les requêtes sont bloquées."
                        : "Le service répond normalement. Le Kill Switch bloque toutes les requêtes en cas d’urgence."}
                    </p>
                  </div>
                  <button
                    type="button"
                    className={`${styles.btn} ${killSwitch ? styles.btnPrimary : styles.btnDanger}`}
                    onClick={() => void handleToggleKillSwitch(!killSwitch)}
                  >
                    {killSwitch ? "Réactiver le service" : "Activer le Kill Switch"}
                  </button>
                </div>
              </section>
            </>
          )}

          {/* ------------------------------------------------------ Emails */}
          {activeTab === "emails" && (
            <section className={styles.grid2}>
              {[
                { title: "Tous les emails", desc: "Comptes inscrits et liste d’attente.", href: "/api/v1/admin/emails/export" },
                { title: "Opt-in uniquement", desc: "Contacts ayant accepté la newsletter.", href: "/api/v1/admin/emails/export?optIn=true" },
                { title: "Non opt-in", desc: "Contacts n’ayant pas accepté la newsletter.", href: "/api/v1/admin/emails/export?optIn=false" },
              ].map((item) => (
                <div key={item.href} className={styles.exportCard}>
                  <div>
                    <h3>{item.title}</h3>
                    <p>{item.desc}</p>
                  </div>
                  <a href={item.href} className={`${styles.btn}`} style={{ alignSelf: "flex-start" }}>
                    <Icon name="download" />
                    Télécharger le CSV
                  </a>
                </div>
              ))}
            </section>
          )}

          {/* ------------------------------------------------------- Logs */}
          {activeTab === "logs" && (
            <section className={styles.card}>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Acteur</th>
                      <th>Action</th>
                      <th>Cible</th>
                      <th>Détails</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.length === 0 && (
                      <tr>
                        <td colSpan={5} className={styles.empty}>
                          Aucune entrée dans le journal.
                        </td>
                      </tr>
                    )}
                    {logs.map((log) => (
                      <tr key={log.id}>
                        <td className={`${styles.nowrap} ${styles.num}`}>{fmtDateTime(log.at)}</td>
                        <td>{log.actor_email || log.actor_id}</td>
                        <td>
                          <span className={`${styles.badge} ${styles.mono}`}>{log.action}</span>
                        </td>
                        <td className={`${styles.num} ${styles.mono}`}>{log.target_id || "—"}</td>
                        <td>
                          <div className={`${styles.details} ${styles.mono}`} title={JSON.stringify(log.details)}>
                            {JSON.stringify(log.details)}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      </main>

      {message && (
        <div className={`${styles.toast} ${message.type === "success" ? styles.toastSuccess : styles.toastError}`} role="status">
          {message.text}
        </div>
      )}
    </div>
  );
}