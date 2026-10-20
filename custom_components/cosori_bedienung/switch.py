"""Schalter pro Zone: Senden (An) und Beenden (Aus).

Für Doofe: Wie in der App. Schalter AN = die Werte dieser Zone (Programm,
Temperatur, Garzeit) an die Fritteuse SENDEN. Sie wacht auf und wartet, bis du
am Gerät auf Start drückst (Starten aus der Ferne sperrt Cosori in der EU).
Schalter AUS = Zone beenden.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import CosoriDeviceOffline, CosoriError
from .const import (
    CODE_VALUE_NOT_ALLOWED,
    DOMAIN,
    SENT_OPTIMISTIC_SECONDS,
    STATE_WAITING,
    zone_label,
)
from .coordinator import CosoriCoordinator
from .entity import CosoriEntity, async_remove_stale
from .parser import zone_view, zones_for_device
from .senden import async_end, async_send, clamp_temp, get_plan


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CosoriCoordinator = entry.runtime_data
    entities: list[SwitchEntity] = []
    for cid, fryer in coordinator.fryers.items():
        if fryer.model.startswith("CS"):
            continue  # alte Modelle sprechen eine andere Befehls-Sprache
        for zone in zones_for_device(fryer.state, fryer.multizone):
            entities.append(ZoneSwitch(coordinator, cid, zone))
    async_remove_stale(hass, entry, "switch", {e.unique_id for e in entities})
    async_add_entities(entities)


class ZoneSwitch(CosoriEntity, SwitchEntity):
    """An = Werte senden / Zone aktiv. Aus = Zone beenden."""

    _attr_translation_key = "zone_senden"
    _attr_icon = "mdi:pot-steam"

    def __init__(self, coordinator, cid, zone: int) -> None:
        super().__init__(coordinator, cid, f"zone{zone}_gart")
        self._zone = zone
        self._sent_at = None
        self._attr_translation_placeholders = {"zone": zone_label(coordinator.hass.config.language, zone)}

    @property
    def is_on(self) -> bool:
        if not self.fryer.online:
            return False
        zs = zone_view(self.fryer.state, self._zone)
        if zs and (zs.active or zs.status == STATE_WAITING):
            return True
        if self._sent_at is not None:
            age = (dt_util.utcnow() - self._sent_at).total_seconds()
            return age < SENT_OPTIMISTIC_SECONDS
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        plan = get_plan(self.coordinator, self._cid, self._zone)
        return {
            "programm": plan["mode"],
            "temperatur": plan["temp"],
            "minuten": plan["minuten"],
            "senden_variante": self.coordinator.send_variant,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        plan = get_plan(self.coordinator, self._cid, self._zone)
        plan["temp"] = clamp_temp(plan["mode"], plan["temp"])
        try:
            results = await async_send(
                self.coordinator,
                self.fryer,
                self._zone,
                plan["temp"],
                plan["minuten"],
                plan["mode"],
            )
        except CosoriDeviceOffline as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="abgelehnt",
                translation_placeholders={"fehler": str(err)},
            ) from err
        if not any(r["ok"] for r in results):
            if any(r.get("code") == CODE_VALUE_NOT_ALLOWED for r in results):
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="wert_nicht_erlaubt",
                    translation_placeholders={
                        "programm": plan["mode"],
                        "temp": str(plan["temp"]),
                        "minuten": str(plan["minuten"]),
                    },
                )
            codes = ", ".join(f"{r['variante']}: {r.get('code')}" for r in results)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="senden_abgelehnt",
                translation_placeholders={"codes": codes},
            )
        self._sent_at = dt_util.utcnow()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        zs = zone_view(self.fryer.state, self._zone)
        chamber = zs.zone if zs else self._zone
        try:
            await async_end(self.coordinator, self.fryer, chamber)
        except CosoriError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="abgelehnt",
                translation_placeholders={"fehler": str(err)},
            ) from err
        self._sent_at = None
        self.async_write_ha_state()
