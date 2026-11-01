import type { ReactNode } from "react";

// Textes de la page d'accueil (nouvelles sections). Voix : tutoiement, phrases courtes, sans jargon.

export const NEWS: ReadonlyArray<{ title: string; text: ReactNode }> = [
  {
    title: "Un compte gratuit, si tu le souhaites",
    text: "Connecte-toi avec un lien envoyé par e-mail ou avec GitHub, sans mot de passe à retenir. Un tableau de bord montre ton quota du jour et les appareils reliés à ton compte. Sans compte, ezShell fonctionne comme avant.",
  },
  {
    title: "Un terminal relié avec ton accord",
    text: "Quand tu relies un terminal à ton compte, la page te montre un code. Tu le compares à celui du terminal, puis tu approuves toi-même. Un lien piégé ne suffit plus pour relier l'appareil de quelqu'un d'autre à ton compte.",
  },
  {
    title: "Mise à jour en une commande",
    text: (
      <>
        La commande <code>ezsh --update</code> affiche les nouveautés, te demande confirmation, puis met à jour.
        Quand une version est disponible, un rappel discret apparaît au plus une fois par jour.
      </>
    ),
  },
  {
    title: "Des raccourcis à ta façon",
    text: (
      <>
        Remplace <kbd>Alt</kbd>+<kbd>E</kbd> par la combinaison que tu préfères. ezShell te prévient en cas de conflit.
      </>
    ),
  },
  {
    title: "Plusieurs interfaces",
    text: "Le panneau s'ouvre dans ton terminal. Tu peux aussi utiliser une interface plein terminal ou une fenêtre de bureau.",
  },
];

export const WITHOUT_ACCOUNT = [
  "Ton appareil reçoit un identifiant anonyme au premier usage, avec un quota quotidien gratuit.",
  "Tu n'as ni inscription ni e-mail à fournir.",
] as const;

export const WITH_ACCOUNT = [
  "Tu vois ton quota du jour dans un tableau de bord.",
  "Tu peux retirer l'accès d'un appareil que tu n'utilises plus.",
  "Tu te connectes par lien magique ou avec GitHub.",
] as const;
