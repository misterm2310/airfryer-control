"""Gemeinsame Basis für alle Entitäten einer Fritteuse."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import CosoriCoordinator, FryerData


class CosoriEntity(CoordinatorEntity[CosoriCoordinator]):
    """Eine Entität, die zu genau einer Fritteuse gehört."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CosoriCoordinator, cid: str, key: str) -> None:
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
