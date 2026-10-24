"""📱 Handy-App: eine eigene kleine Seite nur für die Fritteuse.

Für Doofe: Auf dem Handy im Browser öffnen (z. B. über die Nabu-Casa-Adresse), anmelden und
„Zum Startbildschirm“. Die Seite zeigt das Laufband und die Zonenkarte im Vollbild.
Die Seite selbst enthält keine Daten – die kommen erst nach der Anmeldung über die normale,
geschützte Home-Assistant-Verbindung. Ohne Netz zeigt sie „Keine Verbindung“; Befehle werden
bewusst nie gemerkt und später gesendet (ein verspäteter Start wäre gefährlich).
"""

from __future__ import annotations

from pathlib import Path

from aiohttp import web

from homeassistant.components.http import HomeAssistantView

from .frontend import async_version

APP_DIR = Path(__file__).parent / "www" / "app"
APP_URL = "/airfryer_control/app/"

_TYPES = {
    "index.html": "text/html; charset=utf-8",
    "sw.js": "text/javascript; charset=utf-8",
    "manifest.webmanifest": "application/manifest+json",
    "icon-192.png": "image/png",
    "icon-512.png": "image/png",
}
_MANIFEST_EN = {
    "Die Cosori-Heißluftfritteuse aus Home Assistant – Zonen, Fertig-Zeiten, Senden und Beenden.":
        "The Cosori air fryer from Home Assistant – zones, finish times, send and stop.",
}


class AppView(HomeAssistantView):
    """Liefert die Handy-App aus (ohne Anmeldung – die Seite enthält nur Programm, keine Daten)."""

    url = "/airfryer_control/app/{file:.*}"
    name = "airfryer_control:app"
    requires_auth = False

    async def get(self, request: web.Request, file: str = "") -> web.StreamResponse:
        file = file or "index.html"
        if file not in _TYPES:
            return web.Response(status=404)
        hass = request.app["hass"]
        body = await hass.async_add_executor_job((APP_DIR / file).read_bytes)
        if file in ("index.html", "sw.js"):
            body = body.replace(b"__AC_VERSION__", (await async_version(hass)).encode())
        if file == "manifest.webmanifest" and not str(getattr(hass.config, "language", "de") or "de").lower().startswith("de"):
            for de, en in _MANIFEST_EN.items():
                body = body.replace(de.encode(), en.encode())
        headers = {"Cache-Control": "no-cache"}
        if file == "sw.js":
            headers["Service-Worker-Allowed"] = APP_URL
        content_type = _TYPES[file]
        return web.Response(
            body=body,
            content_type=content_type.split(";")[0],
            charset="utf-8" if "charset" in content_type else None,
            headers=headers,
        )


class AppRedirectView(HomeAssistantView):
    """/airfryer_control/app ohne Schrägstrich -> mit Schrägstrich."""

    url = "/airfryer_control/app"
    name = "airfryer_control:app_redirect"
    requires_auth = False

    async def get(self, request: web.Request) -> web.StreamResponse:
        raise web.HTTPFound(APP_URL)
