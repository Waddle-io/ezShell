import CopyButton from "../CopyButton";
import styles from "./landing.module.css";

// Une commande par système : installe pipx puis ajoute son dossier au PATH.
const PIPX_COMMANDS = [
  ["Debian, Ubuntu, Parrot", "sudo apt install pipx && pipx ensurepath"],
  ["macOS", "brew install pipx && pipx ensurepath"],
  ["Fedora", "sudo dnf install pipx && pipx ensurepath"],
  ["Arch", "sudo pacman -S python-pipx && pipx ensurepath"],
  ["Windows (PowerShell)", "py -m pip install --user pipx; py -m pipx ensurepath"],
] as const;

const ONE_LINE_INSTALLER = "curl -fsSL https://raw.githubusercontent.com/Waddle-io/ezShell/main/install.sh | bash";

export default function PipxHelp() {
  return (
    <details className={styles.pipx}>
      <summary>pipx n'est pas installé ?</summary>
      <dl className={styles.pipxList}>
        {PIPX_COMMANDS.map(([system, command]) => (
          <div key={system}>
            <dt>{system}</dt>
            <dd>
              <div className="code-line">
                <code>{command}</code>
                <CopyButton value={command} label={`Copier la commande d'installation de pipx (${system})`} compact />
              </div>
            </dd>
          </div>
        ))}
      </dl>
      <p className={styles.pipxNote}>Ferme et rouvre ton terminal, puis lance la commande d'installation d'ezShell.</p>
      <p className={styles.pipxNote}>
        Autre option sous Linux et macOS : l'installateur en une ligne, qui n'a pas besoin de pipx. Il installe la version
        de développement depuis GitHub et demande Python 3.10 ou plus récent, ainsi que git.
      </p>
      <div className="code-line">
        <code>{ONE_LINE_INSTALLER}</code>
        <CopyButton value={ONE_LINE_INSTALLER} label="Copier la commande de l'installateur en une ligne" compact />
      </div>
    </details>
  );
}
