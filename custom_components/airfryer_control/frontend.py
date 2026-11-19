"""Karten automatisch im Dashboard bereitstellen.

Für Doofe: Die Integration bringt zwei eigene Karten mit
(`custom:airfryer-control-card` und `custom:airfryer-control-ticker`).
Hier legen wir die Datei bereit und tragen sie bei den Dashboard-Ressourcen ein,
damit du sie im Karten-Dialog einfach auswählen kannst.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from .const import CARD_FILENAME, OPT_SIDEBAR, PANEL_FILENAME, PANEL_URL_PATH, STATIC_URL

_LOGGER = logging.getLogger(__name__)

CARD_URL = f"{STATIC_URL}/{CARD_FILENAME}"


_VERSION: str | None = None


def _version() -> str:
    """Version aus der manifest.json lesen (blockiert kurz – nur im Hintergrund-Thread aufrufen!)."""
    try:
        manifest = Path(__file__).parent / "manifest.json"
        return str(json.loads(manifest.read_text(encoding="utf-8")).get("version", "0"))
    except (OSError, ValueError):
        return "0"


async def async_version(hass: HomeAssistant) -> str:
    """Version für „?v=…“ (damit der Browser nach einem Update neu lädt).

    Für Doofe: Die Datei wird nur ein einziges Mal gelesen, und zwar im Hintergrund,
    damit Home Assistant nicht kurz warten muss. Danach kommt der Wert aus dem Gedächtnis.
    """
    global _VERSION  # noqa: PLW0603
    if _VERSION is None:
        _VERSION = await hass.async_add_executor_job(_version)
    return _VERSION


def _resources(hass: HomeAssistant):
    """Die Dashboard-Ressourcen holen (nur im normalen UI-Modus, nicht YAML)."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA  # noqa: PLC0415

        data = hass.data.get(LOVELACE_DATA)
    except ImportError:
        data = hass.data.get("lovelace")
    if data is None:
        return None
    if isinstance(data, dict):  # ältere HA-Versionen
        mode, resources = data.get("resource_mode", data.get("mode")), data.get("resources")
    else:
        mode, resources = getattr(data, "resource_mode", None), getattr(data, "resources", None)
    if mode == "yaml" or resources is None or not hasattr(resources, "async_create_item"):
        return None
    return resources


@websocket_api.websocket_command({"type": "airfryer_control/info"})
@callback
def _ws_info(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """🔄 Welche Version läuft in Home Assistant? Die Karte vergleicht das mit sich selbst
    und zeigt „Neue Version da – Neu laden“, wenn der Browser noch die alte Karte hat."""
    connection.send_result(msg["id"], {"version": _VERSION or ""})


def _entries_for(hass: HomeAssistant) -> list:
    from .const import DOMAIN  # noqa: PLC0415

    return hass.config_entries.async_entries(DOMAIN)


@websocket_api.websocket_command(
    {vol.Required("type"): "airfryer_control/optionen", vol.Optional("entry_id"): str}
)
@websocket_api.require_admin
@callback
def _ws_options(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """🔌 Einstellungen der Integration lesen – für ⚙️ in Karte, Seitenleiste UND Offline-App.

    Für Doofe: Die Offline-App hat nur die Websocket-Verbindung, nicht den Optionen-Dialog
    von Home Assistant. Darum gibt es diesen eigenen kleinen Weg (nur für Admins).
    """
    from .config_flow import clean_options  # noqa: PLC0415 (spät laden, vermeidet Kreis-Import)

    entries = _entries_for(hass)
    if not entries:
        connection.send_error(msg["id"], "not_found", "Airfryer Control ist nicht eingerichtet")
        return
    entry = next((e for e in entries if e.entry_id == msg.get("entry_id")), entries[0])
    services = sorted(
        (s for s in hass.services.async_services().get("notify", {}) if s != "send_message"),
        key=lambda s: (not s.startswith("mobile_app_"), s),
    )
    connection.send_result(
        msg["id"],
        {
            "entry": entry.entry_id,
            "entries": [{"entry_id": e.entry_id, "title": e.title} for e in entries],
            "data": clean_options(entry.options),
            "notify": services,  # 📲 zur Auswahl (die Offline-App kennt die Dienste sonst nicht)
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "airfryer_control/optionen_speichern",
        vol.Required("entry_id"): str,
        vol.Required("daten"): dict,
    }
)
@websocket_api.require_admin
@callback
def _ws_options_save(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
    """🔌 Einstellungen speichern (nur Admins). Die Integration lädt danach kurz neu – die Seitenleiste bleibt."""
    from .config_flow import clean_options  # noqa: PLC0415

    entry = next((e for e in _entries_for(hass) if e.entry_id == msg["entry_id"]), None)
    if entry is None:
        connection.send_error(msg["id"], "not_found", "Unbekannte Fritteuse")
        return
    new = clean_options({**clean_options(entry.options), **msg["daten"]})
    if new != dict(entry.options):
        hass.config_entries.async_update_entry(entry, options=new)
    connection.send_result(msg["id"], {"data": new})


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Datei bereitstellen und als Dashboard-Ressource eintragen."""
    await async_version(hass)  # Version einmal lesen (für airfryer_control/info)
    websocket_api.async_register_command(hass, _ws_info)
    websocket_api.async_register_command(hass, _ws_options)
    websocket_api.async_register_command(hass, _ws_options_save)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "www"), False)]
    )
    from .app_view import AppRedirectView, AppView  # noqa: PLC0415 (vermeidet Kreis-Import)

    hass.http.register_view(AppView())
    hass.http.register_view(AppRedirectView())
    versioned = f"{CARD_URL}?v={await async_version(hass)}"

    resources = _resources(hass)
    if resources is None:
        # YAML-Modus o. ä.: Karte trotzdem laden
        add_extra_js_url(hass, versioned)
        return

    try:
        if not getattr(resources, "loaded", True):
            await resources.async_load()
            resources.loaded = True
        for item in resources.async_items():
            if str(item.get("url", "")).split("?")[0] == CARD_URL:
                if item["url"] != versioned:
                    await resources.async_update_item(
                        item["id"], {"res_type": "module", "url": versioned}
                    )
                return
        await resources.async_create_item({"res_type": "module", "url": versioned})
        _LOGGER.info("Airfryer-Control-Karten als Dashboard-Ressource eingetragen")
    except Exception:  # noqa: BLE001
        _LOGGER.warning(
            "Konnte die Karten nicht als Ressource eintragen – lade sie stattdessen direkt",
            exc_info=True,
        )
        add_extra_js_url(hass, versioned)


def sidebar_wanted(hass: HomeAssistant, skip_entry_id: str | None = None) -> bool:
    """Ist bei irgendeinem (anderen) geladenen Konto die Seitenleiste eingeschaltet?"""
    from homeassistant.config_entries import ConfigEntryState  # noqa: PLC0415

    from .const import DOMAIN  # noqa: PLC0415

    return any(
        e.entry_id != skip_entry_id and e.state is ConfigEntryState.LOADED and bool(e.options.get(OPT_SIDEBAR, False))
        for e in hass.config_entries.async_entries(DOMAIN)
    )


async def async_set_sidebar(hass: HomeAssistant, enabled: bool, mascot: bool = False) -> None:
    """📌 Fritteuse als eigener Eintrag in der Seitenleiste (Option, standardmäßig aus).

    Für Doofe: Ist der Eintrag schon da, wird er NICHT erst weggenommen und neu angelegt –
    sonst merkt Home Assistant „Seite weg“ und wirft jeden raus, der gerade auf der Seite
    ist (z. B. beim Speichern einer Einstellung, weil die Integration dann neu lädt).
    Stattdessen werden nur die Angaben aktualisiert.
    """
    from homeassistant.components import frontend  # noqa: PLC0415

    panels = hass.data.get(frontend.DATA_PANELS, {})
    present = PANEL_URL_PATH in panels
    if not enabled:
        if present:
            frontend.async_remove_panel(hass, PANEL_URL_PATH)
        return
    try:
        version = await async_version(hass)
        config = {
            "card_url": f"{CARD_URL}?v={version}",
            "maskottchen": mascot,  # 🍟 Maskottchen auch in der Seitenleiste
            # So legt panel_custom einen eigenen Eintrag an (gleiche Form wie panel_custom.async_register_panel)
            "_panel_custom": {
                "name": "airfryer-control-panel",
                "embed_iframe": False,
                "trust_external": False,
                "module_url": f"{STATIC_URL}/{PANEL_FILENAME}?v={version}",
            },
        }
        if present and getattr(panels[PANEL_URL_PATH], "config", None) == config:
            return  # schon genau so da – nichts anfassen
        frontend.async_register_built_in_panel(
            hass,
            component_name="custom",
            sidebar_title="Fritteuse",
            sidebar_icon="mdi:toaster-oven",
            frontend_url_path=PANEL_URL_PATH,
            config=config,
            require_admin=False,
            update=present,  # schon da → nur aktualisieren, nie wegnehmen
        )
    except Exception:  # noqa: BLE001
        _LOGGER.warning("Seitenleisten-Eintrag konnte nicht angelegt werden", exc_info=True)
