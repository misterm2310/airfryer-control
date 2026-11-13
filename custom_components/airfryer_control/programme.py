"""⭐ Lieblings-Programme und 🕘 „Zuletzt gesendet“.

Für Doofe: Hier merkt sich Home Assistant pro Fritteuse
- deine Lieblinge (z. B. „Pommes 200 °C, 18 min“) – höchstens 12,
- die letzten 5 Programme, die an die Fritteuse gegangen sind.
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

    def save_favorite(self, cid: str, name: str, mode: str, temp: int, minutes: int) -> bool:
        """Liebling speichern. Gleicher Name = überschreiben. False = schon 12 Stück."""
        favs = self._fryer(cid)["lieblinge"]
        entry = {"name": name, "programm": mode, "temperatur": int(temp), "minuten": int(minutes)}
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
