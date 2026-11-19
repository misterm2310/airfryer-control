"""⭐ Lieblings-Programme und 🕘 „Zuletzt gesendet“.

Für Doofe: Hier merkt sich Home Assistant pro Fritteuse
- deine Lieblinge (z. B. „Pommes 200 °C, 18 min“) – höchstens 12,
- die letzten 5 Programme, die an die Fritteuse gegangen sind,
- ↕️ wie oft in welcher Zone ans Schütteln erinnert wird (Knopf pro Schublade),
- 🏷️ was gerade in welcher Zone liegt („Zone 1: Pommes“) und ob dort geschüttelt
  werden soll (kommt vom Liebling). Das wird nach dem Garen von selbst vergessen.
Beides liegt in Home Assistant (Ordner .storage), nicht im Browser. So sieht das
Küchen-Tablet dieselben Lieblinge wie dein Handy. Die Karte liest sie aus dem
Sensor „Lieblings-Programme“ der Fritteuse.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MAX_FAVORITES, MAX_RECENT

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.programme"
DATA_KEY = "programme"


class ProgramStore:
    """Lieblinge und zuletzt gesendete Programme – pro Fritteuse (cid)."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, dict[str, list[dict[str, Any]]]] = {}
        self._listeners: list[Callable[[str], None]] = []

    async def async_load(self) -> None:
        data = await self._store.async_load()
        self._data = data if isinstance(data, dict) else {}

    def _fryer(self, cid: str) -> dict[str, list[dict[str, Any]]]:
        return self._data.setdefault(cid, {"lieblinge": [], "zuletzt": []})

    def zone_info(self, cid: str, zone: int) -> dict[str, Any]:
        """🏷️ Was liegt in der Zone? {"inhalt": "Pommes", "gegart": True} – leer = nichts bekannt."""
        data = self._data.get(cid, {})
        return dict(data.get("zonen", {}).get(str(zone), {})) if isinstance(data, dict) else {}

    def set_zone_info(self, cid: str, zone: int, **values: Any) -> bool:
        """🏷️ Inhalt/Schütteln einer Zone setzen. None oder "" löscht den Wert. True = etwas hat sich geändert."""
        zones = self._data.setdefault(cid, {"lieblinge": [], "zuletzt": []}).setdefault("zonen", {})
        info = dict(zones.get(str(zone), {}))
        for key, value in values.items():
            if value is None or value == "":
                info.pop(key, None)
            else:
                info[key] = value
        if info == zones.get(str(zone), {}):
            return False
        if info:
            zones[str(zone)] = info
        else:
            zones.pop(str(zone), None)
        self._changed(cid)
        return True

    def clear_zone_info(self, cid: str, zone: int) -> bool:
        """🧹 Nach dem Garen: Inhalt und Schütteln der Zone vergessen."""
        zones = self._data.get(cid, {}).get("zonen", {})
        if str(zone) not in zones:
            return False
        zones.pop(str(zone))
        self._changed(cid)
        return True

    def shake(self, cid: str, zone: int) -> int | None:
        """↕️ Knopf der Zone: None = aus, 0 = zur Halbzeit, X = alle X Minuten."""
        value = self._data.get(cid, {}).get("schuetteln", {}).get(str(zone))
        return int(value) if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None

    def set_shake(self, cid: str, zone: int, every: int | None) -> bool:
        """↕️ Knopf der Zone setzen (None = aus). True = etwas hat sich geändert."""
        knobs = self._data.setdefault(cid, {"lieblinge": [], "zuletzt": []}).setdefault("schuetteln", {})
        old = knobs.get(str(zone))
        if every is None:
            if old is None:
                return False
            knobs.pop(str(zone))
        else:
            if old == int(every):
                return False
            knobs[str(zone)] = int(every)
        self._changed(cid)
        return True

    def migrated(self) -> bool:
        """Wurden die alten Schüttel-Einstellungen schon auf die Knöpfe übertragen?"""
        return bool(self._data.get("_schuetteln_uebertragen"))

    def set_migrated(self) -> None:
        self._data["_schuetteln_uebertragen"] = True
        self._store.async_delay_save(lambda: self._data, 2)

    def favorites(self, cid: str) -> list[dict[str, Any]]:
        return list(self._data.get(cid, {}).get("lieblinge", []))

    def recent(self, cid: str) -> list[dict[str, Any]]:
        return list(self._data.get(cid, {}).get("zuletzt", []))

    @callback
    def async_add_listener(self, func: Callable[[str], None]) -> Callable[[], None]:
        """Bei jeder Änderung Bescheid sagen (der Sensor zeichnet sich dann neu)."""
        self._listeners.append(func)
        return lambda: self._listeners.remove(func) if func in self._listeners else None

    def _changed(self, cid: str) -> None:
        self._store.async_delay_save(lambda: self._data, 2)
        for func in list(self._listeners):
            func(cid)

    def save_favorite(
        self, cid: str, name: str, mode: str, temp: int, minutes: int, shake: bool = True
    ) -> bool:
        """Liebling speichern. Gleicher Name = überschreiben. False = schon 12 Stück.

        ``shake`` = False: ↕️ beim Senden dieses Lieblings den Schüttel-Knopf der Zone auf „aus“ (z. B. Kuchen).
        """
        favs = self._fryer(cid)["lieblinge"]
        entry = {"name": name, "programm": mode, "temperatur": int(temp), "minuten": int(minutes), "schuetteln": bool(shake)}
        for i, fav in enumerate(favs):
            if str(fav.get("name", "")).casefold() == name.casefold():
                favs[i] = entry
                self._changed(cid)
                return True
        if len(favs) >= MAX_FAVORITES:
            return False
        favs.append(entry)
        self._changed(cid)
        return True

    def delete_favorite(self, cid: str, name: str) -> bool:
        favs = self._fryer(cid)["lieblinge"]
        keep = [f for f in favs if str(f.get("name", "")).casefold() != name.casefold()]
        if len(keep) == len(favs):
            return False
        self._fryer(cid)["lieblinge"] = keep
        self._changed(cid)
        return True

    def add_recent(self, cid: str, zone: int, mode: str, temp: int, minutes: int) -> None:
        """Gesendetes Programm vorne einreihen – doppelte Einträge rutschen nach vorn."""
        item = {"programm": mode, "temperatur": int(temp), "minuten": int(minutes)}
        same = lambda r: all(r.get(k) == v for k, v in item.items())  # noqa: E731
        rest = [r for r in self._fryer(cid)["zuletzt"] if not same(r)]
        new = {**item, "zone": int(zone), "zeit": dt_util.utcnow().replace(microsecond=0).isoformat()}
        self._fryer(cid)["zuletzt"] = [new, *rest][:MAX_RECENT]
        self._changed(cid)


async def async_setup_store(hass: HomeAssistant) -> ProgramStore:
    """Speicher einmal laden (beim Start der Integration)."""
    store = ProgramStore(hass)
    await store.async_load()
    hass.data.setdefault(DOMAIN, {})[DATA_KEY] = store
    return store


def get_store(hass: HomeAssistant) -> ProgramStore | None:
    data = hass.data.get(DOMAIN)
    return data.get(DATA_KEY) if isinstance(data, dict) else None
