"""Dienste (Aktionen) für Automationen und Skripte.

Für Doofe:
- garen_beenden: Stopp.
- programm_senden: Für alle (auch Nicht-Admins, z. B. die Einkaufsliste) – schickt
  Programm, Temperatur und Zeit an eine Zone, NUR zum Bereitstellen (startet nie).
- match_senden / sync_senden: Match (beide Zonen gleich) oder Sync (beide fertig
  zur selben Zeit) an die Fritteuse schicken – nur bereitstellen, Start am Gerät.
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

from .core.api import AirfryerError
from .const import (
    DOMAIN,
    MODES,
    SERVICE_MATCH,
    SERVICE_PROGRAM,
    SERVICE_RAW,
    SERVICE_SEND_TEST,
    SERVICE_STOP,
    SERVICE_SYNC,
)
from .coordinator import AirfryerCoordinator, FryerData
from .senden import async_end, async_send, async_send_sync, clamp_minutes, clamp_temp
from .core.util import redact

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
        vol.Optional(ATTR_ZONE, default=1): vol.All(vol.Coerce(int), vol.In([1, 2, 3])),
        vol.Optional(ATTR_TEMP, default=180): vol.All(vol.Coerce(int), vol.Range(min=35, max=240)),
        vol.Optional(ATTR_MINUTES, default=10): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=2880)
        ),
        vol.Optional(ATTR_MODE, default="airfry"): vol.In(list(MODES)),
        vol.Optional(ATTR_VARIANT): cv.string,
        vol.Optional(ATTR_ALL, default=False): cv.boolean,
    }
)
PROGRAM_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DEVICE): cv.string,
        vol.Optional(ATTR_ZONE, default=1): vol.All(vol.Coerce(int), vol.In([1, 2, 3])),
        vol.Required(ATTR_TEMP): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
        vol.Required(ATTR_MINUTES): vol.All(vol.Coerce(int), vol.Range(min=1, max=5000)),
        vol.Required(ATTR_MODE): vol.In(list(MODES)),
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


def _find(hass: HomeAssistant, device_id: str) -> tuple[AirfryerCoordinator, FryerData]:
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="geraet_unbekannt"
        )
    cid = next((ident[1] for ident in device.identifiers if ident[0] == DOMAIN), None)
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinator: AirfryerCoordinator = entry.runtime_data
        if cid in coordinator.fryers:
            return coordinator, coordinator.fryers[cid]
    raise ServiceValidationError(translation_domain=DOMAIN, translation_key="geraet_unbekannt")


async def _stop(call: ServiceCall) -> None:
    coordinator, fryer = _find(call.hass, call.data[ATTR_DEVICE])
    try:
        await async_end(coordinator, fryer)
    except AirfryerError as err:
        raise HomeAssistantError(f"Fritteuse hat „Beenden“ abgelehnt: {err}") from err
    await coordinator.async_request_fast_refresh()


async def _send_sync(call: ServiceCall, sync_type: int) -> None:
    coordinator, fryer = _find(call.hass, call.data[ATTR_DEVICE])
    try:
        await async_send_sync(coordinator, fryer, sync_type)
    except AirfryerError as err:
        raise HomeAssistantError(f"Fritteuse hat Match/Sync abgelehnt: {err}") from err


async def _match(call: ServiceCall) -> None:
    await _send_sync(call, 1)


async def _sync(call: ServiceCall) -> None:
    await _send_sync(call, 2)


def _find_any(hass: HomeAssistant, device_id: str | None) -> tuple[AirfryerCoordinator, FryerData]:
    """Gerät finden. Ohne Angabe: die einzige Fritteuse (praktisch für Nicht-Admins)."""
    if device_id:
        return _find(hass, device_id)
    found = [
        (entry.runtime_data, fryer)
        for entry in hass.config_entries.async_loaded_entries(DOMAIN)
        for fryer in entry.runtime_data.fryers.values()
    ]
    if len(found) != 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="geraet_unbekannt"
        )
    return found[0]


async def _program(call: ServiceCall) -> ServiceResponse:
    """Für alle: Programm an eine Zone schicken – nur bereitstellen, startet nie."""
    coordinator, fryer = _find_any(call.hass, call.data.get(ATTR_DEVICE))
    mode = call.data[ATTR_MODE]
    try:
        results = await async_send(
            coordinator,
            fryer,
            call.data[ATTR_ZONE],
            clamp_temp(mode, call.data[ATTR_TEMP]),
            clamp_minutes(mode, call.data[ATTR_MINUTES]),
            mode,
        )  # ohne only/try_all: nie die startende Variante
    except AirfryerError as err:
        return {"ok": False, "fehler": str(err), "code": err.code}
    ok = any(r["ok"] for r in results)
    if ok:
        return {"ok": True}
    last = results[-1] if results else {}
    return {"ok": False, "fehler": last.get("fehler", "abgelehnt"), "code": last.get("code")}


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
    except AirfryerError as err:
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
    except AirfryerError as err:
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
        SERVICE_PROGRAM,
        _program,
        schema=PROGRAM_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(DOMAIN, SERVICE_MATCH, _match, schema=STOP_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SYNC, _sync, schema=STOP_SCHEMA)
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
