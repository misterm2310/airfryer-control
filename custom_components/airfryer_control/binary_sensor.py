"""Binärsensoren: „Gart gerade“ und „Online“."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import CosoriCoordinator
from .entity import CosoriEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CosoriCoordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = []
    for cid in coordinator.fryers:
        entities.append(RunningSensor(coordinator, cid))
        entities.append(OnlineSensor(coordinator, cid))
    async_add_entities(entities)


class RunningSensor(CosoriEntity, BinarySensorEntity):
    """An, solange vorgeheizt, gegart oder kurz pausiert wird."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_translation_key = "gart"

    def __init__(self, coordinator, cid) -> None:
        super().__init__(coordinator, cid, "gart")

    @property
    def is_on(self) -> bool:
        return self.fryer.online and self.fryer.state.active


class OnlineSensor(CosoriEntity, BinarySensorEntity):
    """Ist die Fritteuse mit der Cloud verbunden?"""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "online"

    def __init__(self, coordinator, cid) -> None:
        super().__init__(coordinator, cid, "online")

    @property
    def is_on(self) -> bool:
        return self.fryer.online
