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
    MODE_TEMP_RANGE,
    MODE_TIME_RANGE,
    MODES,
    TEMP_MAX_DEFAULT,
    TEMP_MIN_DEFAULT,
    TIME_MAX_DEFAULT,
    TIME_MIN_DEFAULT,
)
from .coordinator import AirfryerCoordinator, FryerData
from .core.parser import zones_for_device
from .core.util import redact

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


def temp_limits(mode: str) -> tuple[int, int]:
    """Erlaubter Temperaturbereich (°C) für ein Programm."""
    return MODE_TEMP_RANGE.get(mode, (TEMP_MIN_DEFAULT, TEMP_MAX_DEFAULT))


def clamp_temp(mode: str, temp: int) -> int:
    """Temperatur in den erlaubten Bereich schieben."""
    low, high = temp_limits(mode)
    return max(low, min(high, int(temp)))


def time_limits(mode: str) -> tuple[int, int]:
    """Erlaubte Garzeit (Minuten) für ein Programm."""
    return MODE_TIME_RANGE.get(mode, (TIME_MIN_DEFAULT, TIME_MAX_DEFAULT))


def clamp_minutes(mode: str, minutes: int) -> int:
    """Garzeit in den erlaubten Bereich schieben."""
    low, high = time_limits(mode)
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
    app_mode = MODES.get(mode, mode)
    secs = int(minutes) * 60
    acc = account_id or ""

    def multi(unit: str, work: int, *, ready: bool = True) -> dict[str, Any]:
        config: dict[str, Any] = {
            "cookSetTime": secs,
            "cookTemp": int(temp),
            "mode": app_mode,
            "chamber": zone,
        }
        # Wie die Schwester-Fritteuse (Turbo Tower Pro) in pyvesync: mit Rezept-Angaben
        config.update(
            recipeId=14,
            recipeName="Air Fry" if mode == "airfry" else app_mode,
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
        app_mode = MODES.get(mode, mode)
        config: dict[str, Any] = {
            "cookSetTime": minutes * 60,
            "cookTemp": int(temp),
            "mode": app_mode,
            "chamber": chamber,
            "recipeId": 14,
            "recipeName": "Air Fry" if mode == "airfry" else app_mode,
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


async def _reset_prepared_zones(coordinator: AirfryerCoordinator, fryer: FryerData) -> None:
    """Vorbereitete (nicht gestartete) Zonen zurücksetzen, damit Match/Sync angenommen wird.

    Sicherung: Nur wenn **keine** Zone arbeitet. Beendet wird nur, was auf „Wartet auf Start“
    (oder „Wartet auf Sync“) steht – nie etwas, das schon läuft.
    """
    await coordinator.async_refresh()  # aktuellen Stand holen, nicht den von vor einer Minute
    zones = (1, 2)
    states = {z: _zone_status(fryer, z) for z in zones}
    if any(st in BUSY for st in states.values()):
        return  # irgendwas arbeitet: nichts anfassen, die Fritteuse entscheidet selbst
    todo = [z for z in zones if states[z] in PREPARED]
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
    if not todo:
        return
    for _ in range(RESET_TRIES):  # warten, bis beide Zonen wieder frei sind
        await asyncio.sleep(RESET_WAIT_SECONDS)
        await coordinator.async_refresh()
        if not any(_zone_status(fryer, z) in PREPARED for z in zones):
            return


async def async_send_sync(
    coordinator: AirfryerCoordinator, fryer: FryerData, sync_type: int
) -> dict[str, Any]:
    """Match/Sync mit den Werten der beiden Zonen-Eingaben bereitstellen.

    Für Doofe: Hat man vorher einzelne Zonen mit „Senden“ vorbereitet, lehnt die Fritteuse
    Match/Sync ab (Code 11912000, gemeldet an einer Turbo Tower Pro Smart). Darum werden
    zuerst nur **vorbereitete, noch nicht gestartete** Zonen zurückgesetzt. Läuft irgendeine
    Zone (heizt, gart, pausiert, Schublade offen), wird NICHTS beendet.
    """
    cid = fryer.cid
    await _reset_prepared_zones(coordinator, fryer)
    plans = []
    for zone in (1, 2):
        plan = get_plan(coordinator, cid, zone)
        plans.append(
            (plan["mode"], clamp_temp(plan["mode"], plan["temp"]), clamp_minutes(plan["mode"], int(plan["minuten"])))
        )
    payload = build_sync_payload(coordinator.api.account_id, sync_type, plans[0], plans[1])
    answer = await coordinator.api.bypass_v2(fryer.info, "startMultiCook", payload)
    await coordinator.async_request_fast_refresh()
    return redact(answer) if isinstance(answer, dict) else {"antwort": answer}


RESULT_ACCEPTED = "angenommen"  # die Cloud hat den Befehl angenommen
RESULT_REJECTED = "abgelehnt"  # sicher nicht ausgeführt (Fehlercode, Anmeldung abgelaufen)
RESULT_UNKNOWN = "unbekannt"  # Verbindung weg/Zeitüberschreitung: vielleicht angekommen
SAFE_VARIANTS = ("multi_app", "multi_app_celsius", "multi_app_zone0")


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
    variants = build_variants(
        coordinator.api.account_id,
        zone,
        temp,
        minutes,
        mode,
        include_start=bool(only) and allow_start,
    )
    if only:
        variants = [v for v in variants if v.name == only]
    elif coordinator.send_variant:
        variants.sort(key=lambda v: v.name != coordinator.send_variant)
    if once:
        variants = variants[:1]
    extra = {"retry": False} if once else {}
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
