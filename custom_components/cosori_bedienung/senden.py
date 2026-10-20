"""„Senden“: Garwerte an die Fritteuse schicken, ohne zu starten.

Für Doofe: In der App gibst du Korb, Programm, Temperatur und Zeit ein und
drückst unten „Senden“. Die Fritteuse wacht auf und wartet, bis du am Gerät
auf Start drückst. Der Befehl dafür ist `startMultiCook` mit Rezept-Angaben
(so macht es auch die Schwester-Fritteuse in pyvesync). Zur Sicherheit probieren wir
bei Ablehnung noch ältere Schreibweisen durch und merken uns die, die klappt.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from .api import CosoriDeviceOffline, CosoriError
from .const import DEFAULT_MODE, MODE_DEFAULTS, MODES
from .coordinator import CosoriCoordinator, FryerData
from .util import redact

PAUSE_SECONDS = 1.0


def get_plan(coordinator: CosoriCoordinator, cid: str, zone: int) -> dict[str, Any]:
    """Die Eingaben einer Zone (Programm, Temperatur, Minuten) – mit Vorschlagswerten."""
    plan = coordinator.plans.get((cid, zone))
    if plan is None:
        temp, minutes = MODE_DEFAULTS[DEFAULT_MODE]
        plan = {"mode": DEFAULT_MODE, "temp": temp, "minuten": minutes}
        coordinator.plans[(cid, zone)] = plan
    return plan


@dataclass(frozen=True)
class SendVariant:
    """Eine Schreibweise des „Senden“-Befehls."""

    name: str
    method: str
    payload: dict[str, Any]


def build_variants(
    account_id: str | None, zone: int, temp: int, minutes: int, mode: str
) -> list[SendVariant]:
    """Alle Schreibweisen, die wir ausprobieren (die erste ist die bestätigte Form der App)."""
    app_mode = MODES.get(mode, mode)
    secs = int(minutes) * 60
    acc = account_id or ""

    def multi(unit: str, work: int, *, app: bool = False, ready: bool = False) -> dict[str, Any]:
        config: dict[str, Any] = {
            "cookSetTime": secs,
            "cookTemp": int(temp),
            "mode": app_mode,
            "chamber": zone,
        }
        if app:
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
            # „true“ heißt hier: Programm bereitstellen (Zone steht dann auf „ready“ und wartet
            # auf den Start-Knopf am Gerät) – ein Fernstart ist das nicht.
            "readyStart": ready,
            "cookConfigs": [config],
        }

    cook_mode_base = {
        "accountId": acc,
        "appointmentTs": 0,
        "cookSetTemp": int(temp),
        "cookSetTime": secs,
        "cookStatus": "cooking",
        "readyStart": False,
        "recipeType": 3,
        "tempUnit": "celsius",
    }
    start_cook = {
        "accountId": acc,
        "cookTempDECP": 0,
        "hasPreheat": 0,
        "hasWarm": False,
        "imageUrl": "",
        "mode": app_mode,
        "readyStart": False,
        "recipeId": 14,
        "recipeName": app_mode,
        "recipeType": 3,
        "startAct": {
            "appointingTime": 0,
            "cookSetTime": secs,
            "cookTemp": int(temp),
            "cookTempDECP": 0,
            "imageUrl": "",
            "level": 0,
            "preheatTemp": 0,
            "shakeTime": 0,
            "targetTemp": 0,
        },
        "tempUnit": "c",
    }
    return [
        SendVariant("multi_app", "startMultiCook", multi("c", zone, app=True, ready=True)),
        SendVariant("multi_app_ohne_ready", "startMultiCook", multi("c", zone, app=True)),
        SendVariant("multi_c", "startMultiCook", multi("c", zone)),
        SendVariant("multi_celsius", "startMultiCook", multi("celsius", zone)),
        SendVariant("multi_arbeitszone0", "startMultiCook", multi("c", 0)),
        SendVariant(
            "kochmodus_manuell",
            "cookMode",
            {**cook_mode_base, "customRecipe": "Manuell", "mode": "custom", "recipeId": 1,
             "chamber": zone},
        ),
        SendVariant(
            "kochmodus_programm",
            "cookMode",
            {**cook_mode_base, "mode": app_mode, "recipeId": 14, "chamber": zone},
        ),
        SendVariant(
            "kochmodus_ohne_zone",
            "cookMode",
            {**cook_mode_base, "customRecipe": "Manuell", "mode": "custom", "recipeId": 1},
        ),
        SendVariant("startkochen_zone", "startCook", {**start_cook, "chamber": zone}),
        SendVariant("startkochen", "startCook", start_cook),
    ]


async def async_send(
    coordinator: CosoriCoordinator,
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
    sie zuerst raus.
    """
    variants = build_variants(coordinator.api.account_id, zone, temp, minutes, mode)
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
        except CosoriDeviceOffline:
            raise
        except CosoriError as err:
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
