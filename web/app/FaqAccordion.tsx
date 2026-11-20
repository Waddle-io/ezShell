"use client";

import { useState } from "react";

const FAQ_ITEMS = [
  {
    q: "Est-ce qu'ezShell exécute les commandes à ma place ?",
    a: "Jamais. ezShell insère la commande suggérée directement dans votre prompt terminal. Vous gardez le contrôle total : vous relisez la commande, pouvez l'éditer, la copier ou simplement l'exécuter avec Entrée.",
  },
  {
    q: "Faut-il obligatoirement fournir une clé d'API ?",
    a: "Non. ezShell inclut un quota gratuit prêt à l'emploi via son proxy sécurisé. Si vous disposez de votre propre clé (Groq, OpenAI, etc.), vous pouvez la configurer via `ezsh --set-key <votre-clé>` pour lever tout quota.",
  },
  {
    q: "Faut-il créer un compte pour utiliser ezShell ?",
    a: "Non. ezShell fonctionne immédiatement dès l'installation avec un identifiant anonyme généré localement. Le compte est strictement optionnel pour suivre votre quota quotidien depuis l'interface web.",
  },
  {
    q: "Que se passe-t-il si je pose une question plutôt qu'une erreur ?",
    a: "ezShell fonctionne dans les deux sens : si vous tapez une phrase en français ou en anglais dans votre prompt (ex: « trouver les fichiers .log de plus de 100 Mo ») et pressez Alt+E, il la traduit instantanément en commande shell optimisée.",
  },
  {
    q: "Mes identifiants et secrets sont-ils protégés ?",
    a: "Absolument. Un filtre de caviardage local strict analyse le contenu de la commande et masque systématiquement clés API, mots de passe, tokens et clés SSH avant tout appel réseau.",
  },
  {
    q: "Comment mettre à jour ou désinstaller l'outil ?",
    a: "La mise à jour s'effectue via `ezsh --update`. Pour le désinstaller, supprimez la ligne d'initialisation de votre configuration shell (~/.zshrc, ~/.bashrc) puis lancez `pipx uninstall ezshell`.",
  },
];

export default function FaqAccordion() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  function toggle(idx: number) {
    setOpenIndex(openIndex === idx ? null : idx);
  }

  return (
    <div className="faq-container">
      {FAQ_ITEMS.map((item, idx) => {
        const isOpen = openIndex === idx;
        return (
          <div key={idx} className={`faq-item ${isOpen ? "open" : ""}`}>
            <button
              className="faq-trigger"
              onClick={() => toggle(idx)}
              aria-expanded={isOpen}
              type="button"
            >
              <span>{item.q}</span>
              <span className="faq-icon" aria-hidden="true">+</span>
            </button>
            {isOpen && (
              <div className="faq-content">
                <p style={{ margin: 0 }}>{item.a}</p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
