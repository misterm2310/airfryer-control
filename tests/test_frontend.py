"""Prüft die Dateien der Karte und der Offline-App (ohne Browser)."""

from __future__ import annotations

import json
import re
from pathlib import Path

WWW = Path(__file__).parent.parent / "custom_components" / "airfryer_control" / "www"


def _app_icons() -> dict[str, str]:
    html = (WWW / "app" / "index.html").read_text(encoding="utf-8")
    m = re.search(r"const ICONS = (\{.*?\});\n", html)
    assert m, "ICONS fehlt in app/index.html"
    return json.loads(m.group(1))


def test_app_kennt_alle_symbole_der_karte() -> None:
    """🧩 Jedes mdi:-Symbol der Karte braucht in der Offline-App einen Pfad – sonst ist dort nur ein leeres Kästchen."""
    card = (WWW / "airfryer-control-card.js").read_text(encoding="utf-8")
    used = set(re.findall(r"mdi:([a-z0-9-]+)", card))
    icons = _app_icons()
    missing = sorted(used - set(icons))
    assert not missing, f"In app/index.html fehlen Symbole: {missing}"
    for name, path in icons.items():
        assert re.fullmatch(r"[MmLlHhVvCcSsQqTtAaZz0-9 .,\-]+", path), name


def test_neu_in_dieser_beta_passt_zur_version() -> None:
    """📢 Bei einer Beta muss der Kasten „Neu in dieser Beta“ Einträge für genau diese Version haben."""
    manifest = json.loads((WWW.parent / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    if "beta" not in version:
        return
    card = (WWW / "airfryer-control-card.js").read_text(encoding="utf-8")
    news = card[card.index("const AC_NEWS = [") : card.index("];", card.index("const AC_NEWS = ["))]
    assert f'["{version}"' in news, f"AC_NEWS hat nichts für {version}"
