"""Gemeinsame Basis für alle Entitäten einer Fritteuse."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import AirfryerCoordinator, FryerData


class AirfryerEntity(CoordinatorEntity[AirfryerCoordinator]):
    """Eine Entität, die zu genau einer Fritteuse gehört."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AirfryerCoordinator, cid: str, key: str) -> None:
        super().__init__(coordinator)
        self._cid = cid
        self._attr_unique_id = f"{cid}_{key}"
        info = self.fryer.info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, cid)},
            manufacturer=MANUFACTURER,
            model=str(info.get("deviceType") or "Heißluftfritteuse"),
            name=str(info.get("deviceName") or "Cosori Fritteuse"),
            sw_version=str(info["currentFirmVersion"]) if info.get("currentFirmVersion") else None,
        )

    @property
    def fryer(self) -> FryerData:
        return self.coordinator.fryers[self._cid]

    @property
    def available(self) -> bool:
        return super().available and self._cid in self.coordinator.fryers


@callback
def async_remove_stale(
    hass: HomeAssistant, entry: ConfigEntry, platform: str, keep: set[str | None]
) -> None:
    """Alte Entitäten löschen, die es nach einem Update nicht mehr gibt.

    Für Doofe: Sonst stünden z. B. nach der Umstellung auf Zonen die alten
    Sensoren als „nicht mehr bereitgestellt“ in der Liste herum.
    """
    coordinator: AirfryerCoordinator = entry.runtime_data
    if any(
        not f.online or (not f.raw_status and not f.raw_multi)
        for f in coordinator.fryers.values()
    ):
        # Ohne frische Daten wissen wir nicht sicher, was es gibt → nichts löschen
        return
    registry = er.async_get(hass)
    for reg in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg.domain == platform and reg.unique_id not in keep:
            registry.async_remove(reg.entity_id)
