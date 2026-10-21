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

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import CARD_FILENAME, OPT_SIDEBAR, PANEL_FILENAME, PANEL_URL_PATH, STATIC_URL

_LOGGER = logging.getLogger(__name__)

CARD_URL = f"{STATIC_URL}/{CARD_FILENAME}"


def _version() -> str:
    """Version aus der manifest.json (damit der Browser nach einem Update neu lädt)."""
    try:
        manifest = Path(__file__).parent / "manifest.json"
        return str(json.loads(manifest.read_text(encoding="utf-8")).get("version", "0"))
    except (OSError, ValueError):
        return "0"


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


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Datei bereitstellen und als Dashboard-Ressource eintragen."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "www"), False)]
    )
    from .app_view import AppRedirectView, AppView  # noqa: PLC0415 (vermeidet Kreis-Import)

    hass.http.register_view(AppView())
    hass.http.register_view(AppRedirectView())
    versioned = f"{CARD_URL}?v={_version()}"

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


async def async_set_sidebar(hass: HomeAssistant, enabled: bool) -> None:
    """📌 Fritteuse als eigener Eintrag in der Seitenleiste (Option, standardmäßig aus)."""
    from homeassistant.components import frontend, panel_custom  # noqa: PLC0415

    present = PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {})
    if present:
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
    if not enabled:
        return
    try:
        await panel_custom.async_register_panel(
            hass,
            webcomponent_name="airfryer-control-panel",
            frontend_url_path=PANEL_URL_PATH,
            module_url=f"{STATIC_URL}/{PANEL_FILENAME}?v={_version()}",
            sidebar_title="Fritteuse",
            sidebar_icon="mdi:toaster-oven",
            require_admin=False,
            config={"card_url": f"{CARD_URL}?v={_version()}"},
        )
    except Exception:  # noqa: BLE001
        _LOGGER.warning("Seitenleisten-Eintrag konnte nicht angelegt werden", exc_info=True)
