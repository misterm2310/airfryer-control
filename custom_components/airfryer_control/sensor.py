"""Sensoren: Zustand, Restzeit, „Fertig um“, Temperaturen, Programm."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ALL_STATES, DOMAIN, STATE_OFFLINE, zone_label
from .coordinator import AirfryerCoordinator, FryerData
from .entity import AirfryerEntity, async_setup_dynamic
from .core.parser import ZoneState, reports_current_temp, zone_view, zones_for_device
from .core.util import redact


def _minutes(seconds: int | None) -> int | None:
    """Restzeit in ganzen Minuten (aufgerundet, wie die App)."""
    if seconds is None:
        return None
    return int(math.ceil(seconds / 60))


def _zone_finish(fryer: FryerData, zone: int) -> datetime | None:
    """„Fertig um“ einer Zone (None, wenn die Fritteuse die Zone gerade nicht meldet)."""
    return fryer.zone_finish_at.get(zone)


@dataclass(frozen=True, kw_only=True)
class FryerSensorDescription(SensorEntityDescription):
    """Sensor über die ganze Fritteuse."""

    value_fn: Callable[[FryerData], Any]


@dataclass(frozen=True, kw_only=True)
class ZoneSensorDescription(SensorEntityDescription):
    """Sensor über eine Zone."""

    value_fn: Callable[[FryerData, ZoneState | None, int], Any]


FRYER_SENSORS: tuple[FryerSensorDescription, ...] = (
    FryerSensorDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=ALL_STATES,
        value_fn=lambda f: f.state.status,
    ),
    FryerSensorDescription(
        key="restzeit",
        translation_key="restzeit",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda f: None if not f.online else _minutes(f.state.remaining_s),
    ),
    FryerSensorDescription(
        key="fertig_um",
        translation_key="fertig_um",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda f: f.finish_at,
    ),
)

SINGLE_SENSORS: tuple[ZoneSensorDescription, ...] = (
    ZoneSensorDescription(
        key="solltemperatur",
        translation_key="solltemperatur",
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda f, z, _n: z.set_temp if z else None,
    ),
    ZoneSensorDescription(
        key="temperatur",
        translation_key="temperatur",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda f, z, _n: z.current_temp if z else None,
    ),
    ZoneSensorDescription(
        key="programm",
        translation_key="programm",
        value_fn=lambda f, z, _n: z.mode if (z and z.busy) else None,
    ),
)

ZONE_SENSORS: tuple[ZoneSensorDescription, ...] = (
    ZoneSensorDescription(
        key="status",
        translation_key="zone_status",
        device_class=SensorDeviceClass.ENUM,
        options=ALL_STATES,
        value_fn=lambda f, z, _n: (
            STATE_OFFLINE if not f.online else (z.status if z else "bereit")
        ),
    ),
    ZoneSensorDescription(
        key="restzeit",
        translation_key="zone_restzeit",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda f, z, _n: _minutes(z.remaining_s) if (z and f.online) else None,
    ),
    ZoneSensorDescription(
        key="fertig_um",
        translation_key="zone_fertig_um",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda f, z, n: _zone_finish(f, n),
    ),
    ZoneSensorDescription(
        key="temperatur",
        translation_key="zone_temperatur",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda f, z, _n: z.current_temp if z else None,
    ),
    ZoneSensorDescription(
        key="programm",
        translation_key="zone_programm",
        value_fn=lambda f, z, _n: z.mode if (z and z.busy) else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_setup_dynamic(hass, entry, "sensor", async_add_entities, _build)


def _build(coordinator: AirfryerCoordinator) -> list[SensorEntity]:
    entities: list[SensorEntity] = []
    for cid, fryer in coordinator.fryers.items():
        entities += [FryerSensor(coordinator, cid, d) for d in FRYER_SENSORS]
        zones = zones_for_device(fryer.state, fryer.multizone)
        # Gemessene Temperatur nur, wenn die Fritteuse sie überhaupt schickt
        with_temp = reports_current_temp(fryer.state)
        if zones:
            for zone in zones:
                entities += [
                    ZoneSensor(coordinator, cid, d, zone)
                    for d in ZONE_SENSORS
                    if d.key != "temperatur" or with_temp
                ]
        else:
            entities += [
                ZoneSensor(coordinator, cid, d, 1, single=True)
                for d in SINGLE_SENSORS
                if d.key != "temperatur" or with_temp
            ]
        entities.append(RawDataSensor(coordinator, cid))
    return entities


class FryerSensor(AirfryerEntity, SensorEntity):
    """Sensor über die ganze Fritteuse."""

    entity_description: FryerSensorDescription

    def __init__(self, coordinator, cid, description: FryerSensorDescription) -> None:
        super().__init__(coordinator, cid, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.fryer)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key != "status":
            return None
        state = self.fryer.state
        attrs: dict[str, Any] = {"rohwert": state.status_raw}
        if self.fryer.last_error:
            attrs["letzter_fehler"] = self.fryer.last_error
        return attrs


class ZoneSensor(AirfryerEntity, SensorEntity):
    """Sensor für eine Zone (oder für die einzige Kammer)."""

    entity_description: ZoneSensorDescription

    def __init__(
        self, coordinator, cid, description: ZoneSensorDescription, zone: int, single: bool = False
    ) -> None:
        key = description.key if single else f"zone{zone}_{description.key}"
        super().__init__(coordinator, cid, key)
        self.entity_description = description
        self._zone = zone
        if not single:
            self._attr_translation_placeholders = {"zone": zone_label(coordinator.hass.config.language, zone)}

    @property
    def _zone_state(self) -> ZoneState | None:
        return zone_view(self.fryer.state, self._zone)

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.fryer, self._zone_state, self._zone)

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.entity_description.device_class == SensorDeviceClass.TEMPERATURE:
            if self.fryer.state.temp_unit == "fahrenheit":
                return UnitOfTemperature.FAHRENHEIT
            return UnitOfTemperature.CELSIUS
        return self.entity_description.native_unit_of_measurement

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key != "status":
            return None
        zs = self._zone_state
        return {"rohwert": zs.status_raw if zs else None}


class RawDataSensor(AirfryerEntity, SensorEntity):
    """Diagnose: was die Cloud zuletzt geschickt hat (ohne Konto-Daten).

    Hilft in der Beta beim Nachbessern: Wenn ein Wert falsch angezeigt wird,
    steht hier, was die Fritteuse wirklich gemeldet hat.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "rohdaten"

    def __init__(self, coordinator, cid) -> None:
        super().__init__(coordinator, cid, "rohdaten")

    @property
    def native_value(self) -> datetime | str | None:
        return "online" if self.fryer.online else "offline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        fryer = self.fryer
        return {
            "modell": fryer.model,
            "status": redact(fryer.raw_status),
            "mehrzonen_status": redact(fryer.raw_multi),
            "abgelehnte_abfragen": dict(fryer.method_errors),
            "letzter_fehler": fryer.last_error,
        }


__all__ = ["DOMAIN"]
