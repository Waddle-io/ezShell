import { WITH_ACCOUNT, WITHOUT_ACCOUNT } from "./content";
import styles from "./landing.module.css";

export default function AccountSection() {
  return (
    <section className="section shell" id="compte" aria-labelledby="account-title">
      <div className="section-intro">
        <p className="eyebrow">compte</p>
        <h2 id="account-title">Un compte, seulement si tu en as besoin.</h2>
        <p className="section-lede">
          ezShell fonctionne dès l'installation, sans inscription. Le compte sert à retrouver ton quota et tes appareils
          au même endroit.
        </p>
      </div>
      <div className="privacy-grid">
        <div className="privacy-col">
          <h3>Sans compte</h3>
          <ul>{WITHOUT_ACCOUNT.map((s) => <li key={s}>{s}</li>)}</ul>
        </div>
        <div className="privacy-col">
          <h3>Avec un compte gratuit</h3>
          <ul>{WITH_ACCOUNT.map((s) => <li key={s}>{s}</li>)}</ul>
        </div>
      </div>
      <div className={styles.accountActions}>
        <a className="button-link" href="/login">Se connecter ou créer un compte</a>
      </div>
    </section>
  );
}
