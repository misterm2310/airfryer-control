"""Airfryer Control – Cosori-Heißluftfritteusen (z. B. Dual Blaze TwinFry) in Home Assistant.

Für Doofe: Beim Start meldet sich die Integration mit deinem VeSync-Konto an,
sucht deine Fritteusen und legt für jede ein Gerät mit Sensoren und Knöpfen an.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import UpdateFailed

from .core.api import AirfryerApi, AirfryerAuthError, AirfryerError
from .const import CONF_EMAIL, CONF_PASSWORD_HASH, CONF_REGION, CONF_TERMINAL_ID, DOMAIN
from .coordinator import AirfryerCoordinator
from .services import async_register_services

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type AirfryerConfigEntry = ConfigEntry[AirfryerCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Dienste anmelden (einmal für alle Konten)."""
    async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: AirfryerConfigEntry) -> bool:
    api = AirfryerApi(
        async_get_clientsession(hass),
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD_HASH],
        entry.data[CONF_REGION],
        entry.data[CONF_TERMINAL_ID],
        time_zone=str(hass.config.time_zone or "Europe/Berlin"),
    )
    try:
        await api.login()
    except AirfryerAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except AirfryerError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = AirfryerCoordinator(hass, entry, api)
    try:
        await coordinator.async_load_devices()
    except UpdateFailed as err:
        raise ConfigEntryNotReady(str(err)) from err
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: AirfryerConfigEntry) -> None:
    """Optionen geändert → neu laden."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: AirfryerConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
