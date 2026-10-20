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

from .core.api import AirfryerDeviceOffline, AirfryerError
from .const import (
    DEFAULT_MODE,
    MODE_DEFAULTS,
    MODE_TEMP_RANGE,
    MODES,
    TEMP_MAX_DEFAULT,
    TEMP_MIN_DEFAULT,
)
from .coordinator import AirfryerCoordinator, FryerData
from .core.parser import zones_for_device
from .core.util import redact

PAUSE_SECONDS = 1.0


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
) -> list[dict[str, Any]]:
    """Varianten durchprobieren. Merkt sich die erste, die angenommen wird.

    Mit ``only`` wird genau eine Variante geschickt, mit ``try_all`` alle
    (sonst Stopp beim ersten Treffer). Ist schon eine Variante bekannt, geht
    sie zuerst raus. Nur mit ``only`` darf auch die startende Form raus.
    """
    variants = build_variants(
        coordinator.api.account_id, zone, temp, minutes, mode, include_start=bool(only)
    )
    if only:
        variants = [v for v in variants if v.name == only]
    elif coordinator.send_variant:
        variants.sort(key=lambda v: v.name != coordinator.send_variant)
    results: list[dict[str, Any]] = []
    for i, variant in enumerate(variants):
        if i:
            await asyncio.sleep(PAUSE_SECONDS)
        entry: dict[str, Any] = {"variante": variant.name, "methode": variant.method}
        try:
            answer = await coordinator.api.bypass_v2(fryer.info, variant.method, variant.payload)
        except AirfryerDeviceOffline:
            raise
        except AirfryerError as err:
            entry.update(ok=False, code=err.code, fehler=str(err))
            results.append(entry)
            continue
        entry.update(ok=True, antwort=redact(answer))
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
