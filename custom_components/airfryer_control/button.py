"""Knöpfe: „Garen beenden“ und „Jetzt aktualisieren“."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .core.api import AirfryerError
from .coordinator import AirfryerCoordinator
from .entity import AirfryerEntity
from .senden import async_end


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: AirfryerCoordinator = entry.runtime_data
    entities: list[ButtonEntity] = []
    for cid in coordinator.fryers:
        entities.append(StopButton(coordinator, cid))
        entities.append(RefreshButton(coordinator, cid))
    async_add_entities(entities)


class StopButton(AirfryerEntity, ButtonEntity):
    """Beendet den laufenden Garvorgang (wie „Stopp“ in der App)."""

    _attr_translation_key = "garen_beenden"

    def __init__(self, coordinator, cid) -> None:
        super().__init__(coordinator, cid, "garen_beenden")

    async def async_press(self) -> None:
        try:
            await async_end(self.coordinator, self.fryer)
        except AirfryerError as err:
            raise HomeAssistantError(f"Fritteuse hat „Beenden“ abgelehnt: {err}") from err
        await self.coordinator.async_request_fast_refresh()


class RefreshButton(AirfryerEntity, ButtonEntity):
    """Sofort nachfragen statt auf den nächsten Takt zu warten."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "aktualisieren"

    def __init__(self, coordinator, cid) -> None:
        super().__init__(coordinator, cid, "aktualisieren")

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
