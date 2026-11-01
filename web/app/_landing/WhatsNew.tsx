import { NEWS } from "./content";
import styles from "./landing.module.css";

export default function WhatsNew() {
  return (
    <section className="section shell" id="nouveautes" aria-labelledby="news-title">
      <div className="section-intro">
        <p className="eyebrow">nouveautés</p>
        <h2 id="news-title">Ce qui a changé récemment.</h2>
        <p className="section-lede">Les évolutions récentes d'ezShell, côté terminal et côté site.</p>
      </div>
      <ul className={styles.news}>
        {NEWS.map(({ title, text }) => (
          <li className={styles.newsItem} key={title}>
            <h3 className={styles.newsTitle}>{title}</h3>
            <p className={styles.newsText}>{text}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
