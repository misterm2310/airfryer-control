"""Eingabefelder pro Zone: Temperatur und Garzeit.

Für Doofe: Die Felder zeigen, was die Fritteuse gerade eingestellt hat.
Änderst du einen Wert, während die Zone gart, schicken wir ihn hin – wie
die App mit „setTimeOrTemp“. Steht die Zone still, gibt's eine Meldung,
denn ohne Garvorgang gibt es nichts zu ändern (Starten ist ja gesperrt).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import CosoriError
from .const import DOMAIN
from .coordinator import CosoriCoordinator
from .entity import CosoriEntity, async_remove_stale
from .parser import ZoneState, zone_view, zones_for_device


@dataclass(frozen=True, kw_only=True)
class ZoneNumberDescription(NumberEntityDescription):
    """Ein Eingabefeld einer Zone."""

    value_fn: Callable[[ZoneState], float | None]


NUMBERS: tuple[ZoneNumberDescription, ...] = (
    ZoneNumberDescription(
        key="temperatur",
        translation_key="zone_temperatur",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=35,
        native_max_value=240,
        native_step=5,
        mode=NumberMode.BOX,
        value_fn=lambda z: z.set_temp,
    ),
    ZoneNumberDescription(
        key="garzeit",
        translation_key="zone_garzeit",
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_min_value=1,
        native_max_value=720,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda z: round(z.set_time_s / 60) if z.set_time_s else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CosoriCoordinator = entry.runtime_data
    entities: list[NumberEntity] = []
    for cid, fryer in coordinator.fryers.items():
        if fryer.model.startswith("CS"):
            continue
        for zone in zones_for_device(fryer.state, fryer.multizone):
            entities += [ZoneNumber(coordinator, cid, d, zone) for d in NUMBERS]
    async_remove_stale(hass, entry, "number", {e.unique_id for e in entities})
    async_add_entities(entities)


def build_change_payload(zs: ZoneState, temp: int | None, minutes: int | None) -> dict:
    """Befehl „Zeit oder Temperatur ändern“ – der andere Wert bleibt, wie er ist."""
    new_temp = temp if temp is not None else (zs.set_temp or 0)
    new_time = minutes * 60 if minutes is not None else (zs.set_time_s or 0)
    return {"cookSetTime": int(new_time), "cookSetTemp": int(new_temp), "chamber": zs.zone}


class ZoneNumber(CosoriEntity, NumberEntity):
    """Temperatur oder Garzeit einer Zone."""

    entity_description: ZoneNumberDescription

    def __init__(self, coordinator, cid, description: ZoneNumberDescription, zone: int) -> None:
        super().__init__(coordinator, cid, f"zone{zone}_{description.key}")
        self.entity_description = description
        self._zone = zone
        self._attr_translation_placeholders = {"zone": str(zone)}

    @property
    def native_value(self) -> float | None:
        zs = zone_view(self.fryer.state, self._zone)
        if not self.fryer.online or zs is None or not zs.active:
            return None
        return self.entity_description.value_fn(zs)

    async def async_set_native_value(self, value: float) -> None:
        zs = zone_view(self.fryer.state, self._zone)
        if zs is None or not zs.active:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="nur_beim_garen")
        if self.entity_description.key == "temperatur":
            payload = build_change_payload(zs, int(value), None)
        else:
            payload = build_change_payload(zs, None, int(value))
        try:
            await self.coordinator.api.bypass_v2(self.fryer.info, "setTimeOrTemp", payload)
        except CosoriError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="abgelehnt",
                translation_placeholders={"fehler": str(err)},
            ) from err
        await self.coordinator.async_request_fast_refresh()
