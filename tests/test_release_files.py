"""Cohérence des versions : src/__init__.py, CHANGELOG.md, README, web/data/releases.json."""

import json
import re
from pathlib import Path

from src import __version__

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = {"À noter en premier": "important", "Nouveautés": "added", "Corrections": "fixed"}


def parse_changelog() -> dict:
    out, version, key = {}, None, None
    for line in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines():
        if m := re.match(r"^## (\d+\.\d+\.\d+)\b", line):
            version, key = m.group(1), None
            out[version] = {"important": [], "added": [], "fixed": []}
        elif m := re.match(r"^### (.+)$", line):
            key = SECTIONS.get(m.group(1).strip())
        elif version and key and line.startswith("- "):
            out[version][key].append(line[2:].strip())
    return out


def test_la_version_du_code_a_une_section_dans_le_changelog():
    assert __version__ in parse_changelog()


def test_le_badge_du_readme_suit_la_version():
    assert f"version-{__version__}-" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_releases_json_identique_au_changelog():
    changelog = parse_changelog()
    data = json.loads((ROOT / "web" / "data" / "releases.json").read_text(encoding="utf-8"))
    assert {r["version"] for r in data["releases"]} == set(changelog)
    for r in data["releases"]:
        for key in ("important", "added", "fixed"):
            assert r[key] == changelog[r["version"]][key], f"{r['version']} / {key}"


def test_aucune_version_publiee_au_dessus_du_code():
    """Le serveur n'annonce que des versions « released » : jamais plus récentes que le code."""
    data = json.loads((ROOT / "web" / "data" / "releases.json").read_text(encoding="utf-8"))

    def key(v):
        return tuple(int(x) for x in v.split("."))

    released = [r["version"] for r in data["releases"] if r["status"] == "released"]
    assert all(key(v) <= key(__version__) for v in released)
