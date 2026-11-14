"""Eingabefelder pro Zone: Temperatur und Garzeit.

Für Doofe: Die Felder merken sich, was du für die Zone einstellen willst.
Gesendet wird erst mit dem Schalter „Zone n senden“. Gart die Zone schon,
schicken wir die Änderung sofort hin – wie die App mit „setTimeOrTemp“.
Ausnahme TwinFry: Die lehnt das beim Garen ab (Code 11030000). Dort gibt es
eine klare Meldung „bitte am Gerät ändern“ und das Feld bleibt, wie es war.
"""

from __future__ import annotations

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
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .core.api import AirfryerError
from .const import DOMAIN, zone_label
from .coordinator import AirfryerCoordinator, fryer_zones
from .entity import AirfryerEntity, async_setup_dynamic
from .core.parser import ZoneState, zone_view
from .modelle import change_while_cooking, temp_step
from .senden import clamp_minutes, clamp_temp, get_plan, temp_limits, time_limits


@dataclass(frozen=True, kw_only=True)
class ZoneNumberDescription(NumberEntityDescription):
    """Ein Eingabefeld einer Zone."""

    plan_key: str


NUMBERS: tuple[ZoneNumberDescription, ...] = (
    ZoneNumberDescription(
        key="temperatur",
        translation_key="zone_temperatur",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=30,
        native_max_value=240,
        native_step=5,
        mode=NumberMode.BOX,
        plan_key="temp",
    ),
    ZoneNumberDescription(
        key="garzeit",
        translation_key="zone_garzeit",
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_min_value=1,
        native_max_value=2880,
        native_step=1,
        mode=NumberMode.BOX,
        plan_key="minuten",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_setup_dynamic(hass, entry, "number", async_add_entities, _build)


def _build(coordinator: AirfryerCoordinator) -> list[NumberEntity]:
    entities: list[NumberEntity] = []
    for cid, fryer in coordinator.fryers.items():
        if fryer.model.startswith("CS"):
            continue
        for zone in fryer_zones(fryer):
            entities += [ZoneNumber(coordinator, cid, d, zone) for d in NUMBERS]
    return entities


def build_change_payload(zs: ZoneState, temp: int | None, minutes: int | None) -> dict:
    """Befehl „Zeit oder Temperatur ändern“ – der andere Wert bleibt, wie er ist."""
    new_temp = temp if temp is not None else (zs.set_temp or 0)
    new_time = minutes * 60 if minutes is not None else (zs.set_time_s or 0)
    return {"cookSetTime": int(new_time), "cookSetTemp": int(new_temp), "chamber": zs.zone}


class ZoneNumber(AirfryerEntity, NumberEntity, RestoreEntity):
    """Temperatur oder Garzeit, die für eine Zone gesendet wird."""

    entity_description: ZoneNumberDescription

    def __init__(self, coordinator, cid, description: ZoneNumberDescription, zone: int) -> None:
        super().__init__(coordinator, cid, f"zone{zone}_{description.key}")
        self.entity_description = description
        self._zone = zone
        self._attr_translation_placeholders = {"zone": zone_label(coordinator.hass.config.language, zone)}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state not in ("unknown", "unavailable"):
            try:
                get_plan(self.coordinator, self._cid, self._zone)[
                    self.entity_description.plan_key
                ] = int(float(last.state))
            except ValueError:
                pass

    @property
    def _model(self) -> str:
        fryer = self.coordinator.fryers.get(self._cid)
        return fryer.model if fryer else ""

    @property
    def native_min_value(self) -> float:
        mode = get_plan(self.coordinator, self._cid, self._zone)["mode"]
        if self.entity_description.key == "temperatur":
            return temp_limits(mode, self._model)[0]
        return time_limits(mode, self._model)[0]

    @property
    def native_max_value(self) -> float:
        mode = get_plan(self.coordinator, self._cid, self._zone)["mode"]
        if self.entity_description.key == "temperatur":
            return temp_limits(mode, self._model)[1]
        return time_limits(mode, self._model)[1]

    @property
    def native_step(self) -> float:
        """Gären an der Turbo Tower: 1 °C, sonst 5 °C (Zeit: 1 Minute)."""
        if self.entity_description.key == "temperatur":
            return temp_step(get_plan(self.coordinator, self._cid, self._zone)["mode"], self._model)
        return 1

    @property
    def native_value(self) -> float:
        return get_plan(self.coordinator, self._cid, self._zone)[self.entity_description.plan_key]

    async def async_set_native_value(self, value: float) -> None:
        plan = get_plan(self.coordinator, self._cid, self._zone)
        zs_now = zone_view(self.fryer.state, self._zone)
        if zs_now is not None and zs_now.active and not change_while_cooking(self._model):
            # TwinFry: beim Garen nimmt sie keine neue Zeit/Temperatur an – lieber ehrlich sagen
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="nicht_beim_garen",
            )
        if self.entity_description.key == "temperatur":
            value = clamp_temp(plan["mode"], int(value), self._model)
        else:
            value = clamp_minutes(plan["mode"], int(value), self._model)
        plan[self.entity_description.plan_key] = int(value)
        self.async_write_ha_state()
        zs = zone_view(self.fryer.state, self._zone)
        if zs is None or not zs.active:
            return  # nur merken – gesendet wird mit dem Schalter
        if self.entity_description.key == "temperatur":
            payload = build_change_payload(zs, int(value), None)
        else:
            payload = build_change_payload(zs, None, int(value))
        try:
            await self.coordinator.api.bypass_v2(self.fryer.info, "setTimeOrTemp", payload)
        except AirfryerError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="abgelehnt",
                translation_placeholders={"fehler": str(err)},
            ) from err
        await self.coordinator.async_request_fast_refresh()
