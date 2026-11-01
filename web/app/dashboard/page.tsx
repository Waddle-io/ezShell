"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authClient } from "@/lib/auth-client";
import styles from "./dashboard.module.css";

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
    await authClient.signOut();
    router.push("/login");
  }

  if (loading) {
    return (
      <div className={styles.loading}>
        <p className={styles.loadingText}>Chargement de votre tableau de bord...</p>
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
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div className={styles.brandGroup}>
            <Link href="/" className={styles.brand}>
              ezShell
            </Link>
            <span className={styles.badge}>
              Dashboard
            </span>
            {user?.role === "admin" && (
              <Link
                href="/admin"
                className={styles.adminLink}
              >
                ★ Console Admin
              </Link>
            )}
          </div>
          <div className={styles.userActions}>
            <span className={styles.email}>{user?.email || user?.github_login}</span>
            <button
              onClick={handleLogout}
              className={styles.logoutButton}
            >
              Déconnexion
            </button>
          </div>
        </div>
      </header>

      <main className={styles.main}>
        {message && (
          <div
            className={`${styles.alert} ${
              message.type === "success"
                ? styles.alertSuccess
                : styles.alertError
            }`}
          >
            {message.text}
          </div>
        )}

        {/* Section Quota & Consommation */}
        <section className={styles.sectionGrid}>
          <div className={styles.quotaCard}>
            <div className={styles.sectionHeader}>
              <div>
                <h2 className={styles.sectionTitle}>Consommation journalière</h2>
                <p className={styles.sectionDescription}>Réinitialisation automatique chaque jour à minuit UTC</p>
              </div>
              <span className={styles.planBadge}>
                Plan {quota?.tier}
              </span>
            </div>

            <div className={styles.quotaDetails}>
              <div className={styles.quotaRow}>
                <span>Requêtes utilisées aujourd&apos;hui :</span>
                <span className={styles.quotaValue}>
                  {used} {isUnlimited ? "(Illimité)" : `/ ${limit}`}
                </span>
              </div>
              {!isUnlimited && (
                <div className={styles.progressTrack}>
                  <div
                    className={`${styles.progressFill} ${
                      percentage > 85 ? styles.progressDanger : percentage > 60 ? styles.progressWarning : ""
                    }`}
                    style={{ width: `${percentage}%` }}
                  ></div>
                </div>
              )}
              <div className={styles.quotaMeta}>
                <span>Restantes : {isUnlimited ? "∞" : quota?.remaining_today}</span>
                <span>Reset UTC : {quota?.reset_at ? new Date(quota.reset_at).toLocaleTimeString() : "--"}</span>
              </div>
            </div>
          </div>

          <div className={styles.connectCard}>
            <div>
              <h3 className={styles.connectTitle}>Connecter un terminal</h3>
              <p className={styles.connectDescription}>
                Lancez <code className={styles.code}>ezsh login</code> dans votre terminal pour lier votre machine à ce compte.
              </p>
            </div>
            <Link
              href="/activate"
              className={styles.activateLink}
            >
              Saisir un code d&apos;activation ›
            </Link>
          </div>
        </section>

        {/* Section Appareils connectés */}
        <section className={styles.card}>
          <div className={styles.sectionHeader}>
            <div>
              <h2 className={styles.sectionTitle}>Appareils et terminaux autorisés</h2>
              <p className={styles.sectionDescription}>Gérez les sessions de vos machines connectées</p>
            </div>
            <span className={styles.sectionDescription}>
              {data?.devices?.length || 0} appareil(s) actif(s)
            </span>
          </div>

          <div className={styles.devicesList}>
            {data?.devices && data.devices.length > 0 ? (
              data.devices.map((dev) => (
                <div key={dev.id} className={styles.deviceRow}>
                  <div className={styles.deviceInfo}>
                    <p className={styles.deviceId}>ID : {dev.id}</p>
                    <p className={styles.deviceMeta}>
                      Connecté le {new Date(dev.created_at).toLocaleDateString()} • Vu pour la dernière fois : {new Date(dev.last_seen_at).toLocaleTimeString()}
                    </p>
                  </div>
                  <button
                    onClick={() => handleRevokeDevice(dev.id)}
                    disabled={revoking === dev.id}
                    className={styles.revokeButton}
                  >
                    {revoking === dev.id ? "Révocation..." : "Révoquer"}
                  </button>
                </div>
              ))
            ) : (
              <p className={styles.emptyState}>Aucun appareil lié pour le moment.</p>
            )}
          </div>
        </section>

        {/* Section Détails du compte */}
        <section className={styles.card}>
          <h2 className={styles.sectionTitle}>Détails du compte</h2>
          <div className={styles.accountGrid}>
            <div className={styles.detailItem}>
              <span className={styles.detailLabel}>Identifiant :</span>
              <span className={`${styles.detailValue} ${styles.detailValueMono}`}>{user?.id}</span>
            </div>
            <div className={styles.detailItem}>
              <span className={styles.detailLabel}>E-mail :</span>
              <span className={styles.detailValue}>{user?.email || "Non renseigné"}</span>
            </div>
            <div className={styles.detailItem}>
              <span className={styles.detailLabel}>GitHub :</span>
              <span className={styles.detailValue}>{user?.github_login ? `@${user.github_login}` : "Non lié"}</span>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
