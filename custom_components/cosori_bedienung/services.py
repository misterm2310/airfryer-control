"""Dienste (Aktionen) für Automationen und Skripte.

Für Doofe:
- garen_beenden: Stopp.
- senden_testen: Für Bastler (nur Admins) – schickt Programm, Temperatur und
  Zeit an eine Zone (ohne zu starten) und zeigt, welche Schreibweise die
  Fritteuse angenommen hat.
- befehl_senden: Für Bastler (nur Admins) – einen beliebigen App-Befehl
  schicken und die Antwort sehen.
"""

from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError, Unauthorized
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .api import CosoriError
from .const import (
    DOMAIN,
    MODES,
    SERVICE_RAW,
    SERVICE_SEND_TEST,
    SERVICE_STOP,
)
from .coordinator import CosoriCoordinator, FryerData
from .senden import async_end, async_send
from .util import redact

ATTR_DEVICE = "geraet"
ATTR_ZONE = "zone"
ATTR_TEMP = "temperatur"
ATTR_MINUTES = "minuten"
ATTR_MODE = "programm"
ATTR_VARIANT = "variante"
ATTR_ALL = "alle"
ATTR_METHOD = "methode"
ATTR_DATA = "daten"

SEND_TEST_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE): cv.string,
        vol.Optional(ATTR_ZONE, default=1): vol.All(vol.Coerce(int), vol.In([1, 2])),
        vol.Optional(ATTR_TEMP, default=180): vol.All(vol.Coerce(int), vol.Range(min=35, max=240)),
        vol.Optional(ATTR_MINUTES, default=10): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=1440)
        ),
        vol.Optional(ATTR_MODE, default="airfry"): vol.In(list(MODES)),
        vol.Optional(ATTR_VARIANT): cv.string,
        vol.Optional(ATTR_ALL, default=False): cv.boolean,
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


async def _stop(call: ServiceCall) -> None:
    coordinator, fryer = _find(call.hass, call.data[ATTR_DEVICE])
    try:
        await async_end(coordinator, fryer)
    except CosoriError as err:
        raise HomeAssistantError(f"Fritteuse hat „Beenden“ abgelehnt: {err}") from err
    await coordinator.async_request_fast_refresh()


async def _require_admin(call: ServiceCall) -> None:
    if call.context.user_id:
        user = await call.hass.auth.async_get_user(call.context.user_id)
        if user is None or not user.is_admin:
            raise Unauthorized()


async def _send_test(call: ServiceCall) -> ServiceResponse:
    await _require_admin(call)
    coordinator, fryer = _find(call.hass, call.data[ATTR_DEVICE])
    try:
        results = await async_send(
            coordinator,
            fryer,
            call.data[ATTR_ZONE],
            call.data[ATTR_TEMP],
            call.data[ATTR_MINUTES],
            call.data[ATTR_MODE],
            only=call.data.get(ATTR_VARIANT),
            try_all=call.data[ATTR_ALL],
        )
    except CosoriError as err:
        return {"ok": False, "fehler": str(err), "code": err.code}
    return {
        "ok": any(r["ok"] for r in results),
        "gemerkte_variante": coordinator.send_variant,
        "versuche": results,
    }


async def _raw(call: ServiceCall) -> ServiceResponse:
    await _require_admin(call)
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
    if hass.services.has_service(DOMAIN, SERVICE_STOP):
        return
    hass.services.async_register(DOMAIN, SERVICE_STOP, _stop, schema=STOP_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_TEST,
        _send_test,
        schema=SEND_TEST_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RAW,
        _raw,
        schema=RAW_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
