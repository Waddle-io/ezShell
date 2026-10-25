"""Mise à jour : versions, notes, rappel quotidien, détection d'installation, confirmation."""
# ruff: noqa: E501

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core import updater
from src.core.updater import (
    InstallPlan,
    cached_latest,
    collect_notes,
    compare_versions,
    detect_install,
    fetch_release_info,
    format_notes,
    note_latest,
    parse_version,
    run_update,
    take_notice,
    version_hint,
)

REL_02 = {"version": "0.2.0", "important": [], "added": ["Commande --update"], "fixed": []}
REL_03 = {
    "version": "0.3.0",
    "important": ["Lance `ezsh login`"],
    "added": ["Comptes", "Commande --update"],
    "fixed": ["Un bug"],
}


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("EZSHELL_LANG", "fr")
    monkeypatch.delenv("EZSH_NO_UPDATE_CHECK", raising=False)
    monkeypatch.setattr(updater, "installed_version", lambda: "0.1.0")


def test_versions():
    assert parse_version("v0.3") == (0, 3, 0)
    assert parse_version("n'importe quoi") == (0, 0, 0)
    assert compare_versions("0.10.0", "0.2.0") == 1
    assert compare_versions("0.2.0", "0.2.0") == 0
    assert compare_versions("", "0.0.1") == -1


# ---------------------------------------------------------------- nouveautés
def test_notes_cumulees_sans_doublon_important_en_premier():
    notes = collect_notes([REL_03, REL_02])
    assert notes["added"] == ["Commande --update", "Comptes"]
    lines = format_notes("0.1.0", "0.3.0", [REL_02, REL_03], "fr")
    assert lines[0] == "ezShell 0.1.0 → 0.3.0"
    assert lines.index("⚠ Important") < lines.index("Nouveautés") < lines.index("Corrections")


def test_notes_tronquees_a_dix_lignes():
    rel = {"version": "0.2.0", "important": [], "added": [f"n{i}" for i in range(14)], "fixed": []}
    lines = format_notes("0.1.0", "0.2.0", [rel], "fr")
    assert sum(1 for line in lines if line.startswith("  •")) == 10
    assert "4 autres" in lines[-1] and updater.RELEASES_URL in lines[-1]


def test_sans_notes_renvoie_vers_les_releases():
    assert updater.RELEASES_URL in format_notes("0.1.0", "0.2.0", [], "en")[-1]


# ---------------------------------------------------------------- réseau
class FakeResp:
    def __init__(self, payload):
        self._raw = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._raw


def test_fetch_nettoie_les_textes_du_serveur():
    payload = {
        "latest": "0.2.0",
        "min_supported": "0.1.0",
        "releases": [{"version": "0.2.0", "added": ["ok\x1b[31mROUGE\x1b[0m\x07", 42], "important": [], "fixed": []}],
    }
    info = fetch_release_info("https://x", "0.1.0", opener=lambda *a, **k: FakeResp(payload))
    assert info["releases"][0]["added"] == ["okROUGE"]


@pytest.mark.parametrize("payload", [{"latest": "pas-une-version"}, {"releases": []}, []])
def test_fetch_refuse_les_reponses_invalides(payload):
    assert fetch_release_info("https://x", "0.1.0", opener=lambda *a, **k: FakeResp(payload)) is None


def test_fetch_hors_ligne():
    def boom(*a, **k):
        raise OSError("offline")

    assert fetch_release_info("https://x", "0.1.0", opener=boom) is None


# ---------------------------------------------------------------- rappel quotidien
def test_rappel_une_fois_par_jour(tmp_path):
    p = tmp_path / "u.json"
    note_latest("0.2.0", p)
    assert cached_latest(p) == "0.2.0"
    msg = take_notice(now=1000.0, path=p)
    assert msg and "0.1.0 → 0.2.0" in msg and "ezsh --update" in msg
    assert take_notice(now=1000.0 + 3600, path=p) is None  # trop tôt
    assert take_notice(now=1000.0 + 24 * 3600 + 1, path=p) is not None  # le lendemain


def test_pas_de_rappel_si_a_jour_ou_desactive(tmp_path, monkeypatch):
    p = tmp_path / "u.json"
    note_latest("0.1.0", p)
    assert take_notice(path=p) is None
    note_latest("0.2.0", p)
    monkeypatch.setenv("EZSH_NO_UPDATE_CHECK", "1")
    assert take_notice(path=p) is None
    assert version_hint(p) is None


def test_note_latest_ignore_les_valeurs_bizarres(tmp_path):
    p = tmp_path / "u.json"
    for bad in (None, "", "x", "1.2", "0.2.0\x1b[31m"):
        note_latest(bad, p)
    assert cached_latest(p) is None


def test_version_hint_lit_le_cache_sans_reseau(tmp_path):
    p = tmp_path / "u.json"
    assert version_hint(p) is None
    note_latest("0.2.0", p)
    assert "0.2.0" in version_hint(p)


# ---------------------------------------------------------------- détection d'installation
def test_install_pipx():
    plan = detect_install(direct_url={}, prefix="/home/u/.local/pipx/venvs/ezshell", executable="/p/python")
    assert plan.method == "pipx" and plan.commands == [["pipx", "upgrade", "ezshell"]]


def test_install_pipx_depuis_git_bascule_sur_pypi():
    du = {"url": "https://github.com/Waddle-io/ezShell.git", "vcs_info": {"vcs": "git"}}
    plan = detect_install(direct_url=du, prefix="/home/u/.local/pipx/venvs/ezshell", executable="/p/python")
    assert plan.commands == [["pipx", "install", "--force", "ezshell"]]


def test_install_pip():
    plan = detect_install(direct_url={}, prefix="/venv", executable="/venv/bin/python")
    assert plan.method == "pip"
    assert plan.commands == [["/venv/bin/python", "-m", "pip", "install", "--upgrade", "ezshell"]]


def test_install_editable_de_developpement(tmp_path):
    du = {"url": f"file://{tmp_path}", "dir_info": {"editable": True}}
    assert detect_install(direct_url=du, prefix=str(tmp_path / ".venv")).method == "editable"


def test_install_par_script(tmp_path, monkeypatch):
    root = tmp_path / "ezshell"
    (root / ".git").mkdir(parents=True)
    monkeypatch.setenv("EZSHELL_INSTALL_DIR", str(root))
    du = {"url": root.as_uri(), "dir_info": {"editable": True}}
    plan = detect_install(direct_url=du, prefix=str(root / ".venv"), executable="/py")
    assert plan.method == "script"
    assert plan.commands[0][:4] == ["git", "-C", str(root), "pull"]
    assert plan.commands[1][:4] == ["/py", "-m", "pip", "install"]


def test_file_url_path_windows_backslash_in_netloc(monkeypatch):
    monkeypatch.setattr(os, "name", "nt")
    from src.core.updater import _file_url_path

    root = Path(r"C:\Users\runner\AppData\Local\ezshell")
    assert _file_url_path("file://" + str(root)) == root


# ---------------------------------------------------------------- flux
class Harness:
    def __init__(self, *, latest="0.2.0", releases=(REL_02,), pypi="0.2.0", rc=0, answer="o"):
        self.lines, self.cmds, self.asked, self.events = [], [], [], []
        self.info = {"latest": latest, "min_supported": "0.0.0", "releases": list(releases)}
        self.pypi_version, self.rc, self.answer = pypi, rc, answer

    def run(self, plan=None, **kw):
        def runner(cmd, **_):
            if "-c" not in cmd:  # l'appel `python -c` relit la version après coup : pas une installation
                self.cmds.append(cmd)
                self.events.append("install")
            return SimpleNamespace(returncode=self.rc, stdout="0.2.0\n")

        def ask(prompt):
            self.asked.append(prompt)
            self.events.append("confirm")
            return self.answer

        def out(line):
            self.lines.append(line)
            if "Commande --update" in line:
                self.events.append("notes")

        return run_update(
            base_url="https://x",
            out=out,
            input_fn=ask,
            interactive=kw.pop("interactive", True),
            fetch=lambda *a, **k: self.info,
            pypi=lambda: self.pypi_version,
            runner=runner,
            plan=plan or InstallPlan("pip", [["py", "-m", "pip", "install", "--upgrade", "ezshell"]], True),
            state=kw.pop("state", None),
            windows=kw.pop("windows", False),
            **kw,
        )

    @property
    def text(self):
        return "\n".join(self.lines)


def test_deja_a_jour(tmp_path):
    h = Harness(latest="0.1.0")
    assert h.run(state=tmp_path / "s.json") == 0
    assert "Déjà à jour (0.1.0)" in h.text and not h.cmds and not h.asked


def test_montre_les_nouveautes_puis_demande_confirmation_puis_installe(tmp_path):
    h = Harness()
    assert h.run(state=tmp_path / "s.json") == 0
    assert h.asked == ["Mettre à jour maintenant ? [o/N] "]
    assert "0.1.0 → 0.2.0" in h.text and "Commande --update" in h.text
    assert h.events == ["notes", "confirm", "install"]  # nouveautés → confirmation → installation
    assert h.cmds == [["py", "-m", "pip", "install", "--upgrade", "ezshell"]]
    assert "Mis à jour : 0.1.0 → 0.2.0" in h.text


@pytest.mark.parametrize("answer", ["", "n", "non", "peut-être", "  "])
def test_reponse_par_defaut_ou_non_n_installe_rien(tmp_path, answer):
    h = Harness(answer=answer)
    assert h.run(state=tmp_path / "s.json") == 0
    assert not h.cmds and "annulée" in h.text


@pytest.mark.parametrize("answer", ["o", "O", "oui", "y", "YES"])
def test_reponses_positives(tmp_path, answer):
    h = Harness(answer=answer)
    h.run(state=tmp_path / "s.json")
    assert h.cmds


def test_yes_saute_la_confirmation(tmp_path):
    h = Harness()
    assert h.run(yes=True, state=tmp_path / "s.json") == 0
    assert not h.asked and h.cmds


def test_non_interactif_sans_yes_n_installe_rien(tmp_path):
    h = Harness()
    assert h.run(interactive=False, state=tmp_path / "s.json") == 2
    assert not h.cmds and "--yes" in h.text


def test_installation_de_developpement_refusee(tmp_path):
    h = Harness()
    assert h.run(plan=InstallPlan("editable"), yes=True, state=tmp_path / "s.json") == 1
    assert not h.cmds and "git pull" in h.text


def test_echec_affiche_la_commande_manuelle(tmp_path):
    h = Harness(rc=1)
    assert h.run(yes=True, state=tmp_path / "s.json") == 1
    assert "a échoué" in h.text and "pip install --upgrade ezshell" in h.text


def test_version_pas_encore_sur_pypi(tmp_path):
    h = Harness(latest="0.2.0", pypi="0.1.0")
    assert h.run(yes=True, state=tmp_path / "s.json") == 1
    assert not h.cmds and "pas encore publiée" in h.text


def test_pypi_injoignable_ne_bloque_pas(tmp_path):
    h = Harness(pypi=None)
    assert h.run(yes=True, state=tmp_path / "s.json") == 0 and h.cmds


def test_windows_affiche_la_commande_au_lieu_de_se_remplacer(tmp_path):
    h = Harness()
    assert h.run(yes=True, windows=True, state=tmp_path / "s.json") == 0
    assert not h.cmds and "NOUVEAU terminal" in h.text and "pip install" in h.text


def test_hors_ligne(tmp_path):
    h = Harness()
    h.info = None
    h.pypi_version = None
    assert h.run(state=tmp_path / "s.json") == 1 and "Impossible de joindre" in h.text


def test_repli_sur_pypi_si_le_serveur_ne_repond_pas(tmp_path):
    h = Harness(pypi="0.2.0")
    h.info = None
    assert h.run(yes=True, state=tmp_path / "s.json") == 0
    assert "Pas de détail" in h.text and h.cmds


def test_la_mise_a_jour_memorise_la_derniere_version(tmp_path):
    h = Harness()
    s = tmp_path / "s.json"
    h.run(yes=True, state=s)
    assert cached_latest(s) == "0.2.0"
