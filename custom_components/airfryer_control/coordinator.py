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

from .core.api import (
    AirfryerApi,
    AirfryerAuthError,
    AirfryerConnectionError,
    AirfryerDeviceOffline,
    AirfryerError,
    is_air_fryer,
)
from .const import (
    DEFAULT_INTERVAL,
    DOMAIN,
    EVENT_FINISHED,
    EVENT_SHAKE,
    EVENT_FORGOT,
    OPT_SHAKE,
    OPT_SHAKE_EVERY,
    OPT_FORGOT,
    OPT_NOTIFY_FORGOT,
    DEFAULT_FORGOT,
    SHAKE_LAST_SECONDS,
    SHAKE_SHOW_SECONDS,
    STATE_DRAWER_OPEN,
    OPT_NOTIFY,
    OPT_NOTIFY_SHAKE,
    NOTIFY_MAX,
    ZONE_WHOLE,
    SHAKE_MIN_SECONDS,
    FAST_INTERVAL,
    STATE_WAITING,
    WAITING_INTERVAL,
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
from .core.parser import FryerState, guess_unit, parse, zones_for_device
from . import modelle
from .programme import get_store

_LOGGER = logging.getLogger(__name__)

RUNNING = {STATE_COOKING, STATE_PREHEAT}
METHOD_STATUS = "getAirfryerStatus"
METHOD_MULTI = "getAirfryerMultiStatus"
DONE_STATES = {STATE_FINISHED, STATE_STANDBY, STATE_KEEP_WARM, STATE_OFF, STATE_PREHEATED}
IDLE_STATES = {STATE_STANDBY, STATE_OFF}  # 🧹 Zone steht still → Inhalt vom letzten Garen vergessen
# 🤫 Kurzer Aussetzer: So lange behalten wir die letzten Werte, bevor wir „offline“ zeigen
OFFLINE_GRACE_SECONDS = 90
# … und so schnell fragen wir in der Zeit nochmal nach
RETRY_SECONDS = 5


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
    # Wann kam die letzte echte Antwort der Fritteuse? (None = noch nie)
    last_report: datetime | None = None
    # Zählt hoch, sobald sich etwas an der gemeldeten Antwort ändert
    revision: int = 0
    # Seit wann schweigt die Fritteuse? (None = alles gut) – für kurze Aussetzer
    silent_since: datetime | None = None

    @property
    def connection(self) -> str:
        """„ok“, „offline“ (Fritteuse weg) oder „fehler“ (letzte Abfrage ging schief)."""
        if not self.online:
            return "offline"
        if self.last_error or self.last_report is None:
            return "fehler"
        return "ok"

    @property
    def cid(self) -> str:
        return str(self.info.get("cid"))

    @property
    def name(self) -> str:
        return str(self.info.get("deviceName") or "Cosori")

    @property
    def model(self) -> str:
        return str(self.info.get("deviceType") or "Heißluftfritteuse")


class AirfryerCoordinator(DataUpdateCoordinator[dict[str, FryerData]]):
    """Ein Koordinator pro VeSync-Konto."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: AirfryerApi) -> None:
        self.api = api
        self._interval = int(entry.options.get(OPT_INTERVAL, DEFAULT_INTERVAL))
        self._unit_option = entry.options.get(OPT_TIME_UNIT, TIME_UNIT_AUTO)
        # 📲 Handy-Meldung ohne eigene Automation: notify-Dienste (leer = aus) + „auch beim Schütteln“
        self._notify: list[str] = clean_notify(entry.options.get(OPT_NOTIFY))
        self._notify_shake = bool(entry.options.get(OPT_NOTIFY_SHAKE, False)) and bool(self._notify)
        # ⏰ „Vergessen zu starten?“ nach X Minuten „Wartet auf Start“ (0 = aus) + auch aufs Handy
        self._forgot_min = max(0, int(entry.options.get(OPT_FORGOT, DEFAULT_FORGOT) or 0))
        self._notify_forgot = bool(entry.options.get(OPT_NOTIFY_FORGOT, True)) and bool(self._notify)
        # Wie oft schon erinnert (pro Fritteuse+Zone und Garvorgang)
        self._shaken: dict[tuple[str, int], tuple[int, int]] = {}  # (Takt, so oft schon erinnert)
        # ↕️ Seit wann „Jetzt schütteln!“ gilt (für Karte und Laufband, verschwindet nach 3 Minuten)
        self.shake_at: dict[tuple[str, int], datetime] = {}
        # ⏰ Seit wann eine Zone auf Start wartet – und ob schon daran erinnert wurde
        self.waiting_since: dict[tuple[str, int], datetime] = {}
        self._forgot_sent: set[tuple[str, int]] = set()
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
        except AirfryerAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except AirfryerError as err:
            raise UpdateFailed(str(err)) from err
        for dev in devices:
            if not is_air_fryer(dev) or not dev.get("cid"):
                continue
            cid = str(dev["cid"])
            if cid in self.fryers:
                self.fryers[cid].info = dev
            else:
                self.fryers[cid] = FryerData(info=dev)
            # 🍟 Eine TwinFry hat IMMER Zonen – auch wenn sie sie beim Start kurz nicht meldet
            if modelle.has_zones(str(dev.get("deviceType") or "")):
                self.fryers[cid].multizone = True
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
            except AirfryerAuthError as err:
                raise ConfigEntryAuthFailed(str(err)) from err
            except AirfryerConnectionError as err:
                if self._tolerate(fryer, err):
                    any_ok = True  # kurzer Aussetzer: letzte Werte bleiben stehen
                    continue
                fryer.silent_since = None
                last_conn_error = err
                fryer.last_error = str(err)
        if not any_ok and last_conn_error is not None:
            raise UpdateFailed(str(last_conn_error))

        # Arbeitet eine Fritteuse? Dann öfter nachfragen.
        busy = any(f.online and f.state.active for f in self.fryers.values())
        # Wartet eine Zone auf den Start am Gerät? Dann noch schneller, damit „Fertig um“ gleich kommt.
        waiting = any(
            f.online and any(z.status == STATE_WAITING for z in f.state.zones.values())
            for f in self.fryers.values()
        )
        # 🤫 Hat eine Fritteuse gerade kurz geschwiegen? Dann gleich nochmal fragen
        hiccup = any(f.online and f.silent_since is not None for f in self.fryers.values())
        if hiccup:
            seconds = RETRY_SECONDS
        elif waiting:
            seconds = WAITING_INTERVAL
        else:
            seconds = FAST_INTERVAL if busy else self._interval
        wanted = timedelta(seconds=seconds)
        if self.update_interval != wanted:
            self.update_interval = wanted
        return self.fryers

    async def _update_fryer(self, fryer: FryerData) -> None:
        previous = fryer.state
        previous_raw = (fryer.raw_status, fryer.raw_multi)
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
            if (
                not was_online
                or fryer.last_report is None
                or (fryer.raw_status, fryer.raw_multi) != previous_raw
            ):
                fryer.revision += 1
            fryer.last_report = dt_util.utcnow()
            fryer.online = True
            fryer.last_error = None
            fryer.silent_since = None
        except AirfryerDeviceOffline as err:
            if self._tolerate(fryer, err):
                return  # kurzer Aussetzer: letzte Werte bleiben, gleich nochmal fragen
            fryer.silent_since = None
            fryer.online = False
            fryer.last_error = str(err)
            fryer.state = FryerState(status=STATE_OFFLINE)
            fryer.finish_at = None
            fryer.zone_finish_at = {}
            if was_online:
                fryer.revision += 1
                _LOGGER.info("%s ist offline: %s", fryer.name, err)
            return
        except (AirfryerAuthError, AirfryerConnectionError):
            raise
        except AirfryerError as err:
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

    def _tolerate(self, fryer: FryerData, err: Exception) -> bool:
        """Kurzer Aussetzer? Dann NICHT gleich „offline“ melden.

        Für Doofe: Beim Garen verpasst die Fritteuse manchmal eine einzelne Antwort
        an die Cloud. Bisher hieß das sofort „offline“ – und erst nach einer Minute
        wurde wieder gefragt. Jetzt bleiben die letzten Werte stehen, es wird nach
        wenigen Sekunden nochmal gefragt, und erst wenn sie länger als 90 Sekunden
        schweigt, steht „offline“ da (Issue #8).
        """
        if not fryer.online or fryer.last_report is None:
            return False  # war schon offline oder hat noch nie geantwortet
        now = dt_util.utcnow()
        if fryer.silent_since is None:
            fryer.silent_since = now
        if (now - fryer.silent_since).total_seconds() < OFFLINE_GRACE_SECONDS:
            _LOGGER.debug("%s: kurzer Aussetzer, frage gleich nochmal: %s", fryer.name, err)
            return True
        return False

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
        except (AirfryerDeviceOffline, AirfryerAuthError, AirfryerConnectionError):
            raise
        except AirfryerError as err:
            _LOGGER.debug("%s kennt „%s“ nicht: %s", fryer.name, method, err)
            unsupported.add(method)
            fryer.method_errors[method] = str(err)
            return None
        fryer.method_errors.pop(method, None)
        return data

    # ---------------------------------------------------------------- 🏷️ Inhalt pro Zone
    def zone_info(self, cid: str, zone: int) -> dict[str, Any]:
        """🏷️ Was liegt in der Zone (Inhalt, Schütteln ja/nein)? Leer = nichts bekannt."""
        store = get_store(self.hass)
        return store.zone_info(cid, zone) if store is not None else {}

    def content(self, cid: str, zone: int) -> str | None:
        return self.zone_info(cid, zone).get("inhalt") or None

    def _track_content(self, fryer: FryerData, new: FryerState) -> None:
        """🧹 Merkt sich „hat gegart“ – und vergisst Inhalt + Schütteln, sobald die Zone danach still steht.

        Für Doofe: Du tippst „Pommes“ ein, die Fritteuse gart, ist fertig – und steht
        wieder auf „Bereit“ oder „Aus“. Dann ist „Pommes“ weg, damit beim nächsten Mal
        nicht noch „Pommes“ dasteht, obwohl Kuchen drin ist. Vor dem Garen (Inhalt schon
        eingetippt, Zone noch aus) bleibt er natürlich stehen.
        """
        store = get_store(self.hass)
        if store is None:
            return
        for zone, zs in new.zones.items():
            info = store.zone_info(fryer.cid, zone)
            if not info:
                continue
            if zs.active or zs.status in (STATE_FINISHED, STATE_KEEP_WARM):
                if not info.get("gegart"):
                    store.set_zone_info(fryer.cid, zone, gegart=True)
            elif zs.status in IDLE_STATES and info.get("gegart"):
                store.clear_zone_info(fryer.cid, zone)

    def _fire_events(self, fryer: FryerData, old: FryerState, new: FryerState) -> None:
        """Ereignis „fertig“, wenn etwas aufhört zu garen."""
        base = {"geraet": fryer.name, "modell": fryer.model}
        done: dict[int, str] = {}  # 📲 Zone → Zustand, für EINE Handy-Meldung pro Abfrage
        for zone, zs in new.zones.items():
            before = old.zones.get(zone)
            if before is not None and before.active and zs.status in DONE_STATES:
                self.hass.bus.async_fire(
                    EVENT_FINISHED,
                    {**base, "zone": zone, "zustand": zs.status, "programm": before.mode,
                     "inhalt": self.content(fryer.cid, zone)},
                )
                done[zone] = zs.status
        if old.active and not new.active and new.status in DONE_STATES:
            self.hass.bus.async_fire(
                EVENT_FINISHED, {**base, "zone": "alle", "zustand": new.status}
            )
        if self._notify and done:
            self._notify_done(fryer, done)
        self._shake_events(fryer, old, new, base)
        self._forgot_events(fryer, new, base)
        self._track_content(fryer, new)  # erst NACH den Meldungen – die sollen „Pommes“ ja noch nennen

    def _forgot_events(self, fryer: FryerData, new: FryerState, base: dict[str, Any]) -> None:
        """⏰ „Vergessen zu starten?“ – Zone wartet schon X Minuten auf Start am Gerät.

        Für Doofe: Nach „Senden“ muss man am Gerät noch auf Start drücken. Das vergisst
        man gern. Steht eine Zone 10 Minuten (einstellbar) auf „Wartet auf Start“, kommt
        einmal das Ereignis ``airfryer_control_start_vergessen`` – und mit Handys unter
        „Fertig melden an“ auch eine Nachricht. Karte und Laufband zeigen ⏰.
        """
        now = dt_util.utcnow()
        for zone, zs in new.zones.items():
            key = (fryer.cid, zone)
            if zs.status != STATE_WAITING:
                self.waiting_since.pop(key, None)
                self._forgot_sent.discard(key)
                continue
            since = self.waiting_since.setdefault(key, now)
            if not self._forgot_min or key in self._forgot_sent:
                continue
            waited = (now - since).total_seconds()
            if waited < self._forgot_min * 60:
                continue
            self._forgot_sent.add(key)
            minutes = int(waited // 60)
            content = self.content(fryer.cid, zone)
            self.hass.bus.async_fire(
                EVENT_FORGOT,
                {**base, "zone": zone, "programm": zs.mode, "wartet_minuten": minutes, "inhalt": content},
            )
            if self._notify_forgot:
                de = self._de()
                self._notify_send(
                    "⏰ Vergessen zu starten?" if de else "⏰ Forgot to start?",
                    (f"{_zone_txt(fryer, zone, de, content)} wartet seit {minutes} Min. auf Start – bitte am Gerät drücken."
                     if de else f"{_zone_txt(fryer, zone, de, content)} has been waiting {minutes} min for start – press Start on the device."),
                    f"airfryer_control_vergessen_{fryer.cid}_{zone}",
                )

    def forgot(self, cid: str, zone: int) -> bool:
        """⏰ Wartet die Zone schon länger als eingestellt auf Start? (für Karte und Laufband)"""
        since = self.waiting_since.get((cid, zone))
        if since is None or not self._forgot_min:
            return False
        return (dt_util.utcnow() - since).total_seconds() >= self._forgot_min * 60

    def shaking(self, cid: str, zone: int) -> bool:
        """↕️ Gilt gerade „Jetzt schütteln!“? (3 Minuten lang, Schublade auf = vorbei)"""
        at = self.shake_at.get((cid, zone))
        return at is not None and (dt_util.utcnow() - at).total_seconds() < SHAKE_SHOW_SECONDS

    def shake_every(self, cid: str, zone: int) -> int | None:
        """↕️ Knopf der Zone: None = aus, 0 = zur Halbzeit, X = alle X Minuten."""
        store = get_store(self.hass)
        return store.shake(cid, zone) if store is not None else None

    @staticmethod
    def _shake_count(total: int, left: int, every: int) -> int:
        """Wie viele Schüttel-Zeitpunkte sind schon vorbei? Halbzeit: 0 oder 1, sonst alle X Minuten einer."""
        if not every:
            return 1 if left <= total / 2 else 0
        return int((total - left) // (every * 60))

    def _shake_events(self, fryer: FryerData, old: FryerState, new: FryerState, base: dict[str, Any]) -> None:
        """↕️ Ereignis „schütteln“ – je nach Knopf der Zone zur Halbzeit oder alle X Minuten.

        Für Doofe: Jede Schublade hat in der Karte ihren eigenen Knopf „↕️ Schütteln“
        (aus, Halbzeit, alle 3/5/8 Minuten). Ist es so weit, kommt das Ereignis
        ``airfryer_control_schuetteln`` (für Automationen), Karte und Laufband zeigen 3 Minuten
        lang ein blinkendes ↕️ – Schublade auf (= geschüttelt) und es ist sofort weg. Mit
        „Auch aufs Handy“ kommt zusätzlich eine Nachricht. In der letzten Minute wird nicht mehr
        erinnert. Startet Home Assistant mitten im Garen neu oder wird der Knopf mitten im Garen
        umgestellt, wird nichts Verpasstes nachgeholt.
        """
        now = dt_util.utcnow()
        for zone, zs in new.zones.items():
            key = (fryer.cid, zone)
            if key in self.shake_at and (
                zs.status == STATE_DRAWER_OPEN or (now - self.shake_at[key]).total_seconds() >= SHAKE_SHOW_SECONDS
            ):
                self.shake_at.pop(key, None)  # geschüttelt (Schublade war auf) oder 3 Minuten vorbei
            if zs.status != STATE_COOKING:
                if not zs.active:
                    self._shaken.pop(key, None)  # Garvorgang vorbei → nächstes Mal wieder erinnern
                    self.shake_at.pop(key, None)
                continue
            total, left = zs.set_time_s, zs.remaining_s
            every = self.shake_every(fryer.cid, zone)
            if every is None:
                self._shaken[key] = (-1, 0)  # Knopf aus – merken, damit beim Einschalten nichts nachgeholt wird
                continue
            if not total or left is None or total < SHAKE_MIN_SECONDS:
                continue
            count = self._shake_count(total, left, every)
            seen = self._shaken.get(key)
            if seen is None or seen[0] != every:
                # Garen beginnt, HA neu gestartet oder Knopf umgestellt: ab jetzt zählen, nichts nachholen
                seen = self._shaken[key] = (every, count)
            if count <= seen[1] or left < SHAKE_LAST_SECONDS:
                continue
            self._shaken[key] = (every, count)
            self.shake_at[key] = now
            rest = int(round(left / 60))
            content = self.content(fryer.cid, zone)
            self.hass.bus.async_fire(
                EVENT_SHAKE,
                {
                    **base,
                    "zone": zone,
                    "programm": zs.mode,
                    "rest_minuten": rest,
                    "garzeit_minuten": int(round(total / 60)),
                    "mal": count,
                    "alle_minuten": every,
                    "inhalt": content,
                },
            )
            if self._notify_shake:
                de = self._de()
                name = _zone_txt(fryer, zone, de, content)
                self._notify_send(
                    "↕️ Jetzt schütteln!" if de else "↕️ Shake now!",
                    (f"{name}: {'' if every else 'Halbzeit – '}noch {rest} Min." if de
                     else f"{name}: {'' if every else 'half time – '}{rest} min left."),
                    f"airfryer_control_schuetteln_{fryer.cid}_{zone}",
                )

    def migrate_shake(self) -> None:
        """↕️ Einmalig: alte Einstellung „Schüttel-Erinnerung“ (für alle) auf die Knöpfe pro Zone übertragen.

        Für Doofe: Bis 1.0.5-beta.3 gab es den Schalter in den Einstellungen. Wer ihn an hatte,
        bekommt jetzt jede Zone auf „Halbzeit“ (bzw. seinen alten Takt) – es fällt also nichts weg.
        """
        store = get_store(self.hass)
        if store is None or store.migrated():
            return
        opts = self.config_entry.options
        if opts.get(OPT_SHAKE) or (opts.get(OPT_NOTIFY_SHAKE) and opts.get(OPT_NOTIFY)):
            every = max(0, int(opts.get(OPT_SHAKE_EVERY, 0) or 0))
            for fryer in self.fryers.values():
                for zone in fryer_zones(fryer) or [1]:
                    if store.shake(fryer.cid, zone) is None:
                        store.set_shake(fryer.cid, zone, every)
        store.set_migrated()

    # ---------------------------------------------------------------- 📲 Handy-Meldung
    def _de(self) -> bool:
        return str(self.hass.config.language or "de").lower().startswith("de")

    def _notify_done(self, fryer: FryerData, done: dict[int, str]) -> None:
        """📲 „Fertig“ aufs Handy – eine Meldung pro Fritteuse, egal wie viele Zonen gleichzeitig fertig sind.

        Für Doofe: Nur wenn wirklich fertig (oder warmhalten / vorgeheizt). Hat jemand
        selbst auf Stopp gedrückt (Zustand „bereit“ oder „aus“), kommt keine Meldung.
        """
        de = self._de()
        if ZONE_WHOLE in done:  # Grandzone = ganze Schublade → Zone 1/2 nicht extra nennen
            done = {ZONE_WHOLE: done[ZONE_WHOLE]}
        ready = [z for z, st in done.items() if st in (STATE_FINISHED, STATE_KEEP_WARM)]
        heated = [z for z, st in done.items() if st == STATE_PREHEATED]
        if ready:
            names = (" und " if de else " and ").join(
                _zone_txt(fryer, z, de, self.content(fryer.cid, z)) for z in sorted(ready)
            )
            self._notify_send(
                "🍟 Fritteuse fertig!" if de else "🍟 Air fryer done!",
                f"{names}: {'fertig – guten Appetit!' if de else 'done – enjoy your meal!'}",
                f"airfryer_control_fertig_{fryer.cid}",
            )
        if heated:
            names = (" und " if de else " and ").join(_zone_txt(fryer, z, de) for z in sorted(heated))
            self._notify_send(
                "🔥 Vorgeheizt!" if de else "🔥 Preheated!",
                f"{names}: {'Essen kann rein.' if de else 'food can go in.'}",
                f"airfryer_control_vorgeheizt_{fryer.cid}",
            )

    def _notify_send(self, title: str, message: str, tag: str) -> None:
        """Schickt die Meldung an alle gewählten Handys – im Hintergrund, Fehler landen nur im Log."""
        self.hass.async_create_task(self._async_notify(title, message, tag), "airfryer_control_melden")

    async def _async_notify(self, title: str, message: str, tag: str) -> None:
        for svc in self._notify:
            if not self.hass.services.has_service("notify", svc):
                _LOGGER.warning("📲 notify.%s gibt es nicht (mehr) – bitte in den Einstellungen neu wählen", svc)
                continue
            data: dict[str, Any] = {"title": title, "message": message}
            if svc.startswith("mobile_app_"):  # nur die Companion-App kennt diese Zusätze
                data["data"] = {"tag": tag, "ttl": 0, "priority": "high", "push": {"interruption-level": "time-sensitive"}}
            try:
                await self.hass.services.async_call("notify", svc, data, blocking=True)
            except Exception as err:  # noqa: BLE001 – eine kaputte Meldung darf nie das Abfragen stören
                _LOGGER.warning("📲 Meldung an notify.%s ging nicht: %s", svc, err)

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


def clean_notify(value: Any) -> list[str]:
    """📲 Gewählte notify-Dienste aufräumen: Text oder Liste, ohne „notify.“, ohne Doppelte, höchstens 10."""
    if isinstance(value, str):
        value = [value]
    out: list[str] = []
    for v in value or []:
        v = str(v or "").strip().removeprefix("notify.")
        if v and v not in out and v.replace("_", "").isalnum():
            out.append(v)
    return out[:NOTIFY_MAX]


def _zone_txt(fryer: FryerData, zone: int, de: bool, content: str | None = None) -> str:
    """„Zone 1“ – oder bei einer Fritteuse mit nur einer Zone einfach ihr Name. Mit Inhalt: „Zone 1 (Pommes)“."""
    if zone == ZONE_WHOLE:
        name = "Grandzone"
    elif len(fryer_zones(fryer)) <= 1:
        name = fryer.name or ("Fritteuse" if de else "Air fryer")
    else:
        name = f"Zone {zone}"
    return f"{name} ({content})" if content else name


def fryer_zones(fryer: FryerData) -> list[int]:
    """Zonen-Entitäten einer Fritteuse.

    Wie ``zones_for_device`` – nur bekommt die Dual Blaze CAF-P583S (ein Korb)
    ihre Steuerung als „Zone 1“, damit Senden, Programm, Temperatur und Zeit gehen.
    """
    zones = zones_for_device(fryer.state, fryer.multizone)
    if not zones and modelle.single_basket(fryer.model):
        return [1]
    return zones
