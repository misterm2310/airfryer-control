"""Dienste (Aktionen) für Automationen und Skripte.

Für Doofe:
- garen_starten: Fritteuse mit Temperatur, Zeit und Programm loslegen lassen.
- garen_beenden: Stopp.
- befehl_senden: Für Bastler (nur Admins) – einen beliebigen App-Befehl
  schicken und die Antwort sehen. Damit finden wir in der Beta heraus,
  was die Fritteuse alles versteht.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError, Unauthorized
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .api import CosoriError
from .const import (
    DOMAIN,
    MODES,
    SERVICE_RAW,
    SERVICE_START,
    SERVICE_STOP,
    ZONE_1,
    ZONE_2,
    ZONE_WHOLE,
)
from .coordinator import CosoriCoordinator, FryerData
from .util import redact

ATTR_DEVICE = "geraet"
ATTR_ZONE = "zone"
ATTR_TEMP = "temperatur"
ATTR_MINUTES = "minuten"
ATTR_MODE = "programm"
ATTR_TEMP_2 = "temperatur_zone2"
ATTR_MINUTES_2 = "minuten_zone2"
ATTR_MODE_2 = "programm_zone2"
ATTR_METHOD = "methode"
ATTR_DATA = "daten"

ZONES = ["1", "2", "beide", "ganz"]

START_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE): cv.string,
        vol.Optional(ATTR_ZONE, default="1"): vol.In(ZONES),
        vol.Required(ATTR_TEMP): vol.All(vol.Coerce(int), vol.Range(min=35, max=240)),
        vol.Required(ATTR_MINUTES): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
        vol.Optional(ATTR_MODE, default="airfry"): vol.In(list(MODES)),
        vol.Optional(ATTR_TEMP_2): vol.All(vol.Coerce(int), vol.Range(min=35, max=240)),
        vol.Optional(ATTR_MINUTES_2): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
        vol.Optional(ATTR_MODE_2): vol.In(list(MODES)),
    }
)
STOP_SCHEMA = vol.Schema({vol.Required(ATTR_DEVICE): cv.string})
RAW_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE): cv.string,
        vol.Required(ATTR_METHOD): vol.All(cv.string, vol.Match(r"^[A-Za-z0-9_]{2,64}$")),
        vol.Optional(ATTR_DATA, default=dict): dict,
    }
)


def build_start_payload(
    account_id: str | None,
    zone: str,
    temp: int,
    minutes: int,
    mode: str,
    temp2: int | None = None,
    minutes2: int | None = None,
    mode2: str | None = None,
) -> dict[str, Any]:
    """Baut den Start-Befehl wie die App (startMultiCook).

    Zeiten gehen in Sekunden raus, Temperaturen in °C.
    """

    def cfg(chamber: int, t: int, m: int, md: str) -> dict[str, Any]:
        return {
            "cookSetTime": m * 60,
            "cookTemp": t,
            "mode": MODES.get(md, md),
            "chamber": chamber,
        }

    if zone == "beide":
        configs = [
            cfg(ZONE_1, temp, minutes, mode),
            cfg(ZONE_2, temp2 or temp, minutes2 or minutes, mode2 or mode),
        ]
        work = 4
    elif zone == "ganz":
        configs = [cfg(ZONE_WHOLE, temp, minutes, mode)]
        work = ZONE_WHOLE
    else:
        chamber = ZONE_2 if zone == "2" else ZONE_1
        configs = [cfg(chamber, temp, minutes, mode)]
        work = chamber
    return {
        "syncType": 0,
        "workChamber": work,
        "tempUnit": "celsius",
        "accountId": account_id or "",
        "readyStart": True,
        "cookConfigs": configs,
    }


def _find(hass: HomeAssistant, device_id: str) -> tuple[CosoriCoordinator, FryerData]:
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="geraet_unbekannt"
        )
    cid = next((ident[1] for ident in device.identifiers if ident[0] == DOMAIN), None)
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinator: CosoriCoordinator = entry.runtime_data
        if cid in coordinator.fryers:
            return coordinator, coordinator.fryers[cid]
    raise ServiceValidationError(translation_domain=DOMAIN, translation_key="geraet_unbekannt")


async def _start(call: ServiceCall) -> None:
    coordinator, fryer = _find(call.hass, call.data[ATTR_DEVICE])
    if fryer.model.startswith("CS"):
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="start_nicht_unterstuetzt"
        )
    payload = build_start_payload(
        coordinator.api.account_id,
        call.data[ATTR_ZONE],
        call.data[ATTR_TEMP],
        call.data[ATTR_MINUTES],
        call.data[ATTR_MODE],
        call.data.get(ATTR_TEMP_2),
        call.data.get(ATTR_MINUTES_2),
        call.data.get(ATTR_MODE_2),
    )
    try:
        await coordinator.api.bypass_v2(fryer.info, "startMultiCook", payload)
    except CosoriError as err:
        raise HomeAssistantError(
            f"Die Fritteuse hat den Start abgelehnt ({err}). Hinweis: In der EU erlaubt "
            "Cosori das Starten aus der Ferne teils nicht – Schublade rein und am Gerät starten."
        ) from err
    await coordinator.async_request_fast_refresh()


async def _stop(call: ServiceCall) -> None:
    coordinator, fryer = _find(call.hass, call.data[ATTR_DEVICE])
    try:
        await coordinator.api.bypass_v2(fryer.info, "endCook", {})
    except CosoriError as err:
        raise HomeAssistantError(f"Fritteuse hat „Beenden“ abgelehnt: {err}") from err
    await coordinator.async_request_fast_refresh()


async def _raw(call: ServiceCall) -> ServiceResponse:
    if call.context.user_id:
        user = await call.hass.auth.async_get_user(call.context.user_id)
        if user is None or not user.is_admin:
            raise Unauthorized()
    coordinator, fryer = _find(call.hass, call.data[ATTR_DEVICE])
    try:
        result = await coordinator.api.bypass_v2(
            fryer.info, call.data[ATTR_METHOD], call.data[ATTR_DATA]
        )
    except CosoriError as err:
        return {"ok": False, "fehler": str(err), "code": err.code}
    await coordinator.async_request_fast_refresh()
    return {"ok": True, "antwort": redact(result)}


def async_register_services(hass: HomeAssistant) -> None:
    """Dienste einmalig anmelden."""
    if hass.services.has_service(DOMAIN, SERVICE_START):
        return
    hass.services.async_register(DOMAIN, SERVICE_START, _start, schema=START_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_STOP, _stop, schema=STOP_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_RAW,
        _raw,
        schema=RAW_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
