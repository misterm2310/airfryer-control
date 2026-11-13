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
- liebling_speichern / liebling_loeschen: Für alle – ⭐ Lieblings-Programme pro
  Fritteuse merken oder löschen (die Karte zeigt sie als Knöpfe).
- garzeit_plus: Für alle – ⏱️ 1–30 Minuten dazu: gart die Zone, wird die laufende
  Zeit länger; ist sie fertig, wird dasselbe Programm nochmal bereitgestellt.
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

from .core.api import CODE_DEVICE_TIMEOUT, AirfryerConnectionError, AirfryerError
from .const import (
    DOMAIN,
    SERVICE_ADD_TIME,
    SERVICE_CAPABILITIES,
    SERVICE_FAV_DELETE,
    SERVICE_FAV_SAVE,
    STATE_FINISHED,
    STATE_KEEP_WARM,
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
from .modelle import ALL_MODES, modes_for
from .senden import (
    RESULT_ACCEPTED,
    RESULT_REJECTED,
    RESULT_UNKNOWN,
    SAFE_VARIANTS,
    SyncBlocked,
    async_end,
    async_send,
    async_send_sync,
    clamp_minutes,
    clamp_temp,
    get_plan,
    sync_plans,
)
from .number import build_change_payload
from .programme import get_store
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
ATTR_ZONE1 = "zone1"
ATTR_ZONE2 = "zone2"
ATTR_SOURCE = "quelle"
ATTR_RESET = "zuruecksetzen"
ATTR_NAME = "name"

# „bestätigen“: so oft und so lange nachsehen, ob die Werte an der Zone angekommen sind
CONFIRM_TRIES = 3
CONFIRM_WAIT_SECONDS = 3.0

SEND_TEST_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE): cv.string,
        vol.Optional(ATTR_ZONE, default=1): vol.All(vol.Coerce(int), vol.In([1, 2, 3])),
        vol.Optional(ATTR_TEMP, default=180): vol.All(vol.Coerce(int), vol.Range(min=30, max=240)),
        vol.Optional(ATTR_MINUTES, default=10): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=2880)
        ),
        vol.Optional(ATTR_MODE, default="airfry"): vol.In(list(ALL_MODES)),
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
        vol.Required(ATTR_MODE): vol.In(list(ALL_MODES)),
        # Nur die sicheren Schreibweisen – die startende ist hier nie erlaubt
        vol.Optional(ATTR_VARIANT): vol.In(list(SAFE_VARIANTS)),
        vol.Optional(ATTR_ONCE, default=False): cv.boolean,
        vol.Optional(ATTR_STRICT, default=False): cv.boolean,
        vol.Optional(ATTR_CONFIRM, default=False): cv.boolean,
    }
)
ZONE_VALUES = vol.Schema(
    {
        vol.Required(ATTR_MODE): vol.In(list(ALL_MODES)),
        vol.Required(ATTR_TEMP): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
        vol.Required(ATTR_MINUTES): vol.All(vol.Coerce(int), vol.Range(min=1, max=5000)),
    }
)
SYNC_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DEVICE): cv.string,
        vol.Optional(ATTR_ZONE1): ZONE_VALUES,
        vol.Optional(ATTR_ZONE2): ZONE_VALUES,
        # Match: von welcher Zone die Werte für beide kommen
        vol.Optional(ATTR_SOURCE, default=1): vol.All(vol.Coerce(int), vol.In([1, 2])),
        vol.Optional(ATTR_ONCE, default=False): cv.boolean,
        vol.Optional(ATTR_STRICT, default=False): cv.boolean,
        # true (wie bisher) = vorbereitete Zonen vorher zurücksetzen; false = dann abbrechen
        vol.Optional(ATTR_RESET, default=True): cv.boolean,
    }
)
FAV_SAVE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DEVICE): cv.string,
        vol.Required(ATTR_NAME): vol.All(cv.string, vol.Strip, vol.Length(min=1, max=40)),
        vol.Required(ATTR_MODE): vol.In(list(ALL_MODES)),
        vol.Required(ATTR_TEMP): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
        vol.Required(ATTR_MINUTES): vol.All(vol.Coerce(int), vol.Range(min=1, max=5000)),
    }
)
FAV_DELETE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DEVICE): cv.string,
        vol.Required(ATTR_NAME): vol.All(cv.string, vol.Strip, vol.Length(min=1, max=40)),
    }
)
ADD_TIME_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DEVICE): cv.string,
        vol.Optional(ATTR_ZONE, default=1): vol.All(vol.Coerce(int), vol.In([1, 2, 3])),
        vol.Optional(ATTR_MINUTES, default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
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


async def _send_sync(call: ServiceCall, sync_type: int) -> ServiceResponse:
    """Match (1) oder Sync (2) bereitstellen – nie starten.

    Ohne Extras wie bisher: Werte aus den Zonen-Eingaben, vorbereitete Zonen werden
    vorher zurückgesetzt, ein Fehler erscheint als Meldung. Mit ``return_response``
    gibt es statt der Meldung eine Antwort mit ``ergebnis``.
    """
    coordinator, fryer = _find_any(call.hass, call.data.get(ATTR_DEVICE))
    base: dict[str, Any] = {"art": "match" if sync_type == 1 else "sync", "revision_vorher": fryer.revision}
    values = {
        zone: (v[ATTR_MODE], v[ATTR_TEMP], v[ATTR_MINUTES])
        for zone, key in ((1, ATTR_ZONE1), (2, ATTR_ZONE2))
        if (v := call.data.get(key))
    }
    source = call.data[ATTR_SOURCE]
    if sync_type == 2 and len(values) == 1:
        return _sync_fail(call, {**base, "fehler": "beide_zonen_noetig"},
                          "Für Sync bitte Werte für beide Zonen angeben (zone1 und zone2) – oder keine.")
    if sync_type == 1 and values and source not in values:
        return _sync_fail(call, {**base, "fehler": "quelle_fehlt"},
                          f"Für Match fehlen die Werte der Quelle (zone{source}).")
    for zone, (mode, _t, _m) in values.items():
        if mode not in modes_for(fryer.model):
            return _sync_fail(call, {**base, "fehler": "programm_unbekannt", "zone": zone},
                              f"Das Programm „{mode}“ gibt es an diesem Modell nicht (Zone {zone}).")
    try:
        plans = sync_plans(
            coordinator, fryer, sync_type, values, source=source, strict=call.data[ATTR_STRICT]
        )
    except ValueError as err:
        zone, limits = err.args
        return _sync_fail(call, {**base, "fehler": "ausserhalb_grenzen", "zone": zone, "grenzen": limits},
                          f"Zone {zone}: Werte außerhalb der Grenzen {limits}. Nichts gesendet.")
    sent = {
        f"zone{zone}": {"programm": p[0], "temperatur": p[1], "minuten": p[2]}
        for zone, p in ((1, plans[0]), (2, plans[1]))
    }
    try:
        await async_send_sync(
            coordinator, fryer, sync_type, plans=plans,
            once=call.data[ATTR_ONCE], reset=call.data[ATTR_RESET],
        )
    except SyncBlocked as err:
        return _sync_fail(call, {**base, "fehler": err.reason}, str(err))
    except AirfryerError as err:
        unknown = isinstance(err, AirfryerConnectionError) or err.code == CODE_DEVICE_TIMEOUT
        answer = {**base, "ergebnis": RESULT_UNKNOWN if unknown else RESULT_REJECTED,
                  "fehler": str(err), "code": err.code, "gesendet": sent}
        return _sync_fail(call, answer, f"Fritteuse hat Match/Sync abgelehnt: {err}")
    if not call.return_response:
        return None
    return {**base, "ok": True, "ergebnis": RESULT_ACCEPTED, "gesendet": sent}


def _sync_fail(call: ServiceCall, answer: dict[str, Any], message: str) -> ServiceResponse:
    """Ohne Antwort-Wunsch wie bisher eine Meldung, sonst eine Antwort mit ``ergebnis``."""
    if not call.return_response:
        raise HomeAssistantError(message)
    return {"ok": False, "ergebnis": RESULT_REJECTED, **answer}


async def _match(call: ServiceCall) -> ServiceResponse:
    return await _send_sync(call, 1)


async def _sync(call: ServiceCall) -> ServiceResponse:
    return await _send_sync(call, 2)


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
    if mode not in modes_for(fryer.model):  # z. B. Gären nur an der Turbo Tower
        return {**base, "ok": False, "ergebnis": RESULT_REJECTED, "fehler": "programm_unbekannt", "programme": list(modes_for(fryer.model))}
    if call.data[ATTR_STRICT]:
        limits = outside_limits(mode, temp, minutes, fryer.model)
        if limits is not None:
            return {
                **base,
                "ok": False,
                "ergebnis": RESULT_REJECTED,
                "fehler": "ausserhalb_grenzen",
                "grenzen": limits,
            }
    else:
        temp = clamp_temp(mode, temp, fryer.model)
        minutes = clamp_minutes(mode, minutes, fryer.model)
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
            and zs.mode.lower() == ALL_MODES[mode].lower()
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


def _program_store(call: ServiceCall):
    store = get_store(call.hass)
    if store is None:
        raise HomeAssistantError("Airfryer Control ist noch nicht fertig geladen.")
    return store


async def _fav_save(call: ServiceCall) -> None:
    """⭐ Liebling speichern (Werte werden auf die Grenzen des Programms gesetzt)."""
    _coordinator, fryer = _find_any(call.hass, call.data.get(ATTR_DEVICE))
    mode = call.data[ATTR_MODE]
    if mode not in modes_for(fryer.model):
        raise ServiceValidationError(f"Das Programm „{mode}“ gibt es an diesem Modell nicht.")
    temp = clamp_temp(mode, call.data[ATTR_TEMP], fryer.model)
    minutes = clamp_minutes(mode, call.data[ATTR_MINUTES], fryer.model)
    if not _program_store(call).save_favorite(fryer.cid, call.data[ATTR_NAME], mode, temp, minutes):
        raise ServiceValidationError("Schon 12 Lieblinge – lösch erst einen, dann passt der neue rein.")


async def _fav_delete(call: ServiceCall) -> None:
    _coordinator, fryer = _find_any(call.hass, call.data.get(ATTR_DEVICE))
    _program_store(call).delete_favorite(fryer.cid, call.data[ATTR_NAME])


async def _add_time(call: ServiceCall) -> ServiceResponse:
    """⏱️ Garzeit verlängern: +1 / +3 Minuten aus der Karte.

    Für Doofe – je nachdem, was die Zone gerade macht:
    - gart (oder Pause/Schublade offen): die eingestellte Zeit wird um X Minuten länger
      (gleicher Befehl wie die App beim Zeit-Ändern, „setTimeOrTemp“),
    - fertig oder hält warm: dasselbe Programm wird für X Minuten nochmal bereitgestellt
      („Nachgaren“) – gestartet wird wie immer am Gerät,
    - sonst: nur das Zeit-Feld der Zone wird um X Minuten größer.
    """
    coordinator, fryer = _find_any(call.hass, call.data.get(ATTR_DEVICE))
    zone, extra = call.data[ATTR_ZONE], call.data[ATTR_MINUTES]
    plan = get_plan(coordinator, fryer.cid, zone)
    zs = zone_view(fryer.state, zone) if fryer.online else None
    if zs is not None and zs.active:
        if not zs.set_time_s:
            raise HomeAssistantError("Die Fritteuse meldet keine eingestellte Garzeit – bitte am Gerät verlängern.")
        minutes = clamp_minutes(plan["mode"], round(zs.set_time_s / 60) + extra, fryer.model)
        try:
            await coordinator.api.bypass_v2(fryer.info, "setTimeOrTemp", build_change_payload(zs, None, minutes))
        except AirfryerError as err:
            raise HomeAssistantError(f"Fritteuse hat „Garzeit verlängern“ abgelehnt: {err}") from err
        plan["minuten"] = minutes
        await coordinator.async_request_fast_refresh()
        return {"ergebnis": "verlaengert", "minuten": minutes} if call.return_response else None
    if zs is not None and zs.status in (STATE_FINISHED, STATE_KEEP_WARM):
        minutes = clamp_minutes(plan["mode"], extra, fryer.model)
        temp = clamp_temp(plan["mode"], plan["temp"], fryer.model)
        try:
            results = await async_send(
                coordinator, fryer, zone, temp, minutes, plan["mode"], allow_start=False
            )
        except AirfryerError as err:
            raise HomeAssistantError(f"Fritteuse hat „Nachgaren“ abgelehnt: {err}") from err
        if not any(r["ok"] for r in results):
            raise HomeAssistantError("Fritteuse hat „Nachgaren“ abgelehnt.")
        plan["minuten"] = minutes
        coordinator.async_update_listeners()
        return {"ergebnis": "bereitgestellt", "minuten": minutes} if call.return_response else None
    minutes = clamp_minutes(plan["mode"], int(plan["minuten"]) + extra, fryer.model)
    plan["minuten"] = minutes
    coordinator.async_update_listeners()  # Zeit-Feld der Zone zeigt den neuen Wert
    return {"ergebnis": "gemerkt", "minuten": minutes} if call.return_response else None


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
    hass.services.async_register(
        DOMAIN, SERVICE_MATCH, _match, schema=SYNC_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SYNC, _sync, schema=SYNC_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )
    hass.services.async_register(DOMAIN, SERVICE_FAV_SAVE, _fav_save, schema=FAV_SAVE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_FAV_DELETE, _fav_delete, schema=FAV_DELETE_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_TIME, _add_time, schema=ADD_TIME_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )
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
