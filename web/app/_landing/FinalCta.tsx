import CopyButton from "../CopyButton";
import styles from "./landing.module.css";

export default function FinalCta({ installCommand }: { installCommand: string }) {
  return (
    <section className="section shell" aria-labelledby="cta-title">
      <div className={styles.cta}>
        <div>
          <h2 id="cta-title">Essaie-le sur ta prochaine erreur.</h2>
          <p>L'installation prend deux minutes et ne demande aucun compte.</p>
        </div>
        <div className={styles.ctaAction}>
          <div className="install-box" aria-label="Commande d'installation">
            <code><span className="prompt">$</span> {installCommand}</code>
            <CopyButton value={installCommand} label="Copier la commande d'installation" />
          </div>
          <a href="#installation">Voir les étapes d'installation</a>
        </div>
      </div>
    </section>
  );
}
