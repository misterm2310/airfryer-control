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
- faehigkeiten: Für alle (nur lesen) – welche Programme, Grenzen und Zonen ein
  Gerät hat, und ob das bestätigt oder nur geschätzt ist.
- befehl_senden: Für Bastler (nur Admins) – einen beliebigen App-Befehl
  schicken und die Antwort sehen.
"""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError, Unauthorized
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .core.api import CODE_DEVICE_TIMEOUT, AirfryerError
from .const import (
    DOMAIN,
    MODES,
    SERVICE_CAPABILITIES,
    SERVICE_MATCH,
    SERVICE_PROGRAM,
    SERVICE_RAW,
    SERVICE_SEND_TEST,
    SERVICE_STOP,
    SERVICE_SYNC,
    STATE_HOLD,
    STATE_WAITING,
)
from .coordinator import AirfryerCoordinator, FryerData
from .core.parser import zone_view
from .faehigkeiten import capabilities, outside_limits
from .senden import (
    RESULT_REJECTED,
    RESULT_UNKNOWN,
    SAFE_VARIANTS,
    async_end,
    async_send,
    async_send_sync,
    clamp_minutes,
    clamp_temp,
)
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
ATTR_ONCE = "einmal"
ATTR_STRICT = "streng"
ATTR_CONFIRM = "bestaetigen"

# „bestätigen“: so oft und so lange nachsehen, ob die Werte an der Zone angekommen sind
CONFIRM_TRIES = 3
CONFIRM_WAIT_SECONDS = 3.0

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
        # Nur die sicheren Schreibweisen – die startende ist hier nie erlaubt
        vol.Optional(ATTR_VARIANT): vol.In(list(SAFE_VARIANTS)),
        vol.Optional(ATTR_ONCE, default=False): cv.boolean,
        vol.Optional(ATTR_STRICT, default=False): cv.boolean,
        vol.Optional(ATTR_CONFIRM, default=False): cv.boolean,
    }
)
CAPABILITIES_SCHEMA = vol.Schema({vol.Optional(ATTR_DEVICE): cv.string})
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
    """Für alle: Programm an eine Zone schicken – nur bereitstellen, startet nie.

    Antwort: ``ok`` und ``ergebnis`` („angenommen“, „abgelehnt“ oder
    „unbekannt“). Mit ``bestaetigen`` zusätzlich ``bestaetigt``: Zeigt die
    Fritteuse die Werte danach wirklich an der Zone?
    """
    coordinator, fryer = _find_any(call.hass, call.data.get(ATTR_DEVICE))
    mode = call.data[ATTR_MODE]
    zone = call.data[ATTR_ZONE]
    temp = call.data[ATTR_TEMP]
    minutes = call.data[ATTR_MINUTES]
    base: dict[str, Any] = {"revision_vorher": fryer.revision}
    if call.data[ATTR_STRICT]:
        limits = outside_limits(mode, temp, minutes)
        if limits is not None:
            return {
                **base,
                "ok": False,
                "ergebnis": RESULT_REJECTED,
                "fehler": "ausserhalb_grenzen",
                "grenzen": limits,
            }
    else:
        temp = clamp_temp(mode, temp)
        minutes = clamp_minutes(mode, minutes)
    try:
        results = await async_send(
            coordinator,
            fryer,
            zone,
            temp,
            minutes,
            mode,
            only=call.data.get(ATTR_VARIANT),
            once=call.data[ATTR_ONCE],
            allow_start=False,
        )  # allow_start=False: nie die startende Variante
    except AirfryerError as err:
        # „Gerät antwortet nicht rechtzeitig“: Der Befehl kann trotzdem angekommen sein
        kind = RESULT_UNKNOWN if err.code == CODE_DEVICE_TIMEOUT else RESULT_REJECTED
        return {**base, "ok": False, "ergebnis": kind, "fehler": str(err), "code": err.code}
    if not results:
        return {**base, "ok": False, "ergebnis": RESULT_REJECTED, "fehler": "keine_variante"}
    last = next((r for r in results if r["ok"]), results[-1])
    answer: dict[str, Any] = {
        **base,
        "ok": last["ok"],
        "ergebnis": last["ergebnis"],
        "variante": last["variante"],
        "versuche": len(results),
        "gesendet": {"programm": mode, "temperatur": temp, "minuten": minutes, "zone": zone},
    }
    if not last["ok"]:
        answer.update(fehler=last.get("fehler", "abgelehnt"), code=last.get("code"))
    elif call.data[ATTR_CONFIRM]:
        answer.update(await _confirm(coordinator, fryer, zone, temp, minutes, mode))
    return answer


async def _confirm(
    coordinator: AirfryerCoordinator, fryer: FryerData, zone: int, temp: int, minutes: int, mode: str
) -> dict[str, Any]:
    """Ein paar Mal nachfragen, ob die Zone die Werte wirklich zeigt."""
    seen: dict[str, Any] = {}
    for attempt in range(CONFIRM_TRIES):
        if attempt:
            await asyncio.sleep(CONFIRM_WAIT_SECONDS)
        await coordinator.async_refresh()
        zs = zone_view(fryer.state, zone) if fryer.online else None
        if zs is None:
            seen = {"gemeldet": False}
            continue
        seen = {
            "gemeldet": True,
            "zustand": zs.status,
            "programm": zs.mode,
            "temperatur": zs.set_temp,
            "minuten": None if zs.set_time_s is None else round(zs.set_time_s / 60),
        }
        ready = zs.status in (STATE_WAITING, STATE_HOLD) or zs.active
        same = (
            zs.mode is not None
            and zs.mode.lower() == MODES[mode].lower()
            and zs.set_temp == temp
            and zs.set_time_s == minutes * 60
        )
        if ready and same:
            return {"bestaetigt": True, "am_geraet": seen, "revision": fryer.revision}
    return {"bestaetigt": False, "am_geraet": seen, "revision": fryer.revision}


async def _capabilities(call: ServiceCall) -> ServiceResponse:
    """Für alle (nur lesen): Programme, Grenzen und Zonen – mit „bestätigt“ oder „geschätzt“."""
    _coordinator, fryer = _find_any(call.hass, call.data.get(ATTR_DEVICE))
    return {
        **capabilities(fryer),
        "verbindung": fryer.connection,
        "letzte_meldung": fryer.last_report.isoformat() if fryer.last_report else None,
        "revision": fryer.revision,
    }


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
    hass.services.async_register(
        DOMAIN,
        SERVICE_CAPABILITIES,
        _capabilities,
        schema=CAPABILITIES_SCHEMA,
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
