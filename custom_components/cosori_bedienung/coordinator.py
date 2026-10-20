"""Holt regelmäßig den Zustand aller Fritteusen eines Kontos.

Für Doofe: Das ist der „Postbote“. Er fragt alle paar Sekunden bei VeSync
nach, was die Fritteuse macht, und verteilt das an alle Sensoren. Solange
die Fritteuse arbeitet, fragt er öfter (alle 15 Sekunden), sonst seltener.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    CosoriApi,
    CosoriAuthError,
    CosoriConnectionError,
    CosoriDeviceOffline,
    CosoriError,
    is_air_fryer,
)
from .const import (
    DEFAULT_INTERVAL,
    DOMAIN,
    EVENT_FINISHED,
    FAST_INTERVAL,
    OPT_INTERVAL,
    OPT_TIME_UNIT,
    STATE_FINISHED,
    STATE_KEEP_WARM,
    STATE_OFF,
    STATE_OFFLINE,
    STATE_PREHEATED,
    STATE_COOKING,
    STATE_PREHEAT,
    STATE_STANDBY,
    TIME_UNIT_AUTO,
)
from .parser import FryerState, guess_unit, parse

_LOGGER = logging.getLogger(__name__)

RUNNING = {STATE_COOKING, STATE_PREHEAT}
METHOD_STATUS = "getAirfryerStatus"
METHOD_MULTI = "getAirfryerMultiStatus"
DONE_STATES = {STATE_FINISHED, STATE_STANDBY, STATE_KEEP_WARM, STATE_OFF, STATE_PREHEATED}


@dataclass
class FryerData:
    """Alles, was wir über eine Fritteuse wissen."""

    info: dict[str, Any]
    state: FryerState = field(default_factory=FryerState)
    raw_status: dict[str, Any] = field(default_factory=dict)
    raw_multi: dict[str, Any] = field(default_factory=dict)
    online: bool = True
    last_error: str | None = None
    finish_at: datetime | None = None
    zone_finish_at: dict[int, datetime | None] = field(default_factory=dict)
    multizone: bool = False
    method_errors: dict[str, str] = field(default_factory=dict)

    @property
    def cid(self) -> str:
        return str(self.info.get("cid"))

    @property
    def name(self) -> str:
        return str(self.info.get("deviceName") or "Cosori")

    @property
    def model(self) -> str:
        return str(self.info.get("deviceType") or "Heißluftfritteuse")


class CosoriCoordinator(DataUpdateCoordinator[dict[str, FryerData]]):
    """Ein Koordinator pro VeSync-Konto."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: CosoriApi) -> None:
        self.api = api
        self._interval = int(entry.options.get(OPT_INTERVAL, DEFAULT_INTERVAL))
        self._unit_option = entry.options.get(OPT_TIME_UNIT, TIME_UNIT_AUTO)
        self._unsupported: dict[str, set[str]] = {}
        self.fryers: dict[str, FryerData] = {}
        # Eingaben pro (Fritteuse, Zone): {"temp": °C, "minuten": min, "mode": "airfry"}
        self.plans: dict[tuple[str, int], dict[str, Any]] = {}
        # Name der „Senden“-Schreibweise, die die Fritteuse angenommen hat
        self.send_variant: str | None = None
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=self._interval),
        )

    async def async_load_devices(self) -> None:
        """Geräteliste holen (einmal beim Start)."""
        try:
            devices = await self.api.get_devices()
        except CosoriAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CosoriError as err:
            raise UpdateFailed(str(err)) from err
        for dev in devices:
            if not is_air_fryer(dev) or not dev.get("cid"):
                continue
            cid = str(dev["cid"])
            if cid in self.fryers:
                self.fryers[cid].info = dev
            else:
                self.fryers[cid] = FryerData(info=dev)
        _LOGGER.debug("%s Fritteuse(n) gefunden", len(self.fryers))

    async def _async_update_data(self) -> dict[str, FryerData]:
        if not self.fryers:
            await self.async_load_devices()
        any_ok = False
        last_conn_error: Exception | None = None
        for fryer in self.fryers.values():
            try:
                await self._update_fryer(fryer)
                any_ok = True
            except CosoriAuthError as err:
                raise ConfigEntryAuthFailed(str(err)) from err
            except CosoriConnectionError as err:
                last_conn_error = err
                fryer.last_error = str(err)
        if not any_ok and last_conn_error is not None:
            raise UpdateFailed(str(last_conn_error))

        # Arbeitet eine Fritteuse? Dann öfter nachfragen.
        busy = any(f.online and f.state.active for f in self.fryers.values())
        wanted = timedelta(seconds=FAST_INTERVAL if busy else self._interval)
        if self.update_interval != wanted:
            self.update_interval = wanted
        return self.fryers

    async def _update_fryer(self, fryer: FryerData) -> None:
        previous = fryer.state
        was_online = fryer.online
        unit = guess_unit(fryer.model, self._unit_option)
        try:
            if fryer.model.startswith("CS"):
                fryer.raw_status = await self.api.bypass_v1_status(fryer.info)
                fryer.raw_multi = {}
                fryer.method_errors = {}
            else:
                # Beide Fragen getrennt stellen: Die TwinFry kennt z. B. nur die
                # Mehrzonen-Frage und lehnt die normale ab. Eine Absage darf die
                # andere Antwort nicht blockieren.
                status = await self._ask(fryer, METHOD_STATUS)
                multi = await self._ask(fryer, METHOD_MULTI)
                if status is None and multi is None:
                    # Beides abgelehnt → nächstes Mal wieder beides probieren
                    self._unsupported.pop(fryer.cid, None)
                    fryer.last_error = "; ".join(fryer.method_errors.values()) or None
                    _LOGGER.warning("%s: keine Statusabfrage klappt: %s", fryer.name, fryer.last_error)
                    return
                fryer.raw_status = status or {}
                fryer.raw_multi = multi or {}
            fryer.online = True
            fryer.last_error = None
        except CosoriDeviceOffline as err:
            fryer.online = False
            fryer.last_error = str(err)
            fryer.state = FryerState(status=STATE_OFFLINE)
            fryer.finish_at = None
            fryer.zone_finish_at = {}
            if was_online:
                _LOGGER.info("%s ist offline: %s", fryer.name, err)
            return
        except (CosoriAuthError, CosoriConnectionError):
            raise
        except CosoriError as err:
            fryer.last_error = str(err)
            _LOGGER.warning("%s: %s", fryer.name, err)
            return

        new = parse(fryer.raw_status, fryer.raw_multi, unit)
        fryer.multizone = fryer.multizone or bool(fryer.raw_multi) or len(new.zones) > 1
        fryer.state = new
        now = dt_util.utcnow()
        running = new.status in RUNNING or any(z.status in RUNNING for z in new.zones.values())
        fryer.finish_at = _stable_finish(fryer.finish_at, new.remaining_s, running, now)
        # Nur Zonen, die die Fritteuse gerade meldet – alte Werte fallen weg
        fryer.zone_finish_at = {
            zone: _stable_finish(
                fryer.zone_finish_at.get(zone), zs.remaining_s, zs.status in RUNNING, now
            )
            for zone, zs in new.zones.items()
        }
        self._fire_events(fryer, previous, new)

    async def _ask(self, fryer: FryerData, method: str) -> dict[str, Any] | None:
        """Eine Statusfrage stellen. None = Gerät kennt die Frage nicht.

        Lehnt die Fritteuse eine Frage ab, merken wir uns das und fragen sie
        bis zum nächsten Neustart nicht mehr (spart Anfragen).
        """
        unsupported = self._unsupported.setdefault(fryer.cid, set())
        if method in unsupported:
            return None
        try:
            data = await self.api.bypass_v2(fryer.info, method)
        except (CosoriDeviceOffline, CosoriAuthError, CosoriConnectionError):
            raise
        except CosoriError as err:
            _LOGGER.debug("%s kennt „%s“ nicht: %s", fryer.name, method, err)
            unsupported.add(method)
            fryer.method_errors[method] = str(err)
            return None
        fryer.method_errors.pop(method, None)
        return data

    def _fire_events(self, fryer: FryerData, old: FryerState, new: FryerState) -> None:
        """Ereignis „fertig“, wenn etwas aufhört zu garen."""
        base = {"geraet": fryer.name, "modell": fryer.model}
        for zone, zs in new.zones.items():
            before = old.zones.get(zone)
            if before is not None and before.active and zs.status in DONE_STATES:
                self.hass.bus.async_fire(
                    EVENT_FINISHED,
                    {**base, "zone": zone, "zustand": zs.status, "programm": before.mode},
                )
        if old.active and not new.active and new.status in DONE_STATES:
            self.hass.bus.async_fire(
                EVENT_FINISHED, {**base, "zone": "alle", "zustand": new.status}
            )

    async def async_request_fast_refresh(self) -> None:
        """Nach einem Befehl gleich nachschauen (und dann wieder im Takt)."""
        self.update_interval = timedelta(seconds=FAST_INTERVAL)
        await self.async_request_refresh()


def _stable_finish(
    old: datetime | None, remaining_s: int | None, active: bool, now: datetime
) -> datetime | None:
    """„Fertig um“-Zeit, die nicht bei jeder Abfrage um Sekunden wackelt."""
    if not active or not remaining_s:
        return None
    new = (now + timedelta(seconds=remaining_s)).replace(microsecond=0)
    if old is not None and abs((new - old).total_seconds()) < 45:
        return old
    return new
