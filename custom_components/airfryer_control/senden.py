"""„Senden“: Garwerte an die Fritteuse schicken, ohne zu starten.

Für Doofe: In der App gibst du Korb, Programm, Temperatur und Zeit ein und
drückst unten „Senden“. Die Fritteuse wacht auf und wartet, bis du am Gerät
auf Start drückst. Der Befehl dafür ist `startMultiCook` mit Rezept-Angaben und
`readyStart: true` (so macht es auch die Schwester-Fritteuse in pyvesync).
Gemessen an Marcos TwinFry (20.10.2026): `readyStart: true` = bereitstellen, die Zone
steht danach auf „ready“ und wartet auf Start am Gerät. `readyStart: false` = die
Fritteuse STARTET sofort! Diese Form wird darum nie automatisch geschickt, nur wenn
man sie ausdrücklich verlangt.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from .core.api import (
    AirfryerAuthError,
    AirfryerConnectionError,
    AirfryerDeviceOffline,
    AirfryerError,
)
from .const import (
    STATE_COOKING,
    STATE_DRAWER_OPEN,
    STATE_HOLD,
    STATE_PAUSED,
    STATE_PREHEAT,
    STATE_WAITING,
    DEFAULT_MODE,
    MODE_DEFAULTS,
)
from .coordinator import AirfryerCoordinator, FryerData
from . import modelle
from .core.parser import zones_for_device
from .core.util import redact
from .programme import get_store

PAUSE_SECONDS = 1.0
RESET_WAIT_SECONDS = 1.5  # so lange warten, bis die Fritteuse das Zurücksetzen übernommen hat
RESET_TRIES = 6
PREPARED = {STATE_WAITING, STATE_HOLD}  # vorbereitet, aber noch nicht gestartet
BUSY = {STATE_PREHEAT, STATE_COOKING, STATE_PAUSED, STATE_DRAWER_OPEN}  # arbeitet: nie anfassen


def get_plan(coordinator: AirfryerCoordinator, cid: str, zone: int) -> dict[str, Any]:
    """Die Eingaben einer Zone (Programm, Temperatur, Minuten) – mit Vorschlagswerten."""
    plan = coordinator.plans.get((cid, zone))
    if plan is None:
        temp, minutes = MODE_DEFAULTS[DEFAULT_MODE]
        plan = {"mode": DEFAULT_MODE, "temp": temp, "minuten": minutes}
        coordinator.plans[(cid, zone)] = plan
    return plan


def temp_limits(mode: str, model: str | None = None) -> tuple[int, int]:
    """Erlaubter Temperaturbereich (°C) für ein Programm (je Modell, siehe modelle.py)."""
    return modelle.temp_limits(mode, model)


def clamp_temp(mode: str, temp: int, model: str | None = None) -> int:
    """Temperatur in den erlaubten Bereich schieben."""
    low, high = temp_limits(mode, model)
    return max(low, min(high, int(temp)))


def time_limits(mode: str, model: str | None = None) -> tuple[int, int]:
    """Erlaubte Garzeit (Minuten) für ein Programm (je Modell)."""
    return modelle.time_limits(mode, model)


def clamp_minutes(mode: str, minutes: int, model: str | None = None) -> int:
    """Garzeit in den erlaubten Bereich schieben."""
    low, high = time_limits(mode, model)
    return max(low, min(high, int(minutes)))


@dataclass(frozen=True)
class SendVariant:
    """Eine Schreibweise des „Senden“-Befehls."""

    name: str
    method: str
    payload: dict[str, Any]


def build_variants(
    account_id: str | None,
    zone: int,
    temp: int,
    minutes: int,
    mode: str,
    *,
    include_start: bool = False,
) -> list[SendVariant]:
    """Schreibweisen für „Senden“ (bereitstellen) – mit Start nur, wenn include_start an ist."""
    app_mode = modelle.ALL_MODES.get(mode, mode)
    secs = int(minutes) * 60
    acc = account_id or ""

    def multi(unit: str, work: int, *, ready: bool = True) -> dict[str, Any]:
        config: dict[str, Any] = {
            "cookSetTime": secs,
            "cookTemp": int(temp),
            "mode": app_mode,
            "chamber": zone,
        }
        # Rezept-Angaben wie die App (Nummern aus pyvesync, siehe modelle.RECIPES)
        rid, rname = modelle.recipe(mode)
        config.update(
            recipeId=rid,
            recipeName=rname,
            recipeType=3,
            shakeTime=0,
        )
        return {
            "syncType": 0,
            "workChamber": work,
            "tempUnit": unit,
            "accountId": acc,
            # true = nur bereitstellen (Zone steht dann auf „ready“ und wartet auf Start am Gerät).
            # false = die TwinFry STARTET sofort!
            "readyStart": ready,
            "cookConfigs": [config],
        }

    safe = [
        SendVariant("multi_app", "startMultiCook", multi("c", zone)),
        SendVariant("multi_app_celsius", "startMultiCook", multi("celsius", zone)),
        SendVariant("multi_app_zone0", "startMultiCook", multi("c", 0)),
    ]
    if include_start:
        # Nur auf ausdrücklichen Wunsch (Dienst „Senden testen“ mit variante): STARTET wirklich!
        safe.append(
            SendVariant("multi_app_startet", "startMultiCook", multi("c", zone, ready=False))
        )
    return safe


# 🍗 Dual Blaze CAF-P583S: Diese Felder schickt die App bei JEDEM Befehl mit (pyvesync)
SUB_DEVICE = {"subDeviceNo": 0, "subDeviceType": ""}


def build_single_variants(
    account_id: str | None,
    temp: int,
    minutes: int,
    mode: str,
    *,
    include_start: bool = False,
) -> list[SendVariant]:
    """„Senden“ für die Dual Blaze CAF-P583S (ein Korb): Befehl ``startCook``.

    Für Doofe: Die TwinFry versteht „startMultiCook“ (mehrere Körbe). Die
    P583S hat nur einen Korb und will „startCook“ mit ``startAct`` – so steht es in
    pyvesync (mitgeschnitten an einer CAF-P583S-KUS). ``readyStart: true`` = nur
    bereitstellen, gestartet wird am Gerät.
    """
    rid, rname = modelle.recipe(mode)

    def single(unit: str, *, ready: bool = True) -> dict[str, Any]:
        return {
            "accountID": account_id or "",
            "hasLinkage": False,
            "hasPreheat": 0,
            "hasWarm": False,
            "mode": modelle.ALL_MODES.get(mode, mode),
            "readyStart": ready,
            "recipeId": rid,
            "recipeName": rname,
            "recipeType": 3,
            "tempUnit": unit,
            "startAct": {
                "cookSetTime": int(minutes) * 60,
                "cookTemp": int(temp),
                "preheatTemp": 0,
                "shakeTime": 0,
            },
        }

    variants = [
        SendVariant("single_app", "startCook", single("c")),
        SendVariant("single_app_celsius", "startCook", single("celsius")),
    ]
    if include_start:
        variants.append(SendVariant("single_app_startet", "startCook", single("c", ready=False)))
    return variants


def build_sync_payload(
    account_id: str | None,
    sync_type: int,
    zone1: tuple[str, int, int],
    zone2: tuple[str, int, int],
) -> dict[str, Any]:
    """Match (1: beide Zonen gleich) oder Sync (2: beide fertig zur selben Zeit) bereitstellen.

    Je Zone ``(Programm, Temperatur °C, Minuten)``. Bei Match gelten die Werte von
    Zone 1 für beide Zonen. Bei Sync bekommt die kürzere Zone ``holdTime`` = Zeitunterschied
    (sie wartet, bis die längere dran ist). ``readyStart: true`` = nur bereitstellen,
    nichts heizt, Start am Gerät. Gemessen an Marcos TwinFry: ``workChamber`` 4 bei beiden.
    ACHTUNG: Der genaue App-Befehl wurde nicht mitgeschnitten – das ist die vermutete Form.
    """
    if sync_type == 1:
        zone2 = zone1
    configs: list[dict[str, Any]] = []
    times = [zone1[2] * 60, zone2[2] * 60]
    longest = max(times)
    for chamber, (mode, temp, minutes) in enumerate((zone1, zone2), start=1):
        app_mode = modelle.ALL_MODES.get(mode, mode)
        rid, rname = modelle.recipe(mode)
        config: dict[str, Any] = {
            "cookSetTime": minutes * 60,
            "cookTemp": int(temp),
            "mode": app_mode,
            "chamber": chamber,
            "recipeId": rid,
            "recipeName": rname,
            "recipeType": 3,
            "shakeTime": 0,
        }
        if sync_type == 2:
            config["holdTime"] = longest - minutes * 60
        configs.append(config)
    return {
        "syncType": sync_type,
        "workChamber": 4,
        "tempUnit": "c",
        "accountId": account_id or "",
        "readyStart": True,
        "cookConfigs": configs,
    }


def _zone_status(fryer: FryerData, zone: int) -> str | None:
    zs = fryer.state.zones.get(zone)
    return zs.status if zs else None


class SyncBlocked(AirfryerError):
    """Match/Sync geht gerade nicht (Zone arbeitet, vorbereitete Zone, offline) – nichts gesendet."""

    def __init__(self, message: str, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


async def _check_and_reset(
    coordinator: AirfryerCoordinator, fryer: FryerData, *, reset: bool
) -> None:
    """Vor Match/Sync prüfen – und vorbereitete Zonen nur zurücksetzen, wenn ``reset`` an ist.

    Für Doofe: Arbeitet eine Zone (heizt, gart, pausiert, Schublade offen), wird
    NICHTS gesendet und NICHTS beendet – es gibt eine klare Meldung (SyncBlocked).
    Vorbereitete (noch nicht gestartete) Zonen lehnt die Fritteuse bei Match/Sync ab
    (Code 11912000). Mit ``reset`` werden nur diese zurückgesetzt; klappt das nicht
    rechtzeitig, wird ebenfalls abgebrochen statt trotzdem zu senden.
    """
    await coordinator.async_refresh()  # aktuellen Stand holen, nicht den von vor einer Minute
    if not fryer.online:
        raise SyncBlocked("Die Fritteuse ist offline – Match/Sync wurde nicht gesendet.", "offline")
    zones = (1, 2)
    states = {z: _zone_status(fryer, z) for z in zones}
    busy = [z for z in zones if states[z] in BUSY]
    if busy:
        names = " und ".join(f"Zone {z}" for z in busy)
        raise SyncBlocked(
            f"{names} {'arbeiten' if len(busy) > 1 else 'arbeitet'} gerade – Match/Sync geht erst, wenn beide Zonen frei sind. Nichts gesendet.",
            "zone_arbeitet",
        )
    todo = [z for z in zones if states[z] in PREPARED]
    if not todo:
        return
    if not reset:
        names = " und ".join(f"Zone {z}" for z in todo)
        raise SyncBlocked(
            f"{names} {'sind' if len(todo) > 1 else 'ist'} schon vorbereitet. Ohne „zuruecksetzen“ wird nichts gesendet.",
            "zone_vorbereitet",
        )
    for z in todo:
        try:
            await coordinator.api.bypass_v2(fryer.info, "endCook", {"chamber": z})
        except AirfryerDeviceOffline:
            raise
        except AirfryerError as err:
            if err.code == NO_PROGRAM_CODE:
                continue  # war schon leer
            raise AirfryerError(
                f"Das vorbereitete Programm in Zone {z} ließ sich nicht zurücksetzen: {err}", err.code
            ) from err
    for _ in range(RESET_TRIES):  # warten, bis beide Zonen wieder frei sind
        await asyncio.sleep(RESET_WAIT_SECONDS)
        await coordinator.async_refresh()
        if not any(_zone_status(fryer, z) in PREPARED for z in zones):
            return
    raise SyncBlocked(
        "Die vorbereiteten Zonen sind nach dem Zurücksetzen noch nicht frei – Match/Sync wurde nicht gesendet.",
        "zuruecksetzen_dauert",
    )


def sync_plans(
    coordinator: AirfryerCoordinator,
    fryer: FryerData,
    sync_type: int,
    values: dict[int, tuple[str, int, int]] | None = None,
    *,
    source: int = 1,
    strict: bool = False,
) -> tuple[tuple[str, int, int], tuple[str, int, int]]:
    """Werte für Zone 1 und 2: übergeben (``values``) oder aus den Eingaben der Karte.

    Match: die Werte der Quell-Zone gelten für beide. Mit ``strict`` wird nichts still
    angepasst – Werte außerhalb der Grenzen werfen ValueError(zone, grenzen).
    """
    from .faehigkeiten import outside_limits  # spät laden: faehigkeiten importiert senden

    values = values or {}
    plans: dict[int, tuple[str, int, int]] = {}
    for zone in (1, 2):
        if zone in values:
            mode, temp, minutes = values[zone]
        else:
            plan = get_plan(coordinator, fryer.cid, zone)
            mode, temp, minutes = plan["mode"], int(plan["temp"]), int(plan["minuten"])
        plans[zone] = (mode, temp, minutes)
    if sync_type == 1:
        plans = {1: plans[source], 2: plans[source]}
    checked: dict[int, tuple[str, int, int]] = {}
    for zone, (mode, temp, minutes) in plans.items():
        if strict:
            limits = outside_limits(mode, temp, minutes, fryer.model)
            if limits is not None:
                raise ValueError(zone, limits)
            checked[zone] = (mode, temp, minutes)
        else:
            checked[zone] = (
                mode,
                clamp_temp(mode, temp, fryer.model),
                clamp_minutes(mode, minutes, fryer.model),
            )
    return checked[1], checked[2]


async def async_send_sync(
    coordinator: AirfryerCoordinator,
    fryer: FryerData,
    sync_type: int,
    *,
    plans: tuple[tuple[str, int, int], tuple[str, int, int]] | None = None,
    once: bool = False,
    reset: bool = True,
) -> dict[str, Any]:
    """Match/Sync bereitstellen (nie starten). Ohne ``plans``: die Werte der Zonen-Eingaben.

    Wirft SyncBlocked, wenn gerade nichts gesendet werden darf (dann ist auch nichts
    rausgegangen). Mit ``once`` keine Wiederholung nach neuer Anmeldung.
    """
    await _check_and_reset(coordinator, fryer, reset=reset)
    if plans is None:
        plans = sync_plans(coordinator, fryer, sync_type)
    payload = build_sync_payload(coordinator.api.account_id, sync_type, plans[0], plans[1])
    extra = {"retry": False} if once else {}
    answer = await coordinator.api.bypass_v2(fryer.info, "startMultiCook", payload, **extra)
    await coordinator.async_request_fast_refresh()
    return redact(answer) if isinstance(answer, dict) else {"antwort": answer}


RESULT_ACCEPTED = "angenommen"  # die Cloud hat den Befehl angenommen
RESULT_REJECTED = "abgelehnt"  # sicher nicht ausgeführt (Fehlercode, Anmeldung abgelaufen)
RESULT_UNKNOWN = "unbekannt"  # Verbindung weg/Zeitüberschreitung: vielleicht angekommen
SAFE_VARIANTS = ("multi_app", "multi_app_celsius", "multi_app_zone0", "single_app", "single_app_celsius")


def _other_side(zone: int) -> tuple[int, ...]:
    """Was schließt sich aus? Grandzone (3) ↔ Zone 1 und 2."""
    return (1, 2) if zone == 3 else (3,) if zone in (1, 2) else ()


def _side_name(zone: int, de: bool) -> str:
    if zone == 3:
        return "Grandzone" if de else "Whole basket"
    return f"Zone {zone}"


async def _free_other_side(coordinator: AirfryerCoordinator, fryer: FryerData, zone: int) -> None:
    """Grandzone und Zone 1/2 automatisch umschalten (Issue #9).

    Für Doofe: Die TwinFry kann entweder EINE große Schublade (Grandzone) oder zwei
    Körbe (Zone 1/2). Ist die andere Seite nur vorbereitet („Wartet auf Start“), wird
    sie vorher automatisch zurückgesetzt. Gart sie gerade, wird NICHTS beendet –
    dann kommt eine klare Meldung (SyncBlocked), und nichts wird gesendet.
    """
    others = _other_side(zone)
    if not others:
        return
    de = str(coordinator.hass.config.language or "de").startswith("de")
    if any(_zone_status(fryer, z) in PREPARED | BUSY for z in others):
        await coordinator.async_refresh()  # frischen Stand holen, nicht den von vor einer Minute
    states = {z: _zone_status(fryer, z) for z in others}
    busy = [z for z in others if states[z] in BUSY]
    if busy:
        name = " und ".join(_side_name(z, de) for z in busy) if de else " and ".join(_side_name(z, de) for z in busy)
        verb = ("garen" if len(busy) > 1 else "gart") if de else ("are" if len(busy) > 1 else "is")
        raise SyncBlocked(
            f"{name} {verb} gerade – bitte erst beenden. Nichts gesendet."
            if de
            else f"{name} {verb} cooking right now – please stop it first. Nothing was sent.",
            "andere_seite_gart",
        )
    todo = [z for z in others if states[z] in PREPARED]
    if not todo:
        return
    for z in todo:
        try:
            await coordinator.api.bypass_v2(fryer.info, "endCook", {"chamber": z})
        except AirfryerDeviceOffline:
            raise
        except AirfryerError as err:
            if err.code != NO_PROGRAM_CODE:
                raise
    for _ in range(RESET_TRIES):  # warten, bis die Fritteuse das übernommen hat
        await asyncio.sleep(RESET_WAIT_SECONDS)
        await coordinator.async_refresh()
        if not any(_zone_status(fryer, z) in PREPARED for z in others):
            return
    raise SyncBlocked(
        f"{' und '.join(_side_name(z, de) for z in todo)} ließ sich nicht rechtzeitig zurücksetzen – nichts gesendet."
        if de
        else f"{' and '.join(_side_name(z, de) for z in todo)} could not be reset in time – nothing was sent.",
        "zuruecksetzen_dauert",
    )


async def async_send(
    coordinator: AirfryerCoordinator,
    fryer: FryerData,
    zone: int,
    temp: int,
    minutes: int,
    mode: str,
    *,
    only: str | None = None,
    try_all: bool = False,
    once: bool = False,
    allow_start: bool = True,
) -> list[dict[str, Any]]:
    """Varianten durchprobieren. Merkt sich die erste, die angenommen wird.

    Mit ``only`` wird genau eine Variante geschickt, mit ``try_all`` alle
    (sonst Stopp beim ersten Treffer). Ist schon eine Variante bekannt, geht
    sie zuerst raus. Nur mit ``only`` (und ``allow_start``) darf auch die
    startende Form raus. Mit ``once`` geht genau ein Befehl raus: keine
    weitere Variante und keine Wiederholung nach neuer Anmeldung.

    Für Doofe: Ist das Ergebnis „unbekannt“ (Verbindung weg), wird NIE eine
    weitere Variante geschickt – der erste Befehl könnte ja angekommen sein.
    """
    single = modelle.single_basket(fryer.model)
    if single:
        variants = build_single_variants(
            coordinator.api.account_id, temp, minutes, mode, include_start=bool(only) and allow_start
        )
        extra_payload: dict[str, Any] = {"payload_extra": dict(SUB_DEVICE)}
    else:
        variants = build_variants(
            coordinator.api.account_id,
            zone,
            temp,
            minutes,
            mode,
            include_start=bool(only) and allow_start,
        )
        extra_payload = {}
        if fryer.multizone:
            await _free_other_side(coordinator, fryer, zone)
    if only:
        variants = [v for v in variants if v.name == only]
    elif coordinator.send_variant:
        variants.sort(key=lambda v: v.name != coordinator.send_variant)
    if once:
        variants = variants[:1]
    extra: dict[str, Any] = {"retry": False} if once else {}
    extra.update(extra_payload)
    results: list[dict[str, Any]] = []
    for i, variant in enumerate(variants):
        if i:
            await asyncio.sleep(PAUSE_SECONDS)
        entry: dict[str, Any] = {"variante": variant.name, "methode": variant.method}
        try:
            answer = await coordinator.api.bypass_v2(
                fryer.info, variant.method, variant.payload, **extra
            )
        except AirfryerDeviceOffline:
            raise
        except AirfryerConnectionError as err:
            entry.update(ok=False, ergebnis=RESULT_UNKNOWN, code=err.code, fehler=str(err))
            results.append(entry)
            break
        except AirfryerAuthError as err:
            entry.update(ok=False, ergebnis=RESULT_REJECTED, code=err.code, fehler=str(err))
            results.append(entry)
            break
        except AirfryerError as err:
            entry.update(ok=False, ergebnis=RESULT_REJECTED, code=err.code, fehler=str(err))
            results.append(entry)
            continue
        entry.update(ok=True, ergebnis=RESULT_ACCEPTED, antwort=redact(answer))
        results.append(entry)
        store = get_store(coordinator.hass)
        if store is not None and sum(r["ok"] for r in results) == 1:
            store.add_recent(fryer.cid, zone, mode, temp, minutes)  # 🕘 für „Zuletzt gesendet“ (einmal)
        if coordinator.send_variant != variant.name:
            coordinator.send_variant = variant.name
        if not try_all:
            break
    await coordinator.async_request_fast_refresh()
    return results


NO_PROGRAM_CODE = 11923000  # „Zone hat kein Programm“ → ist schon aus


async def async_end(
    coordinator: AirfryerCoordinator, fryer: FryerData, zone: int | None = None
) -> None:
    """Zone(n) beenden. Ohne ``zone`` werden alle Zonen beendet.

    Die TwinFry will bei ``endCook`` die Zone wissen. Hat eine Zone kein Programm,
    meldet sie Code 11923000 – das zählt als „schon aus“, nicht als Fehler.
    """
    if fryer.model.startswith("CS"):
        await coordinator.api.bypass_v2(fryer.info, "endCook", {})
        await coordinator.async_request_fast_refresh()
        return
    if modelle.single_basket(fryer.model):
        # 🍗 Dual Blaze P583S: „endCook“ ohne Zone, mit den App-Zusatzfeldern (pyvesync)
        try:
            await coordinator.api.bypass_v2(fryer.info, "endCook", {}, payload_extra=dict(SUB_DEVICE))
        except AirfryerError as err:
            if isinstance(err, AirfryerDeviceOffline) or err.code != NO_PROGRAM_CODE:
                raise
        await coordinator.async_request_fast_refresh()
        return
    zones = [zone] if zone else zones_for_device(fryer.state, fryer.multizone)
    errors: list[AirfryerError] = []
    done = 0
    for z in zones:
        try:
            await coordinator.api.bypass_v2(fryer.info, "endCook", {"chamber": z})
            done += 1
        except AirfryerDeviceOffline:
            raise
        except AirfryerError as err:
            if err.code == NO_PROGRAM_CODE:
                done += 1
            else:
                errors.append(err)
    await coordinator.async_request_fast_refresh()
    if errors and not done:
        raise errors[0]
