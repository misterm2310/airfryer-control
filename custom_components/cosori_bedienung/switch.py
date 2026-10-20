"""Schalter pro Zone: „Zone 1 gart“ – umlegen auf Aus beendet die Zone.

Für Doofe: Der Schalter steht auf An, solange die Zone gart. Legst du ihn
um, wird die Zone beendet. Einschalten geht nicht, weil Cosori das Starten
aus der Ferne in der EU sperrt – dann gibt's eine klare Meldung.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import CosoriError
from .const import DOMAIN
from .coordinator import CosoriCoordinator
from .entity import CosoriEntity, async_remove_stale
from .parser import zone_view, zones_for_device


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
    """An = Zone gart. Aus schalten = Zone beenden."""

    _attr_translation_key = "zone_gart"
    _attr_icon = "mdi:pot-steam"

    def __init__(self, coordinator, cid, zone: int) -> None:
        super().__init__(coordinator, cid, f"zone{zone}_gart")
        self._zone = zone
        self._attr_translation_placeholders = {"zone": str(zone)}

    @property
    def is_on(self) -> bool:
        zs = zone_view(self.fryer.state, self._zone)
        return bool(self.fryer.online and zs and zs.active)

    async def async_turn_on(self, **kwargs: Any) -> None:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="start_gesperrt")

    async def async_turn_off(self, **kwargs: Any) -> None:
        zs = zone_view(self.fryer.state, self._zone)
        chamber = zs.zone if zs else self._zone
        try:
            await self.coordinator.api.bypass_v2(self.fryer.info, "endCook", {"chamber": chamber})
        except CosoriError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="abgelehnt",
                translation_placeholders={"fehler": str(err)},
            ) from err
        await self.coordinator.async_request_fast_refresh()
