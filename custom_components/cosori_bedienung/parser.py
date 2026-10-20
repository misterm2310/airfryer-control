"""Übersetzt die Antwort der Cloud in einfache Werte.

Für Doofe: Die Fritteuse schickt ein großes Durcheinander an Feldern. Hier
picken wir uns das Wichtige raus: Was macht sie gerade? Wie lange noch? Wie
heiß? Und das für jede Zone (Zone 1, Zone 2 oder die ganze Schublade).

Weil Cosori die Feldnamen nirgends offen beschreibt, sucht der Parser
tolerant nach mehreren bekannten Namen. Unbekanntes geht nicht verloren:
Es landet in den Diagnose-Daten, damit man nachbessern kann.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import (
    ACTIVE_STATES,
    STATE_COOKING,
    STATE_DRAWER_OPEN,
    STATE_FINISHED,
    STATE_KEEP_WARM,
    STATE_OFF,
    STATE_PAUSED,
    STATE_PREHEAT,
    STATE_PREHEATED,
    STATE_STANDBY,
    STATE_UNKNOWN,
    STATE_WAITING,
    TIME_UNIT_MINUTES,
    TIME_UNIT_SECONDS,
    ZONE_1,
    ZONE_2,
    ZONE_WHOLE,
)

# Rohwerte der Cloud → unsere Zustände (alles klein geschrieben verglichen)
STATUS_MAP: dict[str, str] = {
    "off": STATE_OFF,
    "poweroff": STATE_OFF,
    "standby": STATE_STANDBY,
    "idle": STATE_STANDBY,
    "ready": STATE_WAITING,  # Programm gesendet, wartet auf Start am Gerät
    "free": STATE_STANDBY,
    "cooking": STATE_COOKING,
    "cook": STATE_COOKING,
    "working": STATE_COOKING,
    "running": STATE_COOKING,
    "heating": STATE_PREHEAT,
    "preheating": STATE_PREHEAT,
    "preheat": STATE_PREHEAT,
    "preheatend": STATE_PREHEATED,
    "preheatfinish": STATE_PREHEATED,
    "cookstop": STATE_PAUSED,
    "preheatstop": STATE_PAUSED,
    "stop": STATE_PAUSED,
    "pause": STATE_PAUSED,
    "paused": STATE_PAUSED,
    "suspend": STATE_PAUSED,
    "pullout": STATE_DRAWER_OPEN,
    "drawerout": STATE_DRAWER_OPEN,
    "cookend": STATE_FINISHED,
    "end": STATE_FINISHED,
    "finish": STATE_FINISHED,
    "finished": STATE_FINISHED,
    "done": STATE_FINISHED,
    "complete": STATE_FINISHED,
    "keepwarm": STATE_KEEP_WARM,
    "warm": STATE_KEEP_WARM,
    "warming": STATE_KEEP_WARM,
}

STATUS_KEYS = ("cookStatus", "workStatus", "deviceStatus", "status", "runStatus")
REMAIN_KEYS = (
    "currentRemainingTime",  # TwinFry (getAirfryerMultiStatus), Sekunden
    "cookLastTime",
    "remainTime",
    "remainingTime",
    "cookRemainTime",
    "lastTime",
    "leftTime",
    "restTime",
)
SET_TIME_KEYS = ("cookSetTime", "setTime", "totalTime")
SET_TEMP_KEYS = ("cookSetTemp", "cookTemp", "targetTemp", "setTemp")
CUR_TEMP_KEYS = ("currentTemp", "curTemp", "realTemp", "temp")
MODE_KEYS = ("mode", "cookMode", "recipeName", "customRecipe", "workMode")
CHAMBER_KEYS = ("chamber", "chamberId", "zone", "zoneId", "workChamber")
TOTAL_REMAIN_KEYS = ("totalTimeRemaining", "totalRemainTime", "totalLastTime")
LIST_KEYS = ("statusList", "chamberStatusList", "zoneStatusList", "cookConfigs", "chambers", "zones")


@dataclass
class ZoneState:
    """Was eine Zone gerade macht."""

    zone: int
    status: str = STATE_UNKNOWN
    status_raw: str | None = None
    remaining_s: int | None = None
    set_time_s: int | None = None
    set_temp: float | int | None = None
    current_temp: float | int | None = None
    mode: str | None = None
    reports_current_temp: bool = False

    @property
    def active(self) -> bool:
        return self.status in ACTIVE_STATES

    @property
    def busy(self) -> bool:
        """Arbeitet die Zone oder ist gerade fertig (dann ist das Programm interessant)?"""
        return self.status in ACTIVE_STATES | {
            STATE_FINISHED,
            STATE_KEEP_WARM,
            STATE_PREHEATED,
            STATE_WAITING,
        }


@dataclass
class FryerState:
    """Gesamtzustand einer Fritteuse."""

    status: str = STATE_UNKNOWN
    status_raw: str | None = None
    remaining_s: int | None = None
    temp_unit: str = "celsius"
    zones: dict[int, ZoneState] = field(default_factory=dict)

    @property
    def active(self) -> bool:
        return self.status in ACTIVE_STATES or any(z.active for z in self.zones.values())


def _first(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _temp(value: Any) -> float | int | None:
    """Temperatur; ganze Zahlen bleiben ganz (190 statt 190.0). 0 = nicht gemeldet."""
    num = _num(value)
    if num is None or num <= 0:
        return None
    return int(num) if num.is_integer() else num


def map_status(raw: Any) -> str:
    """Rohwert → unser Zustand."""
    if raw is None:
        return STATE_UNKNOWN
    if isinstance(raw, bool):
        return STATE_COOKING if raw else STATE_STANDBY
    if isinstance(raw, (int, float)):
        # manche Geräte melden Zahlen: 0 = bereit, 1 = gart (sonst unbekannt)
        return {0: STATE_STANDBY, 1: STATE_COOKING}.get(int(raw), STATE_UNKNOWN)
    key = str(raw).replace("_", "").replace(" ", "").lower()
    return STATUS_MAP.get(key, STATE_UNKNOWN)


def _seconds(value: Any, unit: str) -> int | None:
    num = _num(value)
    if num is None or num < 0:
        return None
    return int(round(num * 60)) if unit == TIME_UNIT_MINUTES else int(round(num))


def _zone_from(data: dict[str, Any], zone: int, unit: str) -> ZoneState:
    raw_status = _first(data, STATUS_KEYS)
    zs = ZoneState(zone=zone)
    zs.status_raw = None if raw_status is None else str(raw_status)
    zs.status = map_status(raw_status)
    zs.remaining_s = _seconds(_first(data, REMAIN_KEYS), unit)
    zs.set_time_s = _seconds(_first(data, SET_TIME_KEYS), unit)
    zs.set_temp = _temp(_first(data, SET_TEMP_KEYS))
    zs.current_temp = _temp(_first(data, CUR_TEMP_KEYS))
    zs.reports_current_temp = any(key in data for key in CUR_TEMP_KEYS)
    mode = _first(data, MODE_KEYS)
    zs.mode = None if mode is None or isinstance(mode, (dict, list)) else str(mode)
    # „Fertig“ oder „bereit“ heißt: keine Restzeit mehr
    if zs.status in (STATE_FINISHED, STATE_STANDBY, STATE_OFF, STATE_PREHEATED):
        zs.remaining_s = 0 if zs.remaining_s is not None else None
    return zs


def _find_zone_list(data: Any, depth: int = 0) -> list[dict[str, Any]] | None:
    """Sucht eine Liste von Zonen irgendwo in der Antwort."""
    if depth > 4:
        return None
    if isinstance(data, dict):
        for key in LIST_KEYS:
            val = data.get(key)
            if isinstance(val, list) and val and all(isinstance(v, dict) for v in val):
                return val
        for val in data.values():
            found = _find_zone_list(val, depth + 1)
            if found:
                return found
    elif isinstance(data, list) and data and all(isinstance(v, dict) for v in data):
        if any(_first(v, STATUS_KEYS) is not None for v in data):
            return data
    return None


def _flat_status_dict(data: Any) -> dict[str, Any]:
    """Der „oberste“ Teil mit Status-Feldern (manchmal in returnStatus/cookMode)."""
    if not isinstance(data, dict):
        return {}
    for key in ("returnStatus", "cookMode", "workStatusInfo", "statusInfo"):
        inner = data.get(key)
        if isinstance(inner, dict) and _first(inner, STATUS_KEYS) is not None:
            merged = {**data, **inner}
            return merged
    return data


def guess_unit(device_type: str, configured: str) -> str:
    """Sekunden oder Minuten? Neuere CA-Modelle zählen in Sekunden."""
    if configured in (TIME_UNIT_SECONDS, TIME_UNIT_MINUTES):
        return configured
    return TIME_UNIT_MINUTES if device_type.startswith("CS") else TIME_UNIT_SECONDS


def parse(
    status: dict[str, Any] | None,
    multi: dict[str, Any] | None,
    unit: str,
) -> FryerState:
    """Hauptfunktion: Rohdaten → FryerState."""
    state = FryerState()
    top = _flat_status_dict(status or {})
    multi_top = _flat_status_dict(multi or {})

    unit_raw = _first(top, ("tempUnit", "temperatureUnit")) or _first(
        multi_top, ("tempUnit", "temperatureUnit")
    )
    if isinstance(unit_raw, str) and unit_raw.lower().startswith("f"):
        state.temp_unit = "fahrenheit"

    # 1) Zonen aus der Mehrzonen-Antwort (TwinFry), sonst aus dem normalen Status
    zone_list = _find_zone_list(multi) or _find_zone_list(status)
    if zone_list:
        for index, item in enumerate(zone_list, start=1):
            chamber = _num(_first(item, CHAMBER_KEYS))
            zone = int(chamber) if chamber in (1, 2, 3) else index
            if zone > ZONE_WHOLE:
                continue
            state.zones[zone] = _zone_from(item, zone, unit)

    # 2) Gesamtzustand
    raw = _first(top, STATUS_KEYS)
    if raw is None:
        raw = _first(multi_top, STATUS_KEYS)
    state.status_raw = None if raw is None else str(raw)
    state.status = map_status(raw)
    if state.status == STATE_UNKNOWN and state.zones:
        state.status = _combine([z.status for z in state.zones.values()])
    if not state.zones and top:
        # Nur eine Kammer: aus dem Hauptstatus eine „Zone 1“ machen
        if _first(top, STATUS_KEYS) is not None:
            state.zones[ZONE_1] = _zone_from(top, ZONE_1, unit)

    # 3) Restzeit gesamt
    total = _first(multi_top, TOTAL_REMAIN_KEYS)
    if total is None:
        total = _first(top, TOTAL_REMAIN_KEYS)
    total_s = _seconds(total, unit)
    zone_times = [z.remaining_s for z in state.zones.values() if z.remaining_s is not None]
    if total_s is None and zone_times:
        total_s = max(zone_times)
    if total_s is None:
        total_s = _seconds(_first(top, REMAIN_KEYS), unit)
    if state.status in (STATE_FINISHED, STATE_STANDBY, STATE_OFF) and not any(
        z.active for z in state.zones.values()
    ):
        total_s = 0 if total_s is not None else None
    state.remaining_s = total_s
    return state


def _combine(states: list[str]) -> str:
    """Mehrere Zonen → ein Gesamtzustand (das „Wichtigste“ gewinnt)."""
    order = [
        STATE_COOKING,
        STATE_PREHEAT,
        STATE_DRAWER_OPEN,
        STATE_PAUSED,
        STATE_KEEP_WARM,
        STATE_FINISHED,
        STATE_PREHEATED,
        STATE_WAITING,
        STATE_STANDBY,
        STATE_OFF,
    ]
    for candidate in order:
        if candidate in states:
            return candidate
    return STATE_UNKNOWN


def zones_for_device(state: FryerState, multizone: bool) -> list[int]:
    """Welche Zonen-Entitäten sinnvoll sind.

    Mehrzonen-Geräte (TwinFry) bekommen Zone 1, Zone 2 und die ganze Schublade
    (Zone 3, ohne Trennwand). Ein-Kammer-Geräte haben keine eigenen
    Zonen-Entitäten (die Hauptsensoren reichen).
    """
    if multizone or ZONE_2 in state.zones or ZONE_WHOLE in state.zones:
        return [ZONE_1, ZONE_2, ZONE_WHOLE]
    return []


def reports_current_temp(state: FryerState) -> bool:
    """Meldet die Fritteuse überhaupt eine gemessene Temperatur? (TwinFry: nein)"""
    return any(z.reports_current_temp for z in state.zones.values())


def zone_view(state: FryerState, zone: int) -> ZoneState | None:
    """Zustand einer Zone (None = die Fritteuse hat sie gerade nicht gemeldet)."""
    return state.zones.get(zone)
