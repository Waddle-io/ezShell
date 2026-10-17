"""M0 : prototypes de bout en bout sous un vrai pseudo-terminal (bash et zsh).

Critère de réussite du jalon : la capture de la dernière commande + l'insertion dans le
prompt tiennent sur 3 scénarios. Aucune commande n'est jamais exécutée à l'insertion.
"""

import shutil
import sys
from pathlib import Path

import pytest

pexpect = pytest.importorskip("pexpect")

BIN = str(Path(sys.executable).parent)
SHELLS = [s for s in ("bash", "zsh") if shutil.which(s)]
ALT_E = "\x1be"


def spawn(shell, tmp_path, **extra):
    env = {
        "PATH": f"{BIN}:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "TERM": "xterm",
        "LANG": "C.UTF-8",
        "EZSHELL_LANG": "fr",
        "EZSH_STATE_DIR": str(tmp_path / "state"),
        "EZSH_MOCK_LLM": "1",
        "XDG_CONFIG_HOME": str(tmp_path / "cfg"),
    }
    env.update(extra)
    args = ["--noprofile", "--norc", "-i"] if shell == "bash" else ["-f", "-i"]
    child = pexpect.spawn(
        shell, args, env=env, encoding="utf-8", timeout=20, dimensions=(30, 100), cwd=str(tmp_path)
    )
    prompt_var = "PS1" if shell == "bash" else "PROMPT"
    child.sendline(f'{prompt_var}=\'EZ\'"P> "; eval "$(ezsh init {shell})"')
    child.expect("EZP> ")
    return child


@pytest.mark.parametrize("shell", SHELLS)
def test_scenario_1_error_capture_then_insert_without_executing(shell, tmp_path):
    marker = tmp_path / "executed.flag"
    c = spawn(shell, tmp_path, EZSH_MOCK_COMMAND=f"touch {marker}")
    c.sendline("ezsh run -- ls /nonexistent_ezsh_dir")
    c.expect("EZP> ")
    c.send(ALT_E)
    c.expect("RISQUE FAIBLE")
    c.send("\r")
    c.expect("Commande insérée")
    c.expect(str(marker))  # la commande est dans la ligne de saisie…
    assert not marker.exists()  # …mais n'a PAS été exécutée
    c.send("\r")  # c'est l'utilisateur qui valide
    c.expect("EZP> ")
    assert marker.exists()
    c.close()


@pytest.mark.parametrize("shell", SHELLS)
def test_scenario_2_natural_language_high_risk_needs_explicit_y(shell, tmp_path):
    c = spawn(shell, tmp_path)
    c.send("supprime les logs de plus de 7 jours")  # texte laissé dans la ligne de saisie
    c.send(ALT_E)
    c.expect("RISQUE ÉLEVÉ")
    c.expect("relevé par les règles")  # le modèle annonçait « faible »
    c.send("\r")  # Entrée ne suffit pas pour un risque élevé
    c.send("y")
    c.expect("Commande insérée")
    c.expect("find . -name")
    c.sendcontrol("c")  # on abandonne la ligne : rien n'a tourné
    c.expect("EZP> ")
    c.sendline("echo $((20+22))")
    c.expect("42")
    c.close()


@pytest.mark.parametrize("shell", SHELLS)
def test_scenario_3_hook_only_context_then_cancel(shell, tmp_path):
    c = spawn(shell, tmp_path)
    c.sendline("false")  # pas d'`ezsh run` : seuls code et commande sont connus
    c.expect("EZP> ")
    c.send(ALT_E)
    c.expect("Sortie d'erreur non capturée")
    c.send("q")
    c.sendline("echo $((6*7))")
    c.expect("42")
    c.close()


@pytest.mark.parametrize("shell", SHELLS)
def test_degraded_states_do_not_block_the_terminal(shell, tmp_path):
    c = spawn(shell, tmp_path, EZSH_MOCK_LLM="offline")
    c.sendline("false")
    c.expect("EZP> ")
    c.send(ALT_E)
    c.expect("Hors ligne")
    c.send("q")
    c.sendline("echo $((1+1))")
    c.expect("2")
    c.close()


@pytest.mark.parametrize("shell", SHELLS)
def test_state_is_per_terminal(shell, tmp_path):
    a = spawn(shell, tmp_path)
    b = spawn(shell, tmp_path)
    a.sendline("ezsh run -- ls /only_in_a")
    a.expect("EZP> ")
    b.sendline("ezsh run -- ls /only_in_b")
    b.expect("EZP> ")
    files = sorted(p.name for p in (tmp_path / "state").glob("*.run.json"))
    assert len(files) == 2
    texts = [p.read_text() for p in (tmp_path / "state").glob("*.run.json")]
    assert any("only_in_a" in t for t in texts) and any("only_in_b" in t for t in texts)
    a.close()
    b.close()
