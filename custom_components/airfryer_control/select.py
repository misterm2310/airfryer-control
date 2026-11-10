"""Programm-Auswahl pro Zone (Heißluft, Braten, Backen …).

Für Doofe: Hier stellst du ein, was die Zone machen soll. Gewählt wird erst
mal nur in Home Assistant; an die Fritteuse geht es mit dem Schalter
„Zone n senden“. Beim Wechsel setzt die Auswahl Temperatur und Zeit auf die
Vorschlagswerte des Programms (die kannst du danach noch ändern).
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import zone_label
from .modelle import mode_default, modes_for
from .coordinator import AirfryerCoordinator, fryer_zones
from .entity import AirfryerEntity, async_setup_dynamic

from .senden import get_plan


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_setup_dynamic(hass, entry, "select", async_add_entities, _build)


def _build(coordinator: AirfryerCoordinator) -> list[SelectEntity]:
    entities: list[SelectEntity] = []
    for cid, fryer in coordinator.fryers.items():
        if fryer.model.startswith("CS"):
            continue
        for zone in fryer_zones(fryer):
            entities.append(ZoneProgramSelect(coordinator, cid, zone))
    return entities


class ZoneProgramSelect(AirfryerEntity, SelectEntity, RestoreEntity):
    """Programm, das beim Senden an die Zone geht."""

    _attr_translation_key = "zone_programm_waehlen"
    _attr_icon = "mdi:chef-hat"
    def __init__(self, coordinator, cid, zone: int) -> None:
        super().__init__(coordinator, cid, f"zone{zone}_programm_waehlen")
        self._zone = zone
        self._attr_translation_placeholders = {"zone": zone_label(coordinator.hass.config.language, zone)}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) and last.state in self.options:
            get_plan(self.coordinator, self._cid, self._zone)["mode"] = last.state

    @property
    def _model(self) -> str:
        fryer = self.coordinator.fryers.get(self._cid)
        return fryer.model if fryer else ""

    @property
    def options(self) -> list[str]:
        """Nur die Programme, die dieses Modell kann (Turbo Tower: auch Gären)."""
        return list(modes_for(self._model))

    @property
    def current_option(self) -> str:
        return get_plan(self.coordinator, self._cid, self._zone)["mode"]

    async def async_select_option(self, option: str) -> None:
        plan = get_plan(self.coordinator, self._cid, self._zone)
        plan["mode"] = option
        plan["temp"], plan["minuten"] = mode_default(option, self._model)
        # Temperatur- und Zeit-Felder der Zone mit aktualisieren
        self.coordinator.async_update_listeners()
        self.async_write_ha_state()
