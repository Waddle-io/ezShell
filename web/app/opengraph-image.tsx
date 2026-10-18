import { ImageResponse } from "next/og";

export const alt = "ezShell : une commande échoue, Alt+E explique l'erreur et propose la correction";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const C = {
  bg: "#111315",
  card: "#0c0e0f",
  border: "#2a3033",
  text: "#f4f1ea",
  faint: "#6f7a7b",
  accent: "#2dd4bf",
  ok: "#34d399",
};

// Généré au build (aucune donnée dynamique) : pas de coût à l'exécution.
export default function Image() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", background: C.bg, padding: "64px 72px", color: C.text }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 48, height: 48, borderRadius: 12, background: C.accent, color: C.bg, fontSize: 26, fontWeight: 700 }}>
            {">_"}
          </div>
          <div style={{ display: "flex", fontSize: 34, fontWeight: 700 }}>
            <span style={{ color: C.accent }}>ez</span>
            <span>Shell</span>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", fontSize: 80, fontWeight: 700, lineHeight: 1.06, letterSpacing: -2 }}>
          <span>Ton terminal t'explique</span>
          <span>ses erreurs.</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 14, background: C.card, border: `2px solid ${C.border}`, borderRadius: 16, padding: "26px 32px", fontSize: 27 }}>
          <div style={{ display: "flex", gap: 14 }}>
            <span style={{ color: C.accent }}>$</span>
            <span>git push origin main</span>
          </div>
          <div style={{ display: "flex", color: C.faint }}>fatal: la branche 'main' n'a pas de branche amont</div>
          <div style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 4 }}>
            <span style={{ display: "flex", padding: "4px 14px", borderRadius: 8, background: "rgba(52, 211, 153, 0.14)", color: C.ok, fontSize: 22, fontWeight: 700 }}>
              RISQUE FAIBLE
            </span>
            <span style={{ color: C.accent }}>git push --set-upstream origin main</span>
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}