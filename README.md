<div align="center">

# ezShell

**Dis ce que tu veux faire. ezShell trouve la commande, l'explique et te dit si elle est risquée.**

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Licence](https://img.shields.io/badge/licence-MIT-green)
![Version](https://img.shields.io/badge/version-0.1.0-orange)
![Statut](https://img.shields.io/badge/statut-MVP-yellow)

[Installation](#installation) · [Démarrage rapide](#démarrage-rapide) · [Documentation](docs/guide-utilisateur.md) · [Contribuer](CONTRIBUTING.md) · [Sécurité](SECURITY.md)

</div>

---

## À propos

ezShell est un assistant IA pour le terminal, propulsé par l'API de [Groq](https://groq.com) et doté d'une interface [Rich](https://github.com/Textualize/rich). Tu décris ce que tu veux faire en langage naturel, il propose la commande, l'explique et indique son niveau de risque.

```text
$ ezsh "supprime les .log de plus de 7 jours"

  Commande   find . -name "*.log" -mtime +7 -delete
  Explication  Cherche les fichiers .log modifiés il y a plus de 7 jours
               dans le dossier courant et les supprime.
  Risque     ÉLEVÉ  (-delete détecté)

  [Entrée] exécuter · [c] copier · [e] éditer · [q] fermer
```

> L'exemple ci-dessus illustre le fonctionnement ; le rendu exact peut varier.

## Captures d'écran

<div align="center">

![Demande en langage naturel](docs/images/demo.png)
*Une demande en langage naturel : commande, explication et niveau de risque.*

</div>

<table>
  <tr>
    <td align="center">
      <img src="docs/images/risque-eleve.png" alt="Confirmation pour une commande à risque élevé" width="400"><br>
      <em>Confirmation « oui » pour une commande à risque élevé</em>
    </td>
    <td align="center">
      <img src="docs/images/erreur.png" alt="Explication d'une erreur" width="400"><br>
      <em>Explication d'une erreur avec la correction proposée</em>
    </td>
  </tr>
</table>

## Fonctionnalités

- **Langage naturel vers commande** avec explication.
- **Niveau de risque** : faible, moyen ou élevé. L'avis du modèle est complété par des règles locales (`rm -rf`, `-delete`, `sudo`, `git push --force`, `curl | sh`…). Le niveau le plus prudent est toujours retenu.
- **Explication d'erreurs** : cause probable et correction proposée, y compris depuis un pipe.
- **Actions maîtrisées** : exécuter, copier, éditer ou fermer. Une commande à risque élevé exige de taper `oui`.
- **Contexte automatique** : système, shell, dossier courant et présence d'un dépôt Git sont transmis au modèle.

## Installation

**Prérequis** : Python 3.10 ou plus récent et une clé API Groq.

```bash
git clone https://github.com/<votre-utilisateur>/ezshell.git
cd ezshell
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -e .
```

## Configuration

```bash
cp .env.example .env             # puis renseigne ta clé API Groq
```

Pour utiliser ezShell depuis n'importe quel dossier, place le fichier `.env` dans `~/.config/aiterm/.env`.

| Variable | Description | Défaut |
|---|---|---|
| Clé API Groq | Voir `.env.example` pour le nom exact | — |
| `GROQ_MODEL` | Modèle utilisé | `llama-3.3-70b-versatile` |

## Démarrage rapide

```bash
ezsh                                 # fenêtre interactive
ezsh "supprime les .log de plus de 7 jours"
ezsh erreur "fatal: not a git repository"
git push 2>&1 | ezsh erreur          # lit l'erreur depuis un pipe (affichage seul)
```

Dans la fenêtre interactive, `/erreur <texte>` analyse une erreur.

## Documentation

| Document | Contenu |
|---|---|
| [Guide utilisateur](docs/guide-utilisateur.md) | Installation, usage, risques, dépannage, FAQ |
| [Description du projet](DESCRIPTION.md) | Slogan, description courte et longue, topics |
| [Contribuer](CONTRIBUTING.md) | Environnement de développement, conventions, pull requests |
| [Sécurité](SECURITY.md) | Signaler une vulnérabilité |
| [Changelog](CHANGELOG.md) | Historique des versions |

## Architecture

```text
ezshell/
├── pyproject.toml        # installation et commande `ezsh`
├── requirements.txt
├── .env.example
├── docs/                 # documentation utilisateur
├── .github/              # modèles d'issues et de pull requests
└── aiterm/
    ├── cli.py            # point d'entrée, boucle interactive, actions
    ├── llm.py            # appel à Groq, format de réponse JSON
    ├── risk.py           # règles locales de niveau de risque
    ├── context.py        # infos système envoyées au modèle
    └── ui.py             # fenêtre Rich centrée
```

## Sécurité et confidentialité

- Rien n'est exécuté sans ton action ; `q` ferme sans rien faire.
- Les commandes à risque élevé demandent une confirmation explicite.
- Les règles locales ne remplacent pas ta relecture : lis toujours la commande avant de l'exécuter.
- Ton texte, le dossier courant et les infos système sont envoyés à Groq. **N'y colle jamais de secrets** (mots de passe, clés, tokens).

Pour signaler une vulnérabilité, consulte [SECURITY.md](SECURITY.md).

## Limites connues

- Le terminal n'est pas lu automatiquement : l'erreur doit être collée ou passée par un pipe.
- Une seule commande est proposée à la fois, sans historique de conversation.
- Les règles de risque sont une liste de motifs, donc incomplète.

## Feuille de route

- [ ] Historique des questions (flèches haut et bas)
- [ ] Capture automatique de la dernière erreur via une fonction du shell (bash, zsh, PowerShell)
- [ ] Mode apprentissage : explication détaillée de chaque morceau d'une commande
- [ ] Fenêtre flottante plus avancée avec Textual
- [ ] Tests automatiques pour `risk.py`

## Contribuer

Les contributions sont les bienvenues. Lis [CONTRIBUTING.md](CONTRIBUTING.md) avant d'ouvrir une pull request, et respecte le [code de conduite](CODE_OF_CONDUCT.md).

## Licence

Distribué sous licence MIT. Voir [LICENSE](LICENSE).
